import csv
import json
import math
import os
import random
import statistics

import simpy

# ---------------------------------------------------------------------------
# 1. DATOS OBSERVADOS EN CAMPO
# ---------------------------------------------------------------------------
# Llegadas en minutos desde la 1:27 (1:27, 1:28, 1:33, 1:33, 1:33, 1:35, ...)
LLEGADAS = [0, 1, 6, 6, 6, 8, 9, 9, 9, 10, 13, 13, 16, 18]
# Duración de la atención = hora final - hora de inicio (12 registros completos)
DURACIONES = [1, 10, 0, 1, 0, 2, 1, 0, 4, 3, 4, 5]
# Tasa de llegada: 13 intervalos entre 14 personas en 18 minutos
TASA_LLEGADA = 13 / 18

# ---------------------------------------------------------------------------
# 2. PARÁMETROS DEL EXPERIMENTO
# ---------------------------------------------------------------------------
REPLICAS = 10_000
SEMILLA = 2026

# (clave, descripción, número de ventanillas, tipo de llegadas)
ESCENARIOS = [
    ("E1", "Base: 2 ventanillas (operación actual)", 2, "observadas"),
    ("E2", "Alternativa 1: 1 ventanilla", 1, "observadas"),
    ("E3", "Alternativa 2: 3 ventanillas", 3, "observadas"),
    ("E4", "Alternativa 3: 2 ventanillas, llegadas aleatorias", 2, "aleatorias"),
]

# ---------------------------------------------------------------------------
# 3. NÚMEROS ALEATORIOS (método de la transformada inversa, con U ~ U(0,1))
# ---------------------------------------------------------------------------
def generar_servicio(rng):
    """Elige una de las 12 duraciones observadas, cada una con probabilidad 1/12."""
    u = rng.random()
    return DURACIONES[int(u * len(DURACIONES))]

def generar_entre_llegadas(rng):
    """Tiempo entre llegadas exponencial: X = -ln(1 - U) / tasa."""
    u = rng.random()
    return -math.log(1 - u) / TASA_LLEGADA

# ---------------------------------------------------------------------------
# 4. MODELO SIMPY
# ---------------------------------------------------------------------------
def persona(env, ventanillas, rng, datos):
    """Una persona: llega, espera una ventanilla, es atendida y se va."""
    llegada = env.now
    with ventanillas.request() as pedir:
        yield pedir                                  # espera en la fila común
        datos["esperas"].append(env.now - llegada)   # empieza la atención
        servicio = generar_servicio(rng)
        yield env.timeout(servicio)                  # dura la atención
        datos["ocupado"] += servicio                 # termina el servicio

def llegadas_observadas(env, ventanillas, rng, datos):
    """Crea a las 14 personas en los minutos en que llegaron en la observación."""
    for t in LLEGADAS:
        yield env.timeout(t - env.now)
        env.process(persona(env, ventanillas, rng, datos))

def llegadas_aleatorias(env, ventanillas, rng, datos):
    """Crea a 14 personas: la primera en t = 0 y las demás con tiempos exponenciales."""
    env.process(persona(env, ventanillas, rng, datos))
    for _ in range(len(LLEGADAS) - 1):
        yield env.timeout(generar_entre_llegadas(rng))
        env.process(persona(env, ventanillas, rng, datos))

def correr_replica(semilla, n_ventanillas, tipo):
    """Simula una réplica y regresa sus indicadores y las esperas de cada persona."""
    rng = random.Random(semilla)
    env = simpy.Environment()
    ventanillas = simpy.Resource(env, capacity=n_ventanillas)
    datos = {"esperas": [], "ocupado": 0.0}

    llegadas = llegadas_observadas if tipo == "observadas" else llegadas_aleatorias
    env.process(llegadas(env, ventanillas, rng, datos))
    env.run()                                        # termina al atender a todos

    esperas = datos["esperas"]
    return {
        "espera_media": statistics.fmean(esperas),
        "espera_max": max(esperas),
        "pct_espera": 100 * sum(e > 0 for e in esperas) / len(esperas),
        "utilizacion": 100 * datos["ocupado"] / (n_ventanillas * env.now),
        "tiempo_total": env.now,
    }, esperas

# ---------------------------------------------------------------------------
# 5. EXPERIMENTOS
# ---------------------------------------------------------------------------
def ic95(valores):
    """Semiancho del intervalo de confianza del 95 % para la media."""
    return 1.96 * statistics.stdev(valores) / math.sqrt(len(valores))

def correr_escenario(clave, nombre, n_ventanillas, tipo):
    """Corre todas las réplicas de un escenario y las resume."""
    replicas, todas_las_esperas = [], []
    for r in range(REPLICAS):
        resultado, esperas = correr_replica(SEMILLA + r, n_ventanillas, tipo)
        replicas.append(resultado)
        todas_las_esperas += esperas

    resumen = {"clave": clave, "escenario": nombre, "ventanillas": n_ventanillas, "llegadas": tipo}
    for indicador in ("espera_media", "espera_max", "pct_espera", "utilizacion", "tiempo_total"):
        valores = [x[indicador] for x in replicas]
        resumen[indicador] = statistics.fmean(valores)
        resumen[indicador + "_ic"] = ic95(valores)
    todas_las_esperas.sort()
    resumen["espera_p90"] = todas_las_esperas[int(0.9 * (len(todas_las_esperas) - 1))]
    resumen["medias_replicas"] = [x["espera_media"] for x in replicas]
    return resumen

def replicas_necesarias(piloto=1000, semiancho=0.10):
    """Réplicas necesarias para que el IC 95 % tenga semiancho <= 0.10 min: n = (1.96 s / h)^2."""
    filas = []
    for clave, nombre, n_vent, tipo in ESCENARIOS:
        medias = [correr_replica(SEMILLA + r, n_vent, tipo)[0]["espera_media"] for r in range(piloto)]
        s = statistics.stdev(medias)
        filas.append((clave, s, math.ceil((1.96 * s / semiancho) ** 2), 1.96 * s / math.sqrt(REPLICAS)))
    return filas

def validar_generadores(n=200_000):
    """Comprueba que los números aleatorios generados se parecen a los datos observados."""
    rng = random.Random(SEMILLA)
    servicios = [generar_servicio(rng) for _ in range(n)]
    entre = [generar_entre_llegadas(rng) for _ in range(n)]
    print(f"Servicio: media generada {statistics.fmean(servicios):.3f} vs observada {statistics.fmean(DURACIONES):.3f}")
    print(f"Servicio: P(10 min) generada {servicios.count(10) / n:.4f} vs esperada {1 / 12:.4f}")
    print(f"Servicio: P(0 min)  generada {servicios.count(0) / n:.4f} vs esperada {DURACIONES.count(0) / 12:.4f}")
    print(f"Entre llegadas: media generada {statistics.fmean(entre):.3f} vs esperada {1 / TASA_LLEGADA:.3f} min")

def main(carpeta="resultados"):
    os.makedirs(carpeta, exist_ok=True)
    print("SIMULACIÓN DE LA CAFETERÍA DEL ITSVA (SimPy) - Actividad 2")
    print("Llegadas observadas (min desde 1:27):", LLEGADAS)
    print("Duraciones de atención (min):        ", DURACIONES)
    print(f"Media de duraciones: {statistics.fmean(DURACIONES):.2f} min | tasa de llegada: {TASA_LLEGADA:.3f} personas/min")

    print("\n--- VALIDACIÓN DE GENERADORES (200,000 valores) ---")
    validar_generadores()

    print("\n--- NÚMERO DE RÉPLICAS (objetivo: semiancho IC 95 % <= 0.10 min) ---")
    print(f"{'Esc.':<5}{'Desv. est. entre réplicas':>27}{'Réplicas requeridas':>22}{'Semiancho con 10,000':>22}")
    for clave, s, n, h in replicas_necesarias():
        print(f"{clave:<5}{s:>27.3f}{n:>22,}{h:>22.3f}")

    resultados = [correr_escenario(*e) for e in ESCENARIOS]
    print(f"\n--- RESULTADOS ({REPLICAS:,} réplicas independientes por escenario) ---")
    print(f"{'Esc.':<5}{'Vent.':>6}{'Espera media (min)':>21}{'P90':>7}{'Máx.':>7}{'% espera':>10}{'Utiliz. %':>11}{'T. total':>10}")
    for r in resultados:
        print(f"{r['clave']:<5}{r['ventanillas']:>6}{r['espera_media']:>14.2f} ±{r['espera_media_ic']:.2f}"
              f"{r['espera_p90']:>7.1f}{r['espera_max']:>7.2f}{r['pct_espera']:>10.1f}"
              f"{r['utilizacion']:>11.1f}{r['tiempo_total']:>10.1f}")

    # Comparación contra el escenario base, réplica por réplica (mismas semillas)
    base = resultados[0]
    print("\n--- COMPARACIÓN CONTRA EL ESCENARIO BASE (réplicas pareadas) ---")
    for r in resultados[1:]:
        dif = [a - b for a, b in zip(r["medias_replicas"], base["medias_replicas"])]
        cambio = 100 * (r["espera_media"] / base["espera_media"] - 1)
        print(f"{r['clave']} - E1: {statistics.fmean(dif):+.2f} ± {ic95(dif):.2f} min ({cambio:+.1f} %)")

    # Guardar resultados
    with open(os.path.join(carpeta, "tabla_comparativa.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Escenario", "Descripción", "Ventanillas", "Llegadas", "Espera media (min)", "IC95 ±",
                    "P90 espera (min)", "Espera máx. prom. (min)", "% que espera", "Utilización (%)",
                    "Tiempo total (min)"])
        for r in resultados:
            w.writerow([r["clave"], r["escenario"], r["ventanillas"], r["llegadas"],
                        round(r["espera_media"], 3), round(r["espera_media_ic"], 3), round(r["espera_p90"], 1),
                        round(r["espera_max"], 2), round(r["pct_espera"], 1), round(r["utilizacion"], 1),
                        round(r["tiempo_total"], 1)])
    with open(os.path.join(carpeta, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump({"escenarios": resultados}, f)
    print(f"\nArchivos generados en '{carpeta}/': tabla_comparativa.csv, resultados.json")

if __name__ == "__main__":
    main()

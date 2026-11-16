# simulacion-cafeteria-itsva
Simulación de eventos discretos en Python (SimPy) del proceso de atención en la cafetería del ITSVA (A2T4)
# Simulación de Atención en la Cafetería del ITSVA (A2T4)

Programa informático de simulación de eventos discretos desarrollado en **Python** con la biblioteca **SimPy** para analizar el impacto del número de ventanillas en los tiempos de espera de la cafetería del Instituto Tecnológico Superior de Valladolid (ITSVA)[cite: 3, 9].

## Integrantes
* De la Cruz Ojeda Aaron
* Gonzalez Pool Jared Arturo

## Asignatura
* **Materia:** Simulación (Semestre 2026B)
* **Docente:** ISC. Luis Adrian Balam Espadas
* **Actividad:** Programa Informático Tema 4 (A2T4)

## Descripción del Modelo
El modelo reproduce el flujo de llegada y atención de 14 personas observadas en campo mediante el método de la transformada inversa y 10,000 réplicas independientes por escenario
* **E1 (Base):** 2 ventanillas con llegadas observadas
* **E2 (Alternativa 1):** 1 ventanilla con llegadas observadas
* **E3 (Alternativa 2):** 3 ventanillas con llegadas observadas
* **E4 (Alternativa 3):** 2 ventanillas con llegadas exponenciales aleatorias

## Contenido del Repositorio
* `simulacion_cafeteria_a2.py`: Código fuente principal de la simulación
* `resultados/tabla_comparativa`: Resumen estadístico de los 4 escenarios
* `Programa Informático Tema 4 DE LA CRUZ OJEDA AARON.pdf`: Documento técnico con el análisis, gráficas y respuesta a la pregunta de investigación

## Requisitos y Ejecución
1. Instalar la dependencia requerida:
   ```bash
   pip install simpy
   * **Python:** Versión 3.8 o superior (se utiliza `statistics.fmean`, disponible a partir de Python 3.8).

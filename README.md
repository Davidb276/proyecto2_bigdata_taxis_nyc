# Proyecto 2 – Big Data: Análisis de viajes de taxis amarillos de Nueva York

Universidad EAFIT · SI3007 Sistemas Distribuidos / ST0263 Tópicos Especiales en Telemática · 2026-2

**Integrantes:** David Bermudez, Samuel Sierra, Alejandro Flores

Pipeline de datos en AWS (cuenta AWS Academy, región us-east-1): fuentes (RDS MariaDB, EC2, URL) → Data Lake en S3 → preparación con Glue/Spark → catálogo → consultas con Athena y PySpark → visualización.

## Estructura del repositorio (un directorio por punto del enunciado)

| Directorio | Punto | Estado |
|---|---|---|
| `01_caso_estudio/` | 1. Caso de estudio y preguntas de negocio | Listo |
| `02_fuentes/` | 2. Fuentes: RDS MariaDB, archivos en EC2, URLs | Listo (ejecutado en AWS) |
| `03_ingesta/` | 3. Ingesta automática al Data Lake (S3) | Listo (ejecutado en AWS) |
| `04_preparacion/` | 4. Preparación raw → trusted (Glue + Spark) | Listo (ejecutado en AWS) |
| `05_catalogo/` | 5. Catalogación (Glue y EMR/Hive) | Listo (ejecutado en AWS) |
| `06_consultas_sql/` | 6. Consultas SQL (Athena, Hive, SparkSQL) | Athena listo (ejecutado en AWS); Hive y SparkSQL pendientes |
| `07_pyspark/` | 7. Analítica con PySpark | Código listo (sin ejecutar en AWS) |
| `08_visualizacion/` | 8. Visualización y app Streamlit con API Gateway | Código listo (sin ejecutar en AWS) |

## Fuente de los datos

NYC Taxi & Limousine Commission (TLC), *TLC Trip Record Data*:
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Diccionario de datos (taxis amarillos):
https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf

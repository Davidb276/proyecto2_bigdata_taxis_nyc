# Punto 4 – Preparación de datos: raw → trusted (AWS Glue + Apache Spark)

El script [glue_raw_a_trusted.py](glue_raw_a_trusted.py) lee los datos de la zona **raw** del Data Lake, los limpia con Spark y escribe la zona **trusted** en Parquet.

## Qué hace el script

1. Lee por separado octubre (`raw/ec2_files/`), noviembre (`raw/url/`) y la muestra de diciembre (`raw/rds/viajes_muestra/`).
2. Renombra las columnas al contrato de datos (ver `01_caso_estudio/README.md`) y fija los tipos.
3. Une las tres fuentes con `unionByName`.
4. Imprime un informe de calidad por regla de limpieza.
5. Filtra las filas que incumplen las reglas y escribe `trusted/viajes/` y `trusted/zonas/` en Parquet.

Cada carpeta de origen debe contener un solo archivo; si se agregan más, se mezclarían.

## Job en AWS Glue

| Dato | Valor |
|---|---|
| Nombre | `raw_a_trusted_taxis` |
| Tipo | Glue ETL (Spark), creado con Script editor |
| Versión de Glue | 6.0 |
| Rol | `LabRole` |
| Workers | `G.1X`, 2 workers |
| Parámetro del job | `--BUCKET` = nombre del bucket del Data Lake |

## Resultado de la ejecución (18-nov-2026)

El job terminó en estado **Succeeded** en 2 min 41 s, sin reintentos. El informe de calidad (CloudWatch, grupo `/aws-glue/jobs/output`) fue:

| Regla / total | Filas |
|---|---|
| Filas raw (oct + nov + muestra dic) | 8.810.143 |
| `fecha_bajada_anterior_a_recogida` | 1.437 |
| `distancia_no_positiva_o_nula` | 242.071 |
| `total_negativo_o_nulo` | 237.908 |
| `recogida_fuera_de_rango` | 13 |
| `fechas_nulas` | 0 |
| **Filas trusted** | **8.348.220** (descartadas: 461.923, ≈5,2 %) |

Una fila puede incumplir varias reglas a la vez, por eso la suma de los conteos por regla es mayor que las filas descartadas. Las reglas de limpieza son supuestos del equipo, no una norma oficial.

## Evidencias

Capturas en [`evidencias/`](evidencias/): detalles del job, pestaña Runs con el estado Succeeded, informe de calidad en CloudWatch y carpetas `trusted/viajes/` y `trusted/zonas/` en S3.

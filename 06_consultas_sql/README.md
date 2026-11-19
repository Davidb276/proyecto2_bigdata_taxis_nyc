# Punto 6 – Consultas SQL analíticas (Athena)

Este punto responde las 7 preguntas de negocio del punto 1 con SQL sobre las tablas de la zona *trusted* del Data Lake.

Archivo: [`consultas_athena.sql`](consultas_athena.sql)

## Requisitos previos

Las consultas dependen de los puntos 3, 4 y 5:

1. Los datos limpios (zona trusted) deben estar en S3 en formato Parquet.
2. Las tablas deben estar catalogadas en el Glue Data Catalog como `taxis_trusted.viajes` y `taxis_trusted.zonas`, con las columnas descritas en el contrato de datos (`01_caso_estudio/README.md`).

Si el equipo que hace el punto 4 usa otros nombres de base de datos, tabla o columna, hay que reemplazarlos en el archivo SQL (buscar y reemplazar).

## Cómo ejecutarlas

1. Consola de AWS → **Athena** → *Query editor*.
2. Si Athena lo pide, configura una ubicación de resultados de consultas (un bucket de S3 del proyecto).
3. En el panel izquierdo selecciona la base de datos **`taxis_trusted`**.
4. Copia y ejecuta **una consulta a la vez**.
5. 📸 *Evidencia por consulta:* pantallazo que muestre la consulta y su resultado.

## Orden recomendado

| Orden | Consulta | Pregunta |
|---|---|---|
| 0 | Verificación previa | Confirma que hay datos y el rango de fechas |
| 1 | Top 10 zonas por mes | P1 |
| 2 | Día de la semana y hora | P2 |
| 3 | 3a y 3b | P3 |
| 4 | Distrito de recogida | P4 |
| 5 | 5a y 5b | P5 |
| 6 | Promedios por mes | P6 |
| 7 | 7a y 7b | P7 |

## Cómo documentar cada consulta en el informe

Para cada pregunta, en el documento Word escribe:
1. La pregunta de negocio.
2. La consulta SQL (extracto).
3. El pantallazo del resultado.
4. Una o dos frases con la **interpretación** de lo que muestra el resultado (esto lo escriben ustedes viendo los números reales; no se deben inventar).

## Observaciones

- **Diciembre es una muestra** (ver punto 1). En la pregunta 6 solo se deben comparar promedios, no el número de viajes.
- Las funciones `date_format`, `day_of_week`, `hour` y `date_diff` son de Athena (motor Trino/Presto).
- **Estado:** las consultas de Athena (verificación previa y preguntas 1 a 7) se ejecutaron el 18-nov-2026; las capturas están en `evidencias/`.
- **Pendiente:** versiones de SparkSQL y Hive sobre EMR (también pedidas en el enunciado para este punto).

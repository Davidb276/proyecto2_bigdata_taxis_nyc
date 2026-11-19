# Punto 7 – Analítica descriptiva con PySpark

[`pyspark_analitica.py`](pyspark_analitica.py) es un job de AWS Glue (PySpark, API de DataFrames) que lee `trusted/viajes` y `trusted/zonas`, responde las 7 preguntas de negocio del punto 1 y agrega estadísticas descriptivas (`summary`). Cada resultado se imprime en el log y se guarda como CSV en `s3://<BUCKET>/refined/resultados/<nombre>/` (los lee la app del punto 8).

Las consultas equivalen a las del punto 6 (Athena): se pueden comparar los resultados de ambos puntos.

> **Estado:** probado solo en local (Spark 3.5.1, datos sintéticos de 5.000 filas; los promedios mensuales y un grupo de día/hora coincidieron con un cálculo independiente en pandas). **No se ha ejecutado en AWS Glue ni con los datos reales.**

## Ejecutar en Glue
1. Glue → *ETL jobs* → *Script editor* → Spark → *Start fresh*. Pega el contenido de `pyspark_analitica.py`.
2. *Job details*: nombre `pyspark_analitica_taxis`, rol `LabRole`, mismas versión de Glue y workers que el job del punto 4 (`G.1X`, 2 workers), timeout 30 min.
3. *Advanced properties → Job parameters*: clave `--BUCKET`, valor `taxis-nyc-datalake-david-2026`.
4. *Save* → *Run*. Espera **Succeeded**.
5. Resultados impresos: CloudWatch → grupo `/aws-glue/jobs/output` → flujo que empieza con el Id de la corrida.
6. Archivos: S3 → `refined/resultados/` (12 carpetas, cada una con un `.csv`).

## Salidas
`00_verificacion`, `p1_top10_zonas_por_mes`, `p2_dia_semana_hora`, `p3a_metodos_pago`, `p3b_propinas_tarjeta`, `p4_distritos`, `p5a_pares_frecuentes`, `p5b_pares_ingresos`, `p6_promedios_mensuales`, `p7a_congestion_mensual`, `p7b_congestion_distritos`, `x1_estadisticas_descriptivas`.

## Notas
- `dia_semana`: 1 = lunes … 7 = domingo (igual que en Athena). `duracion_min` son minutos completos.
- Diciembre es una muestra: se comparan promedios, no volúmenes.
- `summary` calcula percentiles de forma aproximada.

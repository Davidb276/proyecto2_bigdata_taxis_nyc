"""
Punto 4 - Preparación de datos: zona RAW -> zona TRUSTED (AWS Glue + Apache Spark).

Lee de s3://<BUCKET>/raw/ :
  - ec2_files/  (octubre 2025, Parquet con nombres originales de la TLC)
  - url/        (noviembre 2025, idem)
  - rds/viajes_muestra/            (muestra de diciembre 2025, ya con nombres del contrato)
  - rds/zonas/
y escribe en s3://<BUCKET>/trusted/ :
  - viajes/  (Parquet, esquema del contrato de datos del punto 1)
  - zonas/   (Parquet)

Parámetros del job (Glue): --BUCKET <nombre-del-bucket>
También corre fuera de Glue con:  spark-submit glue_raw_a_trusted.py --BUCKET <bucket>
"""
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import IntegerType, DoubleType, StringType, TimestampType

# --- parámetros -------------------------------------------------------------
try:  # dentro de AWS Glue
    from awsglue.utils import getResolvedOptions
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from pyspark.context import SparkContext
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "BUCKET"])
    sc = SparkContext.getOrCreate()
    glue_ctx = GlueContext(sc)
    spark = glue_ctx.spark_session
    job = Job(glue_ctx)
    job.init(args["JOB_NAME"], args)
except ImportError:  # ejecución local
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--BUCKET", required=True, help="bucket o ruta base (p. ej. s3://x o /tmp/lago)")
    args = vars(ap.parse_args())
    spark = SparkSession.builder.appName("raw_a_trusted").getOrCreate()
    job = None

BASE = args["BUCKET"] if "://" in args["BUCKET"] or args["BUCKET"].startswith("/") else f"s3://{args['BUCKET']}"
RAW, TRUSTED = f"{BASE}/raw", f"{BASE}/trusted"

# --- contrato de datos (01_caso_estudio/README.md) -----------------------------
# nombre en minúsculas del archivo original -> nombre en el contrato
RENOMBRAR = {
    "vendorid": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "ratecodeid": "ratecode_id",
    "pulocationid": "pu_location_id",
    "dolocationid": "do_location_id",
}
ESQUEMA = [  # (columna, tipo) en el orden del contrato
    ("vendor_id", IntegerType()), ("pickup_datetime", TimestampType()), ("dropoff_datetime", TimestampType()),
    ("passenger_count", IntegerType()), ("trip_distance", DoubleType()), ("ratecode_id", IntegerType()),
    ("store_and_fwd_flag", StringType()), ("pu_location_id", IntegerType()), ("do_location_id", IntegerType()),
    ("payment_type", IntegerType()), ("fare_amount", DoubleType()), ("extra", DoubleType()),
    ("mta_tax", DoubleType()), ("tip_amount", DoubleType()), ("tolls_amount", DoubleType()),
    ("improvement_surcharge", DoubleType()), ("total_amount", DoubleType()),
    ("congestion_surcharge", DoubleType()), ("airport_fee", DoubleType()), ("cbd_congestion_fee", DoubleType()),
]


def normalizar(df, etiqueta):
    """Pone nombres en minúsculas, aplica el contrato y fija los tipos (los meses pueden traer tipos distintos)."""
    for c in df.columns:
        df = df.withColumnRenamed(c, RENOMBRAR.get(c.lower(), c.lower()))
    columnas = []
    for nombre, tipo in ESQUEMA:
        if nombre in df.columns:
            columnas.append(F.col(nombre).cast(tipo).alias(nombre))
        else:
            print(f"AVISO [{etiqueta}]: falta la columna {nombre}; se rellena con nulos")
            columnas.append(F.lit(None).cast(tipo).alias(nombre))
    return df.select(*columnas)


# --- 1. leer raw -------------------------------------------------------------------
oct_df = normalizar(spark.read.parquet(f"{RAW}/ec2_files/"), "oct (EC2)")
nov_df = normalizar(spark.read.parquet(f"{RAW}/url/"), "nov (URL)")
dic_df = normalizar(spark.read.parquet(f"{RAW}/rds/viajes_muestra/"), "dic (RDS)")

viajes = oct_df.unionByName(nov_df).unionByName(dic_df)
n_raw = viajes.count()
print(f"Filas raw (oct + nov + muestra dic): {n_raw}")

# --- 2. limpieza (reglas sugeridas del contrato; ajustar tras inspeccionar los datos) ---
reglas = [
    ("fecha_bajada_anterior_a_recogida", F.col("dropoff_datetime") < F.col("pickup_datetime")),
    ("distancia_no_positiva_o_nula", ~(F.col("trip_distance") > 0)),
    ("total_negativo_o_nulo", ~(F.col("total_amount") >= 0)),
    ("recogida_fuera_de_rango", ~((F.col("pickup_datetime") >= "2025-10-01") & (F.col("pickup_datetime") < "2026-01-01"))),
    ("fechas_nulas", F.col("pickup_datetime").isNull() | F.col("dropoff_datetime").isNull()),
]
# Informe de calidad: cuántas filas incumple cada regla (una fila puede incumplir varias)
print("=== Informe de calidad (filas que incumplen cada regla) ===")
for nombre, cond in reglas:
    print(f"{nombre}: {viajes.filter(cond).count()}")

cond_malo = reglas[0][1]
for _, c in reglas[1:]:
    cond_malo = cond_malo | c
# coalesce: si una condición da nulo, la fila se descarta en vez de colarse
viajes_ok = viajes.filter(~F.coalesce(cond_malo, F.lit(True)))
n_ok = viajes_ok.count()
print(f"Filas trusted: {n_ok}  (descartadas: {n_raw - n_ok})")

# --- 3. zonas ------------------------------------------------------------------------
zonas = (spark.read.parquet(f"{RAW}/rds/zonas/")
         .select(F.col("location_id").cast(IntegerType()), F.col("borough").cast(StringType()),
                 F.col("zone").cast(StringType()), F.col("service_zone").cast(StringType())))

# --- 4. escribir trusted -----------------------------------------------------------------
viajes_ok.write.mode("overwrite").parquet(f"{TRUSTED}/viajes/")
zonas.write.mode("overwrite").parquet(f"{TRUSTED}/zonas/")
print(f"Escrito: {TRUSTED}/viajes/ y {TRUSTED}/zonas/")

if job:
    job.commit()

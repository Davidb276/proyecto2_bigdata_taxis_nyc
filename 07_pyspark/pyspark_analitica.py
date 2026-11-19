"""
Punto 7 - Analítica descriptiva con Spark en Python (PySpark), API de DataFrames.

Lee la zona TRUSTED (s3://<BUCKET>/trusted/viajes y trusted/zonas), responde las 7 preguntas de negocio
del punto 1 y agrega estadísticas descriptivas generales. Cada resultado:
  - se imprime en el log (CloudWatch, grupo /aws-glue/jobs/output)  -> evidencia para el informe
  - se guarda como un CSV (con encabezado) en s3://<BUCKET>/refined/resultados/<nombre>/  -> lo lee la app del punto 8

Parámetro del job (Glue): --BUCKET <nombre-del-bucket>
Ejecución local:  spark-submit pyspark_analitica.py --BUCKET /ruta/a/un/lago/local
"""
import sys

from pyspark.sql import SparkSession, Window, functions as F

try:  # dentro de AWS Glue
    from awsglue.utils import getResolvedOptions
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from pyspark.context import SparkContext
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "BUCKET"])
    glue_ctx = GlueContext(SparkContext.getOrCreate())
    spark = glue_ctx.spark_session
    job = Job(glue_ctx)
    job.init(args["JOB_NAME"], args)
except ImportError:  # ejecución local
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--BUCKET", required=True)
    args = vars(ap.parse_args())
    spark = SparkSession.builder.appName("pyspark_analitica").getOrCreate()
    job = None

BASE = args["BUCKET"] if "://" in args["BUCKET"] or args["BUCKET"].startswith("/") else f"s3://{args['BUCKET']}"
TRUSTED, SALIDA = f"{BASE}/trusted", f"{BASE}/refined/resultados"

viajes = spark.read.parquet(f"{TRUSTED}/viajes/")
zonas = spark.read.parquet(f"{TRUSTED}/zonas/")

# Columnas derivadas usadas en varias preguntas
viajes = (viajes
          .withColumn("mes", F.date_format("pickup_datetime", "yyyy-MM"))
          # Spark: dayofweek 1 = domingo ... 7 = sábado. Se pasa a 1 = lunes ... 7 = domingo (igual que Athena en el punto 6)
          .withColumn("dia_semana", ((F.dayofweek("pickup_datetime") + 5) % 7) + 1)
          .withColumn("hora", F.hour("pickup_datetime"))
          # minutos completos (igual que date_diff('minute', ...) de Athena)
          .withColumn("duracion_min",
                      F.floor((F.unix_timestamp("dropoff_datetime") - F.unix_timestamp("pickup_datetime")) / 60)))
viajes.cache()


def guardar(df, nombre, titulo):
    """Imprime el resultado y lo guarda como un único CSV con encabezado."""
    print(f"\n===== {titulo} =====")
    df.show(50, truncate=False)
    df.coalesce(1).write.mode("overwrite").option("header", True).csv(f"{SALIDA}/{nombre}")


# --- Verificación previa -----------------------------------------------------------------
guardar(viajes.agg(F.count("*").alias("total_viajes"),
                   F.min("pickup_datetime").alias("primera_recogida"),
                   F.max("pickup_datetime").alias("ultima_recogida")),
        "00_verificacion", "Verificación previa")

# --- P1: top 10 zonas de recogida por mes -------------------------------------------------------
conteo = (viajes.join(zonas, viajes.pu_location_id == zonas.location_id)
          .groupBy("mes", F.col("zone").alias("zona"), F.col("borough").alias("distrito"))
          .agg(F.count("*").alias("viajes")))
ventana = Window.partitionBy("mes").orderBy(F.desc("viajes"))
p1 = (conteo.withColumn("posicion", F.row_number().over(ventana))
      .filter("posicion <= 10")
      .select("mes", "posicion", "zona", "distrito", "viajes")
      .orderBy("mes", "posicion"))
guardar(p1, "p1_top10_zonas_por_mes", "P1: Top 10 zonas de recogida por mes")

# --- P2: viajes y tarifa promedio por día de la semana y hora ------------------------------------------
p2 = (viajes.groupBy("dia_semana", "hora")
      .agg(F.count("*").alias("viajes"), F.round(F.avg("total_amount"), 2).alias("tarifa_total_promedio"))
      .orderBy("dia_semana", "hora"))
guardar(p2, "p2_dia_semana_hora", "P2: Viajes y tarifa promedio por día de la semana (1=lunes) y hora")

# --- P3: métodos de pago y propinas -----------------------------------------------------------
total = viajes.count()
etiquetas = F.create_map(*[x for par in [
    (0, "Flex Fare"), (1, "Tarjeta de crédito"), (2, "Efectivo"), (3, "Sin cargo"),
    (4, "Disputa"), (5, "Desconocido"), (6, "Viaje anulado")] for x in (F.lit(par[0]), F.lit(par[1]))])
p3a = (viajes.groupBy("payment_type")
       .agg(F.count("*").alias("viajes"), F.round(F.avg("total_amount"), 2).alias("tarifa_total_promedio"))
       .withColumn("metodo_pago", F.coalesce(etiquetas[F.col("payment_type")], F.lit("Otro")))
       .withColumn("porcentaje_viajes", F.round(100.0 * F.col("viajes") / total, 2))
       .select("metodo_pago", "viajes", "porcentaje_viajes", "tarifa_total_promedio")
       .orderBy(F.desc("viajes")))
guardar(p3a, "p3a_metodos_pago", "P3a: Reparto de viajes por método de pago")

# Solo tarjeta (payment_type = 1): el diccionario de la TLC indica que las propinas en efectivo no se registran
p3b = (viajes.filter((F.col("payment_type") == 1) & (F.col("fare_amount") > 0))
       .agg(F.count("*").alias("viajes_con_tarjeta"),
            F.round(F.avg("tip_amount"), 2).alias("propina_promedio"),
            F.round(100.0 * F.avg(F.col("tip_amount") / F.col("fare_amount")), 2).alias("propina_promedio_pct_de_tarifa")))
guardar(p3b, "p3b_propinas_tarjeta", "P3b: Propinas en pagos con tarjeta de crédito")

# --- P4: distancia y duración promedio por distrito de recogida ---------------------------------------
p4 = (viajes.join(zonas, viajes.pu_location_id == zonas.location_id)
      .groupBy(F.col("borough").alias("distrito"))
      .agg(F.count("*").alias("viajes"),
           F.round(F.avg("trip_distance"), 2).alias("distancia_promedio_millas"),
           F.round(F.avg("duracion_min"), 2).alias("duracion_promedio_min"))
      .orderBy(F.desc("viajes")))
guardar(p4, "p4_distritos", "P4: Distancia y duración promedio por distrito de recogida")

# --- P5: pares origen-destino ---------------------------------------------------------------------------
zo = zonas.select(F.col("location_id").alias("id_o"), F.col("zone").alias("zona_origen"))
zd = zonas.select(F.col("location_id").alias("id_d"), F.col("zone").alias("zona_destino"))
pares = (viajes.join(zo, viajes.pu_location_id == zo.id_o)
         .join(zd, viajes.do_location_id == zd.id_d)
         .groupBy("zona_origen", "zona_destino")
         .agg(F.count("*").alias("viajes"), F.round(F.sum("total_amount"), 2).alias("ingresos_totales")))
pares.cache()
guardar(pares.select("zona_origen", "zona_destino", "viajes").orderBy(F.desc("viajes")).limit(20),
        "p5a_pares_frecuentes", "P5a: 20 pares origen-destino más frecuentes")
guardar(pares.orderBy(F.desc("ingresos_totales")).limit(20),
        "p5b_pares_ingresos", "P5b: 20 pares origen-destino con mayores ingresos totales")

# --- P6: promedios por mes (diciembre es muestra: comparar promedios, no volúmenes) ------------------------
p6 = (viajes.groupBy("mes")
      .agg(F.count("*").alias("viajes_en_los_datos"),
           F.round(F.avg("total_amount"), 2).alias("tarifa_total_promedio"),
           F.round(F.avg("trip_distance"), 2).alias("distancia_promedio_millas"),
           F.round(F.avg("duracion_min"), 2).alias("duracion_promedio_min"))
      .orderBy("mes"))
guardar(p6, "p6_promedios_mensuales", "P6: Promedios por mes")

# --- P7: cargo de congestión (cbd_congestion_fee) ---------------------------------------------------------
con_cargo = F.sum(F.when(F.col("cbd_congestion_fee") > 0, 1).otherwise(0))
p7a = (viajes.groupBy("mes")
       .agg(F.count("*").alias("viajes_en_los_datos"), con_cargo.alias("viajes_con_cargo"),
            F.round(F.sum("cbd_congestion_fee"), 2).alias("recaudo_cargo_congestion"))
       .orderBy("mes"))
guardar(p7a, "p7a_congestion_mensual", "P7a: Cargo de congestión por mes")
p7b = (viajes.join(zonas, viajes.pu_location_id == zonas.location_id)
       .groupBy(F.col("borough").alias("distrito"))
       .agg(con_cargo.alias("viajes_con_cargo"), F.round(F.sum("cbd_congestion_fee"), 2).alias("recaudo_cargo_congestion"))
       .orderBy(F.desc("recaudo_cargo_congestion")))
guardar(p7b, "p7b_congestion_distritos", "P7b: Cargo de congestión por distrito de recogida")

# --- Extra: estadísticas descriptivas generales (solo PySpark; no está en el punto 6) ---------------------------------
cols = ["trip_distance", "duracion_min", "total_amount", "tip_amount", "passenger_count"]
desc = viajes.select(*cols).summary("count", "mean", "stddev", "min", "25%", "50%", "75%", "max")
guardar(desc, "x1_estadisticas_descriptivas", "Extra: estadísticas descriptivas (summary)")

if job:
    job.commit()

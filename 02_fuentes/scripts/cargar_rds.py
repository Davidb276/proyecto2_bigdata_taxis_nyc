#!/usr/bin/env python3
"""
Punto 2 - Carga de datos en RDS MariaDB.

Hace tres cosas:
  1. Ejecuta sql/01_crear_tablas.sql (crea la base, las tablas y los catálogos).
  2. Carga las zonas de taxi desde el CSV oficial de la TLC.
  3. Descarga el Parquet de diciembre 2025, toma una muestra aleatoria y la guarda
     en la tabla viajes_muestra.

Se ejecuta DESDE la instancia EC2 (misma VPC que RDS). Las credenciales se leen de
variables de entorno, no se escriben en el código:

    export DB_HOST="<endpoint-de-rds>"
    export DB_USER="admin"
    export DB_PASSWORD="<contraseña>"
    python3 cargar_rds.py --muestra 200000

Dependencias:  pip install pandas pyarrow sqlalchemy pymysql requests
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import pymysql
import requests
from sqlalchemy import create_engine

BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
ZONES_URL = f"{BASE_URL}/misc/taxi_zone_lookup.csv"
DEC_URL = f"{BASE_URL}/trip-data/yellow_tripdata_2025-12.parquet"
DB_NAME = "taxis_nyc"

# Columnas de la tabla viajes_muestra (en este orden).
COLUMNAS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "passenger_count",
    "trip_distance", "ratecode_id", "store_and_fwd_flag", "pu_location_id",
    "do_location_id", "payment_type", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount",
    "congestion_surcharge", "airport_fee", "cbd_congestion_fee",
]
ENTEROS = ["vendor_id", "passenger_count", "ratecode_id", "pu_location_id",
           "do_location_id", "payment_type"]


def env(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        sys.exit(f"Falta la variable de entorno {nombre}")
    return valor


def conectar():
    return pymysql.connect(host=env("DB_HOST"), user=env("DB_USER"),
                           password=env("DB_PASSWORD"), charset="utf8mb4",
                           autocommit=True)


def crear_esquema(sql_path):
    texto = Path(sql_path).read_text(encoding="utf-8")
    # Quita comentarios de línea y separa por punto y coma.
    lineas = [l for l in texto.splitlines() if not l.strip().startswith("--")]
    sentencias = [s.strip() for s in "\n".join(lineas).split(";") if s.strip()]
    con = conectar()
    try:
        with con.cursor() as cur:
            for s in sentencias:
                cur.execute(s)
    finally:
        con.close()
    print(f"[1/3] Esquema creado ({len(sentencias)} sentencias ejecutadas).")


def cargar_zonas():
    zonas = pd.read_csv(ZONES_URL)
    print("Encabezado original del CSV de zonas:", list(zonas.columns))
    if zonas.shape[1] != 4:
        sys.exit("El CSV de zonas no tiene 4 columnas; revisa el formato antes de seguir.")
    zonas.columns = ["location_id", "borough", "zone", "service_zone"]
    zonas = zonas.astype(object).where(zonas.notna(), None)
    con = conectar()
    try:
        with con.cursor() as cur:
            cur.execute(f"USE {DB_NAME}")
            cur.executemany(
                "REPLACE INTO zonas (location_id, borough, zone, service_zone) "
                "VALUES (%s, %s, %s, %s)",
                zonas.values.tolist(),
            )
    finally:
        con.close()
    print(f"[2/3] Zonas cargadas: {len(zonas)} filas.")


def descargar(url, destino):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for bloque in r.iter_content(chunk_size=1024 * 1024):
                f.write(bloque)


def cargar_muestra(n_muestra):
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "yellow_tripdata_2025-12.parquet"
        print("Descargando", DEC_URL)
        descargar(DEC_URL, ruta)
        df = pd.read_parquet(ruta)

    total = len(df)
    print(f"Filas en el archivo de diciembre 2025: {total}")
    print("Columnas originales:", list(df.columns))

    # Normaliza nombres de columnas.
    df = df.rename(columns={
        "VendorID": "vendor_id",
        "tpep_pickup_datetime": "pickup_datetime",
        "tpep_dropoff_datetime": "dropoff_datetime",
        "RatecodeID": "ratecode_id",
        "PULocationID": "pu_location_id",
        "DOLocationID": "do_location_id",
    })
    df.columns = [c.lower() for c in df.columns]  # por si alguna viene con mayúsculas (ej. Airport_fee)

    for c in COLUMNAS:
        if c not in df.columns:
            print(f"AVISO: la columna {c} no está en el archivo; se guardará como NULL.")
            df[c] = None

    df = df[COLUMNAS].sample(n=min(n_muestra, total), random_state=42)
    for c in ENTEROS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    usuario, clave = quote_plus(env("DB_USER")), quote_plus(env("DB_PASSWORD"))
    engine = create_engine(f"mysql+pymysql://{usuario}:{clave}@{env('DB_HOST')}:3306/{DB_NAME}")
    df.to_sql("viajes_muestra", engine, if_exists="append", index=False,
              chunksize=5000, method="multi")
    print(f"[3/3] Muestra cargada: {len(df)} filas (semilla 42).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", default=str(Path(__file__).resolve().parents[1] / "sql" / "01_crear_tablas.sql"))
    ap.add_argument("--muestra", type=int, default=200000,
                    help="número de viajes de diciembre 2025 a cargar (muestra aleatoria)")
    args = ap.parse_args()

    crear_esquema(args.sql)
    cargar_zonas()
    cargar_muestra(args.muestra)
    print("Listo. Verifica con: SELECT COUNT(*) FROM viajes_muestra;")


if __name__ == "__main__":
    main()

import argparse
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote_plus

import boto3
import pandas as pd
import requests
from sqlalchemy import create_engine

REGION = "us-east-1"
URL_NOV = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-11.parquet"
DB_NAME = "taxis_nyc"
TABLAS_RDS = ["zonas", "tipos_pago", "codigos_tarifa", "proveedores", "viajes_muestra"]


def env(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        sys.exit(f"Falta la variable de entorno {nombre}")
    return valor


def subir(s3, bucket, ruta_local, clave):
    """Sube un archivo y confirma en S3 que llego (imprime el tamano)."""
    s3.upload_file(str(ruta_local), bucket, clave)
    tam = s3.head_object(Bucket=bucket, Key=clave)["ContentLength"]
    print(f"   OK s3://{bucket}/{clave}  ({tam / 1024 / 1024:.2f} MB)")


def ingesta_rds(s3, bucket):
    print("[RDS] Exportando tablas de MariaDB a S3 (raw/rds) ...")
    usuario, clave = quote_plus(env("DB_USER")), quote_plus(env("DB_PASSWORD"))
    engine = create_engine(f"mysql+pymysql://{usuario}:{clave}@{env('DB_HOST')}:3306/{DB_NAME}")
    with tempfile.TemporaryDirectory() as tmp:
        for tabla in TABLAS_RDS:
            df = pd.read_sql(f"SELECT * FROM {tabla}", engine)  # DECIMAL -> float
            print(f"   {tabla}: {len(df)} filas")
            ruta = Path(tmp) / f"{tabla}.parquet"
            df.to_parquet(ruta, index=False, coerce_timestamps="us")
            subir(s3, bucket, ruta, f"raw/rds/{tabla}/{tabla}.parquet")


def ingesta_ec2(s3, bucket):
    carpeta = Path(os.environ.get("DIR_EC2", "/data/taxis"))
    print(f"[EC2] Subiendo archivos de {carpeta} a S3 (raw/ec2_files) ...")
    archivos = sorted(carpeta.glob("*.parquet"))
    if not archivos:
        sys.exit(f"No hay archivos .parquet en {carpeta}. Corre antes descargar_a_ec2.sh")
    for a in archivos:
        subir(s3, bucket, a, f"raw/ec2_files/{a.name}")


def ingesta_url(s3, bucket):
    print("[URL] Descargando noviembre 2025 y subiendo a S3 (raw/url) ...")
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "yellow_tripdata_2025-11.parquet"
        with requests.get(URL_NOV, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(ruta, "wb") as f:
                for bloque in r.iter_content(chunk_size=1024 * 1024):
                    f.write(bloque)
        subir(s3, bucket, ruta, "raw/url/yellow_tripdata_2025-11.parquet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["rds", "ec2", "url"], help="ejecutar una sola fuente")
    args = ap.parse_args()

    bucket = env("BUCKET")
    s3 = boto3.client("s3", region_name=REGION)
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception as e:
        sys.exit(f"No pude acceder al bucket {bucket}: {e}")

    pasos = {"ec2": ingesta_ec2, "url": ingesta_url, "rds": ingesta_rds}
    for nombre, fn in pasos.items():
        if args.solo in (None, nombre):
            fn(s3, bucket)
    print("Listo. Revisa en la consola de S3 la carpeta raw/.")


if __name__ == "__main__":
    main()

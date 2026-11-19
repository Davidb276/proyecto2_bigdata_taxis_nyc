# Punto 3 – Ingesta automática al Data Lake (S3)

El script [ingesta_a_s3.py](ingesta_a_s3.py) carga las tres fuentes del proyecto a un bucket S3 en la región `us-east-1`:

| Fuente | Origen | Prefijo S3 |
|---|---|---|
| RDS MariaDB | Tablas de `taxis_nyc` | `raw/rds/` |
| EC2 | Archivos `.parquet` de `/data/taxis` | `raw/ec2_files/` |
| URL | Viajes de noviembre de 2025 | `raw/url/` |

## Requisitos

```bash
pip3 install boto3 pandas pyarrow sqlalchemy pymysql requests
```

La ejecución requiere credenciales AWS configuradas (en la EC2, el rol `LabRole`) y estas variables:

```bash
export BUCKET="<bucket-del-proyecto>"
export DB_HOST="<endpoint-de-rds>"
export DB_USER="admin"
export DB_PASSWORD="<contraseña>"
```

`DB_HOST`, `DB_USER` y `DB_PASSWORD` solo son necesarios al ejecutar la fuente RDS. Para EC2, el directorio por defecto es `/data/taxis`; se puede cambiar con `DIR_EC2`.

## Ejecución

```bash
python3 ingesta_a_s3.py
```

Para ejecutar una sola fuente:

```bash
python3 ingesta_a_s3.py --solo ec2
python3 ingesta_a_s3.py --solo url
python3 ingesta_a_s3.py --solo rds
```

El script valida el acceso al bucket, sube los archivos y confirma cada objeto con `head_object`. Si se ejecuta dos veces, sobrescribe los mismos archivos en S3. Antes de ejecutar la preparación del punto 4, verifica en S3 que la carpeta `raw/` contenga los datos.

**Estado:** ejecutada con éxito el 18-nov-2026 desde la instancia EC2 (rol `LabRole`), subiendo las tres fuentes al bucket de S3 en `us-east-1`.

# Punto 2 – Fuentes de datos (RDS MariaDB, archivos en EC2, URL)

Este punto deja listas las tres fuentes que alimentarán el Data Lake:

| Fuente | Qué contiene | Cómo se prepara |
|---|---|---|
| RDS MariaDB | Catálogos + zonas + muestra de viajes de dic-2025 | Pasos 1 y 3 (abajo) |
| Archivos en EC2 | Parquet de octubre 2025 | Paso 4 |
| URL en Internet | Parquet de noviembre 2025 | No requiere preparación; la usa el punto 3 |

> **Estado:** el código de este directorio **no se ha probado en AWS**. Si algún paso falla, guarda el mensaje de error: sirve de evidencia y permite corregir el código.
>
> **Regla de costos (AWS Academy):** el crédito del Learner Lab es limitado. Apaga o elimina RDS y EC2 cuando no los uses.

## Paso 0 – Entrar al laboratorio

1. Entra a AWS Academy → Learner Lab → **Start Lab** y espera a que el indicador de AWS esté en verde.
2. Abre la consola de AWS y confirma que la región es **us-east-1 (N. Virginia)**.

## Paso 1 – Crear la base de datos RDS MariaDB

1. Consola → **RDS** → *Create database*.
2. Motor: **MariaDB**. Plantilla: la más pequeña disponible (Dev/Test o Free tier si aparece).
3. Identificador: `taxis-nyc-db`. Usuario maestro: `admin`. Define una contraseña y guárdala.
4. Clase de instancia: la más pequeña disponible (por ejemplo `db.t3.micro`).
5. Almacenamiento: 20 GB.
6. Conectividad: VPC por defecto. **Public access: No** (se accederá desde EC2).
7. Crea la base y espera el estado *Available*. Copia el **Endpoint**.
8. 📸 *Evidencia:* pantallazo de la instancia RDS en estado Available.

## Paso 2 – Crear la instancia EC2

1. Consola → **EC2** → *Launch instance*. Nombre: `taxis-nyc-ec2`.
2. AMI: Amazon Linux (Quick Start). Tipo: `t3.medium` (la lectura del Parquet usa memoria).
3. Key pair: **vockey** (en us-east-1 el laboratorio ofrece este par de claves).
4. Almacenamiento: 16 GB.
5. Grupo de seguridad: permite **SSH (22)** desde tu IP.
6. Lanza la instancia. 📸 *Evidencia:* pantallazo de la instancia en ejecución.

## Paso 3 – Permitir que EC2 hable con RDS

1. En el grupo de seguridad de **RDS** agrega una regla de entrada: tipo **MySQL/Aurora (3306)**, origen = el **grupo de seguridad de la EC2**.
2. 📸 *Evidencia:* pantallazo de la regla.

## Paso 4 – Preparar la EC2 y descargar los archivos (fuente "archivos")

Conéctate a la EC2 (EC2 Instance Connect o SSH) y ejecuta:

```bash
sudo dnf install -y git python3-pip
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>/02_fuentes/scripts

bash descargar_a_ec2.sh /data/taxis
```

Resultado esperado: el archivo `yellow_tripdata_2025-10.parquet` en `/data/taxis`. 📸 *Evidencia:* salida de `ls -lh /data/taxis`.

## Paso 5 – Cargar RDS

```bash
pip3 install pandas pyarrow sqlalchemy pymysql requests

export DB_HOST="<endpoint-de-rds>"
export DB_USER="admin"
export DB_PASSWORD="<tu-contraseña>"

python3 cargar_rds.py --muestra 200000
```

El script crea el esquema (`sql/01_crear_tablas.sql`), carga las zonas desde el CSV oficial de la TLC y guarda una muestra aleatoria de diciembre 2025 en `viajes_muestra`.

**Qué revisar en la salida:**
- Que el encabezado impreso del CSV de zonas tenga 4 columnas (`LocationID`, `Borough`, `Zone`, `service_zone` o similares). Si no, el script se detiene.
- Los avisos "la columna X no está en el archivo".

## Paso 6 – Verificar los datos

Desde la EC2 abre una sesión con Python y ejecuta consultas de comprobación, o usa un cliente SQL conectado a RDS:

```sql
USE taxis_nyc;
SELECT COUNT(*) FROM viajes_muestra;
SELECT COUNT(*) FROM zonas;
SELECT * FROM tipos_pago;
SELECT * FROM viajes_muestra LIMIT 5;
```

📸 *Evidencia:* pantallazo de los resultados.

## Fuente "URL"

El archivo de noviembre 2025 no se almacena en ninguna parte antes de la ingesta. El script del punto 3 lo descargará directamente de:

`https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-11.parquet`

## Solución de problemas

| Síntoma | Posible causa |
|---|---|
| `Can't connect to MySQL server` | La regla del grupo de seguridad de RDS (paso 3) falta o el endpoint está mal |
| `Access denied` | Usuario o contraseña incorrectos en las variables de entorno |
| `MemoryError` o el script se queda sin memoria | Usa una EC2 más grande o baja `--muestra` |
| Error al descargar | Revisa que la EC2 tenga salida a Internet (IP pública asignada) |

# Punto 1 – Caso de estudio

## Contexto

Se analizan los viajes de **taxis amarillos de la ciudad de Nueva York** para los meses de **octubre, noviembre y diciembre de 2025**. Los datos los publica la Comisión de Taxis y Limusinas de NYC (TLC) en archivos mensuales en formato Parquet.

Cada fila es un viaje: fecha y hora de recogida y bajada, zona de recogida y de bajada, distancia, tarifas desglosadas, tipo de pago y número de pasajeros (ver diccionario oficial en el README principal).

## Fuentes de datos (requisito del punto 2)

| Fuente | Contenido | URL / origen |
|---|---|---|
| **RDS MariaDB** | Tablas de referencia (zonas, tipos de pago, códigos de tarifa, proveedores) y una **muestra aleatoria** de viajes de **diciembre 2025** | Zonas: `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv`; viajes: `yellow_tripdata_2025-12.parquet` |
| **Archivos en EC2** | Viajes completos de **octubre 2025** (Parquet) | `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-10.parquet` |
| **URL en Internet** | Viajes completos de **noviembre 2025**, descargados directamente durante la ingesta (punto 3) | `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-11.parquet` |

> Los enlaces de descarga se tomaron de la página oficial de la TLC (consultada el 18-nov-2026).

**Limitación a documentar:** como diciembre es una muestra, **no se pueden comparar volúmenes totales de viajes entre diciembre y los otros meses**; sí se pueden comparar promedios (tarifa, distancia, duración).

## Preguntas de negocio

1. ¿Cuáles son las 10 zonas de recogida con más viajes en cada mes?
2. ¿Qué días de la semana y horas concentran más viajes y cuál es la tarifa total promedio en cada franja?
3. ¿Cómo se reparten los viajes por método de pago y cuál es la propina promedio (monto y porcentaje de la tarifa) en los pagos con tarjeta de crédito?
4. ¿Cuál es la distancia y la duración promedio de los viajes según el distrito (borough) de recogida?
5. ¿Qué pares de zonas origen–destino son los más frecuentes y cuáles generan más ingresos totales?
6. ¿Cómo varían entre octubre, noviembre y diciembre la tarifa total promedio, la distancia promedio y la duración promedio por viaje?
7. ¿Cuánto se recaudó por el cargo de congestión `cbd_congestion_fee` en cada mes y en qué distritos de recogida?

**Notas sobre los datos (según el diccionario oficial de la TLC):**
- En `tip_amount` solo se registran propinas de tarjeta de crédito; las propinas en efectivo no se incluyen. Por eso la pregunta 3 calcula propinas solo para `payment_type = 1`.
- `total_amount` no incluye propinas en efectivo.
- `cbd_congestion_fee` es el cargo por viaje de la Zona de Alivio de Congestión de la MTA, vigente desde el 5 de enero de 2025.

## Contrato de datos para la zona trusted (lo que debe producir el punto 4)

Las consultas del punto 6 asumen esta estructura. Si el job de Glue produce otros nombres, se ajustan las consultas.

**Base de datos del catálogo:** `taxis_trusted`

**Tabla `viajes`** (formato Parquet, columnas en minúsculas):

| Columna | Tipo | Origen |
|---|---|---|
| vendor_id | int | VendorID |
| pickup_datetime | timestamp | tpep_pickup_datetime |
| dropoff_datetime | timestamp | tpep_dropoff_datetime |
| passenger_count | int | passenger_count |
| trip_distance | double | trip_distance |
| ratecode_id | int | RatecodeID |
| store_and_fwd_flag | string | store_and_fwd_flag |
| pu_location_id | int | PULocationID |
| do_location_id | int | DOLocationID |
| payment_type | int | payment_type |
| fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge, total_amount, congestion_surcharge, airport_fee, cbd_congestion_fee | double | igual nombre (en minúsculas) |

**Tabla `zonas`:** location_id (int), borough (string), zone (string), service_zone (string).

**Reglas de limpieza sugeridas (supuestos del equipo, no vienen de la TLC):**
- Eliminar filas con fecha de bajada anterior a la de recogida.
- Eliminar filas con `trip_distance <= 0` o `total_amount < 0`.
- Conservar solo viajes con fecha de recogida entre 2025-10-01 y 2025-12-31.
- No se verificó la calidad real de los archivos desde este entorno; hay que inspeccionarlos (conteo de nulos, rangos) antes de fijar estos filtros.

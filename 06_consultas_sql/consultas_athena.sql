-- Punto 6 - Consultas analíticas descriptivas en Amazon Athena.
-- Base de datos: taxis_trusted. Tablas: viajes, zonas (ver contrato de datos en 01_caso_estudio/README.md).
-- Ejecutadas en Amazon Athena el 18-nov-2026 (consultas de verificación previa y preguntas 1 a 7).
-- Antes de ejecutar: en el editor de Athena selecciona la base de datos taxis_trusted.


-- ============================================================
-- Verificación previa: tamaño de la tabla y rango de fechas
-- ============================================================
SELECT COUNT(*)                AS total_viajes,
       MIN(pickup_datetime)    AS primera_recogida,
       MAX(pickup_datetime)    AS ultima_recogida
FROM taxis_trusted.viajes;


-- ============================================================
-- Pregunta 1: Top 10 zonas de recogida con más viajes por mes
-- ============================================================
WITH conteo AS (
  SELECT date_format(v.pickup_datetime, '%Y-%m') AS mes,
         z.zone                                  AS zona,
         z.borough                               AS distrito,
         COUNT(*)                                AS viajes
  FROM taxis_trusted.viajes v
  JOIN taxis_trusted.zonas z ON v.pu_location_id = z.location_id
  GROUP BY date_format(v.pickup_datetime, '%Y-%m'), z.zone, z.borough
),
ranking AS (
  SELECT mes, zona, distrito, viajes,
         ROW_NUMBER() OVER (PARTITION BY mes ORDER BY viajes DESC) AS posicion
  FROM conteo
)
SELECT mes, posicion, zona, distrito, viajes
FROM ranking
WHERE posicion <= 10
ORDER BY mes, posicion;


-- ============================================================
-- Pregunta 2: Viajes y tarifa total promedio por día de la semana y hora
-- (día de la semana: 1 = lunes ... 7 = domingo)
-- ============================================================
SELECT day_of_week(pickup_datetime)       AS dia_semana,
       hour(pickup_datetime)              AS hora,
       COUNT(*)                           AS viajes,
       ROUND(AVG(total_amount), 2)        AS tarifa_total_promedio
FROM taxis_trusted.viajes
GROUP BY day_of_week(pickup_datetime), hour(pickup_datetime)
ORDER BY dia_semana, hora;


-- ============================================================
-- Pregunta 3a: Reparto de viajes por método de pago
-- ============================================================
SELECT CASE payment_type
         WHEN 0 THEN 'Flex Fare'
         WHEN 1 THEN 'Tarjeta de crédito'
         WHEN 2 THEN 'Efectivo'
         WHEN 3 THEN 'Sin cargo'
         WHEN 4 THEN 'Disputa'
         WHEN 5 THEN 'Desconocido'
         WHEN 6 THEN 'Viaje anulado'
         ELSE 'Otro'
       END                                                    AS metodo_pago,
       COUNT(*)                                               AS viajes,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)     AS porcentaje_viajes,
       ROUND(AVG(total_amount), 2)                            AS tarifa_total_promedio
FROM taxis_trusted.viajes
GROUP BY payment_type
ORDER BY viajes DESC;


-- Pregunta 3b: Propinas en pagos con tarjeta de crédito (payment_type = 1)
-- Solo tarjeta: el diccionario indica que las propinas en efectivo no se registran.
SELECT COUNT(*)                                          AS viajes_con_tarjeta,
       ROUND(AVG(tip_amount), 2)                         AS propina_promedio,
       ROUND(100.0 * AVG(tip_amount / fare_amount), 2)   AS propina_promedio_pct_de_tarifa
FROM taxis_trusted.viajes
WHERE payment_type = 1
  AND fare_amount > 0;


-- ============================================================
-- Pregunta 4: Distancia y duración promedio por distrito de recogida
-- ============================================================
SELECT z.borough                                                       AS distrito,
       COUNT(*)                                                        AS viajes,
       ROUND(AVG(v.trip_distance), 2)                                  AS distancia_promedio_millas,
       ROUND(AVG(date_diff('minute', v.pickup_datetime, v.dropoff_datetime)), 2) AS duracion_promedio_min
FROM taxis_trusted.viajes v
JOIN taxis_trusted.zonas z ON v.pu_location_id = z.location_id
GROUP BY z.borough
ORDER BY viajes DESC;


-- ============================================================
-- Pregunta 5a: 20 pares origen-destino más frecuentes
-- ============================================================
SELECT zo.zone     AS zona_origen,
       zd.zone     AS zona_destino,
       COUNT(*)    AS viajes
FROM taxis_trusted.viajes v
JOIN taxis_trusted.zonas zo ON v.pu_location_id = zo.location_id
JOIN taxis_trusted.zonas zd ON v.do_location_id = zd.location_id
GROUP BY zo.zone, zd.zone
ORDER BY viajes DESC
LIMIT 20;


-- Pregunta 5b: 20 pares origen-destino con mayores ingresos totales
SELECT zo.zone                          AS zona_origen,
       zd.zone                          AS zona_destino,
       COUNT(*)                         AS viajes,
       ROUND(SUM(v.total_amount), 2)    AS ingresos_totales
FROM taxis_trusted.viajes v
JOIN taxis_trusted.zonas zo ON v.pu_location_id = zo.location_id
JOIN taxis_trusted.zonas zd ON v.do_location_id = zd.location_id
GROUP BY zo.zone, zd.zone
ORDER BY ingresos_totales DESC
LIMIT 20;


-- ============================================================
-- Pregunta 6: Promedios por mes (octubre, noviembre, diciembre)
-- Diciembre es una muestra: comparar promedios, NO volúmenes de viajes.
-- ============================================================
SELECT date_format(pickup_datetime, '%Y-%m')                                  AS mes,
       COUNT(*)                                                               AS viajes_en_los_datos,
       ROUND(AVG(total_amount), 2)                                            AS tarifa_total_promedio,
       ROUND(AVG(trip_distance), 2)                                           AS distancia_promedio_millas,
       ROUND(AVG(date_diff('minute', pickup_datetime, dropoff_datetime)), 2)  AS duracion_promedio_min
FROM taxis_trusted.viajes
GROUP BY date_format(pickup_datetime, '%Y-%m')
ORDER BY mes;


-- ============================================================
-- Pregunta 7a: Recaudo del cargo de congestión (cbd_congestion_fee) por mes
-- ============================================================
SELECT date_format(pickup_datetime, '%Y-%m')                                  AS mes,
       COUNT(*)                                                               AS viajes_en_los_datos,
       SUM(CASE WHEN cbd_congestion_fee > 0 THEN 1 ELSE 0 END)                AS viajes_con_cargo,
       ROUND(SUM(cbd_congestion_fee), 2)                                      AS recaudo_cargo_congestion
FROM taxis_trusted.viajes
GROUP BY date_format(pickup_datetime, '%Y-%m')
ORDER BY mes;


-- Pregunta 7b: Recaudo del cargo de congestión por distrito de recogida
SELECT z.borough                                  AS distrito,
       SUM(CASE WHEN v.cbd_congestion_fee > 0 THEN 1 ELSE 0 END) AS viajes_con_cargo,
       ROUND(SUM(v.cbd_congestion_fee), 2)        AS recaudo_cargo_congestion
FROM taxis_trusted.viajes v
JOIN taxis_trusted.zonas z ON v.pu_location_id = z.location_id
GROUP BY z.borough
ORDER BY recaudo_cargo_congestion DESC;

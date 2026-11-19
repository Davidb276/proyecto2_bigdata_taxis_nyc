-- Punto 2: esquema en RDS MariaDB para el caso de estudio de taxis amarillos NYC.
-- Los códigos de los catálogos vienen del diccionario oficial de la TLC (18-mar-2025).
-- Nota: el script de carga separa las sentencias por el caracter de punto y coma, así que no se usa dentro de textos.

CREATE DATABASE IF NOT EXISTS taxis_nyc CHARACTER SET utf8mb4;

USE taxis_nyc;

CREATE TABLE IF NOT EXISTS zonas (
  location_id  INT PRIMARY KEY,
  borough      VARCHAR(50),
  zone         VARCHAR(100),
  service_zone VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS tipos_pago (
  payment_type INT PRIMARY KEY,
  descripcion  VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS codigos_tarifa (
  ratecode_id INT PRIMARY KEY,
  descripcion VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS proveedores (
  vendor_id INT PRIMARY KEY,
  nombre    VARCHAR(80)
);

CREATE TABLE IF NOT EXISTS viajes_muestra (
  id                    BIGINT AUTO_INCREMENT PRIMARY KEY,
  vendor_id             INT,
  pickup_datetime       DATETIME,
  dropoff_datetime      DATETIME,
  passenger_count       INT,
  trip_distance         DECIMAL(12,2),
  ratecode_id           INT,
  store_and_fwd_flag    CHAR(1),
  pu_location_id        INT,
  do_location_id        INT,
  payment_type          INT,
  fare_amount           DECIMAL(12,2),
  extra                 DECIMAL(12,2),
  mta_tax               DECIMAL(12,2),
  tip_amount            DECIMAL(12,2),
  tolls_amount          DECIMAL(12,2),
  improvement_surcharge DECIMAL(12,2),
  total_amount          DECIMAL(12,2),
  congestion_surcharge  DECIMAL(12,2),
  airport_fee           DECIMAL(12,2),
  cbd_congestion_fee    DECIMAL(12,2)
);

REPLACE INTO tipos_pago (payment_type, descripcion) VALUES
  (0, 'Flex Fare trip'),
  (1, 'Credit card'),
  (2, 'Cash'),
  (3, 'No charge'),
  (4, 'Dispute'),
  (5, 'Unknown'),
  (6, 'Voided trip');

REPLACE INTO codigos_tarifa (ratecode_id, descripcion) VALUES
  (1, 'Standard rate'),
  (2, 'JFK'),
  (3, 'Newark'),
  (4, 'Nassau or Westchester'),
  (5, 'Negotiated fare'),
  (6, 'Group ride'),
  (99, 'Null/unknown');

REPLACE INTO proveedores (vendor_id, nombre) VALUES
  (1, 'Creative Mobile Technologies, LLC'),
  (2, 'Curb Mobility, LLC'),
  (6, 'Myle Technologies Inc'),
  (7, 'Helix');

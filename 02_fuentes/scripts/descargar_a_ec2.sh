#!/usr/bin/env bash
# Punto 2 - Archivos en EC2.
# Descarga a la instancia EC2 el archivo de viajes de octubre 2025 (fuente "archivos").
# El mes de noviembre NO se descarga aquí: se toma directamente por URL durante la ingesta (punto 3).
#
# Uso:  bash descargar_a_ec2.sh [directorio_destino]
set -euo pipefail

DEST="${1:-/data/taxis}"
BASE="https://d37ci6vzurychx.cloudfront.net"
ARCHIVOS=(
  "trip-data/yellow_tripdata_2025-10.parquet"
)

sudo mkdir -p "$DEST"
sudo chown "$(id -u):$(id -g)" "$DEST"

for ruta in "${ARCHIVOS[@]}"; do
  nombre="$(basename "$ruta")"
  echo "Descargando $nombre ..."
  curl -fL --retry 3 -o "$DEST/$nombre" "$BASE/$ruta"
done

echo "Archivos en $DEST:"
ls -lh "$DEST"

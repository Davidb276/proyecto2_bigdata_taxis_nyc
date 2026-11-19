# Punto 5 – Catalogación de tablas (AWS Glue y EMR/Hive)

## Catálogo en AWS Glue

| Dato | Valor |
|---|---|
| Base de datos | `taxis_trusted` |
| Crawler | `crawler_taxis_trusted` (ejecución On demand) |
| Fuente | carpeta `trusted/` del bucket del Data Lake (Recrawl all) |
| Rol | `LabRole` |
| Resultado | tablas `viajes` y `zonas`, ambas con clasificación Parquet |

La tabla `viajes` tiene 20 columnas, con los mismos nombres y el mismo orden del contrato de datos (`01_caso_estudio/README.md`). `pickup_datetime` y `dropoff_datetime` quedaron como `timestamp`.

## Consulta con Hive en EMR

Clúster EMR `emr-7.14.0` con Hadoop 3.4.2, Hive 3.1.3 y Spark 3.5.8, un nodo principal `m5.xlarge`, rol de servicio `EMR_DefaultRole` y perfil de instancia `EMR_EC2_DefaultRole`.

Qué pasó (18-nov-2026):

1. **Primer clúster:** terminó con error a los 48 s, con el mensaje `Service role ... LabRole has insufficient EC2 permissions`. `LabRole` no sirvió como rol de servicio de EMR. Se creó otro clúster con `EMR_DefaultRole`.
2. **Paso `hive_prueba`:** falló con `Database does not exist: taxis_trusted`. En la pestaña Configuraciones del clúster solo aparecía la clasificación `spark-hive-site`; faltaba `hive-site`, así que Hive usaba su metastore local y no el catálogo de Glue. No se determinó por qué no se aplicó la opción de usar el catálogo de Glue para Hive.
3. **Paso `hive_prueba2`:** terminó en **Completed**. Es un paso Custom JAR (`command-runner.jar`) con estos argumentos:

```
hive --hiveconf hive.metastore.client.factory.class=com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory -e "SHOW TABLES IN taxis_trusted; SELECT COUNT(*) FROM taxis_trusted.viajes;"
```

Salida (`stdout`): `viajes`, `zonas` y `8348220`, el mismo número de filas trusted que dio el punto 4. Esto muestra que Hive lee el catálogo de Glue.

Si se vuelve a usar Hive en otro clúster, hay que agregar la clasificación `hive-site` con esa propiedad al crearlo, o pasar el `--hiveconf` como arriba.

## Evidencias

Capturas incluidas en [`evidencias/`](evidencias/):

1. `p5_01_tablas_glue.png` — lista de tablas `viajes` y `zonas` en Glue.
2. `p5_02_esquema_viajes.png` — esquema de la tabla `viajes`.
3. `p5_03_esquema_zonas.png` — esquema de la tabla `zonas`.
4. `p5_04_crawler_lista.png` — listado y estado del crawler.
5. `p5_05_crawler_detalle.png` — propiedades e historial de ejecución del crawler.
6. `p5_06_emr_resumen.png` — resumen del clúster EMR.
7. `p5_07_hive_prueba2_stdout.png` — salida `stdout` del paso `hive_prueba2`.
8. `p5_08_emr_steps.png` — listado de pasos del clúster, con los estados de `hive_prueba2` y `hive_prueba`.

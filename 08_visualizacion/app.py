"""
Punto 8 - Aplicación de visualización (Streamlit) sobre los resultados del punto 7.

Lee los CSV de s3://<BUCKET>/refined/resultados/<nombre>/ (los escribe pyspark_analitica.py)
y muestra una página con las 7 preguntas de negocio.

Configuración por variables de entorno:
  BUCKET     nombre del bucket del Data Lake (la EC2 usa el rol LabRole para leer S3, sin claves)
  DATA_DIR   (opcional) carpeta local con la misma estructura de resultados, para probar sin S3

Ejecutar:  streamlit run app.py --server.port 8501 --server.address 0.0.0.0
"""
import glob
import os

import altair as alt
import pandas as pd
import streamlit as st

PREFIJO = "refined/resultados"
DIAS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado", 7: "Domingo"}

st.set_page_config(page_title="Taxis amarillos NYC", layout="wide")


@st.cache_data(show_spinner=False)
def leer(nombre):
    """Devuelve el resultado <nombre> como DataFrame (desde DATA_DIR si está definido, si no desde S3)."""
    data_dir = os.environ.get("DATA_DIR")
    if data_dir:
        archivos = glob.glob(os.path.join(data_dir, PREFIJO, nombre, "*.csv"))
        if not archivos:
            raise FileNotFoundError(f"No hay CSV en {data_dir}/{PREFIJO}/{nombre}")
        return pd.read_csv(archivos[0])
    import boto3
    bucket = os.environ["BUCKET"]
    s3 = boto3.client("s3", region_name="us-east-1")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{PREFIJO}/{nombre}/")
    claves = [o["Key"] for o in resp.get("Contents", []) if o["Key"].endswith(".csv")]
    if not claves:
        raise FileNotFoundError(f"No hay CSV en s3://{bucket}/{PREFIJO}/{nombre}/")
    cuerpo = s3.get_object(Bucket=bucket, Key=claves[0])["Body"]
    return pd.read_csv(cuerpo)


def cargar(nombre):
    try:
        return leer(nombre)
    except Exception as e:  # mostrar el problema en la página en vez de romperla
        st.error(f"No se pudo leer '{nombre}': {e}")
        return None


st.title("Viajes de taxis amarillos de Nueva York (oct–dic 2025)")
st.caption("Fuente: NYC TLC Trip Record Data. Resultados calculados con PySpark (punto 7) sobre la zona trusted del Data Lake. "
           "Diciembre es una muestra aleatoria de 200.000 viajes: se comparan promedios entre meses, no volúmenes.")

v = cargar("00_verificacion")
if v is not None:
    f = v.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Viajes analizados", f"{int(f['total_viajes']):,}")
    c2.metric("Primera recogida", str(f["primera_recogida"])[:10])
    c3.metric("Última recogida", str(f["ultima_recogida"])[:10])

# P1
st.header("1. Zonas de recogida con más viajes")
p1 = cargar("p1_top10_zonas_por_mes")
if p1 is not None:
    meses = sorted(p1["mes"].unique())
    mes = st.selectbox("Mes", meses)
    d = p1[p1["mes"] == mes].sort_values("posicion")
    st.altair_chart(alt.Chart(d).mark_bar().encode(
        x=alt.X("viajes:Q", title="Viajes"), y=alt.Y("zona:N", sort="-x", title=None),
        tooltip=["posicion", "zona", "distrito", "viajes"]), use_container_width=True)
    st.caption("Diciembre es muestra: sirve para el orden de las zonas, no para comparar cantidades con otros meses.")

# P2
st.header("2. Viajes y tarifa por día de la semana y hora")
p2 = cargar("p2_dia_semana_hora")
if p2 is not None:
    p2 = p2.assign(dia=p2["dia_semana"].map(DIAS))
    medida = st.radio("Medida", ["viajes", "tarifa_total_promedio"], horizontal=True)
    st.altair_chart(alt.Chart(p2).mark_rect().encode(
        x=alt.X("hora:O", title="Hora"), y=alt.Y("dia:N", sort=list(DIAS.values()), title=None),
        color=alt.Color(f"{medida}:Q", title=medida),
        tooltip=["dia", "hora", "viajes", "tarifa_total_promedio"]), use_container_width=True)

# P3
st.header("3. Métodos de pago y propinas")
a, b = st.columns(2)
p3a = cargar("p3a_metodos_pago")
if p3a is not None:
    a.altair_chart(alt.Chart(p3a).mark_bar().encode(
        x=alt.X("viajes:Q", title="Viajes"), y=alt.Y("metodo_pago:N", sort="-x", title=None),
        tooltip=["metodo_pago", "viajes", "porcentaje_viajes", "tarifa_total_promedio"]), use_container_width=True)
p3b = cargar("p3b_propinas_tarjeta")
if p3b is not None:
    r = p3b.iloc[0]
    b.metric("Viajes pagados con tarjeta (tarifa > 0)", f"{int(r['viajes_con_tarjeta']):,}")
    b.metric("Propina promedio (USD)", f"{r['propina_promedio']:.2f}")
    b.metric("Propina promedio (% de la tarifa)", f"{r['propina_promedio_pct_de_tarifa']:.2f} %")
    b.caption("Solo tarjeta de crédito: el diccionario de la TLC indica que las propinas en efectivo no se registran.")

# P4
st.header("4. Distancia y duración promedio por distrito de recogida")
p4 = cargar("p4_distritos")
if p4 is not None:
    m = st.radio("Medida", ["distancia_promedio_millas", "duracion_promedio_min"], horizontal=True, key="m4")
    st.altair_chart(alt.Chart(p4).mark_bar().encode(
        x=alt.X(f"{m}:Q"), y=alt.Y("distrito:N", sort="-x", title=None),
        tooltip=["distrito", "viajes", "distancia_promedio_millas", "duracion_promedio_min"]), use_container_width=True)

# P5
st.header("5. Pares origen–destino")
t1, t2 = st.tabs(["Más frecuentes", "Mayores ingresos"])
p5a, p5b = cargar("p5a_pares_frecuentes"), cargar("p5b_pares_ingresos")
if p5a is not None:
    t1.dataframe(p5a, use_container_width=True, hide_index=True)
if p5b is not None:
    t2.dataframe(p5b, use_container_width=True, hide_index=True)

# P6
st.header("6. Promedios por mes")
p6 = cargar("p6_promedios_mensuales")
if p6 is not None:
    st.dataframe(p6, use_container_width=True, hide_index=True)
    m = st.radio("Medida", ["tarifa_total_promedio", "distancia_promedio_millas", "duracion_promedio_min"],
                 horizontal=True, key="m6")
    st.altair_chart(alt.Chart(p6).mark_bar().encode(
        x=alt.X("mes:N", title="Mes"), y=alt.Y(f"{m}:Q"), tooltip=list(p6.columns)), use_container_width=True)

# P7
st.header("7. Cargo de congestión (cbd_congestion_fee)")
x, y = st.columns(2)
p7a, p7b = cargar("p7a_congestion_mensual"), cargar("p7b_congestion_distritos")
if p7a is not None:
    x.subheader("Por mes")
    x.dataframe(p7a, use_container_width=True, hide_index=True)
if p7b is not None:
    y.subheader("Por distrito de recogida")
    y.altair_chart(alt.Chart(p7b).mark_bar().encode(
        x=alt.X("recaudo_cargo_congestion:Q", title="Recaudo (USD)"), y=alt.Y("distrito:N", sort="-x", title=None),
        tooltip=list(p7b.columns)), use_container_width=True)

# Extra
st.header("Estadísticas descriptivas generales")
x1 = cargar("x1_estadisticas_descriptivas")
if x1 is not None:
    st.dataframe(x1, use_container_width=True, hide_index=True)

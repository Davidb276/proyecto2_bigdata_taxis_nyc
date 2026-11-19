# Punto 8 – Visualización (Streamlit) y exposición con API Gateway

[`app.py`](app.py) es una app de Streamlit con gráficos de las 7 preguntas de negocio. Lee los CSV que genera el punto 7 desde `s3://<BUCKET>/refined/resultados/`.

> **Estado:** la app se probó en local (Streamlit 1.45.1, datos sintéticos): arranca, `/_stcore/health` responde `ok` y las 8 secciones se dibujan sin errores. **No se ha ejecutado en AWS ni detrás de API Gateway.**

## A. Correr la app en la EC2
Requisito: el job del punto 7 ya terminó (existe `refined/resultados/`). La EC2 usa LabRole para leer S3 (sin claves).

1. Seguridad: EC2 → la instancia → *Security* → grupo de seguridad → *Edit inbound rules* → regla **TCP 8501**, origen *Anywhere-IPv4* (solo para la prueba; bórrala al terminar).
2. En la EC2:
```bash
cd ~/proyecto2_bigdata_taxis_nyc && git pull
cd 08_visualizacion
pip3 install -r requirements.txt
export BUCKET="taxis-nyc-datalake-david-2026"
nohup python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > app.log 2>&1 &
sleep 5; curl -s localhost:8501/_stcore/health
```
Debe imprimir `ok`. (La EC2 tiene Python 3.9: por eso `requirements.txt` fija Streamlit 1.45.1; versiones más nuevas exigen Python ≥ 3.11.)

3. Navegador: `http://<IP-pública-de-la-EC2>:8501`. 📸 Captura con la barra de direcciones y los gráficos.
4. Si una sección muestra "No se pudo leer…", copia ese mensaje: dice qué carpeta de S3 falta.

## B. Exponerla con API Gateway
1. Consola → **API Gateway** → *Create API* → **HTTP API** → *Build*.
2. *Integrations → Add integration*: tipo **HTTP**, método **ANY**, URL `http://<IP-pública-de-la-EC2>:8501/{proxy}`.
3. *Routes*: `ANY /{proxy+}` y `ANY /` hacia esa integración. *Stages*: `$default` con auto-deploy. *Create*.
4. Copia la *Invoke URL* y ábrela en el navegador. 📸 Capturas de rutas, integración y navegador.

### Advertencia: es probable que no funcione completa
Streamlit se comunica con el navegador por **WebSocket**. Según una respuesta de AWS re:Post, API Gateway no soporta conexiones WebSocket en este escenario; la solución que ahí se sugiere es poner **CloudFront** delante, con ruteo por rutas ([fuente](https://www.repost.aws/questions/QUp_VvvzAYRqWMMsbf9CCTIA/possible-way-to-expose-the-streamlit-application)). No lo he podido comprobar en un Learner Lab: puede que la página cargue el HTML inicial pero se quede en "Please wait…" o sin gráficos.

Qué hacer según el resultado (en cualquier caso, guarda las capturas y el error exacto: sirven como evidencia):
- **Funciona:** documéntalo.
- **Carga a medias o falla:** documenta la limitación y deja la app accesible por `http://<IP>:8501` (parte A). Si quieres intentar la alternativa, CloudFront delante de la EC2; no sé si el Learner Lab lo permite.

## Al terminar
Detén la app (`pkill -f streamlit`), borra la regla del puerto 8501 y apaga/elimina la EC2, RDS y la API para no gastar crédito.

"""Punto de entrada de la aplicacion Streamlit.

Ejecutar con:  streamlit run app.py
"""

import streamlit as st

from core import estado

st.set_page_config(
    page_title="Analisis inteligente de datos",
    page_icon="📊",
    layout="wide",
)

estado.inicializar()

st.title("📊 Analisis inteligente de datos")
st.caption("Modulo 1 — Carga y preprocesamiento de datos")

st.markdown(
    """
Esta aplicacion prepara un conjunto de datos para las tecnicas de analisis que
vienen despues (agrupamiento, deteccion de valores atipicos y correlaciones).

**Flujo de trabajo**

1. **Carga de datos** — subis un CSV o Excel; se valida el formato y se detecta
   automaticamente el separador, la codificacion y el tipo de cada variable.
2. **Limpieza** — duplicados, valores nulos y conversion de tipos, con bitacora
   de todo lo que se le hizo al dataset.
3. **Resumen** — estado final del dataset, columnas aptas para cada tecnica y
   descarga del archivo limpio.
"""
)

st.divider()

if estado.hay_datos():
    meta = estado.obtener_metadatos()
    datos = estado.obtener_datos()
    st.success(f"Dataset activo: **{meta.nombre_archivo}**")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas", f"{len(datos):,}")
    c2.metric("Columnas", datos.shape[1])
    c3.metric("Valores nulos", f"{int(datos.isna().sum().sum()):,}")
    c4.metric("Duplicados", f"{int(datos.duplicated().sum()):,}")

    st.dataframe(datos.head(10), use_container_width=True)
    st.page_link("pages/2_Limpieza.py", label="Continuar a la limpieza", icon="🧹")
else:
    st.info("Todavia no hay datos cargados.")
    st.page_link("pages/1_Carga_de_datos.py", label="Ir a la carga de datos", icon="📁")

with st.sidebar:
    st.header("Estado")
    if estado.hay_datos():
        st.write(estado.obtener_metadatos().resumen())
        if st.button("Descartar dataset", use_container_width=True):
            estado.limpiar_todo()
            st.rerun()
    else:
        st.write("Sin dataset cargado.")

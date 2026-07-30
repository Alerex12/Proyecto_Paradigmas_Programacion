"""Pagina 3 — Resumen del dataset preprocesado y entrega a las etapas siguientes."""

import streamlit as st

from core import estado
from core import tipos as t

st.set_page_config(page_title="Resumen", page_icon="📋", layout="wide")
estado.inicializar()

st.title("📋 Resumen del dataset preprocesado")
datos = estado.exigir_datos()
originales = estado.obtener_originales()
meta = estado.obtener_metadatos()
perfil = t.perfilar(datos)

st.caption(f"Origen: {meta.nombre_archivo} — {meta.resumen()}")

# --- Antes y despues --------------------------------------------------------
st.subheader("Antes y despues")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Filas", f"{len(datos):,}", f"{len(datos) - len(originales):,}")
c2.metric("Columnas", datos.shape[1], datos.shape[1] - originales.shape[1])
c3.metric(
    "Nulos",
    f"{int(datos.isna().sum().sum()):,}",
    f"{int(datos.isna().sum().sum() - originales.isna().sum().sum()):,}",
    delta_color="inverse",
)
c4.metric(
    "Duplicados",
    f"{int(datos.duplicated().sum()):,}",
    f"{int(datos.duplicated().sum() - originales.duplicated().sum()):,}",
    delta_color="inverse",
)

# --- Aptitud para las etapas siguientes ------------------------------------
st.subheader("Columnas disponibles para cada tecnica")
grupos = t.columnas_analizables(perfil)

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Agrupamiento y deteccion de atipicos**")
    if grupos["numericas"]:
        st.write(", ".join(grupos["numericas"]))
    else:
        st.warning("No hay columnas numericas: estas tecnicas no se pueden aplicar todavia.")

    st.markdown("**Categoricas (requieren codificacion)**")
    st.write(", ".join(grupos["categoricas"]) or "—")

with col2:
    st.markdown("**Fechas**")
    st.write(", ".join(grupos["fechas"]) or "—")

    st.markdown("**Recomendadas para excluir**")
    st.write(", ".join(grupos["excluir"]) or "—")
    st.caption("Identificadores, constantes, vacias y texto libre no aportan a los modelos.")

if len(grupos["numericas"]) >= 2:
    st.success("El dataset tiene suficientes variables numericas para clustering y correlaciones.")
else:
    st.warning("Hacen falta al menos 2 variables numericas para correlaciones y clustering.")

# --- Estadisticas -----------------------------------------------------------
st.subheader("Estadisticas descriptivas")
numericas = [c for c in grupos["numericas"] if c in datos.columns]
if numericas:
    st.dataframe(datos[numericas].describe().T, use_container_width=True)
else:
    st.info("Sin columnas numericas para describir.")

st.subheader("Perfil final de variables")
st.dataframe(perfil, use_container_width=True, hide_index=True)

# --- Descarga ---------------------------------------------------------------
st.subheader("Exportar")
st.caption("El archivo limpio es la entrada de los modulos de analisis.")
nombre_base = meta.nombre_archivo.rsplit(".", 1)[0]

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "Descargar dataset limpio (CSV)",
        data=datos.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{nombre_base}_limpio.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col2:
    st.download_button(
        "Descargar perfil de variables (CSV)",
        data=perfil.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{nombre_base}_perfil.csv",
        mime="text/csv",
        use_container_width=True,
    )

registro = estado.bitacora()
if not registro.vacia():
    st.subheader("Bitacora del preprocesamiento")
    st.dataframe(registro.como_dataframe(), use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar bitacora (CSV)",
        data=registro.como_dataframe().to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{nombre_base}_bitacora.csv",
        mime="text/csv",
    )

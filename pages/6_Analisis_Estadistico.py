import streamlit as st

from core import estado, tipos as t, estadisticas as est

st.set_page_config(page_title="Análisis estadístico", layout="wide")
st.title("📊 Análisis estadístico y correlaciones")

datos = estado.exigir_datos()


perfil = estado.perfil_actual()
grupos = t.columnas_analizables(perfil)
columnas_numericas = grupos["numericas"]

if len(columnas_numericas) == 0:
    st.warning("No se detectaron columnas numéricas analizables en el dataset.")
    st.stop()

st.subheader("Selección de variables")
seleccionadas = st.multiselect(
    "Columnas numéricas a incluir en el análisis",
    options=columnas_numericas,
    default=columnas_numericas,
)

if len(seleccionadas) == 0:
    st.info("Seleccioná al menos una columna para ver el resumen.")
    st.stop()

resumen = est.generar_resumen_estadistico(datos, seleccionadas)

st.subheader("Resumen estadístico descriptivo")
st.dataframe(
    resumen["descriptivos"].style.format("{:.2f}"),
    use_container_width=True,
)

csv_descriptivos = resumen["descriptivos"].to_csv().encode("utf-8")
st.download_button(
    "Descargar resumen (CSV)",
    csv_descriptivos,
    "resumen_estadistico.csv",
    "text/csv",
)

if len(seleccionadas) < 2:
    st.info("Seleccioná al menos 2 columnas para calcular correlaciones.")
    st.stop()

st.subheader("Matriz de correlación")
metodo = st.radio("Método", options=["pearson", "spearman"], horizontal=True)
matriz = resumen[f"correlacion_{metodo}"]

st.dataframe(
    matriz.style.background_gradient(cmap="RdBu_r", vmin=-1, vmax=1).format("{:.2f}"),
    use_container_width=True,
)

st.subheader("Pares más correlacionados")
st.dataframe(resumen[f"pares_top_{metodo}"], use_container_width=True)
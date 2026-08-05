import pandas as pd
import plotly.express as px
import streamlit as st
 
from core import estado, tipos as t, estadisticas as est
from core import reportes as r
 
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
 
seccion_estadistico = r.SeccionReporte(
    titulo="Analisis estadistico",
    descripcion=f"Columnas analizadas: {', '.join(seleccionadas)}.",
    tablas=[("Resumen estadistico descriptivo", resumen["descriptivos"].reset_index())],
)
 
if len(seleccionadas) < 2:
    st.info("Seleccioná al menos 2 columnas para calcular correlaciones.")
else:
    st.subheader("Matriz de correlación")
    metodo = st.radio("Método", options=["pearson", "spearman"], horizontal=True)
    matriz = resumen[f"correlacion_{metodo}"]
 
    st.dataframe(
        matriz.style.background_gradient(cmap="RdBu_r", vmin=-1, vmax=1).format("{:.2f}"),
        use_container_width=True,
    )
 
    st.subheader("Pares más correlacionados")
    tabla_pares = resumen[f"pares_top_{metodo}"]
    st.dataframe(tabla_pares, use_container_width=True)
 
    fig_correlacion = px.imshow(
        matriz.round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto"
    )
    fig_correlacion.update_layout(title=f"Matriz de correlacion ({metodo})")
 
    seccion_estadistico.descripcion += f" Metodo de correlacion: {metodo}."
    seccion_estadistico.tablas.append((f"Matriz de correlacion ({metodo})", matriz.round(2).reset_index()))
    seccion_estadistico.tablas.append((f"Pares mas correlacionados ({metodo})", tabla_pares))
    seccion_estadistico.figuras.append((f"Matriz de correlacion ({metodo})", fig_correlacion))
 
estado.registrar_seccion("analisis_estadistico", seccion_estadistico)
 
st.divider()
st.subheader("Exportar esta seccion")
col_html, col_pdf = st.columns(2)
with col_html:
    if st.button("Preparar HTML", key="preparar_html_estadistico"):
        try:
            contenido = r.exportar_html([seccion_estadistico], titulo_reporte="Analisis estadistico")
            st.download_button(
                "⬇️ Descargar HTML", data=contenido, file_name="analisis_estadistico.html",
                mime="text/html", key="descargar_html_estadistico",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
with col_pdf:
    if st.button("Preparar PDF", key="preparar_pdf_estadistico"):
        try:
            with st.spinner("Generando PDF..."):
                contenido = r.exportar_pdf([seccion_estadistico], titulo_reporte="Analisis estadistico")
            st.download_button(
                "⬇️ Descargar PDF", data=contenido, file_name="analisis_estadistico.pdf",
                mime="application/pdf", key="descargar_pdf_estadistico",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
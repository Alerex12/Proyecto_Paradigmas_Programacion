import streamlit as st
 
from core import estado
from core import tipos as t
from core import visualizaciones as v
from core import reportes as r
 
st.set_page_config(page_title="Visualizaciones", page_icon="📈", layout="wide")
estado.inicializar()
 
st.title("📈 Visualizaciones automaticas")
st.caption("Los graficos se eligen segun el tipo semantico detectado para cada variable.")
 
datos = estado.exigir_datos()
perfil = t.perfilar(datos)
grupos = t.columnas_analizables(perfil)
 
with st.spinner("Generando graficos..."):
    graficos = v.generar_todos(datos, perfil)
 
for aviso in graficos.avisos:
    st.info(aviso)
 
if graficos.total_figuras() == 0:
    st.warning("No hay variables aptas para graficar todavia. Revisa la etapa de Limpieza.")
    st.stop()
 
tabs = st.tabs([
    "Distribuciones",
    "Boxplot",
    "Correlacion",
    "Categoricas",
])
 
# --- histogramas ----
with tabs[0]:
    st.subheader("Distribucion de variables numericas")
    if graficos.histogramas:
        columnas_grafico = st.columns(2)
        for i, (nombre_col, fig) in enumerate(graficos.histogramas.items()):
            with columnas_grafico[i % 2]:
                st.plotly_chart(fig, use_container_width=True, key=f"hist_{nombre_col}")
    else:
        st.info("No hay variables numericas para mostrar histogramas.")
 
# --- Boxplot comparativo -----
with tabs[1]:
    st.subheader("Comparacion de variables numericas")
    st.caption("Estandarizadas (z-score) para poder compararlas en el mismo eje. Los puntos fuera de los bigotes son candidatos a outliers.")
    if graficos.boxplot_numericas is not None:
        st.plotly_chart(graficos.boxplot_numericas, use_container_width=True, key="boxplot_general")
    else:
        st.info("No hay variables numericas para comparar.")
 
# --- Correlacion y dispersion -----
with tabs[2]:
    st.subheader("Correlacion entre variables numericas")
    if graficos.mapa_calor is not None:
        st.plotly_chart(graficos.mapa_calor, use_container_width=True, key="mapa_calor")
 
        st.subheader("Relacion mas fuerte detectada")
        if graficos.dispersion is not None and graficos.par_dispersion:
            st.caption(f"Par con mayor correlacion absoluta: **{graficos.par_dispersion[0]}** vs **{graficos.par_dispersion[1]}**")
            st.plotly_chart(graficos.dispersion, use_container_width=True, key="dispersion_auto")
 
        st.divider()
        st.subheader("Explorar otro par manualmente")
        numericas = grupos["numericas"]
        col1, col2, col3 = st.columns(3)
        eje_x = col1.selectbox("Eje X", numericas, index=0, key="eje_x")
        eje_y = col2.selectbox("Eje Y", numericas, index=min(1, len(numericas) - 1), key="eje_y")
        opciones_color = [None] + grupos["categoricas"]
        color = col3.selectbox("Color por (opcional)", opciones_color, key="color_dispersion")
        if eje_x and eje_y:
            fig_manual = v.figura_dispersion(datos, eje_x, eje_y, color=color)
            st.plotly_chart(fig_manual, use_container_width=True, key="dispersion_manual")
    else:
        st.info("Hacen falta al menos 2 variables numericas para calcular correlaciones.")
 
# --- barras ---
with tabs[3]:
    st.subheader("Frecuencia de variables categoricas")
    if graficos.barras:
        columnas_grafico = st.columns(2)
        for i, (nombre_col, fig) in enumerate(graficos.barras.items()):
            with columnas_grafico[i % 2]:
                st.plotly_chart(fig, use_container_width=True, key=f"barras_{nombre_col}")
    else:
        st.info("No hay variables categoricas o booleanas para mostrar.")
 
 
# --------------------------------------------------------------------------- #
# Exportar
# --------------------------------------------------------------------------- #
 
def _construir_seccion() -> r.SeccionReporte:
    """Junta todas las figuras generadas en esta pagina en una SeccionReporte."""
    figuras = []
    figuras.extend((f"Distribucion de '{col}'", fig) for col, fig in graficos.histogramas.items())
    if graficos.boxplot_numericas is not None:
        figuras.append(("Comparacion de variables numericas (z-score)", graficos.boxplot_numericas))
    if graficos.mapa_calor is not None:
        figuras.append(("Mapa de calor de correlacion", graficos.mapa_calor))
    if graficos.dispersion is not None and graficos.par_dispersion:
        nombre = f"Dispersion: {graficos.par_dispersion[0]} vs {graficos.par_dispersion[1]}"
        figuras.append((nombre, graficos.dispersion))
    figuras.extend((f"Frecuencia de '{col}'", fig) for col, fig in graficos.barras.items())
 
    return r.SeccionReporte(
        titulo="Visualizaciones",
        descripcion="Graficos generados automaticamente segun el tipo detectado de cada variable.",
        figuras=figuras,
    )
 
 
seccion_actual = _construir_seccion()
estado.registrar_seccion("visualizaciones", seccion_actual)  # disponible para el reporte completo
 
st.divider()
st.subheader("Exportar esta seccion")
col_html, col_pdf = st.columns(2)
 
with col_html:
    if st.button("Preparar HTML", key="preparar_html_visualizaciones"):
        try:
            contenido = r.exportar_html([seccion_actual], titulo_reporte="Visualizaciones")
            st.download_button(
                "⬇️ Descargar HTML", data=contenido, file_name="visualizaciones.html",
                mime="text/html", key="descargar_html_visualizaciones",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
 
with col_pdf:
    if st.button("Preparar PDF", key="preparar_pdf_visualizaciones"):
        try:
            with st.spinner("Generando PDF..."):
                contenido = r.exportar_pdf([seccion_actual], titulo_reporte="Visualizaciones")
            st.download_button(
                "⬇️ Descargar PDF", data=contenido, file_name="visualizaciones.pdf",
                mime="application/pdf", key="descargar_pdf_visualizaciones",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
 


import streamlit as st

from core import estado
from core import tipos as t
from core import visualizaciones as v

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
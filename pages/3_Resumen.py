"""Pagina 3 — Resumen del dataset preprocesado y entrega a las etapas siguientes."""
 
import pandas as pd
import streamlit as st
 
from core import estado
from core import reportes as r
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
diferencia_filas = len(datos) - len(originales)
diferencia_columnas = datos.shape[1] - originales.shape[1]
nulos_actuales = int(datos.isna().sum().sum())
nulos_originales = int(originales.isna().sum().sum())
duplicados_actuales = int(datos.duplicated().sum())
duplicados_originales = int(originales.duplicated().sum())
 
c1, c2, c3, c4 = st.columns(4)
c1.metric("Filas", f"{len(datos):,}", f"{diferencia_filas:,}")
c2.metric("Columnas", datos.shape[1], diferencia_columnas)
c3.metric("Nulos", f"{nulos_actuales:,}", f"{nulos_actuales - nulos_originales:,}", delta_color="inverse")
c4.metric(
    "Duplicados", f"{duplicados_actuales:,}", f"{duplicados_actuales - duplicados_originales:,}",
    delta_color="inverse",
)
 
tabla_antes_despues = pd.DataFrame([
    {"Metrica": "Filas", "Original": len(originales), "Actual": len(datos)},
    {"Metrica": "Columnas", "Original": originales.shape[1], "Actual": datos.shape[1]},
    {"Metrica": "Nulos", "Original": nulos_originales, "Actual": nulos_actuales},
    {"Metrica": "Duplicados", "Original": duplicados_originales, "Actual": duplicados_actuales},
])
 
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
 
tabla_aptitud = pd.DataFrame([
    {"Grupo": "Numericas", "Columnas": ", ".join(grupos["numericas"]) or "—"},
    {"Grupo": "Categoricas", "Columnas": ", ".join(grupos["categoricas"]) or "—"},
    {"Grupo": "Fechas", "Columnas": ", ".join(grupos["fechas"]) or "—"},
    {"Grupo": "Recomendadas para excluir", "Columnas": ", ".join(grupos["excluir"]) or "—"},
])
 
# --- Estadisticas -----------------------------------------------------------
st.subheader("Estadisticas descriptivas")
numericas = [c for c in grupos["numericas"] if c in datos.columns]
tabla_descriptivos = None
if numericas:
    tabla_descriptivos = datos[numericas].describe().T
    st.dataframe(tabla_descriptivos, use_container_width=True)
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
tabla_bitacora = None
if not registro.vacia():
    tabla_bitacora = registro.como_dataframe()
    st.subheader("Bitacora del preprocesamiento")
    st.dataframe(tabla_bitacora, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar bitacora (CSV)",
        data=tabla_bitacora.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{nombre_base}_bitacora.csv",
        mime="text/csv",
    )
 
# --------------------------------------------------------------------------- #
# Reporte de esta pagina
# --------------------------------------------------------------------------- #
tablas_resumen = [
    ("Antes y despues del preprocesamiento", tabla_antes_despues),
    ("Columnas disponibles por tecnica", tabla_aptitud),
]
if tabla_descriptivos is not None:
    tablas_resumen.append(("Estadisticas descriptivas", tabla_descriptivos.reset_index()))
tablas_resumen.append(("Perfil final de variables", perfil))
if tabla_bitacora is not None:
    tablas_resumen.append(("Bitacora del preprocesamiento", tabla_bitacora))
 
seccion_resumen = r.SeccionReporte(
    titulo="Resumen del dataset preprocesado",
    descripcion=f"Origen: {meta.nombre_archivo} — {meta.resumen()}.",
    tablas=tablas_resumen,
)
estado.registrar_seccion("resumen", seccion_resumen)
 
st.divider()
st.subheader("Exportar esta seccion")
col_html, col_pdf = st.columns(2)
with col_html:
    if st.button("Preparar HTML", key="preparar_html_resumen"):
        try:
            contenido = r.exportar_html([seccion_resumen], titulo_reporte="Resumen del dataset")
            st.download_button(
                "⬇️ Descargar HTML", data=contenido, file_name="resumen.html",
                mime="text/html", key="descargar_html_resumen",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
with col_pdf:
    if st.button("Preparar PDF", key="preparar_pdf_resumen"):
        try:
            with st.spinner("Generando PDF..."):
                contenido = r.exportar_pdf([seccion_resumen], titulo_reporte="Resumen del dataset")
            st.download_button(
                "⬇️ Descargar PDF", data=contenido, file_name="resumen.pdf",
                mime="application/pdf", key="descargar_pdf_resumen",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
 
# --------------------------------------------------------------------------- #
# Reporte completo (todas las secciones que ya se visitaron)
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Reporte completo")
 
ORDEN_SECCIONES = ["resumen", "outliers", "clustering", "analisis_estadistico", "visualizaciones"]
NOMBRES_SECCIONES = {
    "resumen": "Resumen",
    "outliers": "Valores atipicos",
    "clustering": "Clustering",
    "analisis_estadistico": "Analisis estadistico",
    "visualizaciones": "Visualizaciones",
}
 
secciones_completas = estado.obtener_secciones(orden=ORDEN_SECCIONES)
claves_presentes = {clave for clave in ORDEN_SECCIONES if estado.obtener_seccion(clave) is not None}
claves_faltantes = [clave for clave in ORDEN_SECCIONES if clave not in claves_presentes]
 
st.caption(
    "Incluye: " + ", ".join(NOMBRES_SECCIONES[c] for c in ORDEN_SECCIONES if c in claves_presentes) + "."
)
if claves_faltantes:
    st.caption(
        "Todavia no visitaste (no se incluyen): "
        + ", ".join(NOMBRES_SECCIONES[c] for c in claves_faltantes) + "."
    )
 
col_html, col_pdf = st.columns(2)
with col_html:
    if st.button("Preparar HTML completo", key="preparar_html_completo"):
        try:
            contenido = r.exportar_html(secciones_completas, titulo_reporte="Reporte de analisis exploratorio")
            st.download_button(
                "⬇️ Descargar HTML completo", data=contenido, file_name="reporte_completo.html",
                mime="text/html", key="descargar_html_completo",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
with col_pdf:
    if st.button("Preparar PDF completo", key="preparar_pdf_completo"):
        try:
            with st.spinner("Generando PDF completo..."):
                contenido = r.exportar_pdf(secciones_completas, titulo_reporte="Reporte de analisis exploratorio")
            st.download_button(
                "⬇️ Descargar PDF completo", data=contenido, file_name="reporte_completo.pdf",
                mime="application/pdf", key="descargar_pdf_completo",
            )
        except r.ErrorReporte as exc:
            st.error(str(exc))
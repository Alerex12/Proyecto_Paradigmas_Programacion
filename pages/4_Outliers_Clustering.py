"""Pagina 4 — Deteccion de valores atipicos y clustering."""
 
import pandas as pd
import plotly.express as px
import streamlit as st
 
from core import clustering as c
from core import estado
from core import outliers as o
from core import reportes as r
from core import tipos as t
 
st.set_page_config(page_title="Outliers y Clustering", page_icon="🔎", layout="wide")
estado.inicializar()
 
st.title("🔎 Valores atipicos y clustering")
datos = estado.exigir_datos()
perfil = t.perfilar(datos)
numericas_detectadas = t.columnas_analizables(perfil)["numericas"]
numericas = [c for c in numericas_detectadas if pd.api.types.is_numeric_dtype(datos[c])]
pendientes = [c for c in numericas_detectadas if c not in numericas]
 
if pendientes:
    st.info(
        "Estas columnas parecen numericas pero todavia son texto: "
        f"**{', '.join(pendientes)}**. Convertilas en Limpieza -> "
        "'Tipos de dato' -> 'Convertir todo segun la deteccion' para poder usarlas aca."
    )
 
if len(numericas) < 2:
    st.warning("Hacen falta al menos 2 columnas numericas ya convertidas. Revisa la pagina de Limpieza.")
    st.stop()
 
# Secciones de reporte que se van llenando en cada pestaña (quedan en None si
# el usuario todavia no genero nada en esa pestaña).
seccion_outliers = None
seccion_clustering = None
 
pestanas = st.tabs(["1. Valores atipicos", "2. Clustering"])
 
# --------------------------------------------------------------------------- #
# 1. Outliers
# --------------------------------------------------------------------------- #
with pestanas[0]:
    st.subheader("Deteccion de valores atipicos")
    columnas_outliers = st.multiselect(
        "Columnas a evaluar", numericas, default=numericas, key="cols_outliers"
    )
 
    if columnas_outliers:
        tabla_resumen = o.resumen_outliers(datos, columnas_outliers)
        st.markdown("**Resumen por metodo (Z-Score e IQR)**")
        st.dataframe(tabla_resumen, use_container_width=True, hide_index=True)
 
        metodo = st.radio(
            "Metodo para marcar y, si queres, eliminar filas",
            list(o.METODOS.keys()),
            format_func=lambda k: o.METODOS[k],
            horizontal=True,
        )
 
        if metodo == "zscore":
            umbral = st.slider("Umbral |z|", 1.0, 5.0, o.UMBRAL_Z_SCORE, 0.1)
            mascara = o.mascara_combinada(o.detectar_outliers_zscore(datos, columnas_outliers, umbral))
            detalle_metodo = f"Z-Score (umbral |z| = {umbral})"
        elif metodo == "iqr":
            multiplicador = st.slider("Multiplicador IQR", 1.0, 3.0, o.MULTIPLICADOR_IQR, 0.1)
            mascara = o.mascara_combinada(o.detectar_outliers_iqr(datos, columnas_outliers, multiplicador))
            detalle_metodo = f"IQR (multiplicador = {multiplicador})"
        else:
            contaminacion = st.slider("Contaminacion esperada (%)", 1, 20, int(o.CONTAMINACION_ISOLATION_FOREST * 100)) / 100
            mascara = o.detectar_outliers_isolation_forest(datos, columnas_outliers, contaminacion)
            detalle_metodo = f"Isolation Forest (contaminacion = {contaminacion:.0%})"
 
        st.info(f"**{int(mascara.sum())}** filas marcadas como atipicas con este metodo.")
        filas_marcadas = datos.loc[mascara, columnas_outliers].head(50)
        st.dataframe(filas_marcadas, use_container_width=True)
 
        seccion_outliers = r.SeccionReporte(
            titulo="Valores atipicos (outliers)",
            descripcion=(
                f"Columnas evaluadas: {', '.join(columnas_outliers)}. "
                f"Metodo: {detalle_metodo}. Filas marcadas: {int(mascara.sum())} de {len(datos)}."
            ),
            tablas=[
                ("Resumen por metodo (Z-Score e IQR)", tabla_resumen),
                ("Filas marcadas como atipicas (primeras 50)", filas_marcadas),
            ],
        )
 
        if mascara.any() and st.button("Eliminar filas atipicas", type="primary"):
            resultado, eliminadas = o.eliminar_outliers(datos, mascara)
            estado.actualizar_datos(
                resultado, "Outliers", f"{eliminadas} filas eliminadas ({o.METODOS[metodo]})"
            )
            st.success(f"Se eliminaron {eliminadas} filas.")
            st.rerun()
    else:
        st.info("Elegi al menos una columna para analizar.")
 
    if seccion_outliers is not None:
        estado.registrar_seccion("outliers", seccion_outliers)
        st.divider()
        st.subheader("Exportar esta seccion")
        col_html, col_pdf = st.columns(2)
        with col_html:
            if st.button("Preparar HTML", key="preparar_html_outliers"):
                try:
                    contenido = r.exportar_html([seccion_outliers], titulo_reporte="Valores atipicos")
                    st.download_button(
                        "⬇️ Descargar HTML", data=contenido, file_name="outliers.html",
                        mime="text/html", key="descargar_html_outliers",
                    )
                except r.ErrorReporte as exc:
                    st.error(str(exc))
        with col_pdf:
            if st.button("Preparar PDF", key="preparar_pdf_outliers"):
                try:
                    with st.spinner("Generando PDF..."):
                        contenido = r.exportar_pdf([seccion_outliers], titulo_reporte="Valores atipicos")
                    st.download_button(
                        "⬇️ Descargar PDF", data=contenido, file_name="outliers.pdf",
                        mime="application/pdf", key="descargar_pdf_outliers",
                    )
                except r.ErrorReporte as exc:
                    st.error(str(exc))
 
# --------------------------------------------------------------------------- #
# 2. Clustering
# --------------------------------------------------------------------------- #
with pestanas[1]:
    st.subheader("Agrupamiento (clustering)")
    columnas_cluster = st.multiselect(
        "Columnas a usar", numericas, default=numericas, key="cols_cluster"
    )
 
    if len(columnas_cluster) < 2:
        st.info("Elegi al menos 2 columnas numericas.")
    else:
        filas_disponibles = int(datos[columnas_cluster].dropna().shape[0])
 
        if filas_disponibles < c.K_MINIMO:
            st.warning(
                f"Solo hay {filas_disponibles} filas sin nulos en estas columnas; hacen falta "
                f"al menos {c.K_MINIMO} para poder agrupar. Revisa nulos y duplicados en Limpieza."
            )
            st.stop()
 
        algoritmo = st.radio("Algoritmo", ["K-Means", "DBSCAN"], horizontal=True)
        k_maximo_disponible = min(c.K_MAXIMO, filas_disponibles)
 
        if algoritmo == "K-Means":
            try:
                with st.expander("Metodo del codo (ayuda a elegir K)"):
                    codo = c.metodo_codo(datos, columnas_cluster, k_maximo=k_maximo_disponible)
                    st.line_chart(codo.set_index("k")["inercia"])
 
                k = st.slider(
                    "Numero de clusters (K)", c.K_MINIMO, k_maximo_disponible, min(3, k_maximo_disponible)
                )
                if st.button("Ejecutar K-Means", type="primary"):
                    resultado = c.ajustar_kmeans(datos, columnas_cluster, k)
                    st.session_state["resultado_clustering"] = resultado
            except ValueError as exc:
                st.warning(str(exc))
        else:
            col1, col2 = st.columns(2)
            eps = col1.slider("eps (radio de vecindad)", 0.1, 5.0, c.EPS_POR_DEFECTO, 0.1)
            min_muestras = col2.slider("min_samples", 2, max(2, min(20, filas_disponibles)), min(c.MIN_MUESTRAS_POR_DEFECTO, filas_disponibles))
            if st.button("Ejecutar DBSCAN", type="primary"):
                try:
                    resultado = c.ajustar_dbscan(datos, columnas_cluster, eps, min_muestras)
                    st.session_state["resultado_clustering"] = resultado
                except ValueError as exc:
                    st.warning(str(exc))
 
        resultado = st.session_state.get("resultado_clustering")
        if resultado is not None and resultado.columnas == columnas_cluster:
            st.success(resultado.resumen())
 
            m1, m2, m3 = st.columns(3)
            m1.metric("Silhouette", f"{resultado.silhouette:.3f}" if resultado.silhouette is not None else "—")
            m2.metric("Calinski-Harabasz", f"{resultado.calinski_harabasz:.1f}" if resultado.calinski_harabasz is not None else "—")
            m3.metric("Davies-Bouldin", f"{resultado.davies_bouldin:.3f}" if resultado.davies_bouldin is not None else "—")
 
            con_clusters = c.asignar_etiquetas(datos, resultado)
            conteo_clusters = con_clusters["cluster"].value_counts(dropna=False).sort_index()
 
            st.markdown("**Filas por cluster**")
            st.bar_chart(conteo_clusters)
 
            fig_barras_cluster = px.bar(
                x=conteo_clusters.index.astype(str), y=conteo_clusters.values,
                labels={"x": "Cluster", "y": "Filas"},
            )
            fig_barras_cluster.update_layout(title="Filas por cluster", showlegend=False)
 
            fig_dispersion_cluster = None
            if len(columnas_cluster) >= 2:
                st.markdown(f"**Dispersion: {columnas_cluster[0]} vs {columnas_cluster[1]}**")
                st.scatter_chart(con_clusters, x=columnas_cluster[0], y=columnas_cluster[1], color="cluster")
 
                fig_dispersion_cluster = px.scatter(
                    con_clusters, x=columnas_cluster[0], y=columnas_cluster[1],
                    color=con_clusters["cluster"].astype(str),
                    labels={"color": "Cluster"},
                )
                fig_dispersion_cluster.update_layout(
                    title=f"Dispersion: {columnas_cluster[0]} vs {columnas_cluster[1]} (por cluster)"
                )
 
            tabla_metricas = pd.DataFrame([{
                "Silhouette": resultado.silhouette,
                "Calinski-Harabasz": resultado.calinski_harabasz,
                "Davies-Bouldin": resultado.davies_bouldin,
            }])
            tabla_conteo = conteo_clusters.rename_axis("cluster").reset_index(name="filas")
 
            figuras_cluster = [("Filas por cluster", fig_barras_cluster)]
            if fig_dispersion_cluster is not None:
                figuras_cluster.append((
                    f"Dispersion: {columnas_cluster[0]} vs {columnas_cluster[1]}", fig_dispersion_cluster
                ))
 
            seccion_clustering = r.SeccionReporte(
                titulo="Clustering",
                descripcion=f"Columnas usadas: {', '.join(columnas_cluster)}. {resultado.resumen()}",
                tablas=[
                    ("Metricas de calidad", tabla_metricas),
                    ("Filas por cluster", tabla_conteo),
                ],
                figuras=figuras_cluster,
            )
 
            if st.button("Guardar la columna 'cluster' en el dataset"):
                estado.actualizar_datos(
                    con_clusters, "Clustering", f"columna 'cluster' agregada ({resultado.resumen()})"
                )
                st.success("Columna 'cluster' agregada al dataset de trabajo.")
                st.rerun()
 
    if seccion_clustering is not None:
        estado.registrar_seccion("clustering", seccion_clustering)
        st.divider()
        st.subheader("Exportar esta seccion")
        col_html, col_pdf = st.columns(2)
        with col_html:
            if st.button("Preparar HTML", key="preparar_html_clustering"):
                try:
                    contenido = r.exportar_html([seccion_clustering], titulo_reporte="Clustering")
                    st.download_button(
                        "⬇️ Descargar HTML", data=contenido, file_name="clustering.html",
                        mime="text/html", key="descargar_html_clustering",
                    )
                except r.ErrorReporte as exc:
                    st.error(str(exc))
        with col_pdf:
            if st.button("Preparar PDF", key="preparar_pdf_clustering"):
                try:
                    with st.spinner("Generando PDF..."):
                        contenido = r.exportar_pdf([seccion_clustering], titulo_reporte="Clustering")
                    st.download_button(
                        "⬇️ Descargar PDF", data=contenido, file_name="clustering.pdf",
                        mime="application/pdf", key="descargar_pdf_clustering",
                    )
                except r.ErrorReporte as exc:
                    st.error(str(exc))
 
st.page_link("pages/3_Resumen.py", label="Volver al resumen", icon="📋")
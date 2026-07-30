"""Pagina 2 — Limpieza basica: duplicados, nulos y conversion de tipos."""

import streamlit as st

from core import estado, limpieza
from core import tipos as t

st.set_page_config(page_title="Limpieza", page_icon="🧹", layout="wide")
estado.inicializar()

st.title("🧹 Limpieza y preprocesamiento")
datos = estado.exigir_datos()

c1, c2, c3 = st.columns(3)
c1.metric("Filas", f"{len(datos):,}")
c2.metric("Nulos", f"{int(datos.isna().sum().sum()):,}")
c3.metric("Duplicados", f"{int(datos.duplicated().sum()):,}")

pestanas = st.tabs(
    ["1. Normalizacion", "2. Duplicados", "3. Valores nulos", "4. Tipos de dato", "Bitacora"]
)

# --------------------------------------------------------------------------- #
# 1. Normalizacion
# --------------------------------------------------------------------------- #
with pestanas[0]:
    st.subheader("Normalizacion previa")
    st.caption(
        "Antes de contar nulos conviene unificar como se escriben: 'N/A', '-', "
        "'sin dato' y los espacios sobrantes no son datos reales."
    )

    col1, col2 = st.columns(2)
    with col1:
        recortar = st.checkbox("Recortar espacios en textos", value=True)
        unificar = st.checkbox("Convertir marcadores de nulo textuales en nulos reales", value=True)
    with col2:
        descartar_vacias = st.checkbox("Descartar columnas casi vacias", value=False)
        umbral = st.slider("Umbral de nulos para descartar (%)", 50, 100, 95, disabled=not descartar_vacias)

    with st.expander("Marcadores que se consideran nulos"):
        st.code(", ".join(m for m in limpieza.NULOS_TEXTUALES if m.strip()))

    if st.button("Aplicar normalizacion", type="primary"):
        resultado = datos
        detalles = []

        if recortar:
            resultado = limpieza.recortar_espacios(resultado)
            detalles.append("espacios recortados")
        if unificar:
            resultado, nuevos = limpieza.normalizar_nulos(resultado)
            detalles.append(f"{nuevos} valores convertidos a nulo")
        if descartar_vacias:
            resultado, eliminadas = limpieza.eliminar_columnas_vacias(resultado, umbral / 100)
            detalles.append(
                f"columnas descartadas: {', '.join(eliminadas)}" if eliminadas else "sin columnas para descartar"
            )

        estado.actualizar_datos(resultado, "Normalizacion", "; ".join(detalles))
        st.success("Normalizacion aplicada: " + "; ".join(detalles))
        st.rerun()

# --------------------------------------------------------------------------- #
# 2. Duplicados
# --------------------------------------------------------------------------- #
with pestanas[1]:
    st.subheader("Filas duplicadas")

    modo = st.radio(
        "Criterio",
        ["Fila completa identica", "Solo ciertas columnas"],
        horizontal=True,
    )
    subconjunto = None
    if modo == "Solo ciertas columnas":
        subconjunto = st.multiselect("Columnas que definen un duplicado", list(datos.columns))
        if not subconjunto:
            subconjunto = None

    cantidad = limpieza.contar_duplicados(datos, subconjunto)
    if cantidad == 0:
        st.success("No hay filas duplicadas con este criterio.")
    else:
        st.warning(f"Se encontraron **{cantidad}** filas duplicadas.")
        st.dataframe(
            datos[datos.duplicated(subset=subconjunto, keep=False)].head(50),
            use_container_width=True,
        )
        conservar = st.selectbox(
            "Cual conservar",
            ["first", "last"],
            format_func=lambda v: "La primera aparicion" if v == "first" else "La ultima aparicion",
        )
        if st.button("Eliminar duplicados", type="primary"):
            resultado, eliminadas = limpieza.eliminar_duplicados(datos, subconjunto, conservar)
            criterio = "fila completa" if subconjunto is None else ", ".join(subconjunto)
            estado.actualizar_datos(
                resultado, "Duplicados", f"{eliminadas} filas eliminadas (criterio: {criterio})"
            )
            st.success(f"Se eliminaron {eliminadas} filas.")
            st.rerun()

# --------------------------------------------------------------------------- #
# 3. Valores nulos
# --------------------------------------------------------------------------- #
with pestanas[2]:
    st.subheader("Valores nulos")
    resumen = limpieza.resumen_nulos(datos)
    con_nulos = resumen[resumen["nulos"] > 0]

    if con_nulos.empty:
        st.success("El dataset no tiene valores nulos.")
    else:
        st.dataframe(con_nulos, use_container_width=True, hide_index=True)
        st.bar_chart(con_nulos.set_index("columna")["porcentaje"])

        st.markdown("**Tratamiento por columna**")
        columna = st.selectbox("Columna", con_nulos["columna"].tolist())
        es_numerica = t.pdt.is_numeric_dtype(datos[columna])

        disponibles = [
            clave
            for clave in limpieza.ESTRATEGIAS_NULOS
            if es_numerica or clave not in ("media", "mediana", "cero")
        ]
        estrategia = st.selectbox(
            "Estrategia",
            disponibles,
            format_func=lambda k: limpieza.ESTRATEGIAS_NULOS[k],
        )
        valor = st.text_input("Valor fijo") if estrategia == "constante" else None

        if not es_numerica:
            st.caption("Columna no numerica: media, mediana y cero no aplican.")

        if st.button("Aplicar estrategia", type="primary"):
            try:
                resultado, detalle = limpieza.aplicar_estrategia_nulos(datos, columna, estrategia, valor)
            except ValueError as exc:
                st.error(str(exc))
            else:
                estado.actualizar_datos(resultado, "Nulos", detalle)
                st.success(detalle)
                st.rerun()

        st.divider()
        if st.button("Eliminar todas las filas que tengan algun nulo"):
            resultado = datos.dropna().reset_index(drop=True)
            estado.actualizar_datos(
                resultado, "Nulos", f"{len(datos) - len(resultado)} filas eliminadas por tener nulos"
            )
            st.rerun()

# --------------------------------------------------------------------------- #
# 4. Tipos de dato
# --------------------------------------------------------------------------- #
with pestanas[3]:
    st.subheader("Conversion de tipos")
    perfil = t.perfilar(datos)
    st.dataframe(
        perfil[["columna", "tipo", "dtype_pandas", "unicos", "ejemplo", "razon"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("**Conversion automatica**")
    st.caption("Aplica a cada columna el tipo detectado: numeros, fechas, booleanos y categorias.")
    if st.button("Convertir todo segun la deteccion", type="primary"):
        resultado, detalles = limpieza.convertir_automatico(datos, perfil)
        estado.actualizar_datos(
            resultado, "Tipos", f"{len(detalles)} columnas procesadas automaticamente"
        )
        for detalle in detalles:
            st.write("•", detalle)
        st.success("Conversion automatica aplicada.")

    st.divider()
    st.markdown("**Correccion manual**")
    st.caption("Si la deteccion se equivoco en una columna, forza el tipo correcto aca.")
    col1, col2 = st.columns(2)
    with col1:
        columna_manual = st.selectbox("Columna a convertir", list(datos.columns), key="conv_col")
    with col2:
        destinos = [t.NUMERICA_CONTINUA, t.NUMERICA_DISCRETA, t.FECHA, t.BOOLEANA, t.CATEGORICA, t.TEXTO]
        destino = st.selectbox("Tipo destino", destinos, key="conv_tipo")

    if st.button("Convertir columna"):
        try:
            resultado, detalle = limpieza.convertir_columna(datos, columna_manual, destino)
        except Exception as exc:
            st.error(f"No se pudo convertir: {exc}")
        else:
            estado.actualizar_datos(resultado, "Tipos", detalle)
            st.success(detalle)
            st.rerun()

# --------------------------------------------------------------------------- #
# Bitacora
# --------------------------------------------------------------------------- #
with pestanas[4]:
    st.subheader("Bitacora de operaciones")
    st.caption("Registro de todo lo que se le hizo al dataset desde que se cargo.")
    registro = estado.bitacora()
    if registro.vacia():
        st.info("Todavia no se aplico ninguna operacion.")
    else:
        st.dataframe(registro.como_dataframe(), use_container_width=True, hide_index=True)

    if st.button("Restaurar el dataset original"):
        estado.restaurar_originales()
        st.success("Se descartaron todos los cambios.")
        st.rerun()

st.page_link("pages/3_Resumen.py", label="Ver el resumen final", icon="📋")

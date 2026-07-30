"""Pagina 1 — Carga de archivos CSV/Excel con validacion y deteccion de tipos."""

import os

import streamlit as st

from core import estado
from core import tipos as t
from core.carga import (
    EXTENSIONES_SOPORTADAS,
    ErrorCarga,
    cargar,
    cargar_csv,
    cargar_excel,
    detectar_codificacion,
    detectar_separador,
    listar_hojas,
    validar_archivo,
)

st.set_page_config(page_title="Carga de datos", page_icon="📁", layout="wide")
estado.inicializar()

RUTA_EJEMPLO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "datos_ejemplo",
    "clientes_sucio.csv",
)

st.title("📁 Carga de datos")
st.caption("CSV y Excel — validacion de formato, deteccion automatica y manejo de errores")


# --------------------------------------------------------------------------- #
# Bloques de interfaz
# --------------------------------------------------------------------------- #

def opciones_csv(archivo) -> dict:
    contenido = archivo.getvalue()
    codificacion_auto = detectar_codificacion(contenido)
    try:
        separador_auto = detectar_separador(contenido.decode(codificacion_auto, errors="replace"))
    except Exception:
        separador_auto = ","

    nombres_sep = {",": "Coma ( , )", ";": "Punto y coma ( ; )", "\t": "Tabulacion", "|": "Barra ( | )"}
    lista_sep = list(nombres_sep)

    with st.expander("Opciones de lectura (detectadas automaticamente)"):
        col1, col2, col3 = st.columns(3)
        with col1:
            separador = st.selectbox(
                "Separador",
                lista_sep,
                index=lista_sep.index(separador_auto) if separador_auto in lista_sep else 0,
                format_func=lambda s: nombres_sep[s],
            )
        with col2:
            codificaciones = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
            codificacion = st.selectbox(
                "Codificacion",
                codificaciones,
                index=codificaciones.index(codificacion_auto) if codificacion_auto in codificaciones else 0,
            )
        with col3:
            decimal = st.selectbox("Separador decimal", [".", ","], index=0)

    st.caption(f"Deteccion automatica: separador `{separador_auto}`, codificacion `{codificacion_auto}`")
    return {"separador": separador, "codificacion": codificacion, "decimal": decimal}


def bloque_archivo(archivo) -> None:
    """Valida el archivo subido, muestra las opciones y lo carga."""
    try:
        formato = validar_archivo(archivo.name, archivo.size)
    except ErrorCarga as exc:
        st.error(f"❌ {exc}")
        return

    st.success(f"Archivo valido: **{archivo.name}** ({archivo.size / 1024:.1f} KB, formato {formato})")

    if formato == "csv":
        opciones = opciones_csv(archivo)
    else:
        try:
            hojas = listar_hojas(archivo, archivo.name)
        except ErrorCarga as exc:
            st.error(f"❌ {exc}")
            return
        opciones = {"hoja": st.selectbox("Hoja del libro", hojas)}

    if not st.button("Cargar archivo", type="primary"):
        return

    try:
        with st.spinner("Leyendo el archivo..."):
            if formato == "csv":
                resultado = cargar_csv(archivo, archivo.name, **opciones)
            else:
                resultado = cargar_excel(archivo, archivo.name, hoja=opciones["hoja"])
    except ErrorCarga as exc:
        st.error(f"❌ {exc}")
        return
    except Exception as exc:  # un fallo inesperado no debe tumbar la app
        st.error(f"❌ Error inesperado al leer el archivo: {exc}")
        return

    estado.guardar_carga(resultado)
    st.success(f"✅ Cargado correctamente — {resultado.resumen()}")
    for advertencia in resultado.advertencias:
        st.warning(f"⚠️ {advertencia}")


def bloque_sin_archivo() -> None:
    st.info("Arrastra un archivo o usa el boton para seleccionarlo.")

    if os.path.exists(RUTA_EJEMPLO):
        st.caption(
            "Tambien podes usar el dataset de ejemplo, que trae duplicados, nulos "
            "escritos de varias formas, numeros con simbolo de moneda y fechas como texto."
        )
        if st.button("Cargar dataset de ejemplo"):
            try:
                resultado = cargar(RUTA_EJEMPLO, "clientes_sucio.csv", os.path.getsize(RUTA_EJEMPLO))
            except ErrorCarga as exc:
                st.error(f"❌ {exc}")
            else:
                estado.guardar_carga(resultado)
                st.rerun()

    with st.expander("¿Que valida esta pagina?"):
        st.markdown(
            """
- **Extension**: solo CSV/TXT/TSV y XLSX/XLS/XLSM.
- **Tamano**: se rechazan archivos vacios o mayores a 200 MB.
- **Codificacion**: se prueban UTF-8, UTF-8 con BOM, Latin-1 y CP1252.
- **Separador**: se detecta con `csv.Sniffer` y, si falla, contando ocurrencias.
- **Nombres de columna**: se recortan espacios, se nombran las columnas sin
  titulo y se desambiguan los nombres repetidos.
- **Contenido**: se rechaza un archivo que se lea pero no tenga filas o columnas.
            """
        )


def bloque_resultado() -> None:
    datos = estado.obtener_datos()
    perfil = t.perfilar(datos)

    st.divider()
    st.subheader("Vista previa")
    st.dataframe(datos.head(20), use_container_width=True)

    st.subheader("Deteccion automatica del tipo de variable")
    st.caption(
        "El tipo semantico define para que sirve cada columna en los analisis "
        "posteriores. Podes corregirlo en la pagina de limpieza."
    )
    st.dataframe(
        perfil.rename(
            columns={
                "columna": "Columna",
                "tipo": "Tipo detectado",
                "dtype_pandas": "dtype pandas",
                "no_nulos": "No nulos",
                "nulos": "Nulos",
                "porcentaje_nulos": "% nulos",
                "unicos": "Unicos",
                "cardinalidad": "Cardinalidad",
                "ejemplo": "Ejemplo",
                "razon": "Criterio aplicado",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    grupos = t.columnas_analizables(perfil)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Numericas", len(grupos["numericas"]))
    c2.metric("Categoricas", len(grupos["categoricas"]))
    c3.metric("Fechas", len(grupos["fechas"]))
    c4.metric("A excluir", len(grupos["excluir"]))

    with st.expander("Que significa cada tipo"):
        for tipo, descripcion in t.DESCRIPCIONES.items():
            st.markdown(f"- **{tipo}** — {descripcion}")

    st.page_link("pages/2_Limpieza.py", label="Continuar a la limpieza", icon="🧹")


# --------------------------------------------------------------------------- #
# Flujo de la pagina
# --------------------------------------------------------------------------- #

archivo = st.file_uploader(
    "Selecciona un archivo",
    type=[ext.lstrip(".") for ext in sorted(EXTENSIONES_SOPORTADAS)],
    help=f"Formatos soportados: {', '.join(sorted(EXTENSIONES_SOPORTADAS))}",
)

if archivo is None:
    bloque_sin_archivo()
else:
    bloque_archivo(archivo)

if estado.hay_datos():
    bloque_resultado()

"""Estado compartido entre paginas de Streamlit.
 
Cualquier pagina nueva (clustering, outliers, correlaciones) debe usar
`obtener_datos()` para trabajar sobre el dataset ya limpio, y
`hay_datos()` para avisar si todavia no se cargo nada.
 
Ademas de los datos, este modulo guarda un registro de "secciones de
reporte" (ver core/reportes.py): cada pagina, luego de calcular sus
tablas y graficos, llama a `registrar_seccion(...)`. Asi el reporte
consolidado puede juntar en orden lo que ya se calculo en cada pagina
sin volver a correr nada.
"""
 
from __future__ import annotations
 
import pandas as pd
import streamlit as st
 
from .carga import ResultadoCarga
from .limpieza import Bitacora
from . import tipos as t
 
CLAVE_ORIGINAL = "datos_originales"
CLAVE_TRABAJO = "datos_trabajo"
CLAVE_META = "metadatos_carga"
CLAVE_BITACORA = "bitacora"
CLAVE_SECCIONES = "secciones_reporte"
 
 
def inicializar() -> None:
    st.session_state.setdefault(CLAVE_ORIGINAL, None)
    st.session_state.setdefault(CLAVE_TRABAJO, None)
    st.session_state.setdefault(CLAVE_META, None)
    st.session_state.setdefault(CLAVE_BITACORA, Bitacora())
    st.session_state.setdefault(CLAVE_SECCIONES, {})
 
 
def guardar_carga(resultado: ResultadoCarga) -> None:
    st.session_state[CLAVE_ORIGINAL] = resultado.datos.copy()
    st.session_state[CLAVE_TRABAJO] = resultado.datos.copy()
    st.session_state[CLAVE_META] = resultado
    st.session_state[CLAVE_BITACORA] = Bitacora()
    st.session_state[CLAVE_BITACORA].registrar(
        "Carga", f"{resultado.nombre_archivo} ({resultado.resumen()})", 0, resultado.filas
    )
    st.session_state[CLAVE_SECCIONES] = {}
 
 
def hay_datos() -> bool:
    return st.session_state.get(CLAVE_TRABAJO) is not None
 
 
def obtener_datos() -> pd.DataFrame | None:
    return st.session_state.get(CLAVE_TRABAJO)
 
 
def obtener_originales() -> pd.DataFrame | None:
    return st.session_state.get(CLAVE_ORIGINAL)
 
 
def obtener_metadatos() -> ResultadoCarga | None:
    return st.session_state.get(CLAVE_META)
 
 
def actualizar_datos(datos: pd.DataFrame, operacion: str, detalle: str) -> None:
    antes = len(st.session_state[CLAVE_TRABAJO]) if hay_datos() else 0
    st.session_state[CLAVE_TRABAJO] = datos
    bitacora().registrar(operacion, detalle, antes, len(datos))
 
 
def bitacora() -> Bitacora:
    inicializar()
    return st.session_state[CLAVE_BITACORA]
 
 
def restaurar_originales() -> None:
    originales = obtener_originales()
    if originales is not None:
        st.session_state[CLAVE_TRABAJO] = originales.copy()
        st.session_state[CLAVE_BITACORA] = Bitacora()
 
 
def limpiar_todo() -> None:
    for clave in (CLAVE_ORIGINAL, CLAVE_TRABAJO, CLAVE_META, CLAVE_BITACORA, CLAVE_SECCIONES):
        st.session_state.pop(clave, None)
    inicializar()
 
 
def perfil_actual() -> pd.DataFrame | None:
    """Perfil de tipos recalculado sobre el dataset de trabajo."""
    datos = obtener_datos()
    return None if datos is None else t.perfilar(datos)
 
 
def exigir_datos(mensaje: str = "Primero carga un archivo en la pagina 'Carga de datos'.") -> pd.DataFrame:
    """Corta la ejecucion de la pagina si todavia no hay dataset."""
    inicializar()
    if not hay_datos():
        st.warning(mensaje)
        st.stop()
    return obtener_datos()
 
 
# --------------------------------------------------------------------------- #
# Registro de secciones de reporte (para exportar HTML/PDF)
# --------------------------------------------------------------------------- #
 
def registrar_seccion(clave: str, seccion) -> None:
    """Guarda (o reemplaza) la SeccionReporte de una pagina, para el reporte consolidado.
 
    `clave` es un identificador corto y estable por pagina, p.ej. "outliers",
    "clustering", "visualizaciones", "resumen_estadistico".
    """
    inicializar()
    st.session_state[CLAVE_SECCIONES][clave] = seccion
 
 
def obtener_seccion(clave: str):
    return st.session_state.get(CLAVE_SECCIONES, {}).get(clave)
 
 
def obtener_secciones(orden: list[str] | None = None) -> list:
    """Devuelve las secciones ya registradas.
 
    Si se pasa `orden` (lista de claves), devuelve solo esas y en ese orden,
    ignorando las que todavia no se hayan calculado/visitado. Sin `orden`,
    devuelve todas en el orden en que se registraron.
    """
    guardadas = st.session_state.get(CLAVE_SECCIONES, {})
    if orden is None:
        return list(guardadas.values())
    return [guardadas[clave] for clave in orden if clave in guardadas]
 
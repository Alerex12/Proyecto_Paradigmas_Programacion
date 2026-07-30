"""Estado compartido entre paginas de Streamlit.

Cualquier pagina nueva (clustering, outliers, correlaciones) debe usar
`obtener_datos()` para trabajar sobre el dataset ya limpio, y
`hay_datos()` para avisar si todavia no se cargo nada.
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


def inicializar() -> None:
    st.session_state.setdefault(CLAVE_ORIGINAL, None)
    st.session_state.setdefault(CLAVE_TRABAJO, None)
    st.session_state.setdefault(CLAVE_META, None)
    st.session_state.setdefault(CLAVE_BITACORA, Bitacora())


def guardar_carga(resultado: ResultadoCarga) -> None:
    st.session_state[CLAVE_ORIGINAL] = resultado.datos.copy()
    st.session_state[CLAVE_TRABAJO] = resultado.datos.copy()
    st.session_state[CLAVE_META] = resultado
    st.session_state[CLAVE_BITACORA] = Bitacora()
    st.session_state[CLAVE_BITACORA].registrar(
        "Carga", f"{resultado.nombre_archivo} ({resultado.resumen()})", 0, resultado.filas
    )


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
    for clave in (CLAVE_ORIGINAL, CLAVE_TRABAJO, CLAVE_META, CLAVE_BITACORA):
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

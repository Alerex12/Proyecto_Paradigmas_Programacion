"""
Estadísticas descriptivas y análisis de correlaciones.

Este módulo calcula automáticamente estadísticas descriptivas y
matrices de correlación para las columnas numéricas del dataset.
"""
from __future__ import annotations
import pandas as pd
import numpy as np 

from . import tipos as t

PERCENTILES_POR_DEFECTO = [0.05, 0.25, 0.5, 0.75, 0.95]
def resumen_estadistico(
        datos:pd.DataFrame, 
        columnas: list[str] | None = None, 
        percentiles: list[float] | None = None,
) -> pd.DataFrame: 
    if percentiles is None:
        percentiles = PERCENTILES_POR_DEFECTO
    if columnas is None: 
        columnas = datos.select_dtypes(include="number").columns.tolist()
    filas = []
    for col in columnas:
        serie = t.a_numerico(datos[col])
        descripcion = {
            "columna": col,
            "count": int(serie.count()),
            "nulos": int(serie.isna().sum()),
            "media": serie.mean(),
            "mediana": serie.median(),
            "desviacion_std": serie.std(),
            "varianza": serie.var(),
            "minimo": serie.min(),
            "maximo": serie.max(),
            "rango": (serie.max() - serie.min()) if serie.count() else np.nan,
            "asimetria": serie.skew(),
            "curtosis": serie.kurt(),
        }
        for p in percentiles:
            etiqueta = f"p{int(round(p * 100))}"
            descripcion[etiqueta] = serie.quantile(p)
        filas.append(descripcion)
    
    resumen = pd.DataFrame(filas).set_index("columna")
    return resumen

#Matrices de correlacion
METODOS_VALIDOS = ("pearson", "spearman")
 
def matriz_correlacion(
    datos: pd.DataFrame,
    columnas: list[str] | None = None,
    metodo: str = "pearson",
) -> pd.DataFrame:
    if metodo not in METODOS_VALIDOS:
        raise ValueError(
            f"Método '{metodo}' no soportado. Use uno de {METODOS_VALIDOS}."
        )
 
    if columnas is None:
        columnas = datos.select_dtypes(include="number").columns.tolist()
 
    if len(columnas) < 2:
        raise ValueError(
            "Se necesitan al menos 2 columnas numéricas para calcular correlaciones."
        )
 
    subconjunto = datos[columnas].apply(t.a_numerico)
    return subconjunto.corr(method=metodo)


def pares_mas_correlacionados(
    matriz: pd.DataFrame,
    top_n: int = 10,
    umbral_minimo: float = 0.0,
) -> pd.DataFrame:
    pares = []
    columnas = matriz.columns.tolist()
    for i, col_a in enumerate(columnas):
        for col_b in columnas[i + 1:]:
            valor = matriz.loc[col_a, col_b]
            if pd.isna(valor):
                continue
            if abs(valor) >= umbral_minimo:
                pares.append(
                    {
                        "variable_1": col_a,
                        "variable_2": col_b,
                        "correlacion": valor,
                        "correlacion_absoluta": abs(valor),
                    }
                )
 
    tabla = pd.DataFrame(pares)
    if tabla.empty:
        return tabla
    tabla = tabla.sort_values(
        "correlacion_absoluta", ascending=False
    ).drop(columns="correlacion_absoluta")
    return tabla.head(top_n).reset_index(drop=True)
 
#resumen 
def generar_resumen_estadistico(
    datos: pd.DataFrame,
    columnas: list[str] | None = None,
) -> dict:
    if columnas is None:
        columnas = datos.select_dtypes(include="number").columns.tolist()
 
    resultado = {
        "descriptivos": resumen_estadistico(datos, columnas),
        "columnas_analizadas": columnas,
    }
 
    if len(columnas) >= 2:
        pearson = matriz_correlacion(datos, columnas, metodo="pearson")
        spearman = matriz_correlacion(datos, columnas, metodo="spearman")
        resultado["correlacion_pearson"] = pearson
        resultado["correlacion_spearman"] = spearman
        resultado["pares_top_pearson"] = pares_mas_correlacionados(pearson)
        resultado["pares_top_spearman"] = pares_mas_correlacionados(spearman)
    else:
        resultado["correlacion_pearson"] = None
        resultado["correlacion_spearman"] = None
        resultado["pares_top_pearson"] = None
        resultado["pares_top_spearman"] = None
 
    return resultado
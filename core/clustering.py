"""Clustering (K-Means y DBSCAN) y metricas de calidad de los grupos.

Antes de agrupar hay que escalar las variables: si una columna esta en miles
y otra en unidades, la de mayor escala domina la distancia euclidiana. Por
eso preparar_datos() siempre devuelve valores estandarizados (media 0,
desvio 1). Ninguna funcion modifica el DataFrame recibido.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

# Parametros por defecto (centralizados para poder justificarlos en el informe)
K_MINIMO = 2
K_MAXIMO = 10
EPS_POR_DEFECTO = 0.5
MIN_MUESTRAS_POR_DEFECTO = 5
SEMILLA_ALEATORIA = 42

RUIDO_DBSCAN = -1  # etiqueta que usa sklearn para los puntos que no entran en ningun cluster


def _validar_columnas(datos: pd.DataFrame, columnas: list[str]) -> None:
    if len(columnas) < 2:
        raise ValueError("Se necesitan al menos 2 columnas numericas para agrupar.")
    faltantes = [c for c in columnas if c not in datos.columns]
    if faltantes:
        raise ValueError(f"Columnas inexistentes: {', '.join(faltantes)}")
    no_numericas = [c for c in columnas if not pd.api.types.is_numeric_dtype(datos[c])]
    if no_numericas:
        raise ValueError(f"Columnas no numericas: {', '.join(no_numericas)}")


@dataclass
class ResultadoClustering:
    """Etiquetas asignadas junto con las metricas de calidad del agrupamiento."""

    metodo: str
    columnas: list[str]
    parametros: dict
    etiquetas: np.ndarray
    indices: pd.Index  # filas del DataFrame original que se usaron (tras descartar nulos)
    n_clusters: int
    n_ruido: int
    silhouette: float | None
    calinski_harabasz: float | None
    davies_bouldin: float | None

    def resumen(self) -> str:
        partes = [f"{self.n_clusters} clusters"]
        if self.n_ruido:
            partes.append(f"{self.n_ruido} puntos de ruido")
        if self.silhouette is not None:
            partes.append(f"silhouette {self.silhouette:.3f}")
        else:
            partes.append("silhouette no calculable")
        return " | ".join(partes)


def preparar_datos(datos: pd.DataFrame, columnas: list[str]) -> tuple[pd.DataFrame, StandardScaler]:
    """Descarta filas con nulos en las columnas elegidas y estandariza (media 0, desvio 1)."""
    _validar_columnas(datos, columnas)
    subconjunto = datos[columnas].dropna()
    if len(subconjunto) < 2:
        raise ValueError("No hay suficientes filas sin nulos en estas columnas para agrupar.")

    escalador = StandardScaler()
    escalado = escalador.fit_transform(subconjunto)
    return pd.DataFrame(escalado, index=subconjunto.index, columns=columnas), escalador


def _metricas(datos_escalados: pd.DataFrame, etiquetas: np.ndarray) -> dict:
    """Silhouette, Calinski-Harabasz y Davies-Bouldin. None si no se pueden calcular (< 2 clusters)."""
    etiquetas_validas = set(etiquetas) - {RUIDO_DBSCAN}
    if len(etiquetas_validas) < 2 or len(etiquetas_validas) >= len(datos_escalados):
        return {"silhouette": None, "calinski_harabasz": None, "davies_bouldin": None}

    mascara = etiquetas != RUIDO_DBSCAN
    x = datos_escalados[mascara]
    y = etiquetas[mascara]
    return {
        "silhouette": round(float(silhouette_score(x, y)), 4),
        "calinski_harabasz": round(float(calinski_harabasz_score(x, y)), 2),
        "davies_bouldin": round(float(davies_bouldin_score(x, y)), 4),
    }


# --------------------------------------------------------------------------- #
# K-Means
# --------------------------------------------------------------------------- #

def metodo_codo(datos: pd.DataFrame, columnas: list[str], k_minimo: int = K_MINIMO, k_maximo: int = K_MAXIMO) -> pd.DataFrame:
    """Inercia para cada K, para elegir el numero de clusters por el metodo del codo."""
    datos_escalados, _ = preparar_datos(datos, columnas)
    filas = []
    for k in range(k_minimo, k_maximo + 1):
        modelo = KMeans(n_clusters=k, random_state=SEMILLA_ALEATORIA, n_init="auto")
        modelo.fit(datos_escalados)
        filas.append({"k": k, "inercia": round(float(modelo.inertia_), 2)})
    return pd.DataFrame(filas)


def ajustar_kmeans(datos: pd.DataFrame, columnas: list[str], k: int) -> ResultadoClustering:
    datos_escalados, _ = preparar_datos(datos, columnas)
    modelo = KMeans(n_clusters=k, random_state=SEMILLA_ALEATORIA, n_init="auto")
    etiquetas = modelo.fit_predict(datos_escalados)

    return ResultadoClustering(
        metodo="kmeans",
        columnas=columnas,
        parametros={"k": k},
        etiquetas=etiquetas,
        indices=datos_escalados.index,
        n_clusters=k,
        n_ruido=0,
        **_metricas(datos_escalados, etiquetas),
    )


# --------------------------------------------------------------------------- #
# DBSCAN
# --------------------------------------------------------------------------- #

def ajustar_dbscan(
    datos: pd.DataFrame,
    columnas: list[str],
    eps: float = EPS_POR_DEFECTO,
    min_muestras: int = MIN_MUESTRAS_POR_DEFECTO,
) -> ResultadoClustering:
    datos_escalados, _ = preparar_datos(datos, columnas)
    modelo = DBSCAN(eps=eps, min_samples=min_muestras)
    etiquetas = modelo.fit_predict(datos_escalados)

    return ResultadoClustering(
        metodo="dbscan",
        columnas=columnas,
        parametros={"eps": eps, "min_muestras": min_muestras},
        etiquetas=etiquetas,
        indices=datos_escalados.index,
        n_clusters=len(set(etiquetas) - {RUIDO_DBSCAN}),
        n_ruido=int((etiquetas == RUIDO_DBSCAN).sum()),
        **_metricas(datos_escalados, etiquetas),
    )


# --------------------------------------------------------------------------- #
# Resultado sobre el dataset
# --------------------------------------------------------------------------- #

def asignar_etiquetas(datos: pd.DataFrame, resultado: ResultadoClustering, nombre_columna: str = "cluster") -> pd.DataFrame:
    """Copia de datos con una columna nueva con la etiqueta de cluster.

    Las filas que no se usaron (nulos en alguna columna elegida) quedan con
    valor nulo en la columna nueva.
    """
    copia = datos.copy()
    copia[nombre_columna] = pd.NA
    copia.loc[resultado.indices, nombre_columna] = resultado.etiquetas
    return copia

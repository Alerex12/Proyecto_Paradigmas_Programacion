"""Deteccion de valores atipicos: Z-Score, IQR e Isolation Forest.

Z-Score e IQR son univariados: evaluan cada columna por separado. Isolation
Forest es multivariado: puede marcar una fila como atipica por una
combinacion rara de valores aunque ninguna columna individual se salga de
rango. Ninguna funcion modifica el DataFrame recibido.
"""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest

# Umbrales de decision (centralizados para poder justificarlos en el informe)
UMBRAL_Z_SCORE = 3.0
MULTIPLICADOR_IQR = 1.5
CONTAMINACION_ISOLATION_FOREST = 0.05  # % esperado de atipicos
SEMILLA_ALEATORIA = 42

METODOS = {
    "zscore": "Z-Score (univariado, supone distribucion normal)",
    "iqr": "Rango intercuartilico (univariado, robusto a distribuciones no normales)",
    "isolation_forest": "Isolation Forest (multivariado, combinaciones raras entre variables)",
}


def _validar_columnas(datos: pd.DataFrame, columnas: list[str]) -> None:
    if not columnas:
        raise ValueError("Elegi al menos una columna numerica.")
    faltantes = [c for c in columnas if c not in datos.columns]
    if faltantes:
        raise ValueError(f"Columnas inexistentes: {', '.join(faltantes)}")
    no_numericas = [c for c in columnas if not pd.api.types.is_numeric_dtype(datos[c])]
    if no_numericas:
        raise ValueError(f"Columnas no numericas: {', '.join(no_numericas)}")


# --------------------------------------------------------------------------- #
# Z-Score
# --------------------------------------------------------------------------- #

def detectar_outliers_zscore(
    datos: pd.DataFrame, columnas: list[str], umbral: float = UMBRAL_Z_SCORE
) -> pd.DataFrame:
    """Mascara booleana por columna: True si |z| > umbral. Los nulos nunca se marcan."""
    _validar_columnas(datos, columnas)
    mascara = pd.DataFrame(False, index=datos.index, columns=columnas)
    for columna in columnas:
        serie = datos[columna]
        desviacion = serie.std(ddof=0)
        if not desviacion or pd.isna(desviacion):
            continue  # columna constante: no hay nada que marcar
        z = (serie - serie.mean()) / desviacion
        mascara[columna] = z.abs() > umbral
    return mascara


# --------------------------------------------------------------------------- #
# IQR
# --------------------------------------------------------------------------- #

def detectar_outliers_iqr(
    datos: pd.DataFrame, columnas: list[str], multiplicador: float = MULTIPLICADOR_IQR
) -> pd.DataFrame:
    """Mascara booleana por columna: True si cae fuera de [Q1 - m*IQR, Q3 + m*IQR]."""
    _validar_columnas(datos, columnas)
    mascara = pd.DataFrame(False, index=datos.index, columns=columnas)
    for columna in columnas:
        serie = datos[columna]
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        if not iqr or pd.isna(iqr):
            continue
        limite_inferior = q1 - multiplicador * iqr
        limite_superior = q3 + multiplicador * iqr
        mascara[columna] = (serie < limite_inferior) | (serie > limite_superior)
    return mascara


# --------------------------------------------------------------------------- #
# Isolation Forest
# --------------------------------------------------------------------------- #

def detectar_outliers_isolation_forest(
    datos: pd.DataFrame,
    columnas: list[str],
    contaminacion: float = CONTAMINACION_ISOLATION_FOREST,
    semilla: int = SEMILLA_ALEATORIA,
) -> pd.Series:
    """Mascara booleana unica por fila: deteccion multivariada, no columna por columna."""
    _validar_columnas(datos, columnas)
    subconjunto = datos[columnas].dropna()
    if len(subconjunto) < 2:
        return pd.Series(False, index=datos.index)

    modelo = IsolationForest(contamination=contaminacion, random_state=semilla)
    prediccion = modelo.fit_predict(subconjunto)  # -1 = atipico, 1 = normal

    mascara = pd.Series(False, index=datos.index)
    mascara.loc[subconjunto.index] = prediccion == -1
    return mascara


# --------------------------------------------------------------------------- #
# Resumen y accion sobre el dataset
# --------------------------------------------------------------------------- #

def mascara_combinada(mascara_por_columna: pd.DataFrame) -> pd.Series:
    """Una fila se considera atipica si al menos una columna la marco."""
    return mascara_por_columna.any(axis=1)


def resumen_outliers(datos: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Compara cuantos atipicos detecta cada metodo univariado, columna por columna."""
    _validar_columnas(datos, columnas)
    zscore = detectar_outliers_zscore(datos, columnas)
    iqr = detectar_outliers_iqr(datos, columnas)

    filas = [
        {
            "columna": columna,
            "atipicos_zscore": int(zscore[columna].sum()),
            "porcentaje_zscore": round(zscore[columna].mean() * 100, 2),
            "atipicos_iqr": int(iqr[columna].sum()),
            "porcentaje_iqr": round(iqr[columna].mean() * 100, 2),
        }
        for columna in columnas
    ]
    return pd.DataFrame(filas)


def eliminar_outliers(datos: pd.DataFrame, mascara: pd.Series) -> tuple[pd.DataFrame, int]:
    """Elimina las filas marcadas como True. Devuelve (datos, cantidad eliminada)."""
    resultado = datos.loc[~mascara].reset_index(drop=True)
    return resultado, int(mascara.sum())

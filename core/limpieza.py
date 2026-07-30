"""Limpieza basica: duplicados, valores nulos y conversion de tipos.

Cada operacion devuelve (DataFrame nuevo, registro) para poder mostrar una
bitacora de lo que se le hizo al dataset. Ninguna funcion modifica el
DataFrame original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from . import tipos as t

NULOS_TEXTUALES = [
    "", " ", "na", "n/a", "n.a.", "null", "none", "nan", "-", "--",
    "sin dato", "sin datos", "desconocido", "?", "#n/a", "nd",
]

ESTRATEGIAS_NULOS = {
    "conservar": "Dejar los nulos como estan",
    "eliminar_filas": "Eliminar las filas que tengan nulo en esta columna",
    "media": "Rellenar con la media (solo numericas)",
    "mediana": "Rellenar con la mediana (solo numericas)",
    "moda": "Rellenar con el valor mas frecuente",
    "cero": "Rellenar con 0 (solo numericas)",
    "constante": "Rellenar con un valor fijo que vos indiques",
}


@dataclass
class Bitacora:
    """Historial de operaciones aplicadas al dataset."""

    entradas: list[dict] = field(default_factory=list)

    def registrar(self, operacion: str, detalle: str, filas_antes: int, filas_despues: int) -> None:
        self.entradas.append(
            {
                "momento": datetime.now().strftime("%H:%M:%S"),
                "operacion": operacion,
                "detalle": detalle,
                "filas_antes": filas_antes,
                "filas_despues": filas_despues,
                "delta_filas": filas_despues - filas_antes,
            }
        )

    def como_dataframe(self) -> pd.DataFrame:
        if not self.entradas:
            return pd.DataFrame(
                columns=["momento", "operacion", "detalle", "filas_antes", "filas_despues", "delta_filas"]
            )
        return pd.DataFrame(self.entradas)

    def vacia(self) -> bool:
        return not self.entradas


# --------------------------------------------------------------------------- #
# Normalizacion previa
# --------------------------------------------------------------------------- #

def normalizar_nulos(datos: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Convierte marcadores textuales ("N/A", "-", "sin dato") en NaN reales."""
    resultado = datos.copy()
    nulos_antes = int(resultado.isna().sum().sum())

    for columna in resultado.columns:
        if t.es_texto(resultado[columna]):
            serie = resultado[columna].astype(str).str.strip()
            mascara = serie.str.lower().isin(NULOS_TEXTUALES)
            if mascara.any():
                resultado[columna] = resultado[columna].astype("object").mask(mascara, None)

    nulos_despues = int(resultado.isna().sum().sum())
    return resultado, nulos_despues - nulos_antes


def recortar_espacios(datos: pd.DataFrame) -> pd.DataFrame:
    """Quita espacios sobrantes al inicio y final de los valores de texto."""
    resultado = datos.copy()
    for columna in resultado.columns:
        if t.es_texto(resultado[columna]):
            resultado[columna] = resultado[columna].apply(
                lambda v: v.strip() if isinstance(v, str) else v
            )
    return resultado


# --------------------------------------------------------------------------- #
# Duplicados
# --------------------------------------------------------------------------- #

def contar_duplicados(datos: pd.DataFrame, subconjunto: list[str] | None = None) -> int:
    return int(datos.duplicated(subset=subconjunto, keep="first").sum())


def eliminar_duplicados(
    datos: pd.DataFrame,
    subconjunto: list[str] | None = None,
    conservar: str = "first",
) -> tuple[pd.DataFrame, int]:
    antes = len(datos)
    resultado = datos.drop_duplicates(subset=subconjunto, keep=conservar).reset_index(drop=True)
    return resultado, antes - len(resultado)


# --------------------------------------------------------------------------- #
# Nulos
# --------------------------------------------------------------------------- #

def resumen_nulos(datos: pd.DataFrame) -> pd.DataFrame:
    nulos = datos.isna().sum()
    resumen = pd.DataFrame(
        {
            "columna": nulos.index,
            "nulos": nulos.values,
            "porcentaje": (nulos.values / len(datos) * 100).round(2) if len(datos) else 0,
        }
    )
    return resumen.sort_values("nulos", ascending=False).reset_index(drop=True)


def aplicar_estrategia_nulos(
    datos: pd.DataFrame,
    columna: str,
    estrategia: str,
    valor_constante=None,
) -> tuple[pd.DataFrame, str]:
    """Aplica una estrategia de imputacion a una columna. Devuelve (datos, detalle)."""
    if columna not in datos.columns:
        raise KeyError(f"La columna '{columna}' no existe.")
    if estrategia not in ESTRATEGIAS_NULOS:
        raise ValueError(f"Estrategia desconocida: {estrategia}")

    resultado = datos.copy()
    serie = resultado[columna]
    faltantes = int(serie.isna().sum())

    if estrategia == "conservar" or faltantes == 0:
        return resultado, f"'{columna}': sin cambios ({faltantes} nulos)."

    if estrategia == "eliminar_filas":
        resultado = resultado.dropna(subset=[columna]).reset_index(drop=True)
        return resultado, f"'{columna}': se eliminaron {faltantes} filas con nulo."

    if estrategia in ("media", "mediana", "cero"):
        if not pd.api.types.is_numeric_dtype(serie):
            raise ValueError(
                f"'{columna}' no es numerica; la estrategia '{estrategia}' no aplica."
            )
        relleno = {"media": serie.mean(), "mediana": serie.median(), "cero": 0}[estrategia]
        resultado[columna] = serie.fillna(relleno)
        return resultado, f"'{columna}': {faltantes} nulos rellenados con {estrategia} ({relleno:.4g})."

    if estrategia == "moda":
        moda = serie.mode(dropna=True)
        if moda.empty:
            return resultado, f"'{columna}': sin moda calculable, se conservaron los nulos."
        resultado[columna] = serie.fillna(moda.iloc[0])
        return resultado, f"'{columna}': {faltantes} nulos rellenados con la moda ({moda.iloc[0]!r})."

    # constante
    resultado[columna] = serie.fillna(valor_constante)
    return resultado, f"'{columna}': {faltantes} nulos rellenados con {valor_constante!r}."


def eliminar_columnas_vacias(datos: pd.DataFrame, umbral: float = 0.95) -> tuple[pd.DataFrame, list[str]]:
    """Descarta columnas con un porcentaje de nulos por encima del umbral (0-1)."""
    if datos.empty:
        return datos.copy(), []
    proporcion = datos.isna().mean()
    a_eliminar = proporcion[proporcion >= umbral].index.tolist()
    return datos.drop(columns=a_eliminar), a_eliminar


# --------------------------------------------------------------------------- #
# Conversion de tipos
# --------------------------------------------------------------------------- #

def convertir_columna(datos: pd.DataFrame, columna: str, tipo_destino: str) -> tuple[pd.DataFrame, str]:
    """Convierte una columna al tipo indicado (los mismos tipos de core.tipos)."""
    resultado = datos.copy()
    serie = resultado[columna]
    validos_antes = int(serie.notna().sum())

    if tipo_destino in t.APTOS_NUMERICOS:
        limpia = (
            serie.astype(str)
            .str.replace(r"[$₡€\s%]", "", regex=True)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        convertida = pd.to_numeric(limpia, errors="coerce")
        # Si limpiar separadores empeora el resultado, usar la conversion directa.
        directa = pd.to_numeric(serie, errors="coerce")
        if directa.notna().sum() >= convertida.notna().sum():
            convertida = directa
        if tipo_destino == t.NUMERICA_DISCRETA:
            convertida = convertida.round().astype("Int64")

    elif tipo_destino == t.FECHA:
        convertida = pd.to_datetime(serie, errors="coerce", format="mixed", dayfirst=True)

    elif tipo_destino == t.BOOLEANA:
        mapa = {
            "si": True, "s": True, "true": True, "verdadero": True, "yes": True,
            "y": True, "1": True, "t": True,
            "no": False, "n": False, "false": False, "falso": False, "0": False,
            "f": False,
        }
        convertida = serie.astype(str).str.strip().str.lower().map(mapa).astype("boolean")

    elif tipo_destino in (t.CATEGORICA, t.TEXTO):
        convertida = serie.astype("string")

    else:
        raise ValueError(f"No se puede convertir a '{tipo_destino}'.")

    perdidos = validos_antes - int(convertida.notna().sum())
    resultado[columna] = convertida
    detalle = f"'{columna}' convertida a {tipo_destino}"
    if perdidos > 0:
        detalle += f"; {perdidos} valores no se pudieron convertir y quedaron como nulos"
    return resultado, detalle + "."


def convertir_automatico(datos: pd.DataFrame, perfil: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Aplica la conversion sugerida por la deteccion de tipos a todas las columnas."""
    resultado = datos.copy()
    detalles: list[str] = []
    convertibles = t.APTOS_NUMERICOS | {t.FECHA, t.BOOLEANA, t.CATEGORICA}

    for fila in perfil.itertuples():
        if fila.tipo not in convertibles:
            continue
        ya_numerica = fila.tipo in t.APTOS_NUMERICOS and pd.api.types.is_numeric_dtype(resultado[fila.columna])
        ya_fecha = fila.tipo == t.FECHA and pd.api.types.is_datetime64_any_dtype(resultado[fila.columna])
        if ya_numerica or ya_fecha:
            continue
        try:
            resultado, detalle = convertir_columna(resultado, fila.columna, fila.tipo)
            detalles.append(detalle)
        except Exception as exc:  # una columna problematica no debe frenar el resto
            detalles.append(f"'{fila.columna}': no se pudo convertir ({exc}).")

    return resultado, detalles

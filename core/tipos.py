"""Deteccion automatica del tipo semantico de cada variable.

pandas solo sabe de dtypes (int64, object, float64...). Para los analisis que
vienen despues (clustering, outliers, correlaciones) hace falta saber si una
columna es numerica continua, categorica, fecha, booleana o un identificador.
Ese es el trabajo de este modulo.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd
from pandas.api import types as pdt

# Tipos semanticos posibles
NUMERICA_CONTINUA = "numerica_continua"
NUMERICA_DISCRETA = "numerica_discreta"
CATEGORICA = "categorica"
BOOLEANA = "booleana"
FECHA = "fecha"
TEXTO = "texto"
IDENTIFICADOR = "identificador"
CONSTANTE = "constante"
VACIA = "vacia"

# Que tipos sirven para cada tecnica posterior
APTOS_NUMERICOS = {NUMERICA_CONTINUA, NUMERICA_DISCRETA}
APTOS_CATEGORICOS = {CATEGORICA, BOOLEANA}

DESCRIPCIONES = {
    NUMERICA_CONTINUA: "Numero con decimales o de rango amplio. Apta para clustering, outliers y correlacion.",
    NUMERICA_DISCRETA: "Numero entero con pocos valores distintos. Apta para correlacion; revisar si en realidad es categorica.",
    CATEGORICA: "Conjunto acotado de categorias. Requiere codificacion antes de usarse en clustering.",
    BOOLEANA: "Dos valores (si/no, 0/1, true/false).",
    FECHA: "Fecha u hora. Util para derivar variables (mes, dia, antiguedad).",
    TEXTO: "Texto libre de alta variabilidad. No se usa directo en los modelos.",
    IDENTIFICADOR: "Valor casi unico por fila (ID, cedula, codigo). Debe excluirse de los analisis.",
    CONSTANTE: "Un solo valor en toda la columna. No aporta informacion.",
    VACIA: "Columna sin datos.",
}

VALORES_BOOLEANOS = {
    "si", "no", "s", "n", "true", "false", "verdadero", "falso",
    "yes", "y", "1", "0", "t", "f",
}

# Umbrales de decision (centralizados para poder justificarlos en el informe)
UMBRAL_UNICIDAD_IDENTIFICADOR = 0.95   # % de valores distintos sobre filas no nulas
UMBRAL_CARDINALIDAD_CATEGORICA = 0.50  # por encima de esto, texto libre
MAXIMO_CATEGORIAS = 25                 # tope duro de categorias distintas
MAXIMO_ENTEROS_DISCRETOS = 20          # enteros con <= 20 valores unicos -> discreta
MINIMO_EXITO_FECHA = 0.80              # % de valores que deben parsear como fecha


@dataclass
class PerfilColumna:
    columna: str
    tipo: str
    dtype_pandas: str
    no_nulos: int
    nulos: int
    porcentaje_nulos: float
    unicos: int
    cardinalidad: float
    ejemplo: str
    razon: str

    def como_dict(self) -> dict:
        return asdict(self)


def es_texto(serie: pd.Series) -> bool:
    """True si la columna contiene texto.

    En pandas 3 las columnas de texto pueden venir con dtype 'str' en vez de
    'object', asi que no alcanza con comparar contra object.
    """
    if pdt.is_numeric_dtype(serie) or pdt.is_bool_dtype(serie) or pdt.is_datetime64_any_dtype(serie):
        return False
    return pdt.is_object_dtype(serie) or pdt.is_string_dtype(serie)


def _muestra_texto(serie: pd.Series, limite: int = 1000) -> pd.Series:
    limpia = serie.dropna().astype(str).str.strip()
    return limpia.head(limite)


def _parece_booleana(serie: pd.Series) -> bool:
    valores = set(_muestra_texto(serie).str.lower().unique())
    return 0 < len(valores) <= 2 and valores.issubset(VALORES_BOOLEANOS)


def _parece_fecha(serie: pd.Series) -> bool:
    muestra = _muestra_texto(serie, limite=300)
    if muestra.empty:
        return False
    # Descarta numeros puros: "2024" o "15" no deben tomarse como fecha.
    if muestra.str.fullmatch(r"-?\d+([.,]\d+)?").mean() > 0.9:
        return False
    convertidas = pd.to_datetime(muestra, errors="coerce", format="mixed", dayfirst=True)
    return convertidas.notna().mean() >= MINIMO_EXITO_FECHA


def _numerica_encubierta(serie: pd.Series) -> pd.Series | None:
    """Detecta columnas de texto que en realidad son numeros ("1.234,50", "45%", "$300")."""
    muestra = _muestra_texto(serie, limite=500)
    if muestra.empty:
        return None
    limpia = (
        muestra.str.replace(r"[$₡€\s%]", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    convertida = pd.to_numeric(limpia, errors="coerce")
    if convertida.notna().mean() >= 0.9:
        return convertida
    return None


def detectar_tipo(serie: pd.Series) -> tuple[str, str]:
    """Devuelve (tipo_semantico, razon legible) para una columna."""
    no_nulos = serie.dropna()
    total = len(no_nulos)

    if total == 0:
        return VACIA, "Todos los valores son nulos."

    unicos = no_nulos.nunique(dropna=True)
    if unicos == 1:
        return CONSTANTE, f"Un unico valor repetido ({no_nulos.iloc[0]!r})."

    cardinalidad = unicos / total

    if pdt.is_bool_dtype(serie):
        return BOOLEANA, "dtype booleano de pandas."

    if pdt.is_datetime64_any_dtype(serie):
        return FECHA, "dtype de fecha de pandas."

    if pdt.is_numeric_dtype(serie):
        if unicos == 2:
            return BOOLEANA, "Solo dos valores numericos distintos (binaria)."
        if pdt.is_integer_dtype(serie) or (no_nulos % 1 == 0).all():
            if unicos <= MAXIMO_ENTEROS_DISCRETOS:
                return NUMERICA_DISCRETA, f"Enteros con {unicos} valores distintos."
            if cardinalidad >= UMBRAL_UNICIDAD_IDENTIFICADOR:
                return IDENTIFICADOR, f"Enteros casi unicos ({cardinalidad:.0%} distintos)."
            return NUMERICA_CONTINUA, f"Enteros con {unicos} valores distintos."
        return NUMERICA_CONTINUA, "Valores numericos con decimales."

    # A partir de aca la columna es texto/objeto
    if _parece_booleana(serie):
        return BOOLEANA, "Dos valores de tipo si/no."

    if _numerica_encubierta(serie) is not None:
        return NUMERICA_CONTINUA, "Texto que representa numeros (simbolos o separadores de miles)."

    if _parece_fecha(serie):
        return FECHA, "La mayoria de los valores se interpretan como fecha."

    if cardinalidad >= UMBRAL_UNICIDAD_IDENTIFICADOR:
        return IDENTIFICADOR, f"Casi un valor distinto por fila ({cardinalidad:.0%})."

    if unicos <= MAXIMO_CATEGORIAS and cardinalidad < UMBRAL_CARDINALIDAD_CATEGORICA:
        return CATEGORICA, f"{unicos} categorias distintas."

    return TEXTO, f"Texto de alta variabilidad ({unicos} valores distintos)."


def perfilar_columna(serie: pd.Series, nombre: str) -> PerfilColumna:
    tipo, razon = detectar_tipo(serie)
    no_nulos = int(serie.notna().sum())
    nulos = int(serie.isna().sum())
    total = len(serie)
    unicos = int(serie.nunique(dropna=True))
    muestra = serie.dropna()
    ejemplo = str(muestra.iloc[0])[:60] if not muestra.empty else "-"

    return PerfilColumna(
        columna=nombre,
        tipo=tipo,
        dtype_pandas=str(serie.dtype),
        no_nulos=no_nulos,
        nulos=nulos,
        porcentaje_nulos=round(nulos / total * 100, 2) if total else 0.0,
        unicos=unicos,
        cardinalidad=round(unicos / no_nulos, 4) if no_nulos else 0.0,
        ejemplo=ejemplo,
        razon=razon,
    )


def perfilar(datos: pd.DataFrame) -> pd.DataFrame:
    """Tabla resumen con una fila por columna del dataset."""
    perfiles = [perfilar_columna(datos[col], col).como_dict() for col in datos.columns]
    return pd.DataFrame(perfiles)


def columnas_por_tipo(perfil: pd.DataFrame, tipos: set[str]) -> list[str]:
    return perfil.loc[perfil["tipo"].isin(tipos), "columna"].tolist()


def columnas_analizables(perfil: pd.DataFrame) -> dict[str, list[str]]:
    """Agrupa las columnas segun para que sirven en las etapas siguientes."""
    return {
        "numericas": columnas_por_tipo(perfil, APTOS_NUMERICOS),
        "categoricas": columnas_por_tipo(perfil, APTOS_CATEGORICOS),
        "fechas": columnas_por_tipo(perfil, {FECHA}),
        "excluir": columnas_por_tipo(perfil, {IDENTIFICADOR, CONSTANTE, VACIA, TEXTO}),
    }

def a_numerico(serie: pd.Series) -> pd.Series:
    """Convierte una columna a numerica, entendiendo formatos con simbolo de
    moneda, separador de miles y coma decimal (ej. "¢1.028.842,17").
    """
    directo = pd.to_numeric(serie, errors="coerce")
    if directo.notna().mean() >= 0.9:
        return directo

    limpia = (
        serie.astype(str).str.strip()
        .str.replace(r"[$₡¢€\s%]", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(limpia, errors="coerce")

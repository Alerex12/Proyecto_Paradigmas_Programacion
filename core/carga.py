"""Carga de archivos CSV y Excel con validacion de formato y manejo de errores.

Este modulo no conoce Streamlit: recibe rutas o buffers y devuelve DataFrames.
Asi puede reutilizarse desde la app, desde notebooks o desde tests.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass, field

import pandas as pd

EXTENSIONES_CSV = {".csv", ".txt", ".tsv"}
EXTENSIONES_EXCEL = {".xlsx", ".xls", ".xlsm"}
EXTENSIONES_SOPORTADAS = EXTENSIONES_CSV | EXTENSIONES_EXCEL

TAMANO_MAXIMO_MB = 200
CODIFICACIONES = ("utf-8", "utf-8-sig", "latin-1", "cp1252")


class ErrorCarga(Exception):
    """Error controlado durante la carga: el mensaje es apto para mostrar al usuario."""


@dataclass
class ResultadoCarga:
    """DataFrame cargado junto con los metadatos de como se leyo."""

    datos: pd.DataFrame
    nombre_archivo: str
    formato: str  # "csv" o "excel"
    filas: int
    columnas: int
    separador: str | None = None
    codificacion: str | None = None
    hoja: str | None = None
    advertencias: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        partes = [f"{self.filas:,} filas x {self.columnas} columnas"]
        if self.separador:
            partes.append(f"separador '{self.separador}'")
        if self.codificacion:
            partes.append(f"codificacion {self.codificacion}")
        if self.hoja:
            partes.append(f"hoja '{self.hoja}'")
        return " | ".join(partes)


# --------------------------------------------------------------------------- #
# Validacion previa
# --------------------------------------------------------------------------- #

def extension_de(nombre_archivo: str) -> str:
    return os.path.splitext(nombre_archivo)[1].lower()


def validar_archivo(nombre_archivo: str, tamano_bytes: int | None = None) -> str:
    """Valida extension y tamano. Devuelve el formato ("csv" o "excel")."""
    if not nombre_archivo:
        raise ErrorCarga("No se recibio ningun archivo.")

    ext = extension_de(nombre_archivo)
    if ext not in EXTENSIONES_SOPORTADAS:
        soportadas = ", ".join(sorted(EXTENSIONES_SOPORTADAS))
        raise ErrorCarga(
            f"Formato '{ext or 'desconocido'}' no soportado. Formatos validos: {soportadas}."
        )

    if tamano_bytes is not None:
        mb = tamano_bytes / (1024 * 1024)
        if tamano_bytes == 0:
            raise ErrorCarga("El archivo esta vacio (0 bytes).")
        if mb > TAMANO_MAXIMO_MB:
            raise ErrorCarga(
                f"El archivo pesa {mb:.1f} MB y el limite es {TAMANO_MAXIMO_MB} MB."
            )

    return "csv" if ext in EXTENSIONES_CSV else "excel"


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #

def _leer_bytes(origen) -> bytes:
    """Acepta ruta en disco, bytes o un buffer tipo UploadedFile."""
    if isinstance(origen, (bytes, bytearray)):
        return bytes(origen)
    if isinstance(origen, (str, os.PathLike)):
        with open(origen, "rb") as f:
            return f.read()
    if hasattr(origen, "read"):
        if hasattr(origen, "seek"):
            origen.seek(0)
        contenido = origen.read()
        if hasattr(origen, "seek"):
            origen.seek(0)
        return contenido if isinstance(contenido, bytes) else str(contenido).encode("utf-8")
    raise ErrorCarga("No se pudo leer el origen del archivo.")


def detectar_codificacion(contenido: bytes) -> str:
    """Prueba codificaciones comunes en orden y devuelve la primera que decodifica."""
    muestra = contenido[:200_000]
    for codificacion in CODIFICACIONES:
        try:
            muestra.decode(codificacion)
            return codificacion
        except UnicodeDecodeError:
            continue
    return "latin-1"  # nunca falla, aunque pueda producir caracteres raros


def detectar_separador(texto: str) -> str:
    """Usa csv.Sniffer y cae a un conteo manual si no logra decidir."""
    muestra = texto[:10_000]
    try:
        return csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
    except csv.Error:
        pass

    primeras = [linea for linea in muestra.splitlines() if linea.strip()][:10]
    if not primeras:
        return ","
    conteos = {sep: sum(linea.count(sep) for linea in primeras) for sep in (",", ";", "\t", "|")}
    mejor = max(conteos, key=conteos.get)
    return mejor if conteos[mejor] > 0 else ","


def cargar_csv(
    origen,
    nombre_archivo: str,
    separador: str | None = None,
    codificacion: str | None = None,
    decimal: str = ".",
) -> ResultadoCarga:
    contenido = _leer_bytes(origen)
    if not contenido.strip():
        raise ErrorCarga("El archivo esta vacio.")

    codificacion = codificacion or detectar_codificacion(contenido)
    try:
        texto = contenido.decode(codificacion)
    except UnicodeDecodeError as exc:
        raise ErrorCarga(
            f"No se pudo leer el archivo con la codificacion '{codificacion}'. "
            "Proba con latin-1 o cp1252."
        ) from exc

    separador = separador or detectar_separador(texto)
    advertencias: list[str] = []

    try:
        datos = pd.read_csv(
            io.StringIO(texto),
            sep=separador,
            decimal=decimal,
            skipinitialspace=True,
            on_bad_lines="skip",
        )
    except pd.errors.EmptyDataError as exc:
        raise ErrorCarga("El archivo no contiene datos legibles.") from exc
    except pd.errors.ParserError as exc:
        raise ErrorCarga(
            f"El archivo no pudo interpretarse como CSV con separador '{separador}'. "
            "Elegi el separador manualmente."
        ) from exc

    if datos.shape[1] == 1 and separador != ";":
        advertencias.append(
            "Solo se detecto una columna. Es probable que el separador real sea otro."
        )

    datos, avisos_col = normalizar_nombres_columnas(datos)
    advertencias.extend(avisos_col)
    _validar_dataframe(datos)

    return ResultadoCarga(
        datos=datos,
        nombre_archivo=nombre_archivo,
        formato="csv",
        filas=len(datos),
        columnas=datos.shape[1],
        separador=separador,
        codificacion=codificacion,
        advertencias=advertencias,
    )


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #

def listar_hojas(origen, nombre_archivo: str) -> list[str]:
    try:
        with pd.ExcelFile(io.BytesIO(_leer_bytes(origen)), engine=_motor_excel(nombre_archivo)) as libro:
            return list(libro.sheet_names)
    except ImportError as exc:
        raise ErrorCarga(_mensaje_motor_faltante(nombre_archivo)) from exc
    except Exception as exc:
        raise ErrorCarga(f"No se pudo abrir el archivo de Excel: {exc}") from exc


def _motor_excel(nombre_archivo: str) -> str:
    return "xlrd" if extension_de(nombre_archivo) == ".xls" else "openpyxl"


def _mensaje_motor_faltante(nombre_archivo: str) -> str:
    motor = _motor_excel(nombre_archivo)
    return f"Falta la libreria '{motor}' para leer este Excel. Instalala con: pip install {motor}"


def cargar_excel(origen, nombre_archivo: str, hoja: str | int = 0) -> ResultadoCarga:
    contenido = _leer_bytes(origen)
    advertencias: list[str] = []

    try:
        datos = pd.read_excel(
            io.BytesIO(contenido),
            sheet_name=hoja,
            engine=_motor_excel(nombre_archivo),
        )
    except ImportError as exc:
        raise ErrorCarga(_mensaje_motor_faltante(nombre_archivo)) from exc
    except ValueError as exc:
        raise ErrorCarga(f"La hoja '{hoja}' no existe en el archivo.") from exc
    except Exception as exc:
        raise ErrorCarga(f"No se pudo leer el archivo de Excel: {exc}") from exc

    if isinstance(datos, dict):  # sheet_name=None devolveria todas las hojas
        nombre_hoja, datos = next(iter(datos.items()))
    else:
        nombre_hoja = hoja if isinstance(hoja, str) else listar_hojas(contenido, nombre_archivo)[hoja]

    datos, avisos_col = normalizar_nombres_columnas(datos)
    advertencias.extend(avisos_col)
    _validar_dataframe(datos)

    return ResultadoCarga(
        datos=datos,
        nombre_archivo=nombre_archivo,
        formato="excel",
        filas=len(datos),
        columnas=datos.shape[1],
        hoja=str(nombre_hoja),
        advertencias=advertencias,
    )


# --------------------------------------------------------------------------- #
# Entrada unica
# --------------------------------------------------------------------------- #

def cargar(origen, nombre_archivo: str, tamano_bytes: int | None = None, **opciones) -> ResultadoCarga:
    """Punto de entrada: valida, decide el lector y devuelve el ResultadoCarga."""
    formato = validar_archivo(nombre_archivo, tamano_bytes)
    if formato == "csv":
        return cargar_csv(
            origen,
            nombre_archivo,
            separador=opciones.get("separador"),
            codificacion=opciones.get("codificacion"),
            decimal=opciones.get("decimal", "."),
        )
    return cargar_excel(origen, nombre_archivo, hoja=opciones.get("hoja", 0))


# --------------------------------------------------------------------------- #
# Utilidades internas
# --------------------------------------------------------------------------- #

def normalizar_nombres_columnas(datos: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Limpia espacios, rellena nombres vacios y desambigua duplicados."""
    advertencias: list[str] = []
    nombres: list[str] = []
    vistos: dict[str, int] = {}

    for indice, original in enumerate(datos.columns):
        nombre = str(original).strip()
        if not nombre or nombre.lower().startswith("unnamed"):
            nombre = f"columna_{indice + 1}"
            advertencias.append(f"La columna {indice + 1} no tenia nombre; se llamo '{nombre}'.")
        if nombre in vistos:
            vistos[nombre] += 1
            nuevo = f"{nombre}_{vistos[nombre]}"
            advertencias.append(f"Nombre duplicado '{nombre}'; se renombro a '{nuevo}'.")
            nombre = nuevo
        else:
            vistos[nombre] = 0
        nombres.append(nombre)

    datos = datos.copy()
    datos.columns = nombres
    return datos, advertencias


def _validar_dataframe(datos: pd.DataFrame) -> None:
    if datos.empty:
        raise ErrorCarga("El archivo se leyo pero no contiene filas de datos.")
    if datos.shape[1] == 0:
        raise ErrorCarga("El archivo no contiene columnas.")

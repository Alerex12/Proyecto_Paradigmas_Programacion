"""Prueba de humo del modulo core sin levantar Streamlit.

Uso:  python probar_core.py
"""

import os

import pandas as pd

from core import limpieza, tipos as t
from core.carga import ErrorCarga, cargar, listar_hojas

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_ejemplo")


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def main() -> None:
    ruta_csv = os.path.join(CARPETA, "clientes_sucio.csv")
    if not os.path.exists(ruta_csv):
        print("Falta el dataset de prueba. Ejecuta primero: python generar_datos_prueba.py")
        return

    titulo("1. Validacion de formatos invalidos")
    for nombre in ("datos.pdf", "sin_extension", ""):
        try:
            cargar(b"x", nombre, 10)
        except ErrorCarga as exc:
            print(f"  rechazado '{nombre}': {exc}")

    titulo("2. Carga del CSV (separador y codificacion automaticos)")
    resultado = cargar(ruta_csv, "clientes_sucio.csv", os.path.getsize(ruta_csv))
    print(" ", resultado.resumen())
    for advertencia in resultado.advertencias:
        print("  advertencia:", advertencia)

    titulo("3. Deteccion automatica de tipos")
    perfil = t.perfilar(resultado.datos)
    print(perfil[["columna", "tipo", "nulos", "unicos", "razon"]].to_string(index=False))

    titulo("4. Agrupacion por aptitud")
    for grupo, columnas in t.columnas_analizables(perfil).items():
        print(f"  {grupo:12} -> {columnas}")

    titulo("5. Limpieza")
    datos = limpieza.recortar_espacios(resultado.datos)
    datos, nuevos_nulos = limpieza.normalizar_nulos(datos)
    print(f"  marcadores textuales convertidos a nulo: {nuevos_nulos}")

    duplicados = limpieza.contar_duplicados(datos)
    datos, eliminadas = limpieza.eliminar_duplicados(datos)
    print(f"  duplicados detectados: {duplicados} / eliminados: {eliminadas}")

    datos, vacias = limpieza.eliminar_columnas_vacias(datos, 0.95)
    print(f"  columnas casi vacias descartadas: {vacias}")

    titulo("6. Conversion de tipos")
    perfil = t.perfilar(datos)
    datos, detalles = limpieza.convertir_automatico(datos, perfil)
    for detalle in detalles:
        print("  ", detalle)
    print("\n  dtypes finales:")
    print(datos.dtypes.to_string())

    titulo("7. Tratamiento de nulos")
    print(limpieza.resumen_nulos(datos).head(8).to_string(index=False))
    for columna, estrategia in [("edad", "mediana"), ("monto_compra", "media"), ("ciudad", "moda")]:
        if columna in datos.columns:
            datos, detalle = limpieza.aplicar_estrategia_nulos(datos, columna, estrategia)
            print("  ", detalle)

    titulo("8. Estado final")
    print(f"  filas: {len(datos)} | columnas: {datos.shape[1]} | nulos: {int(datos.isna().sum().sum())}")
    perfil_final = t.perfilar(datos)
    print(perfil_final[["columna", "tipo", "dtype_pandas"]].to_string(index=False))

    ruta_xlsx = os.path.join(CARPETA, "clientes_sucio.xlsx")
    if os.path.exists(ruta_xlsx):
        titulo("9. Carga de Excel")
        print("  hojas:", listar_hojas(ruta_xlsx, "clientes_sucio.xlsx"))
        excel = cargar(ruta_xlsx, "clientes_sucio.xlsx", os.path.getsize(ruta_xlsx), hoja="Muestra")
        print(" ", excel.resumen())

    print("\nOK: todas las etapas se ejecutaron sin errores.")


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    main()

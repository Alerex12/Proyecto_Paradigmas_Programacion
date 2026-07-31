"""Prueba de humo de outliers y clustering, sin levantar Streamlit.

Uso:  python probar_outliers_clustering.py
"""

import os

import pandas as pd

from core import clustering as c
from core import limpieza, outliers as o, tipos as t
from core.carga import cargar

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_ejemplo")


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def dataset_limpio() -> pd.DataFrame:
    """Reproduce el pipeline de la Persona 1 para llegar a un dataset usable."""
    ruta_csv = os.path.join(CARPETA, "clientes_sucio.csv")
    resultado = cargar(ruta_csv, "clientes_sucio.csv", os.path.getsize(ruta_csv))

    datos = limpieza.recortar_espacios(resultado.datos)
    datos, _ = limpieza.normalizar_nulos(datos)
    datos, _ = limpieza.eliminar_duplicados(datos)
    datos, _ = limpieza.eliminar_columnas_vacias(datos, 0.95)

    perfil = t.perfilar(datos)
    datos, _ = limpieza.convertir_automatico(datos, perfil)

    for columna in datos.columns:
        if pd.api.types.is_numeric_dtype(datos[columna]):
            datos, _ = limpieza.aplicar_estrategia_nulos(datos, columna, "mediana")

    return datos


def main() -> None:
    if not os.path.exists(os.path.join(CARPETA, "clientes_sucio.csv")):
        print("Falta el dataset de prueba. Ejecuta primero: python generar_datos_prueba.py")
        return

    datos = dataset_limpio()
    perfil = t.perfilar(datos)
    numericas = t.columnas_analizables(perfil)["numericas"]
    print(f"Columnas numericas disponibles: {numericas}")

    if len(numericas) < 2:
        print("Hacen falta al menos 2 columnas numericas; revisa generar_datos_prueba.py")
        return

    titulo("1. Outliers - Z-Score")
    mascara_z = o.detectar_outliers_zscore(datos, numericas)
    print(mascara_z.sum().to_string())

    titulo("2. Outliers - IQR")
    mascara_iqr = o.detectar_outliers_iqr(datos, numericas)
    print(mascara_iqr.sum().to_string())

    titulo("3. Outliers - Isolation Forest (multivariado)")
    mascara_if = o.detectar_outliers_isolation_forest(datos, numericas)
    print(f"  atipicos detectados: {int(mascara_if.sum())} de {len(datos)} filas")

    titulo("4. Resumen comparativo por columna")
    print(o.resumen_outliers(datos, numericas).to_string(index=False))

    titulo("5. Eliminar atipicos combinados (Z-Score + IQR)")
    combinada = o.mascara_combinada(mascara_z | mascara_iqr)
    datos_sin_atipicos, eliminados = o.eliminar_outliers(datos, combinada)
    print(f"  filas eliminadas: {eliminados} / filas restantes: {len(datos_sin_atipicos)}")

    titulo("6. Metodo del codo (K-Means)")
    codo = c.metodo_codo(datos, numericas, k_minimo=2, k_maximo=6)
    print(codo.to_string(index=False))

    titulo("7. K-Means (k=3)")
    resultado_kmeans = c.ajustar_kmeans(datos, numericas, k=3)
    print(" ", resultado_kmeans.resumen())

    titulo("8. DBSCAN")
    resultado_dbscan = c.ajustar_dbscan(datos, numericas, eps=1.0, min_muestras=5)
    print(" ", resultado_dbscan.resumen())

    titulo("9. Asignar etiquetas de K-Means al dataset")
    con_clusters = c.asignar_etiquetas(datos, resultado_kmeans)
    print(con_clusters["cluster"].value_counts(dropna=False).to_string())

    print("\nOK: todas las etapas se ejecutaron sin errores.")


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    main()

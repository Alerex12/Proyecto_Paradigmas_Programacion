"""Genera datasets de prueba deliberadamente sucios para probar el modulo de carga.

Uso:  python generar_datos_prueba.py
"""

import os
import random

import numpy as np
import pandas as pd

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_ejemplo")
random.seed(7)
np.random.seed(7)

N = 300
CIUDADES = ["San Jose", "Alajuela", "Cartago", "Heredia", "Puntarenas"]
PLANES = ["Basico", "Premium", "Empresarial"]


def construir() -> pd.DataFrame:
    datos = pd.DataFrame(
        {
            "id_cliente": [f"CL-{i:05d}" for i in range(1, N + 1)],
            "nombre": [f"Cliente {i}" for i in range(1, N + 1)],
            "edad": np.random.randint(18, 75, N).astype(float),
            "ingreso_mensual": np.round(np.random.normal(850_000, 300_000, N), 2),
            "monto_compra": np.round(np.random.gamma(3, 40_000, N), 2),
            "cantidad_pedidos": np.random.poisson(4, N),
            "ciudad": np.random.choice(CIUDADES, N),
            "plan": np.random.choice(PLANES, N, p=[0.5, 0.35, 0.15]),
            "activo": np.random.choice(["Si", "No"], N, p=[0.8, 0.2]),
            "fecha_registro": pd.to_datetime("2023-01-01")
            + pd.to_timedelta(np.random.randint(0, 900, N), unit="D"),
            "pais": "Costa Rica",  # columna constante a proposito
        }
    )

    # Fechas como texto en formato dd/mm/aaaa
    datos["fecha_registro"] = datos["fecha_registro"].dt.strftime("%d/%m/%Y")

    # Numeros escritos como texto con simbolo de moneda y separador de miles
    datos["ingreso_mensual"] = datos["ingreso_mensual"].map(
        lambda v: f"₡{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    # Valores nulos de varias formas
    for columna, marcador, cantidad in [
        ("edad", np.nan, 20),
        ("monto_compra", np.nan, 15),
        ("ciudad", "N/A", 12),
        ("plan", "-", 8),
        ("nombre", "sin dato", 5),
    ]:
        indices = np.random.choice(datos.index, cantidad, replace=False)
        datos.loc[indices, columna] = marcador

    # Espacios sobrantes
    datos["ciudad"] = datos["ciudad"].map(lambda v: f"  {v} " if random.random() < 0.3 else v)

    # Columna casi vacia
    datos["comentario"] = pd.Series([None] * len(datos), dtype="object")
    datos.loc[datos.sample(4).index, "comentario"] = "revisar"

    # Filas duplicadas
    duplicadas = datos.sample(12, random_state=1)
    datos = pd.concat([datos, duplicadas], ignore_index=True)

    return datos.sample(frac=1, random_state=3).reset_index(drop=True)


def main() -> None:
    os.makedirs(CARPETA, exist_ok=True)
    datos = construir()

    ruta_csv = os.path.join(CARPETA, "clientes_sucio.csv")
    datos.to_csv(ruta_csv, index=False, sep=";", encoding="utf-8-sig")

    ruta_xlsx = os.path.join(CARPETA, "clientes_sucio.xlsx")
    with pd.ExcelWriter(ruta_xlsx, engine="openpyxl") as libro:
        datos.to_excel(libro, sheet_name="Clientes", index=False)
        datos.head(50).to_excel(libro, sheet_name="Muestra", index=False)

    print(f"Generado: {ruta_csv}")
    print(f"Generado: {ruta_xlsx}")
    print(f"{len(datos)} filas x {datos.shape[1]} columnas")


if __name__ == "__main__":
    main()

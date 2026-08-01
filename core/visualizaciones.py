from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import tipos as t

MAXIMO_CATEGORIAS_GRAFICO = 15  
PALETA = px.colors.qualitative.Set2


@dataclass
class GraficosGenerados:
    

    histogramas: dict[str, go.Figure] = field(default_factory=dict)
    barras: dict[str, go.Figure] = field(default_factory=dict)
    boxplot_numericas: go.Figure | None = None
    mapa_calor: go.Figure | None = None
    dispersion: go.Figure | None = None
    par_dispersion: tuple[str, str] | None = None
    avisos: list[str] = field(default_factory=list)

    def total_figuras(self) -> int:
        extra = sum(x is not None for x in (self.boxplot_numericas, self.mapa_calor, self.dispersion))
        return len(self.histogramas) + len(self.barras) + extra


# --- Graficos individuales ----

def figura_histograma(datos: pd.DataFrame, columna: str) -> go.Figure:
    
    serie = t.a_numerico(datos[columna]).dropna()
    fig = px.histogram(serie, x=columna if columna in datos.columns else serie.name,
                        nbins=min(50, max(10, serie.nunique())), opacity=0.85)
    fig.update_traces(marker_color=PALETA[0])
    if not serie.empty:
        media, mediana = serie.mean(), serie.median()
        fig.add_vline(x=media, line_dash="dash", line_color="crimson",
                       annotation_text=f"media {media:.2f}", annotation_position="top")
        fig.add_vline(x=mediana, line_dash="dot", line_color="darkblue",
                       annotation_text=f"mediana {mediana:.2f}", annotation_position="bottom")
    fig.update_layout(title=f"Distribucion de '{columna}'", xaxis_title=columna,
                       yaxis_title="Frecuencia", showlegend=False, bargap=0.05)
    return fig


def figura_boxplot_numericas(datos: pd.DataFrame, columnas: list[str]) -> go.Figure:
    
    filas = []
    for col in columnas:
        serie = t.a_numerico(datos[col]).dropna()
        if serie.empty or serie.std() == 0:
            continue
        estandarizada = (serie - serie.mean()) / serie.std()
        filas.append(pd.DataFrame({"columna": col, "valor": estandarizada}))

    if not filas:
        return go.Figure()

    largo = pd.concat(filas, ignore_index=True)
    fig = px.box(largo, x="columna", y="valor", color="columna", color_discrete_sequence=PALETA, points="outliers")
    fig.update_layout(title="Comparacion de variables numericas (estandarizadas)",
                       xaxis_title="", yaxis_title="Valor estandarizado (z-score)", showlegend=False)
    return fig


def figura_barras_categorica(datos: pd.DataFrame, columna: str, top_n: int = MAXIMO_CATEGORIAS_GRAFICO) -> go.Figure:
    
    conteo = datos[columna].astype(str).str.strip().value_counts()

    if len(conteo) > top_n:
        principales = conteo.iloc[:top_n]
        otros = conteo.iloc[top_n:].sum()
        conteo = pd.concat([principales, pd.Series({"Otros": otros})])

    fig = px.bar(x=conteo.index, y=conteo.values, color=conteo.index, color_discrete_sequence=PALETA)
    fig.update_layout(title=f"Frecuencia de '{columna}'", xaxis_title=columna,
                       yaxis_title="Cantidad", showlegend=False)
    return fig


def figura_mapa_calor_correlacion(datos: pd.DataFrame, columnas: list[str]) -> go.Figure:
    
    numericas = datos[columnas].apply(t.a_numerico)
    correlacion = numericas.corr(numeric_only=True).round(2)

    fig = px.imshow(correlacion, text_auto=True, color_continuous_scale="RdBu_r",
                     zmin=-1, zmax=1, aspect="auto")
    fig.update_layout(title="Mapa de calor — correlacion entre variables numericas")
    return fig


def figura_dispersion(datos: pd.DataFrame, col_x: str, col_y: str, color: str | None = None) -> go.Figure:
    
    columnas = [col_x, col_y] + ([color] if color else [])
    subconjunto = datos[columnas].copy()
    subconjunto[col_x] = t.a_numerico(subconjunto[col_x])
    subconjunto[col_y] = t.a_numerico(subconjunto[col_y])
    subconjunto = subconjunto.dropna(subset=[col_x, col_y])

    fig = px.scatter(subconjunto, x=col_x, y=col_y, color=color, opacity=0.7,
                      color_discrete_sequence=PALETA)

   
    if subconjunto.shape[0] >= 3:
        x = subconjunto[col_x].to_numpy()
        y = subconjunto[col_y].to_numpy()
        pendiente, intercepto = np.polyfit(x, y, 1)
        x_linea = np.linspace(x.min(), x.max(), 100)
        y_linea = pendiente * x_linea + intercepto
        fig.add_trace(go.Scatter(x=x_linea, y=y_linea, mode="lines", name="Tendencia",
                                  line=dict(color="crimson", dash="dash")))

    fig.update_layout(title=f"Dispersion: '{col_x}' vs '{col_y}'")
    return fig


def par_mas_correlacionado(datos: pd.DataFrame, columnas: list[str]) -> tuple[str, str] | None:
    
    if len(columnas) < 2:
        return None
    numericas = datos[columnas].apply(t.a_numerico)
    correlacion = numericas.corr(numeric_only=True).abs()

    mejor_par, mejor_valor = None, -1.0
    for i, col_a in enumerate(columnas):
        for col_b in columnas[i + 1:]:
            valor = correlacion.loc[col_a, col_b]
            if pd.notna(valor) and valor > mejor_valor:
                mejor_par, mejor_valor = (col_a, col_b), valor
    return mejor_par


# --- Orquestador ---

def generar_todos(datos: pd.DataFrame, perfil: pd.DataFrame | None = None,
                   maximo_histogramas: int = 12, maximo_barras: int = 12) -> GraficosGenerados:
    
    if perfil is None:
        perfil = t.perfilar(datos)

    grupos = t.columnas_analizables(perfil)
    numericas = grupos["numericas"]
    categoricas = grupos["categoricas"]

    resultado = GraficosGenerados()

    # Histogramas: uno por variable numerica
    for col in numericas[:maximo_histogramas]:
        resultado.histogramas[col] = figura_histograma(datos, col)
    if len(numericas) > maximo_histogramas:
        resultado.avisos.append(
            f"Se generaron histogramas solo de las primeras {maximo_histogramas} variables numericas "
            f"(hay {len(numericas)} en total)."
        )

    # Boxplot comparativo de todas las numericas
    if len(numericas) >= 1:
        resultado.boxplot_numericas = figura_boxplot_numericas(datos, numericas)

    # Barras: una por variable categorica/booleana
    for col in categoricas[:maximo_barras]:
        resultado.barras[col] = figura_barras_categorica(datos, col)
    if len(categoricas) > maximo_barras:
        resultado.avisos.append(
            f"Se generaron graficos de barras solo de las primeras {maximo_barras} variables categoricas "
            f"(hay {len(categoricas)} en total)."
        )

    # Mapa de calor de correlacion
    if len(numericas) >= 2:
        resultado.mapa_calor = figura_mapa_calor_correlacion(datos, numericas)

       
        par = par_mas_correlacionado(datos, numericas)
        if par:
            resultado.par_dispersion = par
            resultado.dispersion = figura_dispersion(datos, par[0], par[1])
    elif len(numericas) == 1:
        resultado.avisos.append("Hace falta al menos 2 variables numericas para correlacion y dispersion.")

    if not numericas and not categoricas:
        resultado.avisos.append("No hay variables numericas ni categoricas aptas para graficar.")

    return resultado
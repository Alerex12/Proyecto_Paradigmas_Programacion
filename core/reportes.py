"""Generacion de reportes exportables (HTML y PDF) a partir de tablas y graficos.
 
Este modulo no depende de Streamlit: recibe estructuras ya calculadas
(DataFrames y figuras de Plotly) y devuelve bytes listos para descargar
con `st.download_button`. Sirve tanto para exportar una sola seccion
(un boton por pagina) como para el reporte consolidado (varias secciones
juntas, en orden).
"""
 
from __future__ import annotations
 
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
 
import pandas as pd
import plotly.graph_objects as go
 
FORMATO_FECHA = "%Y-%m-%d %H:%M"
 
 
@dataclass
class SeccionReporte:
    """Un bloque de reporte: un titulo, texto opcional, tablas y graficos."""
 
    titulo: str
    descripcion: str | None = None
    tablas: list[tuple[str, pd.DataFrame]] = field(default_factory=list)
    figuras: list[tuple[str, go.Figure]] = field(default_factory=list)
 
    def esta_vacia(self) -> bool:
        return not self.tablas and not self.figuras and not self.descripcion
 
 
class ErrorReporte(Exception):
    """Error controlado al generar un reporte (mensaje apto para mostrar al usuario)."""
 
 
# --------------------------------------------------------------------------- #
# Conversion de figuras Plotly a imagen (usado por el PDF)
# --------------------------------------------------------------------------- #
 
def _figura_a_png(figura: go.Figure, ancho: int = 900, alto: int = 500) -> bytes:
    try:
        return figura.to_image(format="png", width=ancho, height=alto, scale=2, engine="kaleido")
    except Exception as exc:
        raise ErrorReporte(
            "No se pudo convertir un grafico a imagen para el PDF. "
            "Verifica que 'kaleido' este instalado (pip install kaleido)."
        ) from exc
 
 
# --------------------------------------------------------------------------- #
# Exportar a HTML
# --------------------------------------------------------------------------- #
 
_ESTILO_HTML = """
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 40px; color: #1f2937; }
  h1 { border-bottom: 3px solid #2563eb; padding-bottom: 8px; }
  h2 { color: #2563eb; margin-top: 48px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
  .meta { color: #6b7280; font-size: 0.9em; margin-bottom: 32px; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0 32px; font-size: 0.92em; }
  th, td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: left; }
  th { background: #f3f4f6; }
  .grafico { margin: 24px 0; }
  .descripcion { color: #374151; margin-bottom: 12px; }
</style>
"""
 
 
def _tabla_a_html(nombre: str, tabla: pd.DataFrame) -> str:
    return f"<h3>{nombre}</h3>\n{tabla.to_html(index=False, border=0, justify='left')}"
 
 
def exportar_html(secciones: list[SeccionReporte], titulo_reporte: str = "Reporte de analisis") -> bytes:
    """Arma un HTML autocontenido (graficos interactivos incluidos) en bytes utf-8."""
    if not secciones or all(s.esta_vacia() for s in secciones):
        raise ErrorReporte("No hay datos para exportar todavia.")
 
    partes = [
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>",
        f"<title>{titulo_reporte}</title>",
        _ESTILO_HTML,
        "</head><body>",
        f"<h1>{titulo_reporte}</h1>",
        f"<div class='meta'>Generado el {datetime.now().strftime(FORMATO_FECHA)}</div>",
    ]
 
    incluir_plotlyjs = True
    for seccion in secciones:
        if seccion.esta_vacia():
            continue
        partes.append(f"<h2>{seccion.titulo}</h2>")
        if seccion.descripcion:
            partes.append(f"<p class='descripcion'>{seccion.descripcion}</p>")
        for nombre, tabla in seccion.tablas:
            partes.append(_tabla_a_html(nombre, tabla))
        for nombre, figura in seccion.figuras:
            partes.append(f"<div class='grafico'><h3>{nombre}</h3>")
            partes.append(
                figura.to_html(full_html=False, include_plotlyjs="cdn" if incluir_plotlyjs else False)
            )
            partes.append("</div>")
            incluir_plotlyjs = False  # el script de plotly.js solo hace falta incluirlo una vez
 
    partes.append("</body></html>")
    return "\n".join(partes).encode("utf-8")
 
 
# --------------------------------------------------------------------------- #
# Exportar a PDF
# --------------------------------------------------------------------------- #
 
def exportar_pdf(secciones: list[SeccionReporte], titulo_reporte: str = "Reporte de analisis") -> bytes:
    """Arma un PDF con reportlab: tablas nativas + graficos como imagen (via kaleido)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
        )
    except ImportError as exc:
        raise ErrorReporte(
            "Falta la libreria 'reportlab' para generar PDF. Instalala con: pip install reportlab"
        ) from exc
 
    if not secciones or all(s.esta_vacia() for s in secciones):
        raise ErrorReporte("No hay datos para exportar todavia.")
 
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("TituloReporte", parent=estilos["Title"], textColor=colors.HexColor("#1f2937"))
    estilo_seccion = ParagraphStyle("Seccion", parent=estilos["Heading2"], textColor=colors.HexColor("#2563eb"), spaceBefore=18)
    estilo_subtitulo = ParagraphStyle("Subtitulo", parent=estilos["Heading4"], spaceBefore=10)
    estilo_normal = estilos["BodyText"]
    estilo_meta = ParagraphStyle("Meta", parent=estilos["Normal"], textColor=colors.grey, fontSize=9)
 
    elementos = [
        Paragraph(titulo_reporte, estilo_titulo),
        Paragraph(f"Generado el {datetime.now().strftime(FORMATO_FECHA)}", estilo_meta),
        Spacer(1, 12),
    ]
 
    primera_seccion_visible = True
    for seccion in secciones:
        if seccion.esta_vacia():
            continue
        if not primera_seccion_visible:
            elementos.append(PageBreak())
        primera_seccion_visible = False
 
        elementos.append(Paragraph(seccion.titulo, estilo_seccion))
        if seccion.descripcion:
            elementos.append(Paragraph(seccion.descripcion, estilo_normal))
            elementos.append(Spacer(1, 8))
 
        for nombre, tabla in seccion.tablas:
            elementos.append(Paragraph(nombre, estilo_subtitulo))
            elementos.append(_tabla_a_flowable(tabla))
            elementos.append(Spacer(1, 10))
 
        for nombre, figura in seccion.figuras:
            elementos.append(Paragraph(nombre, estilo_subtitulo))
            png = _figura_a_png(figura)
            imagen = Image(BytesIO(png), width=16 * cm, height=16 * cm * 500 / 900)
            elementos.append(imagen)
            elementos.append(Spacer(1, 10))
 
    documento.build(elementos)
    return buffer.getvalue()
 
 
def _tabla_a_flowable(tabla: pd.DataFrame, filas_maximas: int = 40):
    """Convierte un DataFrame en una tabla de reportlab, recortando si tiene muchas filas."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
 
    recortada = tabla.head(filas_maximas)
    datos = [list(recortada.columns)] + recortada.astype(str).values.tolist()
 
    tabla_pdf = Table(datos, hAlign="LEFT", repeatRows=1)
    tabla_pdf.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tabla_pdf
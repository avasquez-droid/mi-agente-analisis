"""Informe en PDF (reportlab)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from .analyzer import ResultadoAnalisis
from .insights import Insight, PlanAccion

AZUL = colors.HexColor("#1F3A5F")
GRIS = colors.HexColor("#F2F4F7")
COLOR_TIPO = {"fortaleza": "#2E7D32", "alerta": "#C62828", "info": "#1565C0"}


def _estilos():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Titulo", parent=ss["Title"], fontSize=20, textColor=AZUL, spaceAfter=6))
    ss.add(ParagraphStyle("Sub", parent=ss["Heading2"], textColor=AZUL, spaceBefore=12))
    ss.add(ParagraphStyle("Cuerpo", parent=ss["BodyText"], fontSize=10, leading=14))
    ss.add(ParagraphStyle("Celda", parent=ss["BodyText"], fontSize=8.5, leading=11))
    return ss


def _tabla(filas: list[list], anchos=None, encabezado=True) -> Table:
    t = Table(filas, colWidths=anchos, repeatRows=1 if encabezado else 0)
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ]
    if encabezado:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(estilo))
    return t


def generar_pdf(res: ResultadoAnalisis, insights: list[Insight], plan: PlanAccion,
                ruta: str | Path, titulo: str = "Informe de Desempeño") -> Path:
    ruta = Path(ruta)
    ss = _estilos()
    doc = SimpleDocTemplate(str(ruta), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=titulo)
    met = res.metodologia
    P = lambda txt, st="Cuerpo": Paragraph(txt, ss[st])  # noqa: E731
    cont = []

    # Portada / resumen
    cont += [P(titulo, "Titulo"),
             P(f"Metodología: <b>{met.nombre}</b> &nbsp;|&nbsp; Fecha: {date.today():%d/%m/%Y} "
               f"&nbsp;|&nbsp; Personas evaluadas: {len(res.individuos)}"),
             Spacer(1, 10)]

    cont.append(P("1. Resumen ejecutivo", "Sub"))
    banda = met.banda_para(res.puntaje_global)
    cont.append(P(f"El equipo obtiene un puntaje global de <b>{res.puntaje_global:.1f}/100</b>, "
                  f"nivel <b>{banda.nombre}</b>. {banda.descripcion}"))
    cont.append(Spacer(1, 6))
    filas = [["Nivel", "Personas", "%"]]
    n = max(len(res.individuos), 1)
    for b in met.bandas:
        c = res.distribucion_bandas.get(b.nombre, 0)
        filas.append([b.nombre, str(c), f"{c / n * 100:.0f}%"])
    cont.append(_tabla(filas, [7 * cm, 3 * cm, 3 * cm]))

    # Criterios
    cont.append(P("2. Resultados por criterio", "Sub"))
    filas = [["Criterio", "Peso", "Promedio (0-100)", "Columna origen"]]
    for c in met.criterios:
        if c.nombre in res.mapeo_criterios:
            filas.append([c.nombre, f"{c.peso * 100:.0f}%",
                          f"{res.promedio_criterios[c.nombre]:.1f}", res.mapeo_criterios[c.nombre]])
    cont.append(_tabla(filas, [5.5 * cm, 2 * cm, 3.5 * cm, 6 * cm]))

    # Grupos
    if res.por_grupo is not None:
        cont.append(P("3. Resultados por grupo", "Sub"))
        filas = [["Grupo", "Personas", "Puntaje"]]
        for g, fila in res.por_grupo.iterrows():
            filas.append([str(g), str(int(fila["Personas"])), f"{fila['Puntaje']:.1f}"])
        cont.append(_tabla(filas, [8 * cm, 3 * cm, 3 * cm]))

    # Insights
    cont.append(P("4. Hallazgos principales", "Sub"))
    for i in insights:
        color = COLOR_TIPO.get(i.tipo, "#000000")
        cont.append(P(f"<font color='{color}'><b>•  {i.titulo}.</b></font> {i.detalle}"))
        cont.append(Spacer(1, 3))

    # Plan de acción
    cont.append(PageBreak())
    cont.append(P("5. Plan de acción", "Sub"))
    cont.append(P(f"<b>Objetivo:</b> {plan.objetivo}"))
    cont.append(Spacer(1, 6))
    filas = [["Prioridad", "Acción", "Dirigido a", "Responsable", "Plazo", "Indicador"]]
    for a in plan.acciones:
        filas.append([a.prioridad, P(a.accion, "Celda"), P(a.dirigido_a, "Celda"),
                      P(a.responsable, "Celda"), a.plazo, P(a.indicador, "Celda")])
    cont.append(_tabla(filas, [1.7 * cm, 5 * cm, 3 * cm, 2.6 * cm, 1.6 * cm, 3.3 * cm]))

    # Detalle individual
    cont.append(PageBreak())
    cont.append(P("6. Detalle individual", "Sub"))
    cols = ["Ranking", "Nombre"] + (["Grupo"] if "Grupo" in res.individuos else []) + \
           ["Puntaje", "Banda", "Fortaleza", "Oportunidad"]
    filas = [cols]
    for _, r in res.individuos.iterrows():
        filas.append([str(r[c]) if c != "Puntaje" else f"{r[c]:.1f}" for c in cols])
    cont.append(_tabla(filas))

    doc.build(cont)
    return ruta

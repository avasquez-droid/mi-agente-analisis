"""Plan de acción en Word (python-docx)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from .analyzer import ResultadoAnalisis
from .insights import Insight, PlanAccion

AZUL = RGBColor(0x1F, 0x3A, 0x5F)


def _tabla(doc, encabezados: list[str], filas: list[list[str]]):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Light Grid Accent 1"
    for i, h in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        celda.text = h
        for p in celda.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(9)
    for fila in filas:
        celdas = t.add_row().cells
        for i, v in enumerate(fila):
            celdas[i].text = str(v)
            for p in celdas[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    return t


def generar_word(res: ResultadoAnalisis, insights: list[Insight], plan: PlanAccion,
                 ruta: str | Path, titulo: str = "Plan de Acción") -> Path:
    ruta = Path(ruta)
    met = res.metodologia
    doc = Document()

    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)

    h = doc.add_heading(titulo, level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in h.runs:
        r.font.color.rgb = AZUL
    doc.add_paragraph(f"Metodología: {met.nombre}  |  Fecha: {date.today():%d/%m/%Y}  |  "
                      f"Personas evaluadas: {len(res.individuos)}")

    doc.add_heading("1. Contexto", level=1)
    banda = met.banda_para(res.puntaje_global)
    doc.add_paragraph(
        f"El equipo obtuvo un puntaje global de {res.puntaje_global:.1f}/100 (nivel "
        f"'{banda.nombre}'). {banda.descripcion} Este plan responde a los hallazgos del análisis "
        "y define acciones concretas con responsables, plazos e indicadores."
    )

    doc.add_heading("2. Hallazgos que sustentan el plan", level=1)
    for i in insights:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(f"{i.titulo}. ")
        r.bold = True
        p.add_run(i.detalle)

    doc.add_heading("3. Objetivo", level=1)
    doc.add_paragraph(plan.objetivo)

    doc.add_heading("4. Acciones", level=1)
    _tabla(doc, ["Prioridad", "Acción", "Dirigido a", "Responsable", "Plazo", "Indicador"],
           [[a.prioridad, a.accion, a.dirigido_a, a.responsable, a.plazo, a.indicador] for a in plan.acciones])

    doc.add_heading("5. Acompañamiento individual", level=1)
    cols = ["Nombre", "Puntaje", "Banda", "Fortaleza", "Oportunidad"]
    _tabla(doc, cols, [[r["Nombre"], f"{r['Puntaje']:.1f}", r["Banda"], r["Fortaleza"], r["Oportunidad"]]
                       for _, r in res.individuos.iterrows()])

    doc.add_heading("6. Seguimiento", level=1)
    doc.add_paragraph(
        "Se recomienda revisar el avance de cada acción mensualmente y repetir la evaluación "
        "completa al cierre del periodo para comparar resultados con esta línea base."
    )
    doc.save(ruta)
    return ruta

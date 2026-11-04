"""Análisis en Excel (openpyxl) con hojas de resumen, criterios, grupos e individuos."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .analyzer import ResultadoAnalisis
from .insights import Insight, PlanAccion

AZUL = "1F3A5F"


def _formatear_hoja(ws, ancho_min=10, ancho_max=45):
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=AZUL)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col in ws.columns:
        largo = max((len(str(c.value)) for c in col if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(ancho_min, min(largo + 2, ancho_max))
    ws.freeze_panes = "A2"


def generar_excel(res: ResultadoAnalisis, insights: list[Insight], plan: PlanAccion,
                  ruta: str | Path) -> Path:
    ruta = Path(ruta)
    met = res.metodologia
    n = max(len(res.individuos), 1)

    resumen = pd.DataFrame(
        [["Metodología", met.nombre], ["Personas evaluadas", len(res.individuos)],
         ["Puntaje global (0-100)", round(res.puntaje_global, 1)],
         ["Nivel global", met.banda_para(res.puntaje_global).nombre]]
        + [[f"Personas en '{b.nombre}'", f"{res.distribucion_bandas.get(b.nombre, 0)} "
            f"({res.distribucion_bandas.get(b.nombre, 0) / n * 100:.0f}%)"] for b in met.bandas],
        columns=["Indicador", "Valor"],
    )
    criterios = pd.DataFrame(
        [[c.nombre, round(c.peso * 100), res.promedio_criterios[c.nombre], res.mapeo_criterios[c.nombre]]
         for c in met.criterios if c.nombre in res.mapeo_criterios],
        columns=["Criterio", "Peso (%)", "Promedio (0-100)", "Columna origen"],
    )
    hallazgos = pd.DataFrame([[i.tipo.capitalize(), i.titulo, i.detalle] for i in insights],
                             columns=["Tipo", "Hallazgo", "Detalle"])
    acciones = pd.DataFrame([[a.prioridad, a.accion, a.dirigido_a, a.responsable, a.plazo, a.indicador]
                             for a in plan.acciones],
                            columns=["Prioridad", "Acción", "Dirigido a", "Responsable", "Plazo", "Indicador"])

    with pd.ExcelWriter(ruta, engine="openpyxl") as w:
        resumen.to_excel(w, sheet_name="Resumen", index=False)
        criterios.to_excel(w, sheet_name="Criterios", index=False)
        if res.por_grupo is not None:
            res.por_grupo.reset_index().to_excel(w, sheet_name="Por grupo", index=False)
        res.individuos.to_excel(w, sheet_name="Individuos", index=False)
        hallazgos.to_excel(w, sheet_name="Hallazgos", index=False)
        acciones.to_excel(w, sheet_name="Plan de acción", index=False)

        for nombre, ws in w.sheets.items():
            _formatear_hoja(ws)
        # Escala de color en la columna Puntaje de individuos
        ws = w.sheets["Individuos"]
        col_puntaje = list(res.individuos.columns).index("Puntaje") + 1
        letra = get_column_letter(col_puntaje)
        ws.conditional_formatting.add(
            f"{letra}2:{letra}{len(res.individuos) + 1}",
            ColorScaleRule(start_type="num", start_value=0, start_color="F8696B",
                           mid_type="num", mid_value=60, mid_color="FFEB84",
                           end_type="num", end_value=100, end_color="63BE7B"),
        )
    return ruta

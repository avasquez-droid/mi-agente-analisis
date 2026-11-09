"""Entregables del análisis de cliente: resumen Markdown (chat) y Excel de oportunidades."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .informe_reader import InformeGrupo
from .oportunidades import Oportunidad, honorario_potencial

ORO = "BDA02D"   # color corporativo Census para títulos


def _usd(v) -> str:
    return "—" if v in (None, "") else f"${v:,.2f}"


def resumen_markdown(inf: InformeGrupo, ops: list[Oportunidad], archivos: dict | None = None) -> str:
    l = [f"# Oportunidades — grupo {inf.main.nombre if inf.main else inf.ruc_main}",
         f"Informe: {inf.archivo} · fecha {inf.fecha} · ejercicio de referencia {inf.anio_ref} · "
         f"{len(inf.empresas)} empresas", ""]
    if not ops:
        l.append("No se detectaron servicios con las métricas actuales.")
    else:
        total = honorario_potencial(ops)
        l += [f"**{len(ops)} oportunidades** · honorario potencial estimado: **{_usd(total)} + IVA** "
              "(sin fees mensuales; en servicios alternativos, como cobranza extrajudicial/judicial, se cuenta solo el mayor)", "",
              "| Prioridad | Empresa | Servicio | Base estimada | Honorario | Motivo |",
              "|---|---|---|---|---|---|"]
        for o in ops:
            hon = o.honorario["texto"] + (f" → {_usd(o.honorario['monto'])}" if o.honorario.get("monto") else "")
            motivo = "; ".join(o.motivos[:2]) + (f" · **Falta:** {o.requiere_dato}" if o.requiere_dato else "")
            l.append(f"| {o.prioridad} | {o.empresa} | {o.servicio} | {_usd(o.base)} | {hon} | {motivo} |")
    if inf.discrepancias:
        l += ["", "## Discrepancias en el informe (se usó la ficha de cada empresa)"]
        l += [f"- {d}" for d in inf.discrepancias]
    l += ["", "_Métricas y honorarios provisionales (conocimiento/metricas.yaml y tarifario.yaml)._"]
    if archivos:
        l += ["", "Archivos: " + ", ".join(f"`{p}`" for p in archivos.values())]
    return "\n".join(l)


def _cabecera(ws, columnas):
    ws.append(columnas)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=ORO)
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"


def _anchos(ws, anchos):
    for i, a in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = a


def excel_oportunidades(inf: InformeGrupo, ops: list[Oportunidad], metricas: dict, salida: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Oportunidades"
    _cabecera(ws, ["Prioridad", "Empresa", "RUC", "Tipo", "Materia", "Servicio", "Base estimada (USD)",
                   "Modelo honorario", "Honorario", "Honorario estimado (USD)", "Motivos",
                   "Dato faltante", "Contrato tipo"])
    for o in ops:
        ws.append([o.prioridad, o.empresa, o.ruc, o.tipo_empresa, o.materia, o.servicio, o.base,
                   o.honorario.get("modelo"), o.honorario.get("texto"), o.honorario.get("monto"),
                   "\n".join(o.motivos), o.requiere_dato or "", "Sí" if o.tiene_contrato_tipo else "Pendiente"])
    for fila in ws.iter_rows(min_row=2):
        fila[6].number_format = fila[9].number_format = '#,##0.00'
        for c in fila:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    _anchos(ws, [12, 30, 15, 13, 16, 38, 16, 13, 34, 16, 45, 35, 12])

    wm = wb.create_sheet("Métricas")
    claves = ["nombre", "ruc", "tipo", "ventas", "ingreso_total", "utilidad_neta", "ir_causado", "trabajadores",
              "importaciones", "exportaciones", "cxc_no_relacionadas", "cxc_sobre_ventas", "ct_iva_ref",
              "ct_ir_ref", "proyeccion_devolucion_ir", "isd_ref", "isd_actual", "sercop_total",
              "omc_total", "reg70_total", "reg21_total", "juicios_actor", "juicios_demandado",
              "juicios_laborales_demandado", "deudas_firmes", "deudas_impugnadas", "facilidades_pago"]
    _cabecera(wm, claves)
    for d in metricas.values():
        wm.append([d.get(k) for k in claves])
    for fila in wm.iter_rows(min_row=2):
        for c in fila[3:]:
            if isinstance(c.value, float):
                c.number_format = '0.0%' if wm.cell(1, c.column).value == "cxc_sobre_ventas" else '#,##0.00'
    _anchos(wm, [30, 15, 13] + [15] * (len(claves) - 3))

    wd = wb.create_sheet("Discrepancias")
    _cabecera(wd, ["Discrepancia entre el cuadro resumen y la ficha"])
    for d in inf.discrepancias or ["Sin discrepancias"]:
        wd.append([d])
    _anchos(wd, [110])

    salida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(salida)
    return salida

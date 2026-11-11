"""Interfaz de línea de comandos del Agente Comercial.

Ejemplos:
    python -m core.cli servicios
    python -m core.cli analizar-cliente informe.docx
    python -m core.cli contrato devolucion_iva --cliente cliente.yaml --var periodo="diciembre 2026"
    python -m core.cli variables devolucion_iva
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

from . import conocimiento as kb
from .contratos import generar_contrato
from .documentos import generar_documento
from .propuestas import generar_propuesta
from .informe_reader import leer_informe
from .oportunidades import analizar_grupo
from .reporte_oportunidades import excel_oportunidades, resumen_markdown


def _valor(texto: str):
    try:
        return yaml.safe_load(texto)
    except yaml.YAMLError:
        return texto


def cmd_servicios(_):
    for sid, s in kb.servicios().items():
        estado = ("propuesta" if s.get("propuesta") else "-") + " / " + ("contrato" if s.get("clausulas") else "-")
        print(f"{sid:28} {s.get('area', s['materia']):20} {estado:21} {s['nombre']}")


def cmd_variables(a):
    from .propuestas import plantilla_servicio
    srv = kb.servicio(a.servicio)
    if srv.get("propuesta"):
        print(f"Propuesta de '{a.servicio}':")
        for k, m in (plantilla_servicio(a.servicio).get("variables") or {}).items():
            req = " (obligatoria)" if m.get("requerido") else ""
            print(f"  {k}{req}: {m.get('descripcion')}  — ej.: {m.get('ejemplo')}")
    if not srv.get("clausulas"):
        print("(sin contrato tipo)")
        return
    scl = kb.clausulas_servicio(a.servicio)
    print(f"Contrato de '{a.servicio}' (además de los datos del cliente):")
    for k, m in (scl.get("variables") or {}).items():
        req = " (obligatoria)" if m.get("requerido") else ""
        print(f"  {k}{req}: {m.get('descripcion')}  — ej.: {m.get('ejemplo')}")


def _base_opcional():
    try:
        from .base_clientes import cargar_base
        return cargar_base()
    except FileNotFoundError:
        return None


def cmd_analizar(a):
    inf = leer_informe(a.informe)
    base = _base_opcional()
    r = analizar_grupo(inf, base)
    if base:
        conocidos = [e.nombre for e in inf.empresas if base.por_ruc(e.ruc)]
        print(f"Base comercial: {len(conocidos)} de {len(inf.empresas)} empresas ya están en la base"
              + (f" ({', '.join(conocidos)})" if conocidos else "") + ".\n")
    carpeta = Path(a.salida) if a.salida else kb.RAIZ / "salidas"
    base = re.sub(r"\W+", "_", inf.main.nombre if inf.main else inf.ruc_main).strip("_")
    archivos = {"xlsx": excel_oportunidades(
        inf, r["oportunidades"], r["metricas"],
        carpeta / f"{base}_oportunidades_{datetime.now():%Y%m%d_%H%M}.xlsx")}
    md = resumen_markdown(inf, r["oportunidades"], archivos)
    ruta_md = archivos["xlsx"].with_suffix(".md")
    ruta_md.write_text(md, encoding="utf-8")
    print(md)
    if a.json:
        print(json.dumps([o.__dict__ for o in r["oportunidades"]], ensure_ascii=False, indent=1, default=str))


def cmd_contrato(a):
    cliente = yaml.safe_load(Path(a.cliente).read_text(encoding="utf-8")) if a.cliente else {}
    variables = {}
    if a.variables:
        variables.update(yaml.safe_load(Path(a.variables).read_text(encoding="utf-8")) or {})
    for par in a.var or []:
        k, _, v = par.partition("=")
        variables[k.strip()] = _valor(v)
    fecha = date.fromisoformat(a.fecha) if a.fecha else date.today()
    c = generar_contrato(a.servicio, cliente, variables, fecha, a.salida)
    print(f"Contrato generado: {c.archivo}")
    if c.pendientes:
        print("Pendientes por completar/revisar (resaltados en amarillo en el Word):")
        for p in c.pendientes:
            print(f"  - {p}")


def cmd_confidencialidad(a):
    cliente = yaml.safe_load(Path(a.cliente).read_text(encoding="utf-8")) if a.cliente else {}
    variables = {}
    for par in a.var or []:
        k, _, v = par.partition("=")
        variables[k.strip()] = _valor(v)
    fecha = date.fromisoformat(a.fecha) if a.fecha else date.today()
    d = generar_documento("acuerdo_confidencialidad", cliente, variables, fecha, a.salida)
    print(f"Acuerdo generado: {d.archivo}")
    if d.pendientes:
        print("Pendientes (resaltados en amarillo):")
        for p in d.pendientes:
            print(f"  - {p}")


def cmd_propuesta(a):
    cliente = yaml.safe_load(Path(a.cliente).read_text(encoding="utf-8")) if a.cliente else {}
    variables = {}
    if a.variables:
        variables.update(yaml.safe_load(Path(a.variables).read_text(encoding="utf-8")) or {})
    for par in a.var or []:
        k, _, v = par.partition("=")
        variables[k.strip()] = _valor(v)
    fecha = date.fromisoformat(a.fecha) if a.fecha else date.today()
    p = generar_propuesta(a.servicio, cliente, variables, fecha, a.salida)
    print(f"Propuesta generada: {p.archivo}")
    if p.pendientes:
        print("Pendientes por completar:")
        for x in p.pendientes:
            print(f"  - {x}")


def _usd(v):
    return f"${v:,.2f}" if v else "—"


def cmd_base(a):
    from .base_clientes import cargar_base
    b = cargar_base(a.archivo)
    if a.accion == "resumen":
        r = b.resumen()
        print(f"Base: {b.archivo} · {r['clientes']} clientes")
        print("Estado en Census:", ", ".join(f"{k} {v}" for k, v in r["estado_census"]))
        print("Estado del RUC:", ", ".join(f"{k} {v}" for k, v in r["estado_ruc"]))
        print("Servicios (historial):", ", ".join(f"{k} {v}" for k, v in r["servicios"]))
        print("Sectores principales:", ", ".join(f"{k} {v}" for k, v in r["sectores"]))
        for o in b.observaciones:
            print("Observación:", o)
        return
    encontrados = b.buscar(" ".join(a.texto or []))
    if not encontrados:
        print("No se encontró el cliente.")
        return
    for c in encontrados[:5]:
        print(f"\n## {c['nombre']}  (RUC {c['ruc'] or 's/RUC'} · {c['estado_ruc'] or 's/estado'})")
        print(f"Census: {c['estado_census']} · Grupo: {c['grupo'] or '—'} · Referidor: {c['referidor'] or '—'} · {c['ciudad']}")
        print(f"Sector: {c['sector']} ({c['tipo_actividad']}) · Actividad: {c['objeto'][:90]}")
        print(f"CT IVA {_usd(c['ct_iva_ref'])} · CT IR {_usd(c['ct_ir_ref'])} · IR causado {_usd(c['ir_causado'])} · "
              f"Proyección IR {_usd(c['proyeccion_devolucion_ir'])}")
        print(f"ISD {_usd(c['isd_ref'])} / {_usd(c['isd_actual'])} · Deudores comerciales {_usd(c['cxc_no_relacionadas'])} · "
              f"Trabajadores (estimado) {c['trabajadores']:.0f}")
        print(f"Accionistas: {len(c['accionistas'])} ({c['accionistas_pn']} personas naturales) · "
              f"Administradores: {', '.join(n for n, _ in c['administradores']) or '—'}")
        for s_ in c["servicios"]:
            print(f"  - {s_['servicio']}: {s_['estado']} ({s_['fecha']}) {s_['detalle'][:70]}")
        if c["observacion_comercial"]:
            print(f"Observación comercial ({c['fecha_observacion']}): {c['observacion_comercial']}")
    if len(encontrados) > 5:
        print(f"\n… y {len(encontrados) - 5} coincidencias más.")


def cmd_presentacion_cobranza(a):
    from .presentacion_cobranzas import generar_presentacion
    ruta = generar_presentacion(" ".join(a.cliente), a.tipo, a.salida)
    print(f"Presentación generada: {ruta}")


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):           # Windows: forzar UTF-8
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agente-comercial", description="Agente Comercial Census")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("servicios", help="Lista la cartera de servicios").set_defaults(f=cmd_servicios)

    v = sub.add_parser("variables", help="Variables que necesita el contrato de un servicio")
    v.add_argument("servicio")
    v.set_defaults(f=cmd_variables)

    an = sub.add_parser("analizar-cliente", help="Lee un informe de investigación (Word) y propone servicios")
    an.add_argument("informe")
    an.add_argument("--salida", default=None)
    an.add_argument("--json", action="store_true", help="Imprime también las oportunidades en JSON")
    an.set_defaults(f=cmd_analizar)

    c = sub.add_parser("contrato", help="Genera el contrato .docx de un servicio")
    c.add_argument("servicio")
    c.add_argument("--cliente", help="YAML con razon_social, ruc, representante, cargo, ciudad, provincia, correos...")
    c.add_argument("--variables", help="YAML con las variables del servicio")
    c.add_argument("--var", action="append", help="variable=valor (se puede repetir)")
    c.add_argument("--fecha", help="AAAA-MM-DD (por defecto hoy)")
    c.add_argument("--salida", default=None)
    c.set_defaults(f=cmd_contrato)

    n = sub.add_parser("confidencialidad", help="Genera el acuerdo de confidencialidad (NDA) con el cliente")
    n.add_argument("--cliente", help="YAML del cliente (puede incluir representada_por y cedula)")
    n.add_argument("--var", action="append", help="objeto, sector, duracion_anios, ciudad_firma... (variable=valor)")
    n.add_argument("--fecha", help="AAAA-MM-DD (por defecto hoy)")
    n.add_argument("--salida", default=None)
    n.set_defaults(f=cmd_confidencialidad)

    pr = sub.add_parser("propuesta", help="Genera la propuesta de servicios (.pptx) con la plantilla Census")
    pr.add_argument("servicio")
    pr.add_argument("--cliente", help="YAML con razon_social y ciudad")
    pr.add_argument("--variables", help="YAML con las variables de la propuesta")
    pr.add_argument("--var", action="append", help="variable=valor (se puede repetir)")
    pr.add_argument("--fecha", help="AAAA-MM-DD")
    pr.add_argument("--salida", default=None)
    pr.set_defaults(f=cmd_propuesta)

    b = sub.add_parser("base", help="Consulta la base comercial de clientes (privado/base/*.xlsx)")
    b.add_argument("accion", choices=["resumen", "cliente"])
    b.add_argument("texto", nargs="*", help="RUC o parte del nombre (para 'cliente')")
    b.add_argument("--archivo", default=None)
    b.set_defaults(f=cmd_base)

    pc = sub.add_parser("presentacion-cobranza", help="Presentación institucional de Census Cobranzas (PDF) para un cliente")
    pc.add_argument("cliente", nargs="+", help="Razón social como debe aparecer")
    pc.add_argument("--tipo", default="empresa", choices=["financiera", "cooperativa", "empresa"])
    pc.add_argument("--salida", default=None)
    pc.set_defaults(f=cmd_presentacion_cobranza)

    a = p.parse_args(argv)
    a.f(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())

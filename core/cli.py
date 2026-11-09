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
        estado = "contrato tipo" if s.get("clausulas") else "SIN contrato tipo"
        print(f"{sid:28} {s['materia']:18} {estado:18} {s['nombre']}")


def cmd_variables(a):
    scl = kb.clausulas_servicio(a.servicio)
    print(f"Variables de '{a.servicio}' (además de los datos del cliente):")
    for k, m in (scl.get("variables") or {}).items():
        req = " (obligatoria)" if m.get("requerido") else ""
        print(f"  {k}{req}: {m.get('descripcion')}  — ej.: {m.get('ejemplo')}")


def cmd_analizar(a):
    inf = leer_informe(a.informe)
    r = analizar_grupo(inf)
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

    a = p.parse_args(argv)
    a.f(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())

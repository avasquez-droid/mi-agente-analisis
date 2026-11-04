"""Interfaz de línea de comandos.

Ejemplos:
    python -m core.cli analizar examples/datos_equipo.xlsx
    python -m core.cli analizar datos.xlsx --skill evaluacion-desempeno --formatos pdf,docx
    python -m core.cli explorar datos.xlsx
    python -m core.cli skills
"""
from __future__ import annotations

import argparse
import json
import sys

from .agent import ejecutar, explorar, listar_skills
from .excel_reader import listar_hojas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agente", description="Agente de Análisis Inteligente")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("analizar", help="Aplica una skill a un Excel y genera entregables")
    p.add_argument("archivo", help="Ruta al .xlsx/.xls/.csv")
    p.add_argument("--skill", default="evaluacion-desempeno", help="Id de la skill (ver 'skills')")
    p.add_argument("--formatos", default="pdf,xlsx,docx,md", help="Lista separada por comas")
    p.add_argument("--salida", default=None, help="Carpeta de salida (por defecto salidas/)")
    p.add_argument("--hoja", default=None, help="Nombre o índice de hoja")
    p.add_argument("--titulo", default=None, help="Título del informe")

    e = sub.add_parser("explorar", help="Perfila el archivo sin aplicar metodología")
    e.add_argument("archivo")
    e.add_argument("--hoja", default=None)

    sub.add_parser("skills", help="Lista las skills disponibles")

    h = sub.add_parser("hojas", help="Lista las hojas de un Excel")
    h.add_argument("archivo")

    args = parser.parse_args(argv)
    hoja = getattr(args, "hoja", None)
    if hoja is not None and str(hoja).isdigit():
        hoja = int(hoja)

    if args.comando == "skills":
        for s in listar_skills():
            print(s)
        return 0
    if args.comando == "hojas":
        print("\n".join(listar_hojas(args.archivo)))
        return 0
    if args.comando == "explorar":
        print(json.dumps(explorar(args.archivo, hoja), ensure_ascii=False, indent=2))
        return 0

    salida = ejecutar(args.archivo, skill=args.skill, formatos=args.formatos.split(","),
                      carpeta_salida=args.salida, hoja=hoja, titulo=args.titulo)
    print(salida.resumen_texto())
    return 0


if __name__ == "__main__":
    sys.exit(main())

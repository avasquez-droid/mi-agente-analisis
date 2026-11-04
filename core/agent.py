"""Agente principal: orquesta lectura → análisis → insights → entregables."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .analyzer import ResultadoAnalisis, analizar
from .excel_reader import cargar_archivo, perfilar
from .insights import Insight, PlanAccion, generar_insights, generar_plan_accion
from .metodologia import RAIZ, cargar_metodologia, listar_skills
from .report_excel import generar_excel
from .report_pdf import generar_pdf
from .report_word import generar_word

FORMATOS_VALIDOS = {"pdf", "xlsx", "docx", "md"}


@dataclass
class ResultadoAgente:
    resultado: ResultadoAnalisis
    insights: list[Insight]
    plan: PlanAccion
    archivos: dict[str, Path] = field(default_factory=dict)

    def resumen_texto(self) -> str:
        """Resumen en Markdown para mostrar en el chat (Claude o GPT)."""
        env = Environment(loader=FileSystemLoader(RAIZ / "templates"), autoescape=False)
        tpl = env.get_template("resumen_chat.md.j2")
        return tpl.render(res=self.resultado, insights=self.insights, plan=self.plan,
                          archivos=self.archivos)


def ejecutar(ruta_excel: str | Path, skill: str = "evaluacion-desempeno",
             formatos: list[str] | None = None, carpeta_salida: str | Path | None = None,
             hoja: str | int | None = None, titulo: str | None = None) -> ResultadoAgente:
    """Punto de entrada único del agente.

    Args:
        ruta_excel: archivo .xlsx/.xls/.csv con los datos.
        skill: id de la metodología en skills/<skill>/metodologia.yaml.
        formatos: subconjunto de {"pdf", "xlsx", "docx", "md"}; por defecto todos.
        carpeta_salida: carpeta donde guardar; por defecto salidas/.
        hoja: nombre o índice de la hoja del Excel.
        titulo: título del informe.
    """
    formatos = [f.lower() for f in (formatos or sorted(FORMATOS_VALIDOS))]
    invalidos = set(formatos) - FORMATOS_VALIDOS
    if invalidos:
        raise ValueError(f"Formatos no válidos: {invalidos}. Use: {sorted(FORMATOS_VALIDOS)}")

    df = cargar_archivo(ruta_excel, hoja=hoja)
    met = cargar_metodologia(skill)
    res = analizar(df, met)
    insights = generar_insights(res)
    plan = generar_plan_accion(res)

    carpeta = Path(carpeta_salida) if carpeta_salida else RAIZ / "salidas"
    carpeta.mkdir(parents=True, exist_ok=True)
    base = f"{Path(ruta_excel).stem}_{skill}_{datetime.now():%Y%m%d_%H%M}"
    titulo = titulo or f"Informe: {met.nombre}"

    archivos: dict[str, Path] = {}
    if "pdf" in formatos:
        archivos["pdf"] = generar_pdf(res, insights, plan, carpeta / f"{base}_informe.pdf", titulo)
    if "xlsx" in formatos:
        archivos["xlsx"] = generar_excel(res, insights, plan, carpeta / f"{base}_analisis.xlsx")
    if "docx" in formatos:
        archivos["docx"] = generar_word(res, insights, plan, carpeta / f"{base}_plan_accion.docx",
                                        "Plan de Acción")

    salida = ResultadoAgente(res, insights, plan, archivos)
    if "md" in formatos:
        ruta_md = carpeta / f"{base}_resumen.md"
        ruta_md.write_text(salida.resumen_texto(), encoding="utf-8")
        archivos["md"] = ruta_md
    return salida


def explorar(ruta_excel: str | Path, hoja: str | int | None = None) -> dict:
    """Perfila un archivo sin aplicar metodología (skill analisis-datos)."""
    df = cargar_archivo(ruta_excel, hoja=hoja)
    return perfilar(df)


__all__ = ["ejecutar", "explorar", "listar_skills", "ResultadoAgente"]

"""Documentos que no son contratos de servicio (p. ej. acuerdo de confidencialidad).

Cada documento se describe en conocimiento/documentos/<id>.yaml con: titulo, introduccion,
exponen (lista romana), clausulas (PRIMERA. - Título:), cierre y firmas (tabla de 2 columnas).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt

from . import conocimiento as kb
from .contratos import MESES, PLANTILLA_BASE, _entorno, ordinal

ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


@dataclass
class DocumentoGenerado:
    doc_id: str
    archivo: Path | None
    titulo: str
    introduccion: list[str]
    exponen: list[str]
    clausulas: list[tuple[str, list[str]]]
    cierre: str
    firmas: list[list[str]]
    pendientes: list[str] = field(default_factory=list)

    def texto(self) -> str:
        l = [self.titulo, ""] + self.introduccion
        if self.exponen:
            l += ["EXPONEN"] + [f"{ROMANOS[i]}. {x}" for i, x in enumerate(self.exponen)]
        l += ["CLÁUSULAS"]
        for i, (t, ps) in enumerate(self.clausulas, 1):
            l += [f"{ordinal(i)}. - {t}:"] + ps
        return "\n".join(l + [self.cierre])


def armar_documento(doc_id: str, cliente: dict, variables: dict | None = None,
                    fecha: date | None = None) -> DocumentoGenerado:
    d = kb.documento(doc_id)
    census = kb.entidades()[d.get("entidad", "censusconsultores")]
    v = dict(d.get("valores_por_defecto") or {})
    v.update({k: x for k, x in (variables or {}).items() if x not in (None, "")})
    cliente = {"persona": "juridica", **{k: x for k, x in cliente.items() if x not in (None, "")}}

    env = _entorno()
    env.filters["mes"] = lambda f: MESES[f.month - 1]
    ctx = {"cliente": cliente, "census": census, "v": v, "fecha": fecha or date.today()}

    def r(texto) -> str:
        return re.sub(r"[ \t]+", " ", env.from_string(str(texto)).render(**ctx)).strip()

    doc = DocumentoGenerado(
        doc_id=doc_id, archivo=None, titulo=r(d["titulo"]),
        introduccion=[r(p) for p in d.get("introduccion", [])],
        exponen=[r(p) for p in (d.get("exponen") or {}).get("items", [])],
        clausulas=[(r(c["titulo"]), [r(p) for p in c["parrafos"]]) for c in d.get("clausulas", [])],
        cierre=r(d.get("cierre", "")),
        firmas=[[r(x) for x in col] for col in d.get("firmas", [])],
    )
    texto = doc.texto() + "\n" + "\n".join(x for col in doc.firmas for x in col)
    doc.pendientes = sorted(set(re.findall(r"\[COMPLETAR: ([^\]]+)\]", texto)))
    return doc


# ----------------------------------------------------------------- Word
def _runs(p, texto, fuente, tam, negrita=False):
    """Escribe texto admitiendo **negrita** y resaltando [COMPLETAR: ...]."""
    for trozo in re.split(r"(\*\*[^*]+\*\*|\[COMPLETAR: [^\]]+\])", texto):
        if not trozo:
            continue
        b = negrita
        if trozo.startswith("**"):
            trozo, b = trozo[2:-2], True
        run = p.add_run(trozo)
        run.bold = b
        run.font.name, run.font.size = fuente, Pt(tam)
        if trozo.startswith("[COMPLETAR"):
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run.bold = True


def escribir_docx(gen: DocumentoGenerado, salida: Path) -> Path:
    d = kb.documento(gen.doc_id)
    fuente, tam = d.get("fuente", "Arial"), float(d.get("tamano", 11))
    doc = docx.Document(str(PLANTILLA_BASE))

    def par(texto="", negrita=False, alinear=WD_ALIGN_PARAGRAPH.JUSTIFY, sangria=0.0, colgante=0.0):
        p = doc.add_paragraph()
        p.alignment = alinear
        pf = p.paragraph_format
        pf.space_after, pf.line_spacing = Pt(6), 1.15
        if sangria:
            pf.left_indent = Cm(sangria)
        if colgante:
            pf.first_line_indent = Cm(-colgante)
        if texto:
            _runs(p, texto, fuente, tam, negrita)
        return p

    par(gen.titulo, True, WD_ALIGN_PARAGRAPH.CENTER)
    par()
    for t in gen.introduccion:
        par(t)
    if gen.exponen:
        par("EXPONEN", True, WD_ALIGN_PARAGRAPH.CENTER).paragraph_format.keep_with_next = True
        for i, t in enumerate(gen.exponen):
            par(f"{ROMANOS[i]}.\t{t}", sangria=1.0, colgante=1.0)
    par(d.get("clausulas_titulo", "CLÁUSULAS"), True, WD_ALIGN_PARAGRAPH.CENTER).paragraph_format.keep_with_next = True
    for i, (titulo, parrafos) in enumerate(gen.clausulas, 1):
        par(f"{ordinal(i)}. - {titulo}:", True).paragraph_format.keep_with_next = True
        for t in parrafos:
            if t.startswith("- "):
                par("•  " + t[2:], sangria=1.0, colgante=0.5)
            elif re.match(r"^[a-z]\)\s", t):
                par(t, sangria=1.0, colgante=0.5)
            else:
                par(t, sangria=0.2)
    par()
    cierre = par(gen.cierre)
    cierre.paragraph_format.keep_with_next = True
    par().paragraph_format.keep_with_next = True

    filas = max(len(c) for c in gen.firmas)
    tabla = doc.add_table(rows=filas, cols=len(gen.firmas))
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    for fila in tabla.rows:
        fila._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    for j, col in enumerate(gen.firmas):
        for i, linea in enumerate(col):
            celda = tabla.cell(i, j).paragraphs[0]
            celda.paragraph_format.keep_with_next = True
            if linea:
                _runs(celda, linea, fuente, tam, negrita=(i == 0))

    props = doc.core_properties
    props.title, props.author = gen.titulo, kb.entidades()[d.get("entidad", "censusconsultores")]["razon_social"]
    salida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(salida))
    return salida


def generar_documento(doc_id: str, cliente: dict, variables: dict | None = None,
                      fecha: date | None = None, carpeta_salida: str | Path | None = None) -> DocumentoGenerado:
    gen = armar_documento(doc_id, cliente, variables, fecha)
    nombre = re.sub(r"[^\w\s.-]", "", cliente.get("razon_social", "CLIENTE")).strip()
    carpeta = Path(carpeta_salida) if carpeta_salida else kb.RAIZ / "salidas"
    gen.archivo = escribir_docx(gen, carpeta / f"{gen.titulo.capitalize()} - {nombre}.docx")
    return gen

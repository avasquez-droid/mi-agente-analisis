"""Generación de contratos .docx a partir de la biblioteca de cláusulas.

Contrato = cláusulas comunes (conocimiento/clausulas/comunes.yaml)
         + cláusulas del servicio (conocimiento/clausulas/servicios/<servicio>.yaml)
         + datos del cliente + variables del servicio + tarifario.

Lo que falte se escribe como [COMPLETAR: campo] resaltado en amarillo, y se informa en
`pendientes` para que el abogado lo revise antes de enviar.
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
from docx.oxml.ns import qn
from docx.shared import Pt, Cm
from jinja2 import ChainableUndefined, Environment
from num2words import num2words

from . import conocimiento as kb

PLANTILLA_BASE = kb.RAIZ / "plantillas" / "contratos" / "base_census.docx"
FUENTE, TAMANO = "Georgia", 10.5

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
ORDINALES = ["PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA", "OCTAVA",
             "NOVENA", "DÉCIMA"]
LITERALES = "abcdefghijklmnopqrstuvwxyz"


def normalizar_cargo(cargo) -> str:
    """Cargo del representante del cliente tal como debe ir en contratos y documentos.
    Regla de Census: "Gerente" se escribe siempre "Gerente General". Quita marcas de la base
    como "(RL)" o "(ADM)" y usa mayúscula inicial."""
    if not cargo or isinstance(cargo, ChainableUndefined):
        return cargo
    texto = re.sub(r"\s*\((RL|ADM|R\.L\.)\)\s*", " ", str(cargo), flags=re.I).strip()
    texto = " ".join(p.capitalize() if p.lower() not in {"de", "del", "y"} else p.lower() for p in texto.split())
    if texto.lower() == "gerente":
        texto = "Gerente General"
    return texto


def ordinal(n: int) -> str:
    if n <= 10:
        return ORDINALES[n - 1]
    return f"DÉCIMA {ORDINALES[n - 11]}"


# ----------------------------------------------------------------- filtros Jinja
class _Falta(ChainableUndefined):
    """Variable no proporcionada: se escribe como marcador visible."""
    def __str__(self):
        return f"[COMPLETAR: {self._undefined_name}]"

    def __mul__(self, other):
        return self
    __rmul__ = __truediv__ = __rtruediv__ = __sub__ = __rsub__ = __add__ = __radd__ = __mul__


def _num(v):
    return None if isinstance(v, _Falta) or v in (None, "") else float(v)


def fecha_larga(d):
    if isinstance(d, _Falta) or d is None:
        return str(d)
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def usd(v):
    n = _num(v)
    if n is None:
        return str(v)
    entero, dec = f"{n:,.2f}".split(".")
    return f"USD ${entero.replace(',', '.')},{dec}"


def letras(v):
    n = _num(v)
    if n is None:
        return str(v)
    entero = int(n)
    centavos = round((n - entero) * 100)
    texto = num2words(entero, lang="es").replace("uno mil", "un mil")
    return f"{texto.title().replace(' Y ', ' y ')} {centavos:02d}/100"


def letras_int(v):
    n = _num(v)
    return str(v) if n is None else num2words(int(n), lang="es")


def pct(v):
    n = _num(v)
    if n is None:
        return str(v)
    return f"{n:g}%".replace(".", ",")


def pct_letras(v):
    n = _num(v)
    if n is None:
        return str(v)
    if n == int(n):
        return f"{num2words(int(n), lang='es')} por ciento ({pct(n)})"
    return f"{pct(n)}"


def _entorno() -> Environment:
    env = Environment(undefined=_Falta, autoescape=False, trim_blocks=True, lstrip_blocks=True)
    env.filters.update(fecha_larga=fecha_larga, usd=usd, letras=letras, letras_int=letras_int,
                       pct=pct, pct_letras=pct_letras)
    return env


# ----------------------------------------------------------------- armado
@dataclass
class Clausula:
    clave: str
    titulo: str
    parrafos: list[str] = field(default_factory=list)


@dataclass
class ContratoGenerado:
    archivo: Path | None
    titulo: str
    encabezado: str
    clausulas: list[Clausula]
    pendientes: list[str]

    def texto(self) -> str:
        partes = [self.titulo, "", self.encabezado, ""]
        for i, c in enumerate(self.clausulas, 1):
            partes += [f"{ordinal(i)}: {c.titulo}. -", ""] + [p + "\n" for p in c.parrafos]
        return "\n".join(partes)


def _variables_por_defecto(servicio_id: str, srv_cl: dict) -> dict:
    t = kb.tarifario().get(servicio_id, {})
    v = {}
    if t.get("valor") is not None:
        v["porcentaje"] = t["valor"] if t.get("modelo") in {"porcentaje", "etapas"} else None
        v["honorario"] = t["valor"] if t.get("modelo") in {"fijo", "mensual"} else None
    if t.get("anticipo_usd") is not None:
        v["anticipo"] = t["anticipo_usd"]
    if t.get("limite_transacciones") is not None:
        v["limite_transacciones"] = t["limite_transacciones"]
    for k in ("tramite", "tipo_servicio", "titulo_tipo"):
        if srv_cl.get(k):
            v[k] = srv_cl[k]
    return {k: x for k, x in v.items() if x is not None}


def armar_contrato(servicio_id: str, cliente: dict, variables: dict | None = None,
                   fecha: date | None = None) -> ContratoGenerado:
    srv = kb.servicio(servicio_id)
    comunes = kb.clausulas_comunes()
    scl = kb.clausulas_servicio(servicio_id)
    census = dict(kb.entidades()[srv["entidad"]])
    if scl.get("actividad_census"):            # p. ej. cobranza judicial
        census["actividad"] = scl["actividad_census"]
    t = kb.tarifario().get(servicio_id, {})

    v = _variables_por_defecto(servicio_id, scl)
    v.update({k: x for k, x in (variables or {}).items() if x not in (None, "")})
    cliente = {"persona": "juridica", "correos": [], **{k: x for k, x in cliente.items() if x not in (None, "")}}
    if cliente.get("cargo"):
        cliente["cargo"] = normalizar_cargo(cliente["cargo"])
    if isinstance(cliente.get("correos"), str):
        cliente["correos"] = [c.strip() for c in re.split(r"[;,]", cliente["correos"]) if c.strip()]

    # Orden de cláusulas
    orden = list(scl.get("orden") or comunes["orden"])
    if "obligaciones" in orden and not scl.get("obligaciones"):
        orden.remove("obligaciones")
    for extra in scl.get("extras", []):
        if extra not in orden:
            orden.insert(orden.index("terminacion"), extra)
    posicion = {clave: i + 1 for i, clave in enumerate(orden)}

    env = _entorno()
    ctx = {"cliente": cliente, "census": census, "fecha": fecha or date.today(), "v": v, "t": t,
           "ordinal_de": lambda clave: ordinal(posicion[clave]) if clave in posicion else f"[COMPLETAR: cláusula {clave}]"}

    def r(texto: str) -> str:
        return re.sub(r"[ \t]+", " ", env.from_string(texto).render(**ctx)).strip()

    def render_parrafos(lista):
        salida = []
        for p in lista:
            for linea in r(p).split("\n"):
                if linea.strip():
                    salida.append(linea.strip())
        return salida

    clausulas: list[Clausula] = []
    for clave in orden:
        if clave == "antecedentes":
            items = [comunes["clausulas"]["antecedente_census"]] + list(scl.get("antecedentes", []))
            if scl.get("cierre_antecedentes"):
                items.append(comunes["clausulas"]["antecedente_cierre"])
            textos = [x for x in (r(i) for i in items) if x and "[COMPLETAR: antecedente_cliente]" not in x]
            parr = [f"{LITERALES[i]}) {x}" for i, x in enumerate(textos)]
            clausulas.append(Clausula(clave, "ANTECEDENTES", parr))
            continue
        fuente = scl.get(clave) or comunes["clausulas"].get(clave)
        if not fuente:
            continue
        clausulas.append(Clausula(clave, r(fuente["titulo"]), render_parrafos(fuente["parrafos"])))

    titulo = r(comunes["titulo"])
    encabezado = r(comunes["encabezado"])
    texto_total = "\n".join([titulo, encabezado] + [p for c in clausulas for p in c.parrafos])
    pendientes = sorted(set(re.findall(r"\[COMPLETAR: ([^\]]+)\]", texto_total)))
    for req, meta in (scl.get("variables") or {}).items():
        if isinstance(meta, dict) and meta.get("requerido") and req not in v and req not in pendientes:
            pendientes.append(req)
    if "PROPUESTA" in (kb.CARPETA / "clausulas" / "servicios" / srv["clausulas"]).read_text(encoding="utf-8"):
        pendientes.append("cláusulas marcadas como PROPUESTA en la plantilla del servicio (validar)")
    return ContratoGenerado(None, titulo, encabezado, clausulas, pendientes)


# ----------------------------------------------------------------- Word
def fijar_fuente_base(doc, fuente: str, tamano: float) -> None:
    """La plantilla trae Calibri 12 por defecto: líneas en blanco y lo que el abogado escriba
    después saldrían en Calibri. Se fija la fuente del documento en el estilo Normal."""
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = fuente, Pt(tamano)
    rpr = normal.element.get_or_add_rPr()
    fuentes = rpr.find(qn("w:rFonts"))
    if fuentes is None:
        fuentes = OxmlElement("w:rFonts")
        rpr.insert(0, fuentes)
    for atributo in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fuentes.set(qn(atributo), fuente)
    for tema in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        fuentes.attrib.pop(qn(tema), None)


def _run(p, texto, negrita=False, fuente=None, tamano=None):
    """Agrega texto al párrafo resaltando los marcadores [COMPLETAR: ...]."""
    for trozo in re.split(r"(\[COMPLETAR: [^\]]+\])", texto):
        if not trozo:
            continue
        run = p.add_run(trozo)
        run.bold = negrita
        run.font.name, run.font.size = fuente or FUENTE, Pt(tamano or TAMANO)
        run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:cs"), fuente or FUENTE)
        if trozo.startswith("[COMPLETAR"):
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            run.bold = True
    return p


def _parrafo(doc, texto="", negrita=False, centrado=False, fuente=None, tamano=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centrado else WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    if texto:
        _run(p, texto, negrita, fuente, tamano)
    return p


_LITERAL = re.compile(r"^((?:[a-z]|\d{1,2}|[ivx]+)\)|\(\d+\))\s+")


def escribir_docx(contrato: ContratoGenerado, cliente: dict, entidad: dict, salida: Path) -> Path:
    doc = docx.Document(str(PLANTILLA_BASE))
    fijar_fuente_base(doc, FUENTE, TAMANO)
    # Título en la misma fuente del contrato (Georgia), negrita, centrado y un punto más grande
    _parrafo(doc, contrato.titulo, negrita=True, centrado=True, tamano=11)
    _parrafo(doc)
    _parrafo(doc, contrato.encabezado)
    _parrafo(doc)
    for i, c in enumerate(contrato.clausulas, 1):
        _parrafo(doc, f"{ordinal(i)}: {c.titulo}. -", negrita=True)
        _parrafo(doc)
        for texto in c.parrafos:
            p = _parrafo(doc)
            if texto.startswith("- "):
                p.paragraph_format.left_indent = Cm(1)
                p.paragraph_format.first_line_indent = Cm(-0.5)
                _run(p, "•  " + texto[2:])
            elif texto.startswith("Obligaciones de"):
                _run(p, texto, negrita=True)
            else:
                m = _LITERAL.match(texto)
                if m:
                    p.paragraph_format.left_indent = Cm(0.6)
                    _run(p, m.group(1), negrita=True)
                    _run(p, " " + texto[m.end():])
                else:
                    _run(p, texto)
            _parrafo(doc)

    # Firmas: la última cláusula (aceptación) queda en la misma página que las firmas
    _parrafo(doc)
    ultima = f"{ordinal(len(contrato.clausulas))}:"
    inicio = max(i for i, p in enumerate(doc.paragraphs) if p.text.startswith(ultima))
    for p in doc.paragraphs[inicio:]:
        p.paragraph_format.keep_with_next = True
    tabla = doc.add_table(rows=1, cols=2)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tr_pr = tabla.rows[0]._tr.get_or_add_trPr()          # el bloque de firmas no se parte entre páginas
    tr_pr.append(OxmlElement("w:cantSplit"))
    firmas = [
        ("“EL CONTRATANTE”", cliente.get("representante") or cliente.get("razon_social"),
         cliente.get("cargo", "") if cliente.get("persona", "juridica") != "natural" else "",
         cliente.get("razon_social") if cliente.get("persona", "juridica") != "natural" else ""),
        ("“EL CONTRATADO”", f"{entidad['representante'].get('tratamiento', '')} {entidad['representante']['nombre']}".strip(),
         entidad["representante"]["cargo"], entidad["razon_social"]),
    ]
    for celda, (rol, nombre, cargo, empresa) in zip(tabla.rows[0].cells, firmas):
        celda.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(celda.paragraphs[0], rol, True)
        for linea in ["", "", "", nombre or "[COMPLETAR: representante]", cargo, empresa]:
            p = celda.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if linea:
                _run(p, linea, True)

    props = doc.core_properties
    props.title = contrato.titulo
    props.author = entidad["razon_social"]
    salida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(salida))
    return salida


def _nombre_archivo(cliente: dict, servicio_id: str) -> str:
    base = re.sub(r"[^\w\s.-]", "", cliente.get("razon_social", "CLIENTE")).strip()
    return f"{base} - {kb.servicio(servicio_id)['nombre'][:60]}.docx".replace("/", "-")


def generar_contrato(servicio_id: str, cliente: dict, variables: dict | None = None,
                     fecha: date | None = None, carpeta_salida: str | Path | None = None) -> ContratoGenerado:
    contrato = armar_contrato(servicio_id, cliente, variables, fecha)
    entidad = kb.entidades()[kb.servicio(servicio_id)["entidad"]]
    carpeta = Path(carpeta_salida) if carpeta_salida else kb.RAIZ / "salidas"
    contrato.archivo = escribir_docx(contrato, cliente, entidad, carpeta / _nombre_archivo(cliente, servicio_id))
    return contrato

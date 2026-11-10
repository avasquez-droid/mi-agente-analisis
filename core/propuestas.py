"""Generación de propuestas de servicios (PPTX) con la plantilla de Census.

La plantilla (privado/plantillas/propuesta_base.pptx) es una propuesta real de Census: portada,
introducción, socios, antecedentes, objetivo, alcance, honorarios, gerentes, coordinadores,
clientes, certificaciones y cierre. Se queda fuera del repositorio público porque contiene fotos
del equipo y logos de clientes.

El agente reemplaza los textos de las diapositivas variables con conocimiento/propuestas/<x>.yaml
y duplica diapositivas cuando hacen falta secciones extra (base legal, plazos...) o más alcance.
Las diapositivas fijas (equipo, clientes, certificaciones, cierre) no se tocan.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml
from pptx import Presentation
from pptx.util import Pt

from . import conocimiento as kb
from .contratos import _entorno

PLANTILLA = kb.RAIZ / "privado" / "plantillas" / "propuesta_base.pptx"
CARPETA = kb.CARPETA / "propuestas"

# Índices (0-based) y nombres de formas en la plantilla
S_PORTADA, S_INTRO, S_SOCIOS, S_ANTEC, S_OBJ, S_ALC, S_HON = 0, 1, 2, 3, 4, 5, 6
F = {
    "portada": "Google Shape;91;p1",
    "destinatario": "Google Shape;101;p2",
    "carta": "Google Shape;102;p2",
    "antec_titulo": "Google Shape;117;p3",
    "antec_cuerpo": "Google Shape;118;p3",
    "objetivo": "Google Shape;149;p5",
    "alc_intro": "Google Shape;161;p6",
    "alc_cuerpo": "Google Shape;159;p6",
    "alc_titulo": "Google Shape;158;p6",
    "hon_titulo": "Google Shape;181;p7",
    "hon_intro": "Google Shape;182;p7",
    "hon_notas": "Google Shape;183;p7",
}
VINETAS_ALC = {f"Google Shape;{n};p6" for n in (160, 162, 164, 166, 167, 168)}
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


# ----------------------------------------------------------------- contenido
@dataclass
class PropuestaArmada:
    servicio_id: str
    portada: str
    destinatario: list[str]
    carta: list[str]
    antecedentes: list[str]
    secciones: list[tuple[str, list[str]]]
    objetivo: str
    alcance: list[tuple[str, list[str]]]
    honorarios_intro: str
    honorarios: list[dict]
    notas: list[str]
    archivo: Path | None = None
    pendientes: list[str] = field(default_factory=list)

    def texto(self) -> str:
        l = [self.portada, *self.destinatario, *self.carta, "ANTECEDENTES", *self.antecedentes]
        for t, ps in self.secciones:
            l += [t.upper(), *ps]
        l += ["OBJETIVO", self.objetivo, "ALCANCE"]
        for t, items in self.alcance:
            l += ([t] if t else []) + [f"- {x}" for x in items]
        l += ["HONORARIOS", self.honorarios_intro]
        l += [f"{h['servicio']} | {h['honorario']} | {h['forma_pago']}" for h in self.honorarios]
        return "\n".join(l + self.notas)


def plantilla_servicio(servicio_id: str) -> dict:
    archivo = kb.servicio(servicio_id).get("propuesta")
    if not archivo:
        raise ValueError(f"El servicio '{servicio_id}' aún no tiene textos de propuesta (campo 'propuesta').")
    return yaml.safe_load((CARPETA / archivo).read_text(encoding="utf-8"))


def armar_propuesta(servicio_id: str, cliente: dict, variables: dict | None = None,
                    fecha: date | None = None) -> PropuestaArmada:
    comunes = yaml.safe_load((CARPETA / "comunes.yaml").read_text(encoding="utf-8"))
    p = plantilla_servicio(servicio_id)
    srv = kb.servicio(servicio_id)
    t = kb.tarifario().get(srv.get("propuesta_tarifa") or srv.get("tarifa", servicio_id), {})
    v = dict(srv.get("propuesta_vars") or {})
    if t.get("valor") is not None:
        v["porcentaje" if t.get("modelo") in {"porcentaje", "etapas"} else "honorario"] = t["valor"]
    v.update({k: x for k, x in (variables or {}).items() if x not in (None, "")})
    cliente = {"ciudad": "Guayaquil", **{k: x for k, x in cliente.items() if x not in (None, "")}}

    env = _entorno()
    ctx = {"cliente": cliente, "v": v, "t": t, "fecha": fecha or date.today(),
           "tarifa": lambda k: kb.tarifario().get(k, {})}

    def r(texto) -> str:
        if texto is None:
            return ""
        return re.sub(r"[ \t]+", " ", env.from_string(str(texto)).render(**ctx)).strip()

    def activo(bloque) -> bool:
        return not (isinstance(bloque, dict) and bloque.get("si") and not v.get(bloque["si"]))

    ctx["asunto"] = r(p.get("asunto"))
    carta = ["De nuestra consideración:", ""]
    for parrafo in comunes["introduccion"]:
        carta += [r(parrafo), ""]
    carta += ["Muy atentamente,", "", "**Census Consultores S.A.S.**"]

    hon = p.get("honorarios", {})
    arm = PropuestaArmada(
        servicio_id=servicio_id,
        portada=r(p["portada"]).upper(),
        destinatario=["Señores", cliente.get("razon_social", "[COMPLETAR: cliente]"),
                      f"{cliente['ciudad']}, Ecuador"],
        carta=carta,
        antecedentes=[x for x in (r(a) for a in p.get("antecedentes", [])) for x in x.split("\n") if x.strip()],
        secciones=[(r(s["titulo"]), [r(x) for x in s["parrafos"]]) for s in p.get("secciones", []) if activo(s)],
        objetivo=r(p.get("objetivo")),
        alcance=[(r(b.get("titulo")), [r(i) for i in b["items"]]) for b in p.get("alcance", []) if activo(b)],
        honorarios_intro=r(comunes["honorarios_intro"]) + (" " + r(hon["intro_extra"]) if hon.get("intro_extra") else ""),
        honorarios=[{k: r(f.get(k)) for k in ("servicio", "honorario", "forma_pago")}
                    for f in hon.get("filas", []) if activo(f)],
        notas=[r(n) for n in hon.get("notas", [])] + [r(comunes["honorarios_cierre"])],
    )
    arm.pendientes = sorted(set(re.findall(r"\[COMPLETAR: ([^\]]+)\]", arm.texto())))
    for k, m in (p.get("variables") or {}).items():
        if isinstance(m, dict) and m.get("requerido") and k not in v and k not in arm.pendientes:
            arm.pendientes.append(k)
    return arm


# ----------------------------------------------------------------- PPTX
def _forma(slide, nombre):
    for sh in slide.shapes:
        if sh.name == nombre:
            return sh
    raise KeyError(f"La plantilla no tiene la forma '{nombre}'")


def _escribir(shape, parrafos: list[str], tamano: float | None = None):
    """Reemplaza el texto conservando el formato del primer párrafo con texto."""
    tf = shape.text_frame
    modelo = next((p for p in tf.paragraphs if p.runs), tf.paragraphs[0])
    p_xml = copy.deepcopy(modelo._p)
    r_xml = copy.deepcopy(modelo.runs[0]._r) if modelo.runs else None
    for p in list(tf.paragraphs):
        p._p.getparent().remove(p._p)
    for texto in parrafos:
        nuevo = copy.deepcopy(p_xml)
        for hijo in list(nuevo):
            if hijo.tag in (f"{NS_A}r", f"{NS_A}br", f"{NS_A}fld"):
                nuevo.remove(hijo)
        tf._txBody.append(nuevo)
        if not texto:
            continue
        vineta = texto.startswith("- ")
        if vineta:
            texto = "▪ " + texto[2:]
        for trozo in re.split(r"(\*\*[^*]+\*\*)", texto):
            if not trozo:
                continue
            run = copy.deepcopy(r_xml) if r_xml is not None else None
            if run is None:
                nuevo_run = tf.paragraphs[-1].add_run()
            else:
                nuevo.append(run)
                nuevo_run = tf.paragraphs[-1].runs[-1]
            negrita = trozo.startswith("**")
            nuevo_run.text = trozo[2:-2] if negrita else trozo
            if negrita:
                nuevo_run.font.bold = True
            if tamano:
                nuevo_run.font.size = Pt(tamano)


def _tamano(parrafos: list[str], base: float, limites=((700, 0), (1100, -2), (1500, -3), (99999, -4))) -> float:
    largo = sum(len(p) for p in parrafos)
    return base + next(d for lim, d in limites if largo <= lim)


def _duplicar(prs, indice: int, despues_de: int):
    """Copia la diapositiva `indice` (con imágenes) y la coloca después de `despues_de`."""
    origen = prs.slides[indice]
    nueva = prs.slides.add_slide(origen.slide_layout)
    for sh in list(nueva.shapes):
        sh._element.getparent().remove(sh._element)
    mapa = {}
    for rid, rel in origen.part.rels.items():
        if rel.reltype.endswith("/notesSlide") or rel.reltype.endswith("/slideLayout"):
            continue
        mapa[rid] = nueva.part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref) if rel.is_external \
            else nueva.part.relate_to(rel.target_part, rel.reltype)
    for el in origen.shapes._spTree.iterchildren():
        if el.tag.endswith("}nvGrpSpPr") or el.tag.endswith("}grpSpPr"):
            continue
        copia = copy.deepcopy(el)
        for nodo in copia.iter():
            for attr, val in list(nodo.attrib.items()):
                if attr.startswith("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}") and val in mapa:
                    nodo.set(attr, mapa[val])
        nueva.shapes._spTree.append(copia)
    bg = origen._element.cSld.bg
    if bg is not None:
        nueva._element.cSld.insert(0, copy.deepcopy(bg))
    lista = prs.slides._sldIdLst
    item = lista[-1]
    lista.remove(item)
    lista.insert(despues_de + 1, item)
    return nueva


def _partir(items: list[str], max_chars=1100, max_items=7) -> list[list[str]]:
    grupos, actual, largo = [], [], 0
    for x in items:
        if actual and (largo + len(x) > max_chars or len(actual) >= max_items):
            grupos.append(actual)
            actual, largo = [], 0
        actual.append(x)
        largo += len(x)
    return grupos + ([actual] if actual else [])


def escribir_pptx(arm: PropuestaArmada, salida: Path) -> Path:
    if not PLANTILLA.exists():
        raise FileNotFoundError(
            f"Falta la plantilla privada {PLANTILLA}. Copie una propuesta de Census (.pptx) con la "
            "estructura estándar en esa ruta.")
    prs = Presentation(str(PLANTILLA))
    s = prs.slides

    _escribir(_forma(s[S_PORTADA], F["portada"]), [arm.portada], 20 if len(arm.portada) < 60 else 14)

    dest = _forma(s[S_INTRO], F["destinatario"]).text_frame.paragraphs
    for par, texto in zip(dest, arm.destinatario):
        if par.runs:
            par.runs[0].text = texto
            for extra in par.runs[1:]:
                extra.text = ""
    _escribir(_forma(s[S_INTRO], F["carta"]), arm.carta, _tamano(arm.carta, 12, ((1200, 0), (1600, -1), (99999, -2))))

    # Antecedentes y secciones extra (copias de la diapositiva de antecedentes)
    _escribir(_forma(s[S_ANTEC], F["antec_cuerpo"]), _con_espacios(arm.antecedentes), _tamano(arm.antecedentes, 14))
    extra = 0
    for titulo, parrafos in arm.secciones:
        d = _duplicar(prs, S_ANTEC, S_ANTEC + extra)
        extra += 1
        _escribir(_forma(d, F["antec_titulo"]), [titulo], 30 if len(titulo) < 22 else 22)
        _escribir(_forma(d, F["antec_cuerpo"]), _con_espacios(parrafos), _tamano(parrafos, 14))

    s_obj, s_alc, s_hon = S_OBJ + extra, S_ALC + extra, S_HON + extra
    _escribir(_forma(s[s_obj], F["objetivo"]), [arm.objetivo], 18 if len(arm.objetivo) < 260 else 15)

    # Alcance: todas las líneas, repartidas en una o varias diapositivas
    lineas = []
    for titulo, items in arm.alcance:
        lineas += ([f"**{titulo}**"] if titulo else []) + [f"- {x}" for x in items]
    bloques = _partir(lineas, max_chars=1150, max_items=12)
    for i in range(1, len(bloques)):
        _duplicar(prs, s_alc, s_alc + i - 1)
    for i, bloque in enumerate(bloques):
        if bloque and bloque[-1].startswith("**"):            # no dejar un subtítulo huérfano
            bloques[i + 1].insert(0, bloque.pop())
        d = s[s_alc + i]
        for sh in list(d.shapes):
            if sh.name in VINETAS_ALC:
                sh._element.getparent().remove(sh._element)
        _escribir(_forma(d, F["alc_cuerpo"]), _con_espacios(bloque), _tamano(bloque, 14))
        if i:
            _escribir(_forma(d, F["alc_titulo"]), ["Alcance del Servicio (cont.)"], 30)
    s_hon += max(len(bloques), 1) - 1

    # Honorarios
    d = s[s_hon]
    _escribir(_forma(d, F["hon_intro"]), [arm.honorarios_intro], 11 if len(arm.honorarios_intro) < 450 else 10)
    tabla = next(sh for sh in d.shapes if sh.has_table).table
    fila_modelo = tabla._tbl.tr_lst[1]
    for tr in tabla._tbl.tr_lst[1:]:
        tabla._tbl.remove(tr)
    largo = sum(len(h["honorario"]) + len(h["forma_pago"]) for h in arm.honorarios)
    tam = 11 if largo < 500 else 10 if largo < 900 else 9
    anchos_pt = [c.width / 12700 for c in tabla.columns]
    alto_total = tabla.rows[0].height
    for h in arm.honorarios:
        tr = copy.deepcopy(fila_modelo)
        tabla._tbl.append(tr)
        fila = tabla.rows[len(tabla.rows) - 1]
        textos = (h["servicio"], h["honorario"], h["forma_pago"])
        for celda, texto in zip(fila.cells, textos):
            _escribir(celda, [texto], tam)
        lineas_fila = max(-(-len(x) // max(int(w / (tam * 0.5)) - 2, 10)) for x, w in zip(textos, anchos_pt))
        fila.height = int((lineas_fila * tam * 1.25 + 14) * 12700)
        alto_total += fila.height
    marco = next(sh for sh in d.shapes if sh.has_table)
    if marco.top + alto_total > 4300000:                      # tabla grande: subirla
        marco.top = 1750000
    notas = _forma(d, F["hon_notas"])
    notas.top = max(marco.top + alto_total + 150000, notas.top if marco.top + alto_total < notas.top else 0)
    _escribir(_forma(d, F["hon_notas"]), [f"*{n}" if i < len(arm.notas) - 1 else n for i, n in enumerate(arm.notas)],
              10 if sum(len(n) for n in arm.notas) < 600 else 9)

    salida.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(salida))
    return salida


def _con_espacios(parrafos: list[str]) -> list[str]:
    salida = []
    for i, p in enumerate(parrafos):
        salida.append(p)
        siguiente = parrafos[i + 1] if i + 1 < len(parrafos) else None
        if siguiente is not None:
            salida.append("")
    return salida


def generar_propuesta(servicio_id: str, cliente: dict, variables: dict | None = None,
                      fecha: date | None = None, carpeta_salida: str | Path | None = None) -> PropuestaArmada:
    arm = armar_propuesta(servicio_id, cliente, variables, fecha)
    nombre = re.sub(r"[^\w\s.-]", "", cliente.get("razon_social", "CLIENTE")).strip()
    carpeta = Path(carpeta_salida) if carpeta_salida else kb.RAIZ / "salidas"
    titulo = kb.servicio(servicio_id)["nombre"][:60].replace("/", "-")
    arm.archivo = escribir_pptx(arm, carpeta / f"Propuesta {titulo} - {nombre}.pptx")
    return arm

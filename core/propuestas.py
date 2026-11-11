"""Generación de propuestas de servicios (PPTX) con la PLANTILLA DE PROPUESTAS 2026 de Census.

Plantilla: plantillas/census/propuesta_base.pptx (o privado/plantillas/ si existe una versión local).
Las láminas fijas (socios, gerentes, jefes y coordinadores, clientes, certificaciones, cierre) no se
tocan. En las variables solo se reemplazan los marcadores <<...>> que dejó el área comercial,
conservando el texto, la fuente, el tamaño y el color de la plantilla:

  1 Portada ........ <<Nombre de servicio>>
  2 Introducción ... <<Señor, Señores, Señora>>, <<razón social>>, <<Ciudad>>, <<nombre del servicio, periodo>>
  4 Antecedentes ... <<Antecedentes>>           (Arial 15, justificado)
  5 Objetivo ....... <<Objetivo del servicio>>  (Arial 12, blanco)
  6 Alcance ........ <<Alcance de servicio>>    (Arial 14, viñetas cuadradas doradas)
  7 Honorarios ..... tabla <<nombre del servicio>> | <<Honorario>> | <<Forma de pago>> (Arial 14)

Si el contenido no cabe, se agregan láminas de continuación (copias de la misma lámina) en lugar
de achicar la letra.
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

PLANTILLA = kb.plantilla("propuesta_base.pptx")
CARPETA = kb.CARPETA / "propuestas"

S_PORTADA, S_INTRO, S_SOCIOS, S_ANTEC, S_OBJ, S_ALC, S_HON = 0, 1, 2, 3, 4, 5, 6
F = {
    "portada": "Google Shape;91;p1",
    "destinatario": "Google Shape;102;p2",
    "carta": "Google Shape;103;p2",
    "antec_titulo": "Google Shape;158;p3",
    "antec_cuerpo": "CuadroTexto 2",
    "objetivo": "Google Shape;149;p5",
    "alc_titulo": "Google Shape;158;p6",
    "alc_cuerpo": "Google Shape;159;p6",
    "hon_notas": "Google Shape;183;p7",
}
VINETAS_ALC = {f"Google Shape;{n};p6" for n in (160, 162, 164, 166, 167, 168)}
ORO = "BDA02D"                                   # color de las viñetas cuadradas de la plantilla
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
EMU_PT = 12700


# ----------------------------------------------------------------- contenido
@dataclass
class PropuestaArmada:
    servicio_id: str
    portada: str
    tratamiento: str
    destinatario: str
    ciudad: str
    referencia: str
    antecedentes: list[str]
    secciones: list[tuple[str, list[str]]]
    objetivo: str
    alcance: list[tuple[str, list[str]]]
    honorarios: list[dict]
    notas: list[str]
    por_confirmar: list[tuple[str, str]] = field(default_factory=list)   # (clave, texto) de notas opcionales
    archivo: Path | None = None
    pendientes: list[str] = field(default_factory=list)

    def texto(self) -> str:
        l = [self.portada, self.tratamiento, self.destinatario, self.ciudad, self.referencia, "ANTECEDENTES",
             *self.antecedentes]
        for t, ps in self.secciones:
            l += [t.upper(), *ps]
        l += ["OBJETIVO", self.objetivo, "ALCANCE"]
        for t, items in self.alcance:
            l += ([t] if t else []) + [f"- {x}" for x in items]
        l += ["HONORARIOS"] + [f"{h['servicio']} | {h['honorario']} | {h['forma_pago']}" for h in self.honorarios]
        return "\n".join(l + self.notas)


def plantilla_servicio(servicio_id: str) -> dict:
    archivo = kb.servicio(servicio_id).get("propuesta")
    if not archivo:
        raise ValueError(f"El servicio '{servicio_id}' aún no tiene textos de propuesta (campo 'propuesta').")
    return yaml.safe_load((CARPETA / archivo).read_text(encoding="utf-8"))


def notas_opcionales(servicio_id: str) -> list[dict]:
    """Notas que solo se incluyen si el usuario lo confirma (p. ej. exclusión de gastos notariales)."""
    notas = (plantilla_servicio(servicio_id).get("honorarios") or {}).get("notas") or []
    return [n for n in notas if isinstance(n, dict) and n.get("confirmar")]


def _lista(x) -> list[str]:
    if x is None:
        return []
    return [str(i) for i in x] if isinstance(x, (list, tuple)) else [str(x)]


def _unir(partes: list[str]) -> str:
    partes = [p for p in partes if p]
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def armar_propuesta(servicio_id: str, cliente: dict, variables: dict | None = None,
                    fecha: date | None = None, adicionales: list[str] | None = None) -> PropuestaArmada:
    """Arma el contenido. Variables generales que el agente puede pasar para adaptar la propuesta al
    contexto que da el usuario (sin tocar la plantilla del servicio):
      antecedentes (lista: reemplaza), antecedentes_extra (lista: agrega), objetivo (texto),
      alcance (lista: reemplaza), alcance_extra (lista: agrega), referencia (texto de la carta),
      tratamiento (Señor/Señora/Señores), confirmadas (claves de notas opcionales a incluir)."""
    env = _entorno()
    v0 = dict(variables or {})
    confirmadas = set(_lista(v0.get("confirmadas")))
    cliente = {"ciudad": "Guayaquil", **{k: x for k, x in cliente.items() if x not in (None, "")}}

    def contexto(sid):
        srv = kb.servicio(sid)
        t = kb.tarifario().get(srv.get("propuesta_tarifa") or srv.get("tarifa", sid), {})
        v = dict(srv.get("propuesta_vars") or {})
        if t.get("valor") is not None:
            v["porcentaje" if t.get("modelo") in {"porcentaje", "etapas"} else "honorario"] = t["valor"]
        v.update({k: x for k, x in v0.items() if x not in (None, "")})
        v.setdefault("institucional", not v.get("cartera"))
        return srv, v, {"cliente": cliente, "v": v, "t": t, "fecha": fecha or date.today(),
                        "tarifa": lambda k: kb.tarifario().get(k, {})}

    def render(ctx, texto) -> str:
        if texto is None:
            return ""
        return re.sub(r"[ \t]+", " ", env.from_string(str(texto)).render(**ctx)).strip()

    def activo(bloque, v) -> bool:
        if not isinstance(bloque, dict):
            return True
        if bloque.get("si") and not v.get(bloque["si"]):
            return False
        if bloque.get("no_si") and v.get(bloque["no_si"]):
            return False
        return True

    def notas_de(p, ctx, v, por_confirmar):
        salida = []
        for n in (p.get("honorarios") or {}).get("notas") or []:
            if isinstance(n, dict):
                if not activo(n, v):
                    continue
                texto = render(ctx, n.get("texto"))
                if n.get("confirmar") and n["confirmar"] not in confirmadas:
                    if texto:
                        por_confirmar.append((n["confirmar"], texto))
                    continue
            else:
                texto = render(ctx, n)
            if texto:
                salida.append(texto)
        return salida

    p = plantilla_servicio(servicio_id)
    srv, v, ctx = contexto(servicio_id)
    r = lambda x: render(ctx, x)

    antecedentes = ([x for a in v0["antecedentes"] for x in str(a).split("\n") if x.strip()]
                    if v0.get("antecedentes") else
                    [x for x in (r(a) for a in p.get("antecedentes", [])) for x in x.split("\n") if x.strip()])
    antecedentes += _lista(v0.get("antecedentes_extra"))

    items_base = _lista(v0["alcance"]) if v0.get("alcance") else None
    alcance = ([("", items_base)] if items_base else
               [(r(b.get("titulo")), [r(i) for i in b["items"]]) for b in p.get("alcance", []) if activo(b, v)])
    if v0.get("alcance_extra"):
        alcance[-1] = (alcance[-1][0], alcance[-1][1] + _lista(v0["alcance_extra"]))

    por_confirmar: list[tuple[str, str]] = []
    honorarios = [{k: r(f.get(k)) for k in ("servicio", "honorario", "forma_pago")}
                  for f in (p.get("honorarios") or {}).get("filas", []) if activo(f, v)]
    notas = notas_de(p, ctx, v, por_confirmar)
    referencias = [r(p.get("referencia") or p.get("asunto"))]

    # Servicios adicionales ofrecidos en la misma propuesta
    adicionales = [a for a in (adicionales or []) if a != servicio_id]
    if adicionales and alcance and not alcance[0][0]:
        alcance[0] = (srv.get("nombre_corto") or srv["nombre"], alcance[0][1])
    for sid in adicionales:
        pa = plantilla_servicio(sid)
        srv_a, va, ctx_a = contexto(sid)
        ra = lambda x, c=ctx_a: render(c, x)
        nombre = srv_a.get("nombre_corto") or srv_a["nombre"]
        for b in pa.get("alcance", []):
            if activo(b, va):
                alcance.append((ra(b.get("titulo")) or nombre, [ra(i) for i in b["items"]]))
        honorarios += [{k: ra(f.get(k)) for k in ("servicio", "honorario", "forma_pago")}
                       for f in (pa.get("honorarios") or {}).get("filas", []) if activo(f, va)]
        for n in notas_de(pa, ctx_a, va, por_confirmar):
            if n not in notas:
                notas.append(n)
        referencias.append(ra(pa.get("referencia") or pa.get("asunto")))

    vistos = set()
    por_confirmar = [(c, t) for c, t in por_confirmar if not (t in vistos or vistos.add(t))]
    arm = PropuestaArmada(
        servicio_id=servicio_id,
        portada=r(p["portada"]).upper(),
        tratamiento=str(v0.get("tratamiento") or "Señores"),
        destinatario=cliente.get("razon_social", "[COMPLETAR: cliente]"),
        ciudad=cliente["ciudad"],
        referencia=str(v0["referencia"]) if v0.get("referencia") else _unir(referencias),
        antecedentes=antecedentes,
        secciones=[(r(s["titulo"]), [r(x) for x in s["parrafos"]]) for s in p.get("secciones", []) if activo(s, v)],
        objetivo=str(v0["objetivo"]) if v0.get("objetivo") else r(p.get("objetivo")),
        alcance=alcance,
        honorarios=honorarios,
        notas=notas,
        por_confirmar=por_confirmar,
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


def _reemplazar_marcadores(parrafo, valores: dict[str, str]) -> bool:
    """Sustituye <<...>> dentro de un párrafo conservando el formato del primer run.
    `valores` mapea un fragmento del marcador (sin <<>>, minúsculas) al texto nuevo."""
    texto = "".join(r.text for r in parrafo.runs)
    if "<<" not in texto:
        return False

    def sustituto(m):
        clave = m.group(1).strip().lower()
        for k, val in valores.items():
            if k in clave:
                return val
        return m.group(0)

    nuevo = re.sub(r"<<(.*?)>>", sustituto, texto)
    runs = parrafo.runs
    # el run con el marcador manda el formato (en la carta, el marcador va en su propio run)
    runs[0].text = nuevo
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)
    return True


def _parrafos_modelo(shape):
    tf = shape.text_frame
    modelo = next((p for p in tf.paragraphs if p.runs), tf.paragraphs[0])
    return copy.deepcopy(modelo._p), (copy.deepcopy(modelo.runs[0]._r) if modelo.runs else None)


def _escribir(shape, parrafos: list[str], p_xml=None, r_xml=None, tamano: float | None = None):
    """Reemplaza todo el texto de la forma clonando el párrafo y el run modelo (formato de la plantilla).
    `- ` al inicio = viñeta cuadrada dorada; `**x**` = negrita."""
    tf = shape.text_frame
    if p_xml is None:
        p_xml, r_xml = _parrafos_modelo(shape)
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
        for trozo in re.split(r"(\*\*[^*]+\*\*)", texto):
            if not trozo:
                continue
            run = copy.deepcopy(r_xml)
            fin = nuevo.find(f"{NS_A}endParaRPr")       # PowerPoint exige los runs ANTES de endParaRPr
            if fin is not None:
                fin.addprevious(run)
            else:
                nuevo.append(run)
            nuevo_run = tf.paragraphs[-1].runs[-1]
            negrita = trozo.startswith("**")
            nuevo_run.text = trozo[2:-2] if negrita else trozo
            if negrita:
                nuevo_run.font.bold = True
            if tamano:
                nuevo_run.font.size = Pt(tamano)


def _vinetas(shape, sangria_emu: int, separacion_pt: float):
    """Convierte los párrafos que empiezan con viñeta en viñetas cuadradas doradas (como las de la
    plantilla) con sangría francesa; los subtítulos (negrita) quedan sin viñeta."""
    from lxml import etree
    for p in shape.text_frame.paragraphs:
        if not p.runs:
            continue
        pPr = p._p.get_or_add_pPr()
        for hijo in list(pPr):
            if hijo.tag in (f"{NS_A}buNone", f"{NS_A}buChar", f"{NS_A}buClr", f"{NS_A}buSzPct",
                            f"{NS_A}buSzPts", f"{NS_A}buFont", f"{NS_A}spcAft", f"{NS_A}spcBef"):
                pPr.remove(hijo)
        es_titulo = all(r.font.bold for r in p.runs)
        pPr.set("marL", str(0 if es_titulo else sangria_emu))
        pPr.set("indent", str(0 if es_titulo else -sangria_emu))
        aft = etree.SubElement(pPr, f"{NS_A}spcAft")
        etree.SubElement(aft, f"{NS_A}spcPts").set("val", str(int(separacion_pt * 100)))
        # orden del esquema: lnSpc, spcBef, spcAft, buClr..., buFont, buChar
        lnspc = pPr.find(f"{NS_A}lnSpc")
        if lnspc is not None:
            pPr.remove(lnspc)
            pPr.insert(0, lnspc)
        if es_titulo:
            etree.SubElement(pPr, f"{NS_A}buNone")
        else:
            clr = etree.SubElement(pPr, f"{NS_A}buClr")
            etree.SubElement(clr, f"{NS_A}srgbClr").set("val", ORO)
            etree.SubElement(pPr, f"{NS_A}buSzPct").set("val", "75000")
            etree.SubElement(pPr, f"{NS_A}buFont").set("typeface", "Arial")
            etree.SubElement(pPr, f"{NS_A}buChar").set("char", "■")


def _lineas(texto: str, ancho_pt: float, tamano: float) -> int:
    por_linea = max(int(ancho_pt / (tamano * 0.5)), 10)
    return max(-(-len(texto) // por_linea), 1)


def _repartir(parrafos: list[str], ancho_pt: float, alto_pt: float, tamano: float, separacion_pt: float):
    """Agrupa párrafos en láminas según la altura disponible (estimada)."""
    grupos, actual, usado = [], [], 0.0
    for x in parrafos:
        alto = _lineas(x.replace("**", ""), ancho_pt, tamano) * tamano * 1.2 + separacion_pt
        if actual and usado + alto > alto_pt:
            grupos.append(actual)
            actual, usado = [], 0.0
        actual.append(x)
        usado += alto
    return grupos + ([actual] if actual else [])


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


def _titulo_continuacion(slide, nombre_forma: str):
    forma = _forma(slide, nombre_forma)
    par = next(p for p in forma.text_frame.paragraphs if p.runs)
    _poner_titulo(forma, "".join(r.text for r in par.runs).rstrip() + " (cont.)")


def _poner_titulo(forma, texto: str):
    """Cambia el título conservando su formato; si no cabe en una línea, ensancha el cuadro (centrado)
    y, como último recurso, baja la letra."""
    par = next(p for p in forma.text_frame.paragraphs if p.runs)
    par.runs[0].text = texto
    for extra in par.runs[1:]:
        extra._r.getparent().remove(extra._r)
    tam = (par.runs[0].font.size or Pt(36)).pt
    necesario = len(texto) * tam * 0.52 * EMU_PT + 2 * 91425
    if necesario > forma.width:
        centro = forma.left + forma.width // 2
        ancho = int(min(necesario, 2 * centro - 2 * 150000))
        forma.left, forma.width = centro - ancho // 2, ancho
        if necesario > ancho:
            par.runs[0].font.size = Pt(int(tam * ancho / necesario))


PIE = 6302352                      # borde superior de la franja inferior de la plantilla (EMU)


def escribir_pptx(arm: PropuestaArmada, salida: Path) -> Path:
    if not PLANTILLA.exists():
        raise FileNotFoundError(f"Falta la plantilla {PLANTILLA} (PLANTILLA DE PROPUESTAS 2026).")
    prs = Presentation(str(PLANTILLA))
    s = prs.slides

    # 1. Portada
    portada = _forma(s[S_PORTADA], F["portada"])
    for par in portada.text_frame.paragraphs:
        _reemplazar_marcadores(par, {"servicio": arm.portada})
    if len(arm.portada) > 110:                           # no cabe en tres líneas a 20 pt
        for run in portada.text_frame.paragraphs[0].runs:
            run.font.size = Pt(16)

    # 2. Introducción (solo se reemplazan los marcadores)
    for par in _forma(s[S_INTRO], F["destinatario"]).text_frame.paragraphs:
        _reemplazar_marcadores(par, {"señor": arm.tratamiento, "razon social": arm.destinatario,
                                     "razón social": arm.destinatario, "ciudad": arm.ciudad})
    for par in _forma(s[S_INTRO], F["carta"]).text_frame.paragraphs:
        _reemplazar_marcadores(par, {"servicio": arm.referencia.rstrip(".") + "."})

    # 4. Antecedentes (+ secciones extra y continuaciones), Arial 15 de la plantilla
    cuerpo = _forma(s[S_ANTEC], F["antec_cuerpo"])
    foto = max((sh for sh in s[S_ANTEC].shapes if sh.shape_type == 13 and sh.left > cuerpo.left),
               key=lambda sh: sh.width * sh.height, default=None)
    if foto is not None and cuerpo.left + cuerpo.width > foto.left - 150000:
        cuerpo.width = foto.left - 150000 - cuerpo.left       # el cuadro de la plantilla invade la foto
    modelo = _parrafos_modelo(cuerpo)
    ancho = cuerpo.width / EMU_PT - 14
    alto = (PIE - cuerpo.top) / EMU_PT - 30
    paginas = [("", g) for g in _repartir(arm.antecedentes, ancho, alto, 15, 14)] or [("", [])]
    for titulo, parrafos in arm.secciones:
        paginas += [(titulo, g) for g in _repartir(parrafos, ancho, alto, 15, 14)]
    for i in range(1, len(paginas)):
        _duplicar(prs, S_ANTEC, S_ANTEC + i - 1)
    for i, (titulo, parrafos) in enumerate(paginas):
        d = s[S_ANTEC + i]
        _escribir(_forma(d, F["antec_cuerpo"]), parrafos, *modelo)
        if titulo:
            _poner_titulo(_forma(d, F["antec_titulo"]), titulo if paginas[i - 1][0] != titulo else titulo + " (cont.)")
        elif i:
            _titulo_continuacion(d, F["antec_titulo"])
    extra = len(paginas) - 1

    # 5. Objetivo
    s_obj, s_alc, s_hon = S_OBJ + extra, S_ALC + extra, S_HON + extra
    for par in _forma(s[s_obj], F["objetivo"]).text_frame.paragraphs:
        _reemplazar_marcadores(par, {"objetivo": arm.objetivo})

    # 6. Alcance: Arial 14, viñetas cuadradas doradas como en la plantilla
    lineas = []
    for titulo, items in arm.alcance:
        lineas += ([f"**{titulo}**"] if titulo else []) + items
    cuerpo = _forma(s[s_alc], F["alc_cuerpo"])
    vineta_x = min(sh.left for sh in s[s_alc].shapes if sh.name in VINETAS_ALC)
    texto_x = cuerpo.left
    derecha = cuerpo.left + cuerpo.width
    ancho = (derecha - texto_x) / EMU_PT - 14
    alto = (PIE - cuerpo.top) / EMU_PT - 30
    bloques = _repartir(lineas, ancho, alto, 14, 10)
    for i in range(len(bloques) - 1):
        if bloques[i] and bloques[i][-1].startswith("**"):      # no dejar un subtítulo huérfano
            bloques[i + 1].insert(0, bloques[i].pop())
    for i in range(1, len(bloques)):
        _duplicar(prs, s_alc, s_alc + i - 1)
    for i, bloque in enumerate(bloques):
        d = s[s_alc + i]
        for sh in list(d.shapes):
            if sh.name in VINETAS_ALC:
                sh._element.getparent().remove(sh._element)
        forma = _forma(d, F["alc_cuerpo"])
        p_xml, r_xml = _parrafos_modelo(forma)
        _escribir(forma, bloque, p_xml, r_xml)
        forma.left = vineta_x - 91425                     # la viñeta queda donde estaba el cuadrado
        forma.width = derecha - forma.left
        _vinetas(forma, texto_x - vineta_x + 91425, 10)   # el texto queda donde estaba
        if i:
            _titulo_continuacion(d, F["alc_titulo"])
    s_hon += max(len(bloques), 1) - 1

    # 7. Honorarios: filas de la tabla con el formato de la fila modelo (Arial 14)
    d = s[s_hon]
    marco = next(sh for sh in d.shapes if sh.has_table)
    tabla = marco.table
    fila_modelo = tabla._tbl.tr_lst[1]
    for tr in tabla._tbl.tr_lst[1:]:
        tabla._tbl.remove(tr)
    anchos_pt = [c.width / EMU_PT for c in tabla.columns]

    def alto_filas(tam):
        total = 0
        for h in arm.honorarios:
            textos = (h["servicio"], h["honorario"], h["forma_pago"])
            n = max(_lineas(x, w - 14, tam) for x, w in zip(textos, anchos_pt))
            total += max(n * tam * 1.2 + 14, 98.2)          # 98,2 pt = alto de la fila de la plantilla
        return total

    tam = 14
    espacio = (PIE - 1750000) / EMU_PT - 21.8 - 60
    while tam > 10 and alto_filas(tam) > espacio:
        tam -= 1
    alto_total = tabla.rows[0].height
    for h in arm.honorarios:
        tr = copy.deepcopy(fila_modelo)
        tabla._tbl.append(tr)
        fila = tabla.rows[len(tabla.rows) - 1]
        textos = (h["servicio"], h["honorario"], h["forma_pago"])
        for celda, texto in zip(fila.cells, textos):
            _escribir(celda, [texto], tamano=None if tam == 14 else tam)
        n = max(_lineas(x, w - 14, tam) for x, w in zip(textos, anchos_pt))
        fila.height = int(max(n * tam * 1.2 + 14, 98.2) * EMU_PT)
        alto_total += fila.height
    if marco.top + alto_total > 4300000:                      # tabla grande: subirla
        marco.top = 1750000
    notas = _forma(d, F["hon_notas"])
    if arm.notas:
        txb = notas.text_frame._txBody
        pars = notas.text_frame.paragraphs
        cierre = next(p for p in pars if p.runs)              # "Creemos que el alcance..." (Arial 14)
        for p in pars:
            if p is not cierre and not p.runs and txb.index(p._p) < txb.index(cierre._p):
                txb.remove(p._p)
        p_nota = copy.deepcopy(cierre._p)
        r_nota = copy.deepcopy(cierre.runs[0]._r)
        largo = sum(len(n) for n in arm.notas)
        tam_notas = 12 if largo < 500 else 11 if largo < 800 else 10
        temporal = copy.deepcopy(notas._element)                # escribir las notas en una copia y moverlas
        from pptx.shapes.autoshape import Shape
        aux = Shape(temporal, notas._parent)
        _escribir(aux, [f"* {n}" for n in arm.notas] + [""], p_nota, r_nota, tamano=tam_notas)
        for i, par in enumerate(aux.text_frame._txBody.findall(f"{NS_A}p")):
            cierre._p.addprevious(par)
    notas.top = int(max(marco.top + alto_total + 120000, notas.top))

    salida.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(salida))
    return salida


def generar_propuesta(servicio_id: str, cliente: dict, variables: dict | None = None,
                      fecha: date | None = None, carpeta_salida: str | Path | None = None,
                      adicionales: list[str] | None = None) -> PropuestaArmada:
    arm = armar_propuesta(servicio_id, cliente, variables, fecha, adicionales)
    nombre = re.sub(r"[^\w\s.-]", "", cliente.get("razon_social", "CLIENTE")).strip()
    carpeta = Path(carpeta_salida) if carpeta_salida else kb.RAIZ / "salidas"
    srv = kb.servicio(servicio_id)
    titulo = (srv.get("nombre_corto") or srv["nombre"])[:60].replace("/", "-")
    arm.archivo = escribir_pptx(arm, carpeta / f"Propuesta {titulo} - {nombre}.pptx")
    return arm

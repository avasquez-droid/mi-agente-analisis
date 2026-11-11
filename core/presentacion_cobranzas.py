"""Presentación institucional de Census Cobranzas (PDF) personalizada para un cliente.

Plantilla: privado/plantillas/presentacion_cobranzas.pdf — la presentación corporativa de Census
Cobranzas (27 láminas: historia, logros, clientes, certificaciones, metodología, distribución de
cartera, transparencia, servicios adicionales, socios). No va al repositorio público.

Solo se reemplazan los textos que mencionan al cliente o al tipo de entidad; el resto de la
presentación queda idéntico. Las coordenadas corresponden a la plantilla actual: si se cambia la
plantilla, revisar `REEMPLAZOS`.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import conocimiento as kb

PLANTILLA = kb.RAIZ / "privado" / "plantillas" / "presentacion_cobranzas.pdf"
FUENTE = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"   # respaldo con métrica de Arial

ENTIDAD = {
    "financiera": {"singular": "la entidad", "deudores": "sus clientes"},
    "cooperativa": {"singular": "la cooperativa", "deudores": "sus socios"},
    "empresa": {"singular": "la empresa", "deudores": "sus clientes"},
}


def _reemplazos(cliente: str, tipo: str) -> list[dict]:
    e = ENTIDAD[tipo]
    return [
        {   # Antecedentes y objetivos — párrafo inicial con el nombre del cliente
            "pagina": 9, "borrar": (44, 126, 730, 167), "caja": (44, 127, 735, 175), "tamano": 16,
            "fondo": (240 / 255, 240 / 255, 240 / 255),      # la lámina tiene fondo gris claro
            "texto": (f"Somos una empresa especializada en cobranza extrajudicial, por lo que podemos coadyuvar a "
                      f"{cliente} en la recuperación extrajudicial de la cartera vencida de {e['deudores']}."),
        },
        {   # Infraestructura tecnológica
            "pagina": 15, "borrar": (90, 190, 704, 209), "origen": (90.36, 205.22), "tamano": 16,
            "justificar_hasta": 702.3,                       # línea intermedia de un párrafo justificado
            "texto": f"de {e['singular']}, a través de medios seguros como Drive, SFTP o cualquier canal",
        },
        {   # Transparencia, auditoría y control
            "pagina": 19, "borrar": (85, 258, 640, 277), "origen": (85.56, 272.93), "tamano": 16,
            "texto": f"Envío diario de reportes de seguimiento según el formato de {e['singular']}.",
        },
    ]


def _fuente_arial(doc, textos: list[str]):
    """Devuelve (buffer, Font) de la Arial embebida en la propia plantilla si tiene todos los
    caracteres que se van a escribir; si no, la Liberation Sans (mismas métricas que Arial)."""
    import pymupdf
    necesarios = {c for t in textos for c in t if not c.isspace()}
    vistos = set()
    for pagina in doc:
        for xref, _, _, nombre, *_ in pagina.get_fonts():
            if xref in vistos or not nombre.endswith("+ArialMT"):
                continue
            vistos.add(xref)
            buf = doc.extract_font(xref)[3]
            if buf:
                f = pymupdf.Font(fontbuffer=buf)
                if all(f.has_glyph(ord(c)) for c in necesarios):
                    return buf, f
    return None, pymupdf.Font(fontfile=FUENTE)


def _linea_justificada(pagina, origen, x_final, texto, tamano, fuente):
    """Escribe una línea repartiendo el espacio entre palabras para que llegue al margen derecho,
    como el resto del párrafo justificado de la plantilla."""
    palabras = texto.split()
    anchos = [fuente.text_length(p, fontsize=tamano) for p in palabras]
    hueco = (x_final - origen[0] - sum(anchos)) / max(len(palabras) - 1, 1)
    x = origen[0]
    for palabra, ancho in zip(palabras, anchos):
        pagina.insert_text((x, origen[1]), palabra, fontname="arialcensus", fontsize=tamano, color=(0, 0, 0))
        x += ancho + hueco


def generar_presentacion(cliente: str, tipo_entidad: str = "empresa",
                         carpeta_salida: str | Path | None = None) -> Path:
    import pymupdf

    if tipo_entidad not in ENTIDAD:
        raise ValueError(f"tipo_entidad debe ser uno de {list(ENTIDAD)}")
    if not PLANTILLA.exists():
        raise FileNotFoundError(f"Falta la plantilla privada {PLANTILLA} (presentación de Census Cobranzas en PDF).")
    doc = pymupdf.open(str(PLANTILLA))
    reemplazos = _reemplazos(cliente, tipo_entidad)
    buf, fuente = _fuente_arial(doc, [r["texto"] for r in reemplazos])
    for r in reemplazos:
        pagina = doc[r["pagina"] - 1]
        fondo = r.get("fondo", (1, 1, 1))
        pagina.add_redact_annot(pymupdf.Rect(*r["borrar"]), fill=fondo)
        pagina.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        if buf:
            pagina.insert_font(fontname="arialcensus", fontbuffer=buf)
        else:
            pagina.insert_font(fontname="arialcensus", fontfile=FUENTE)
        if "origen" in r and r.get("justificar_hasta"):
            _linea_justificada(pagina, r["origen"], r["justificar_hasta"], r["texto"], r["tamano"], fuente)
        elif "origen" in r:
            pagina.insert_text(r["origen"], r["texto"], fontname="arialcensus", fontsize=r["tamano"], color=(0, 0, 0))
        else:
            sobrante = pagina.insert_textbox(pymupdf.Rect(*r["caja"]), r["texto"], fontname="arialcensus",
                                             fontsize=r["tamano"], color=(0, 0, 0), lineheight=1.15)
            if sobrante < 0:      # nombre muy largo: reducir un punto
                pagina.add_redact_annot(pymupdf.Rect(*r["caja"]), fill=fondo)
                pagina.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                        graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
                pagina.insert_textbox(pymupdf.Rect(*r["caja"]), r["texto"], fontname="arialcensus",
                                      fontsize=r["tamano"] - 2, color=(0, 0, 0), lineheight=1.15)
    doc.set_metadata({"title": f"Census Cobranzas — {cliente}", "author": "Census Cobranzas S.A."})
    carpeta = Path(carpeta_salida) if carpeta_salida else kb.RAIZ / "salidas"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = re.sub(r"[^\w\s.-]", "", cliente).strip()
    salida = carpeta / f"Presentación cobranza - {nombre}.pdf"
    doc.save(str(salida), garbage=3, deflate=True)
    return salida

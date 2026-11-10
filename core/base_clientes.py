"""Lectura de la BASE GENERAL COMERCIAL CENSUS (Excel).

Hojas que se usan:
  - Clientes : una fila por cliente, con datos de Superintendencia/SRI y estado en Census.
  - servicios: historial de servicios por cliente (Activo / Inactivo / En gestión comercial).

Las columnas se reconocen por su encabezado (sin importar mayúsculas, acentos ni saltos de
línea), así que la base puede reordenarse sin romper la lectura. Los campos se entregan con los
mismos nombres que usa conocimiento/metricas.yaml, para evaluar oportunidades con las mismas
reglas que el informe de investigación.

La base contiene datos de clientes: vive en privado/base/ y nunca se sube al repositorio.
"""
from __future__ import annotations

import re
import unicodedata
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from . import conocimiento as kb

CARPETA_BASE = kb.RAIZ / "privado" / "base"


def _n(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


# encabezado normalizado (prefijo) -> campo
COLUMNAS = [
    ("cliente", "nombre"),
    ("ruc", "ruc"),
    ("estado ruc", "estado_ruc"),
    ("grupo", "grupo"),
    ("nombres y apellidos accionistas", "accionistas_nombres"),
    ("cargo accionistas", "accionistas_cargos"),
    ("nombres y apellidos", "administradores_nombres"),
    ("cargo administradores", "administradores_cargos"),
    ("referidor", "referidor"),
    ("ciudad", "ciudad"),
    ("actividad economica principal", "objeto"),
    ("sector", "sector"),
    ("tipo de actividad", "tipo_actividad"),
    ("credito tributario iva", "ct_iva_ref"),
    ("credito tributario ir", "ct_ir_ref"),
    ("imp causado", "ir_causado"),
    ("proyeccion ir", "proyeccion_devolucion_ir"),
    ("isd 2025", "isd_ref"),
    ("isd 2026", "isd_actual"),
    ("deudores comerciales", "cxc_no_relacionadas"),
    ("gasto deterioro", "gasto_deterioro"),
    ("sueldos y beneficios sociales", "sueldos"),
    ("sueldos salarios", "sueldos_salarios"),
    ("estimacion de sueldos", "sueldos_estimados"),
    ("n trabajadores", "trabajadores"),
    ("estado census", "estado_census"),
    ("oportunidades", "oportunidades_base"),
    ("observacion comercial", "observacion_comercial"),
    ("fecha observacion", "fecha_observacion"),
]
NUMERICOS = {"ct_iva_ref", "ct_ir_ref", "ir_causado", "proyeccion_devolucion_ir", "isd_ref", "isd_actual",
             "cxc_no_relacionadas", "gasto_deterioro", "sueldos", "sueldos_salarios",
             "sueldos_estimados", "trabajadores"}
SOCIEDAD = re.compile(r"\b(S\.?\s?A\.?\s?S?\.?|C(I|Í)A\.?|LTDA|HOLDING|CORP|INC|LLC|LP|LTD|S\.?\s?L\.?|"
                      r"FIDEICOMISO|SOCIEDAD|COMPA(Ñ|N)IA|GROUP|TRUST|FUND|FOUNDATION|FUNDACION|"
                      r"COOPERATIVA|ASOCIACION|BANCO|CAPITAL|INVESTMENTS?|INVERSIONES|GMBH|BV|N\.V)\b", re.I)


def _mapear(encabezados) -> dict[int, str]:
    mapa, usados = {}, set()
    normal = [_n(h) for h in encabezados]
    for prefijo, campo in COLUMNAS:
        for i, h in enumerate(normal):
            if i not in usados and h.startswith(prefijo):
                mapa[i] = campo
                usados.add(i)
                break
    return mapa


def _num(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _lineas(v) -> list[str]:
    if v in (None, "", "-"):
        return []
    return [x.strip() for x in str(v).split("\n") if x.strip() and x.strip() != "-"]


FIN_SOCIEDAD = re.compile(r"(\bC\.?\s?A\.?|\bS\.?\s?R\.?\s?L\.?|\bS\.?\s?C\.?)\s*$", re.I)


def es_persona_natural(nombre: str) -> bool:
    """Heurística por nombre: descarta sociedades (sufijos S.A., CIA., LTDA, C.A., S.R.L., HOLDING...)
    y filas que no son nombres (p. ej. "1 COPROPIETARIO")."""
    nombre = (nombre or "").strip()
    if not nombre or nombre[0].isdigit():
        return False
    return not (SOCIEDAD.search(nombre) or FIN_SOCIEDAD.search(nombre))


def _fecha(v) -> str:
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return str(v or "")


@dataclass
class BaseComercial:
    archivo: str
    clientes: list[dict] = field(default_factory=list)
    observaciones: list[str] = field(default_factory=list)

    def buscar(self, texto: str) -> list[dict]:
        t = _n(texto)
        exacto = [c for c in self.clientes if c["ruc"] == texto.strip()]
        return exacto or [c for c in self.clientes if t and t in _n(c["nombre"])]

    def por_ruc(self, ruc: str) -> dict | None:
        return next((c for c in self.clientes if c["ruc"] == str(ruc).strip()), None)

    def resumen(self) -> dict:
        from collections import Counter
        return {
            "clientes": len(self.clientes),
            "estado_census": Counter(c["estado_census"] or "(vacío)" for c in self.clientes).most_common(),
            "estado_ruc": Counter(c["estado_ruc"] or "(vacío)" for c in self.clientes).most_common(),
            "servicios": Counter(s["servicio"] for c in self.clientes for s in c["servicios"]).most_common(),
            "sectores": Counter(c["sector"] for c in self.clientes if c["sector"]).most_common(10),
        }


def archivo_por_defecto() -> Path:
    candidatos = sorted(CARPETA_BASE.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise FileNotFoundError(f"No hay base comercial en {CARPETA_BASE} (copie ahí el Excel).")
    return candidatos[0]


def cargar_base(ruta: str | Path | None = None) -> BaseComercial:
    ruta = Path(ruta) if ruta else archivo_por_defecto()
    with warnings.catch_warnings():                       # validaciones de datos del Excel: irrelevantes
        warnings.simplefilter("ignore")
        wb = load_workbook(ruta, read_only=True, data_only=True)
    base = BaseComercial(archivo=ruta.name)

    # Historial de servicios
    historial: dict[str, list[dict]] = {}
    if "servicios" in wb.sheetnames:
        filas = wb["servicios"].iter_rows(values_only=True)
        cab = [_n(h) for h in next(filas)]
        idx = {k: cab.index(k) for k in ("ruc", "servicio", "estado", "ultima fecha", "detalle") if k in cab}
        for f in filas:
            if not f or not f[idx["ruc"]]:
                continue
            historial.setdefault(str(f[idx["ruc"]]).strip(), []).append({
                "servicio": str(f[idx["servicio"]] or "").strip(),
                "estado": str(f[idx["estado"]] or "").strip(),
                "fecha": _fecha(f[idx["ultima fecha"]]) if "ultima fecha" in idx else "",
                "detalle": str(f[idx["detalle"]] or "") if "detalle" in idx else "",
            })

    filas = wb["Clientes"].iter_rows(values_only=True)
    mapa = _mapear(next(filas))
    faltan = {c for _, c in COLUMNAS} - set(mapa.values())
    if faltan:
        base.observaciones.append("Columnas no encontradas en la hoja Clientes: " + ", ".join(sorted(faltan)))
    sin_ruc = 0
    for f in filas:
        if not f or not any(f):
            continue
        c = {campo: f[i] if i < len(f) else None for i, campo in mapa.items()}
        if not c.get("nombre"):
            continue
        for k in NUMERICOS:
            c[k] = _num(c.get(k))
        for k in ("nombre", "ruc", "estado_ruc", "grupo", "referidor", "ciudad", "objeto", "sector",
                  "tipo_actividad", "estado_census", "oportunidades_base", "observacion_comercial"):
            v = c.get(k)
            c[k] = "" if v in (None, "-", 0) else str(v).strip()
        c["fecha_observacion"] = _fecha(c.get("fecha_observacion"))
        c["administradores"] = list(zip(_lineas(c.pop("administradores_nombres", None)),
                                        _lineas(c.pop("administradores_cargos", None)) + [""] * 20))
        accionistas = list(zip(_lineas(c.pop("accionistas_nombres", None)),
                               _lineas(c.pop("accionistas_cargos", None)) + [""] * 50))
        c["accionistas"] = accionistas
        c["accionistas_pn"] = sum(1 for nombre, _ in accionistas if es_persona_natural(nombre))
        c["servicios"] = historial.get(c["ruc"], [])
        c["tipo"] = ""
        if not c["ruc"]:
            sin_ruc += 1
        base.clientes.append(c)
    if sin_ruc:
        base.observaciones.append(f"{sin_ruc} clientes sin RUC (no se pueden cruzar con informes ni servicios).")
    return base

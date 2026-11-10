"""Lectura del informe de investigación de prospecto (Word) generado por Census.

Estructura esperada:
  - Encabezado: "RUC MAIN: ...", "Total empresas consolidadas: N | Fecha: AAAA-MM-DD ..."
  - Cuadro resumen del grupo: tablas Tributario, Legal corporativo, Cobranzas, Aduanero.
  - Una ficha por empresa que empieza con "RUC: <ruc>" y contiene líneas "Etiqueta: valor",
    tablas (administradores, accionistas, evolución de crédito tributario, proyección IR,
    Régimen 70...) y secciones de texto (SATJE, Partidas OMC, Régimen 21, Tarifa diferenciada).

La fuente de verdad es la ficha de cada empresa; el cuadro resumen solo se usa para detectar
discrepancias.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph


# ---------------------------------------------------------------- utilidades
def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


def a_numero(texto) -> float | None:
    """Convierte "$ 1,226,322.14", "($ 158,282.67)", "$ -", "799,0000" a float."""
    if texto is None:
        return None
    t = str(texto).strip()
    if not t or t == "-":
        return None                     # sin dato
    if t in {"$ -", "$-"}:
        return 0.0                      # cero contable
    negativo = t.startswith("(") or t.startswith("-")
    t = re.sub(r"[^\d,\.]", "", t)
    if not t:
        return 0.0
    if "," in t and "." in t:          # 1,226,322.14
        t = t.replace(",", "")
    elif "," in t:                      # 1,226 (miles) o 799,0000 (decimal con coma)
        t = t.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", t) else t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if negativo else v


# Etiqueta del informe (normalizada) -> campo interno. Las que llevan año se tratan aparte.
CAMPOS = {
    "nombre comercial": "nombre_comercial",
    "nombre propietario": "propietario",
    "nombre compania": "nombre",
    "ruc": "ruc",
    "provincia": "provincia",
    "ciudad": "ciudad",
    "objeto compania": "objeto",
    "fecha de constitucion": "fecha_constitucion",
    "numero de trabajadores": "trabajadores",
    "exportaciones": "exportaciones",
    "prestacion de servicios": "prestacion_servicios",
    "venta de bienes": "venta_bienes",
    "importaciones de bienes no producidos": "importaciones_no_producidos",
    "importaciones de materia prima": "importaciones_mp",
    "propiedad, planta y equipo": "ppe",
    "sueldos y beneficios sociales": "sueldos",
    "deudores comerciales y otras cuentas por cobrar no relacionados": "cxc_no_relacionadas",
    "gasto deterioro": "gasto_deterioro",
    "grandes contribuyente": "gran_contribuyente",
}
CAMPOS_CON_ANIO = [
    (r"ingreso por ventas (\d{4})", "ventas"),
    (r"utilidad neta (\d{4})", "utilidad_neta"),
    (r"impuesto a la renta causado (\d{4})", "ir_causado"),
    (r"ingreso total (\d{4})", "ingreso_total"),
    (r"credito tributario a favor de la empresa \(i\.v\.a\) (\d{4})", "ct_iva"),
    (r"credito tributario a favor de la empresa \(i\.r\) (\d{4})", "ct_ir"),
    (r"impuesto salida de divisas (\d{4})", "isd"),
    (r"sercop (\d{4})", "sercop"),
]
TEXTO = {"nombre_comercial", "propietario", "nombre", "ruc", "provincia", "ciudad", "objeto",
         "fecha_constitucion", "gran_contribuyente"}


@dataclass
class Empresa:
    ruc: str
    datos: dict = field(default_factory=dict)          # campos simples
    por_anio: dict = field(default_factory=dict)       # {"ct_iva": {2025: x}, "isd": {...}}
    administradores: list[dict] = field(default_factory=list)
    accionistas: list[dict] = field(default_factory=list)
    juicios_actor: list[dict] = field(default_factory=list)
    juicios_demandado: list[dict] = field(default_factory=list)
    omc: list[dict] = field(default_factory=list)
    reg70: dict = field(default_factory=dict)
    reg21: dict = field(default_factory=dict)
    tarifa_diferenciada: str = ""
    deudas: dict = field(default_factory=dict)          # firmes / impugnadas / facilidades
    proyeccion_ir: dict = field(default_factory=dict)
    tipo: str = ""                                       # MAIN / RELACIONADA

    @property
    def nombre(self) -> str:
        return self.datos.get("nombre") or self.datos.get("nombre_comercial") or self.ruc


@dataclass
class InformeGrupo:
    archivo: str
    ruc_main: str = ""
    fecha: date | None = None
    empresas: list[Empresa] = field(default_factory=list)
    resumen: dict = field(default_factory=dict)          # {seccion: [ {col: valor} ]}
    discrepancias: list[str] = field(default_factory=list)

    @property
    def anio_ref(self) -> int:
        """Último ejercicio fiscal cerrado respecto de la fecha del informe."""
        return (self.fecha.year if self.fecha else date.today().year) - 1

    @property
    def main(self) -> Empresa | None:
        return next((e for e in self.empresas if e.ruc == self.ruc_main), None)


# ---------------------------------------------------------------- lectura
def _bloques(documento):
    """Itera ("p", texto) y ("t", filas) en el orden del documento."""
    for el in documento.element.body.iterchildren():
        tag = el.tag.split("}")[-1]
        if tag == "p":
            texto = Paragraph(el, documento).text.strip()
            if texto:
                yield "p", texto
        elif tag == "tbl":
            tabla = Table(el, documento)
            filas = [[c.text.strip() for c in fila.cells] for fila in tabla.rows]
            yield "t", filas


def _tabla_a_dicts(filas):
    if not filas:
        return []
    cab = filas[0]
    return [dict(zip(cab, f)) for f in filas[1:]]


SECCIONES_RESUMEN = {"tributario", "legal corporativo", "cobranzas", "aduanero"}
SECCIONES_FICHA = {
    "administradores actuales de la compania": "administradores",
    "accionistas": "accionistas",
    "cuadro de evolucion de credito tributario iva e ir": "evolucion_ct",
    "calculo de proyeccion de devolucion del ir": "proyeccion_ir",
    "partidas omc": "omc",
    "regimen 70 (deposito aduanero publico)": "reg70",
    "regimen 21": "reg21",
    "tarifa diferenciada isd": "tarifa_dif",
    "deudas firmes:": "deudas_firmes",
    "deudas impugnadas:": "deudas_impugnadas",
    "facilidades de pago:": "facilidades_pago",
}


def leer_informe(ruta: str | Path) -> InformeGrupo:
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el informe: {ruta}")
    documento = docx.Document(str(ruta))
    inf = InformeGrupo(archivo=ruta.name)

    actual: Empresa | None = None
    seccion: str | None = None
    satje: str | None = None

    for tipo, contenido in _bloques(documento):
        if tipo == "p":
            texto = contenido
            n = _norm(texto)

            if n.startswith("ruc main:"):
                inf.ruc_main = texto.split(":", 1)[1].strip()
                continue
            m = re.search(r"fecha:\s*(\d{4})-(\d{2})-(\d{2})", n)
            if m and actual is None:
                inf.fecha = date(int(m[1]), int(m[2]), int(m[3]))
                continue
            if actual is None and n in SECCIONES_RESUMEN:
                seccion = n
                continue
            m = re.match(r"^RUC:\s*(\d{10,13})$", texto)   # encabezado de ficha (mayúsculas)
            if m:
                actual = Empresa(ruc=m[1])
                inf.empresas.append(actual)
                seccion, satje = None, None
                continue
            if actual is None:
                continue

            # --- dentro de una ficha
            if n in SECCIONES_FICHA:
                seccion = SECCIONES_FICHA[n]
                continue
            if n.startswith("actor / ofendido"):
                satje, seccion = "actor", None
                continue
            if n.startswith("demandado / procesado"):
                satje, seccion = "demandado", None
                continue
            if satje and "|" in texto:
                partes = [p.strip() for p in texto.split("|")]
                causa = {"numero": partes[0], "materia": partes[1] if len(partes) > 1 else "",
                         "fecha": partes[2] if len(partes) > 2 else ""}
                (actual.juicios_actor if satje == "actor" else actual.juicios_demandado).append(causa)
                continue
            if seccion in {"deudas_firmes", "deudas_impugnadas", "facilidades_pago"}:
                actual.deudas[seccion] = not n.startswith("no ")
                seccion = None
                continue
            if seccion == "tarifa_dif":
                actual.tarifa_diferenciada = texto
                seccion = None
                continue
            if seccion in {"omc", "reg70", "reg21"} and n.startswith("sin registro"):
                seccion = None
                continue
            if n.startswith("fuente:"):
                continue

            if ":" in texto:
                etiqueta, valor = texto.split(":", 1)
                et, valor = _norm(etiqueta), valor.strip()
                if et in CAMPOS:
                    campo = CAMPOS[et]
                    actual.datos[campo] = valor if campo in TEXTO else a_numero(valor)
                    satje = None
                    continue
                for patron, campo in CAMPOS_CON_ANIO:
                    m = re.fullmatch(patron, et)
                    if m:
                        actual.por_anio.setdefault(campo, {})[int(m[1])] = a_numero(valor)
                        break
            continue

        # ---------------- tablas
        filas = contenido
        if actual is None:
            if seccion in SECCIONES_RESUMEN:
                inf.resumen[seccion] = _tabla_a_dicts(filas)
            continue
        registros = _tabla_a_dicts(filas)
        if seccion == "administradores":
            actual.administradores = registros
        elif seccion == "accionistas":
            actual.accionistas = registros
        elif seccion == "evolucion_ct":
            for r in registros:
                anio = int(a_numero(r.get("AÑO")) or 0)
                if anio:
                    actual.por_anio.setdefault("ct_iva", {}).setdefault(anio, a_numero(r.get("Crédito Tributario IVA")))
                    actual.por_anio.setdefault("ct_ir", {}).setdefault(anio, a_numero(r.get("Crédito Tributario IR")))
        elif seccion == "proyeccion_ir":
            for f in filas[1:]:
                if len(f) >= 2:
                    actual.proyeccion_ir[_norm(f[0])] = a_numero(f[1])
        elif seccion in {"reg70", "reg21"}:
            destino = actual.reg70 if seccion == "reg70" else actual.reg21
            for f in filas[1:]:
                if len(f) >= 2:
                    destino[f[0].strip()] = a_numero(f[-1])
        elif seccion == "omc":
            actual.omc = registros
        seccion = None

    _marcar_tipos(inf)
    inf.discrepancias = detectar_discrepancias(inf)
    return inf


def _marcar_tipos(inf: InformeGrupo) -> None:
    tipos = {}
    for filas in inf.resumen.values():
        for r in filas:
            if r.get("RUC"):
                tipos[r["RUC"]] = r.get("TIPO", "")
    for e in inf.empresas:
        e.tipo = tipos.get(e.ruc, "MAIN" if e.ruc == inf.ruc_main else "RELACIONADA")


# ---------------------------------------------------------------- métricas
def _total(d: dict, excluir=("TOTAL GENERAL",)) -> float:
    if not d:
        return 0.0
    if "TOTAL GENERAL" in d and d["TOTAL GENERAL"] is not None:
        return float(d["TOTAL GENERAL"])
    return float(sum(v or 0 for k, v in d.items() if k not in excluir))


def _ultimo(serie: dict, desde: int | None = None) -> float:
    """Último valor no nulo de la serie (opcionalmente solo desde el año `desde`)."""
    for anio in sorted(serie, reverse=True):
        if desde is not None and anio < desde:
            break
        if serie[anio]:
            return float(serie[anio])
    return 0.0


LABORAL = re.compile(r"despido|laboral|trabaj|indemnizaci|visto bueno|haberes", re.I)
COBRO = re.compile(r"cobro|cheque|pagar[eé]|letra de cambio|monitorio|ejecutiv", re.I)


def metricas(e: Empresa, anio_ref: int) -> dict:
    """Aplana la ficha en un diccionario de métricas para evaluar los servicios."""
    d = {k: v for k, v in e.datos.items()}
    for k in ("trabajadores", "exportaciones", "importaciones_no_producidos", "importaciones_mp",
              "ppe", "sueldos", "cxc_no_relacionadas", "gasto_deterioro"):
        d[k] = d.get(k) or 0.0
    pa = e.por_anio
    for campo in ("ventas", "utilidad_neta", "ir_causado", "ingreso_total"):
        serie = pa.get(campo, {})
        d[campo] = float(serie.get(anio_ref) if serie.get(anio_ref) is not None else _ultimo(serie))
    for campo in ("ct_iva", "ct_ir", "isd", "sercop"):
        serie = pa.get(campo, {})
        d[f"{campo}_ref"] = float(serie.get(anio_ref) or 0.0)
        d[f"{campo}_ultimo"] = _ultimo(serie, desde=anio_ref - 1)   # solo últimos 2 ejercicios
    isd = pa.get("isd", {})
    d["isd_actual"] = float(isd.get(anio_ref + 1) or 0.0)
    completos = [v for a, v in isd.items() if a <= anio_ref and v]
    d["isd_promedio"] = sum(completos) / len(completos) if completos else 0.0
    ct_iva = pa.get("ct_iva", {})
    d["ct_iva_max_5a"] = max([v or 0 for a, v in ct_iva.items() if a > anio_ref - 5] or [0])
    d["sercop_total"] = float(sum(v or 0 for v in pa.get("sercop", {}).values()))
    d["importaciones"] = d["importaciones_no_producidos"] + d["importaciones_mp"]
    d["cxc_sobre_ventas"] = (d["cxc_no_relacionadas"] / d["ventas"]) if d["ventas"] else 0.0

    proy = e.proyeccion_ir.get("proyeccion devolucion")
    if proy is None:
        proy = d["ct_ir_ref"] - (d["ir_causado"] or 0)
    d["proyeccion_devolucion_ir"] = float(proy)

    # Partidas OMC: formato de tabla aún no visto con datos; se suma la última columna monetaria
    # de cada fila (excepto filas de total). Revisar cuando llegue un informe con registros.
    omc = 0.0
    for r in e.omc:
        if any("total" in _norm(v) for v in r.values()):
            continue
        montos = [a_numero(v) for v in r.values() if "$" in str(v)]
        omc += (montos[-1] or 0.0) if montos else 0.0
    d["omc_total"] = omc
    d["omc_registros"] = len(e.omc)
    d["reg70_total"] = _total(e.reg70)
    d["reg21_total"] = _total(e.reg21)
    d["juicios_demandado"] = len(e.juicios_demandado)
    d["juicios_actor"] = len(e.juicios_actor)
    d["juicios_laborales_demandado"] = sum(1 for j in e.juicios_demandado if LABORAL.search(j["materia"]))
    d["juicios_civiles_demandado"] = sum(1 for j in e.juicios_demandado if not LABORAL.search(j["materia"]))
    d["juicios_cobro_actor"] = sum(1 for j in e.juicios_actor if COBRO.search(j["materia"]))
    d["deudas_firmes"] = bool(e.deudas.get("deudas_firmes"))
    d["deudas_impugnadas"] = bool(e.deudas.get("deudas_impugnadas"))
    d["facilidades_pago"] = bool(e.deudas.get("facilidades_pago"))
    d["gran_contribuyente"] = _norm(e.datos.get("gran_contribuyente", "no")).startswith("si")
    d["tarifa_diferenciada"] = not _norm(e.tarifa_diferenciada or "sin registro").startswith("sin")
    d["objeto"] = e.datos.get("objeto", "")
    d["sector"] = ""
    # accionista persona natural: identificación de 10 dígitos (cédula); RUC de sociedad = 13
    d["accionistas_pn"] = sum(1 for a in e.accionistas
                              if len(re.sub(r"\D", "", str(a.get("IDENTIFICACIÓN", "")))) == 10)
    d["nombre"] = e.nombre
    d["ruc"] = e.ruc
    d["tipo"] = e.tipo
    return d


# ---------------------------------------------------------------- discrepancias
_COMPARAR = [
    # (sección resumen, columna, función que obtiene el valor de la ficha, tolerancia)
    ("tributario", "C.T. IVA {r}", lambda e, r: e.por_anio.get("ct_iva", {}).get(r), 1.0),
    ("tributario", "C.T. IR {r}", lambda e, r: e.por_anio.get("ct_ir", {}).get(r), 1.0),
    ("tributario", "ISD {r}", lambda e, r: e.por_anio.get("isd", {}).get(r), 1.0),
    ("tributario", "ISD {a}", lambda e, r: e.por_anio.get("isd", {}).get(r + 1), 1.0),
    ("legal corporativo", "N° Trab.", lambda e, r: e.datos.get("trabajadores"), 0.0),
    ("cobranzas", "Deudores comerciales y otras CxC no relac.", lambda e, r: e.datos.get("cxc_no_relacionadas"), 1.0),
    ("aduanero", "REG 70 TOTAL", lambda e, r: _total(e.reg70), 1.0),
    ("aduanero", "REG 21 TOTAL", lambda e, r: _total(e.reg21), 1.0),
]


def detectar_discrepancias(inf: InformeGrupo) -> list[str]:
    salida: list[str] = []
    por_ruc = {e.ruc: e for e in inf.empresas}
    r = inf.anio_ref
    for seccion, col_tpl, valor_ficha, tol in _COMPARAR:
        col = col_tpl.format(r=r, a=r + 1)
        for fila in inf.resumen.get(seccion, []):
            e = por_ruc.get(fila.get("RUC"))
            if e is None or col not in fila:
                continue
            v_res = a_numero(fila[col])
            v_fic = valor_ficha(e, r)
            if v_res is None or v_fic is None:
                continue
            if abs((v_res or 0) - (v_fic or 0)) > tol:
                salida.append(f"{e.nombre} ({e.ruc}) — '{col}': resumen {v_res:,.2f} vs ficha {v_fic:,.2f}")
    rucs_resumen = {f.get("RUC") for filas in inf.resumen.values() for f in filas if f.get("RUC", "").isdigit()}
    faltan = rucs_resumen - set(por_ruc)
    if faltan:
        salida.append(f"RUC en el resumen sin ficha de detalle: {', '.join(sorted(faltan))}")
    return salida

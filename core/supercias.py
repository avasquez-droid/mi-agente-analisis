"""Consulta en tiempo real del portal consultaCompanias de la Superintendencia de Compañías.

Trae la ficha pública de una compañía (RUC, expediente, situación legal, provincia, ciudad,
dirección, correos, teléfonos, objeto social) y sus **administradores actuales**, y la convierte
en el diccionario `cliente` que usan propuestas, contratos y acuerdos de confidencialidad.

Flujo del portal (JSF/PrimeFaces, verificado con una captura HAR de 2026-11):
  1. GET  busquedaCompanias.jsf                  → cookie de sesión + ViewState
  2. POST tipoBusqueda (1 expediente · 2 RUC · 3 nombre)
  3. POST autocompletar (parametroBusqueda_query) → "EXPEDIENTE - RUC - NOMBRE"
  4. POST itemSelect                              → compañía seleccionada
  5. GET  altcha-challenge + POST btnConsultarCompania (campo `altcha`)
  6. GET  informacionCompanias.jsf                → información general
  7. POST frmMenu:menuAdministradoresActuales     → abre el diálogo de verificación
  8. GET  altcha-challenge + POST frmCaptcha:btnPresentarContenido → tabla de administradores

La verificación ALTCHA es una prueba de trabajo (ver supercias_altcha.py): se calcula igual que
lo hace el navegador. Es información pública; no constituye certificación. Usar con moderación
(una consulta por cliente), no para descargas masivas.

Requiere salida a internet hacia appscvsgen.supercias.gob.ec (desde el PC del usuario).
"""
from __future__ import annotations

import html
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime

from .supercias_altcha import resolver_challenge

BASE = "https://appscvsgen.supercias.gob.ec/consultaCompanias"
URL_BUSQUEDA = f"{BASE}/societario/busquedaCompanias.jsf"
URL_INFO = f"{BASE}/societario/informacionCompanias.jsf"
URL_ALTCHA = f"{BASE}/altcha-challenge"
AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/157.0.0.0 Safari/537.36")
TIPOS = {"expediente": "1", "ruc": "2", "nombre": "3"}
F = "frmBusquedaCompanias"


class SuperciasError(Exception):
    """No se pudo completar la consulta (red, cambio del portal o compañía no encontrada)."""


class VariasCoincidencias(SuperciasError):
    def __init__(self, texto: str, candidatos: list["Candidato"]):
        self.candidatos = candidatos
        super().__init__(f"'{texto}' coincide con {len(candidatos)} compañías; indique el RUC.")


@dataclass
class Candidato:
    expediente: str
    ruc: str
    nombre: str
    etiqueta: str            # texto exacto del portal (se reenvía al seleccionar)


@dataclass
class Administrador:
    identificacion: str
    nombre: str              # como consta en el registro: APELLIDOS NOMBRES
    nacionalidad: str
    cargo: str
    fecha_nombramiento: str
    periodo: str
    registro_mercantil: str
    fecha_registro_mercantil: str
    tipo: str                # RL (representante legal) | ADM (administrador)


@dataclass
class Ficha:
    general: dict = field(default_factory=dict)        # etiqueta del portal → valor
    administradores: list[Administrador] = field(default_factory=list)
    consultado: str = ""
    avisos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ lectura del HTML
def _limpio(texto: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))).strip()


def _viewstate(texto: str) -> str | None:
    m = (re.search(r'<update id="[^"]*javax\.faces\.ViewState[^"]*"><!\[CDATA\[(.*?)\]\]>', texto)
         or re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]*)"', texto))
    return html.unescape(m.group(1)) if m else None


def _mensajes(texto: str) -> list[str]:
    """Mensajes de error que el portal muestra (p. ej. verificación incorrecta)."""
    return [_limpio(m) for m in re.findall(
        r'class="ui-messages-(?:error|warn|fatal)-(?:summary|detail)">(.*?)</span>', texto, re.S) if _limpio(m)]


def leer_candidatos(texto: str) -> list[Candidato]:
    salida = []
    for etiqueta in re.findall(r'data-item-value="([^"]*)"', texto):
        etiqueta = html.unescape(etiqueta)
        partes = [p.strip() for p in etiqueta.split(" - ", 2)]
        if len(partes) == 3:
            salida.append(Candidato(partes[0], partes[1], partes[2], etiqueta))
    return salida


_CAMPO = re.compile(
    r'<label[^>]*>(?P<etq>[^<]*)</label>'
    r'|<input[^>]*type="text"[^>]*value="(?P<val>[^"]*)"[^>]*readonly'
    r'|<textarea[^>]*readonly[^>]*>(?P<txt>[^<]*)</textarea>', re.S)


def leer_informacion_general(texto: str) -> dict:
    """Pares etiqueta → valor de la pestaña "Información general" (campos de solo lectura)."""
    fin = texto.find("tblAdministradores")
    datos, etiqueta, repetidas = {}, None, {}
    for m in _CAMPO.finditer(texto if fin < 0 else texto[:fin]):
        if m.group("etq") is not None:
            etiqueta = _limpio(m.group("etq")).rstrip(":").strip() or None
            continue
        if not etiqueta:
            continue
        valor = _limpio(m.group("val") if m.group("val") is not None else m.group("txt"))
        if etiqueta in datos:                      # "Descripción" se repite por cada CIIU
            repetidas[etiqueta] = repetidas.get(etiqueta, 1) + 1
            etiqueta = f"{etiqueta} {repetidas[etiqueta]}"
        datos[etiqueta] = valor
        etiqueta = None
    return datos


def leer_administradores(texto: str) -> list[Administrador] | None:
    """Filas de la tabla de administradores actuales; None si la tabla no viene en la respuesta."""
    m = re.search(r'<tbody id="[^"]*tblAdministradoresActuales_data"[^>]*>(.*?)</tbody>', texto, re.S)
    if not m:
        return None
    filas = []
    for fila in re.findall(r"<tr[^>]*data-ri=[^>]*>(.*?)</tr>", m.group(1), re.S):
        c = [_limpio(x) for x in re.findall(r'<td[^>]*role="gridcell"[^>]*>(.*?)</td>', fila, re.S)]
        if len(c) >= 9:
            filas.append(Administrador(*c[:9]))
    return filas


_VACIOS = {"N/A", "NA", "N.A.", "NO APLICA", "NINGUNO", "NINGUNA", "-", "--", "."}   # relleno del registro


# ------------------------------------------------------------------ cliente HTTP
class ConsultaSupercias:
    """Una sesión del portal. `sesion` es inyectable para pruebas (interfaz de requests.Session)."""

    def __init__(self, sesion=None, espera: float = 0.4, timeout: float = 40):
        if sesion is None:
            try:
                import requests
            except ImportError as e:                                    # pragma: no cover
                raise SuperciasError("Falta la librería requests: pip install -r requirements.txt") from e
            sesion = requests.Session()
            sesion.headers.update({"User-Agent": AGENTE, "Accept-Language": "es-419,es;q=0.9"})
        self.s, self.espera, self.timeout = sesion, espera, timeout
        self.vs: str | None = None

    # -- transporte
    def _pedir(self, metodo: str, url: str, **kw) -> str:
        try:
            r = getattr(self.s, metodo)(url, timeout=self.timeout, **kw)
            r.raise_for_status()
        except SuperciasError:
            raise
        except Exception as e:
            raise SuperciasError(
                f"No se pudo conectar con el portal de la Superintendencia de Compañías ({type(e).__name__}: {e}). "
                "La consulta necesita salida a internet hacia appscvsgen.supercias.gob.ec.") from e
        if self.espera:
            time.sleep(self.espera)
        return r.text

    def _ajax(self, url: str, datos: dict) -> str:
        if not self.vs:
            raise SuperciasError("El portal no entregó el ViewState (¿cambió la página?).")
        cuerpo = {"javax.faces.partial.ajax": "true", **datos, "javax.faces.ViewState": self.vs}
        texto = self._pedir("post", url, data=cuerpo, headers={
            "Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest", "Referer": url,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        self.vs = _viewstate(texto) or self.vs
        return texto

    def _altcha(self, referer: str) -> str:
        try:
            r = self.s.get(URL_ALTCHA, timeout=self.timeout, headers={"Referer": referer})
            r.raise_for_status()
            return resolver_challenge(r.json())
        except Exception as e:
            raise SuperciasError(f"No se pudo resolver la verificación ALTCHA del portal ({e}).") from e

    def _campos_navegador(self) -> dict:
        return {f"{F}:browser": "Chrome", f"{F}:altoBrowser": "730", f"{F}:anchoBrowser": "944",
                f"{F}:menuDispositivoMovil": "hidden"}

    # -- pasos
    def buscar(self, texto: str) -> tuple[str, list[Candidato]]:
        """Abre la búsqueda y devuelve (tipo, candidatos) para un RUC, expediente o nombre."""
        texto = texto.strip()
        solo_digitos = re.sub(r"\D", "", texto)
        if solo_digitos and solo_digitos == re.sub(r"[\s.-]", "", texto):
            tipo, consulta = ("ruc" if len(solo_digitos) >= 10 else "expediente"), solo_digitos
        else:
            tipo, consulta = "nombre", texto[:50]
        pagina = self._pedir("get", URL_BUSQUEDA)
        self.vs = _viewstate(pagina)
        render = (f"{F}:parametroBusqueda {F}:panelCompaniaSeleccionada {F}:panelCaptcha "
                  f"{F}:btnConsultarCompania")
        self._ajax(URL_BUSQUEDA, {
            "javax.faces.source": f"{F}:tipoBusqueda", "javax.faces.partial.execute": f"{F}:tipoBusqueda",
            "javax.faces.partial.render": render, "javax.faces.behavior.event": "valueChange",
            "javax.faces.partial.event": "change", f"{F}:tipoBusqueda": TIPOS[tipo]})
        r = self._ajax(URL_BUSQUEDA, {
            "javax.faces.source": f"{F}:parametroBusqueda", "javax.faces.partial.execute": f"{F}:parametroBusqueda",
            "javax.faces.partial.render": f"{F}:parametroBusqueda",
            f"{F}:parametroBusqueda": f"{F}:parametroBusqueda", f"{F}:parametroBusqueda_query": consulta,
            F: F, f"{F}:tipoBusqueda": TIPOS[tipo], f"{F}:parametroBusqueda_input": consulta,
            **self._campos_navegador()})
        self._tipo, self._render = tipo, render
        return tipo, leer_candidatos(r)

    def abrir(self, c: Candidato) -> dict:
        """Selecciona la compañía, pasa la verificación y devuelve la información general."""
        self._ajax(URL_BUSQUEDA, {
            "javax.faces.source": f"{F}:parametroBusqueda", "javax.faces.partial.execute": f"{F}:parametroBusqueda",
            "javax.faces.partial.render": self._render, "javax.faces.behavior.event": "itemSelect",
            "javax.faces.partial.event": "itemSelect", f"{F}:parametroBusqueda_itemSelect": c.etiqueta,
            f"{F}:parametroBusqueda_input": c.etiqueta})
        seleccionado = {"expediente": c.expediente, "ruc": c.ruc, "nombre": c.nombre}[self._tipo]
        payload = self._altcha(URL_BUSQUEDA)
        r = self._ajax(URL_BUSQUEDA, {
            "javax.faces.source": f"{F}:btnConsultarCompania", "javax.faces.partial.execute": F,
            f"{F}:btnConsultarCompania": f"{F}:btnConsultarCompania", F: F,
            f"{F}:tipoBusqueda": TIPOS[self._tipo], f"{F}:parametroBusqueda_input": seleccionado,
            "altcha": payload, f"{F}:payloadOculto": payload, **self._campos_navegador()})
        if '"procesamientoCorrecto":true' not in r.replace(" ", ""):
            raise SuperciasError("El portal rechazó la consulta" +
                                 (": " + "; ".join(_mensajes(r)) if _mensajes(r) else " (verificación o sesión)."))
        pagina = self._pedir("get", URL_INFO, headers={"Referer": URL_BUSQUEDA})
        self.vs = _viewstate(pagina)
        general = {k: ("" if v.strip().upper() in _VACIOS else v) for k, v in leer_informacion_general(pagina).items()}
        if not general.get("R.U.C.") and not general.get("Expediente"):
            raise SuperciasError("No se pudo leer la información general (¿cambió el portal?).")
        return general

    def administradores(self) -> list[Administrador]:
        r = self._ajax(URL_INFO, {
            "javax.faces.source": "frmMenu:menuAdministradoresActuales",
            "javax.faces.partial.execute": "frmMenu:menuAdministradoresActuales",
            "javax.faces.partial.render": "frmInformacionCompanias:panelGroupInformacionCompanias dlgCaptcha",
            "frmMenu:menuAdministradoresActuales": "frmMenu:menuAdministradoresActuales"})
        filas = leer_administradores(r)
        if filas is None:                         # el portal pide la verificación antes de mostrar la tabla
            payload = self._altcha(URL_INFO)
            r = self._ajax(URL_INFO, {
                "javax.faces.source": "frmCaptcha:btnPresentarContenido", "javax.faces.partial.execute": "frmCaptcha",
                "javax.faces.partial.render": "frmInformacionCompanias:panelGroupInformacionCompanias "
                                              "frmCaptcha:msgCaptcha dlgPresentarDocumentoPdf panelPresentarDocumentoPdf "
                                              "dlgPresentarDocumentoPdfConFirmasElectronicas "
                                              "panelPresentarDocumentoPdfConFirmasElectronicas dlgDetalleActoJuridico "
                                              "dlgDetalleInformeSociedadExtranjera dlgInformacionPersona "
                                              "panelInformacionPersona",
                "frmCaptcha:btnPresentarContenido": "frmCaptcha:btnPresentarContenido", "frmCaptcha": "frmCaptcha",
                "altcha": payload, "frmCaptcha:payloadOcultoPopup": payload})
            filas = leer_administradores(r)
        if filas is None:
            raise SuperciasError("El portal no devolvió la tabla de administradores" +
                                 (": " + "; ".join(_mensajes(r)) if _mensajes(r) else "."))
        return filas


def _elegir(texto: str, tipo: str, candidatos: list[Candidato]) -> Candidato:
    if not candidatos:
        raise SuperciasError(f"La Superintendencia de Compañías no tiene una compañía que coincida con '{texto}'. "
                             "(Personas naturales y entidades fuera de su control no constan en este portal.)")
    if len(candidatos) == 1:
        return candidatos[0]
    clave = re.sub(r"\D", "", texto) if tipo != "nombre" else re.sub(r"\W+", "", texto).upper()
    exactos = [c for c in candidatos if clave in (c.ruc, c.expediente, re.sub(r"\W+", "", c.nombre).upper())]
    if len(exactos) == 1:
        return exactos[0]
    raise VariasCoincidencias(texto, candidatos)


def consultar(texto: str, sesion=None, con_administradores: bool = True) -> Ficha:
    """Consulta completa por RUC, expediente o nombre. Lanza VariasCoincidencias si el nombre es ambiguo."""
    portal = ConsultaSupercias(sesion) if not isinstance(sesion, ConsultaSupercias) else sesion
    tipo, candidatos = portal.buscar(texto)
    ficha = Ficha(consultado=datetime.now().isoformat(timespec="seconds"))
    elegido = _elegir(texto, tipo, candidatos)
    ficha.general = portal.abrir(elegido)
    ficha.general.setdefault("Nombre", elegido.nombre)
    if ficha.general.get("R.U.C.") and elegido.ruc and ficha.general["R.U.C."] != elegido.ruc:
        raise SuperciasError("El portal devolvió una compañía distinta de la seleccionada.")
    if con_administradores:
        try:
            ficha.administradores = portal.administradores()
        except SuperciasError as e:
            ficha.avisos.append(f"Administradores no disponibles: {e}")
    return ficha


# ------------------------------------------------------------------ ficha → datos del cliente
_PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "SAN", "SANTA", "VON", "VAN", "DA", "DI", "Y"}
_MINUSCULAS = {"de", "del", "la", "las", "los", "y", "e"}


def _titulo(texto: str) -> str:
    """GUAYAQUIL → Guayaquil; SANTO DOMINGO DE LOS TSACHILAS → Santo Domingo de los Tsachilas."""
    palabras = [p.capitalize() for p in (texto or "").split()]
    return " ".join(p.lower() if i and p.lower() in _MINUSCULAS else p for i, p in enumerate(palabras))


def nombre_natural(registro: str) -> str:
    """El registro escribe APELLIDOS NOMBRES; devuelve 'Nombres Apellidos' (dos apellidos, con sus
    partículas). Si no se puede separar con seguridad, conserva el orden del registro."""
    p = (registro or "").split()
    i, apellidos = 0, 0
    while i < len(p) and apellidos < 2:
        while i < len(p) - 1 and p[i].upper() in _PARTICULAS:
            i += 1
        i += 1
        apellidos += 1
    if apellidos < 2 or i >= len(p):
        return _titulo(registro)
    return _titulo(" ".join(p[i:] + p[:i]))


def representante_legal(administradores: list[Administrador]) -> Administrador | None:
    """Representante legal para firmar: RL con cargo Gerente General; si no, el primer RL."""
    rl = [a for a in administradores if a.tipo.upper().startswith("RL")]
    for patron in (r"GERENTE GENERAL", r"GERENTE", r"PRESIDENTE"):
        for a in rl:
            if re.search(patron, a.cargo.upper()):
                return a
    return rl[0] if rl else None


def direccion(g: dict) -> str:
    via = " ".join(x for x in (g.get("Calle"), g.get("Número")) if x)
    if g.get("Intersección"):
        via = f"{via} y {g['Intersección']}" if via else g["Intersección"]
    partes = [via]
    for etiqueta, prefijo in (("Ciudadela", "Cdla. "), ("Conjunto", "Conj. "), ("Edificio/Centro comercial", "Edif. "),
                              ("Bloque", "bloque "), ("Piso", "piso "), ("Barrio", "barrio "),
                              ("Kilómetro", "km "), ("Camino", "vía ")):
        if g.get(etiqueta):
            partes.append(prefijo + g[etiqueta])
    return ", ".join(x for x in partes if x)


def a_cliente(ficha: Ficha) -> tuple[dict, list[str]]:
    """Convierte la ficha en el `cliente` de contratos/propuestas. Devuelve (cliente, avisos)."""
    g, avisos = ficha.general, list(ficha.avisos)
    correos = []
    for c in (g.get("Correo 1"), g.get("Correo 2")):
        for x in re.split(r"[;,\s]+", (c or "").lower()):
            if "@" in x and x not in correos:
                correos.append(x)
    cliente = {
        "razon_social": g.get("Nombre") or g.get("Denominación") or "",
        "ruc": g.get("R.U.C.", ""),
        "persona": "juridica",
        "expediente": g.get("Expediente", ""),
        "tipo_compania": g.get("Tipo de compañía", ""),
        "situacion_legal": g.get("Situación legal", ""),
        "provincia": _titulo(g.get("Provincia", "")),
        "canton": _titulo(g.get("Cantón", "")),
        "ciudad": _titulo(g.get("Ciudad", "") or g.get("Cantón", "")),
        "direccion": direccion(g),
        "referencia_ubicacion": g.get("Referencia ubicación", ""),
        "correos": correos,
        "telefonos": list(dict.fromkeys(t for t in (g.get("Celular"), g.get("Teléfono 1"), g.get("Teléfono 2")) if t)),
        "sitio_web": (g.get("Sitio web") or "").lower(),
        "objeto_social": g.get("Objeto social", ""),
        "ciiu": g.get("CIIU actividad principal", ""),
        "fecha_constitucion": g.get("Fecha de constitución", ""),
    }
    rl = representante_legal(ficha.administradores)
    if rl:
        cliente.update(representante=nombre_natural(rl.nombre), representante_registro=rl.nombre,
                       tratamiento="[COMPLETAR: tratamiento (el señor / la señora)]",   # el registro no lo indica
                       cargo=_titulo(rl.cargo), cedula=rl.identificacion,
                       nombramiento={"fecha": rl.fecha_nombramiento, "periodo_anios": rl.periodo,
                                     "registro_mercantil": rl.registro_mercantil,
                                     "fecha_registro": rl.fecha_registro_mercantil})
        avisos.append(f"Representante tomado del registro: {rl.nombre} ({rl.cargo}, {rl.tipo}). Confirme el "
                      "tratamiento (el señor / la señora) y las tildes del nombre.")
        if "GERENTE GENERAL" not in rl.cargo.upper():
            avisos.append(f"No consta un Gerente General como representante legal; se usó el cargo '{rl.cargo}'.")
        try:
            anios = int(rl.periodo)
            inicio = datetime.strptime(rl.fecha_registro_mercantil or rl.fecha_nombramiento, "%Y-%m-%d")
            if inicio.replace(year=inicio.year + anios) < datetime.now():
                avisos.append(f"El nombramiento ({inicio:%Y-%m-%d}, {anios} años) aparece vencido: verifique "
                              "si hay prórroga o nuevo nombramiento.")
        except (ValueError, TypeError):
            pass
    elif ficha.administradores:
        avisos.append("Ningún administrador consta como representante legal (RL): indique quién firma.")
    else:
        avisos.append("Sin administradores: indique representante, cargo y cédula.")
    cliente["administradores"] = [
        {"nombre": a.nombre, "identificacion": a.identificacion, "cargo": a.cargo, "tipo": a.tipo,
         "fecha_nombramiento": a.fecha_nombramiento, "periodo_anios": a.periodo} for a in ficha.administradores]
    if cliente["situacion_legal"] and cliente["situacion_legal"].upper() != "ACTIVA":
        avisos.append(f"Situación legal de la compañía: {cliente['situacion_legal']}.")
    if not correos:
        avisos.append("La compañía no registra correo en la Superintendencia: pídalo al cliente.")
    cliente["fuente"] = {"origen": "Superintendencia de Compañías (consultaCompanias)", "consultado": ficha.consultado,
                         "ultima_actualizacion_societaria": g.get("Fecha última actualización societaria", "")}
    return {k: v for k, v in cliente.items() if v not in ("", [], None)}, avisos


def cliente_desde_supercias(texto: str, sesion=None) -> tuple[dict, list[str]]:
    return a_cliente(consultar(texto, sesion))

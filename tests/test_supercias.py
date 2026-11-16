"""Pruebas de la consulta a la Superintendencia de Compañías con un portal simulado (datos FICTICIOS)."""
import base64
import hashlib
import json
import sys
from pathlib import Path

import docx
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import supercias as sc  # noqa: E402
from core.cli import main  # noqa: E402
from core.supercias_altcha import AltchaError, resolver_challenge  # noqa: E402

VS1, VS2 = "111:222", "333:444"
COMPANIAS = ["700001 - 0990000001001 - IMPORTADORA DEMO S.A.", "700002 - 0990000002001 - IMPORTADORA DEMOSTRACION CIA. LTDA."]
CAMPOS = {"Expediente": "700001", "R.U.C.": "0990000001001", "Fecha de constitución": "2011-01-17",
          "Tipo de compañía": "ANÓNIMA", "Situación legal": "ACTIVA", "Provincia": "GUAYAS" + " " * 40,
          "Cantón": "SAMBORONDON", "Ciudad": "SAMBORONDON", "Calle": "AV. FICTICIA", "Número": "123",
          "Intersección": "CALLE DEMO", "Edificio/Centro comercial": "TORRE DEMO", "Piso": "4",
          "Celular": "0990000000", "Teléfono 1": "0990000000", "Barrio": "N/A", "Correo 1": "GERENCIA@IMPORTADORADEMO.EC", "Correo 2": "",
          "Fecha última actualización societaria": "2026-03-17 10:37:56"}
ADMIN = [("0900000001   ", "DE LA CRUZ PEREZ MARIA JOSE", "ECUADOR   ", "GERENTE GENERAL    ", "2025-01-10", "5", "100", "2025-02-01", "RL"),
         ("0900000002", "DEMO FICTICIO JUAN", "ECUADOR", "PRESIDENTE", "2025-01-10", "5", "101", "2025-02-01", "ADM")]


ACCIONISTAS = [("1", "0900000003", "OTRO DEMO PEDRO", "ECUADOR", "NACIONAL", "2.500,0000", "N"),
               ("2", "0900000001", "DE LA CRUZ PEREZ MARIA JOSE", "ECUADOR", "NACIONAL", "7.500,0000", "S")]


def _tabla_accionistas():
    filas = "".join(
        f'<tr data-ri="{i}" class="ui-widget-content" role="row">'
        + "".join(f'<td role="gridcell"><center><a href="#"><label class="ui-outputlabel">{c}</label></a></center></td>'
                  for c in a) + "</tr>" for i, a in enumerate(ACCIONISTAS))
    return (f'<partial-response><changes><update id="p"><![CDATA[<tbody id="frmInformacionCompanias:'
            f'tblAccionistas_data" class="ui-datatable-data">{filas}</tbody>]]></update></changes></partial-response>')


def _pagina_info():
    filas = "".join(
        f'<td role="gridcell" class="c1"><label id="x" class="ui-outputlabel">{k}:</label></td><td role="gridcell">'
        f'<input id="i" name="i" type="text" value="{v}" readonly="readonly" class="ui-inputfield" /></td>'
        for k, v in CAMPOS.items())
    return (f'<html><table>{filas}<td><label>Objeto social:</label></td><td><textarea id="t" readonly="readonly" '
            f'class="x">Venta de productos &amp; servicios ficticios.</textarea></td></table>'
            f'<input type="hidden" name="javax.faces.ViewState" value="{VS2}" /></html>')


def _tabla_admin():
    filas = "".join(
        f'<tr data-ri="{i}" class="ui-widget-content" role="row">'
        + "".join(f'<td role="gridcell"><center><label id="l" class="ui-outputlabel">{c}</label></center></td>' for c in a)
        + '<td role="gridcell"><a href="#">PDF</a></td></tr>' for i, a in enumerate(ADMIN))
    return (f'<partial-response><changes><update id="p"><![CDATA[<tbody id="frmInformacionCompanias:'
            f'tblAdministradoresActuales_data" class="ui-datatable-data">{filas}</tbody>]]></update></changes></partial-response>')


class Respuesta:
    def __init__(self, texto):
        self.text = texto

    def raise_for_status(self):
        pass

    def json(self):
        return json.loads(self.text)


class PortalSimulado:
    """Imita las respuestas del portal y valida ViewState y prueba de trabajo como lo haría el servidor."""

    def __init__(self):
        self.retos, self.pasos, self.n = {}, [], 0

    def get(self, url, **_):
        if url == sc.URL_BUSQUEDA:
            return Respuesta(f'<input type="hidden" name="javax.faces.ViewState" value="{VS1}" />')
        if url == sc.URL_ALTCHA:
            self.n += 1
            salt, numero = f"sal{self.n}?123", 4000 + self.n
            reto = hashlib.sha256(f"{salt}{numero}".encode()).hexdigest()
            self.retos[reto] = numero
            return Respuesta(json.dumps({"algorithm": "SHA-256", "challenge": reto, "salt": salt,
                                         "signature": "firma", "maxnumber": 50000}))
        assert url == sc.URL_INFO and "consultar" in self.pasos
        return Respuesta(_pagina_info())

    def _verificar(self, payload):
        p = json.loads(base64.b64decode(payload))
        assert self.retos.pop(p["challenge"]) == p["number"] and p["signature"] == "firma"

    def post(self, url, data=None, **_):
        fuente = data["javax.faces.source"]
        if url == sc.URL_BUSQUEDA:
            assert data["javax.faces.ViewState"] == VS1
            if fuente.endswith("tipoBusqueda"):
                self.tipo = data["frmBusquedaCompanias:tipoBusqueda"]
                return Respuesta("<partial-response/>")
            if "frmBusquedaCompanias:parametroBusqueda_query" in data:
                q = data["frmBusquedaCompanias:parametroBusqueda_query"].upper()
                items = "".join(f'<li data-item-label="{c}" data-item-value="{c}">{c}</li>' for c in COMPANIAS if q in c)
                return Respuesta(f"<partial-response><![CDATA[<ul>{items}</ul>]]></partial-response>")
            if data.get("javax.faces.behavior.event") == "itemSelect":
                self.pasos.append("seleccionar")
                return Respuesta("<partial-response/>")
            assert fuente.endswith("btnConsultarCompania") and data["altcha"] == data["frmBusquedaCompanias:payloadOculto"]
            self._verificar(data["altcha"])
            self.pasos.append("consultar")
            return Respuesta('<partial-response><extension>{"procesamientoCorrecto":true}</extension></partial-response>')
        assert url == sc.URL_INFO and data["javax.faces.ViewState"] == VS2
        if fuente in ("frmMenu:menuAdministradoresActuales", "frmMenu:menuAccionistas"):
            self.menu = fuente
            return Respuesta("<partial-response><update id='dlgCaptcha'/></partial-response>")
        assert fuente == "frmCaptcha:btnPresentarContenido"
        self._verificar(data["altcha"])
        self.pasos.append(self.menu)
        return Respuesta(_tabla_accionistas() if self.menu.endswith("Accionistas") else _tabla_admin())


@pytest.fixture
def portal():
    return sc.ConsultaSupercias(PortalSimulado(), espera=0)


def test_altcha():
    salt = "abc?1"
    reto = {"algorithm": "SHA-256", "challenge": hashlib.sha256(f"{salt}777".encode()).hexdigest(),
            "salt": salt, "signature": "s", "maxnumber": 1000}
    assert json.loads(base64.b64decode(resolver_challenge(reto)))["number"] == 777
    with pytest.raises(AltchaError):
        resolver_challenge({**reto, "maxnumber": 10})


def test_consulta_por_ruc(portal):
    ficha = sc.consultar("0990000001001", portal)
    assert portal.s.tipo == "2"
    cliente, avisos = sc.a_cliente(ficha)
    assert cliente["razon_social"] == "IMPORTADORA DEMO S.A." and cliente["ruc"] == "0990000001001"
    assert (cliente["provincia"], cliente["ciudad"]) == ("Guayas", "Samborondon")
    assert cliente["direccion"] == "AV. FICTICIA 123 y CALLE DEMO, Edif. TORRE DEMO, piso 4"
    assert cliente["correos"] == ["gerencia@importadorademo.ec"] and cliente["telefonos"] == ["0990000000"]
    assert cliente["representante"] == "Maria Jose de la Cruz Perez"
    assert (cliente["cargo"], cliente["cedula"]) == ("Gerente General", "0900000001")
    assert [a["tipo"] for a in cliente["administradores"]] == ["RL", "ADM"]
    assert cliente["tratamiento"].startswith("[COMPLETAR")
    assert "Objeto social" in ficha.general and any("tratamiento" in a for a in avisos)


def test_accionistas(portal):
    ficha = sc.consultar("0990000001001", portal, con_administradores=False, con_accionistas=True)
    assert "frmMenu:menuAdministradoresActuales" not in portal.s.pasos
    assert [a.nombre for a in ficha.accionistas] == ["OTRO DEMO PEDRO", "DE LA CRUZ PEREZ MARIA JOSE"]
    assert ficha.accionistas[0].capital_usd == 2500.0 and ficha.accionistas[1].persona_natural
    pares = sc.participaciones(ficha.accionistas)
    assert [(a.identificacion, p) for a, p in pares] == [("0900000001", 75.0), ("0900000003", 25.0)]
    assert sc.participaciones([]) == []


def test_accionistas_y_administradores_en_la_misma_sesion(portal):
    ficha = sc.consultar("0990000001001", portal, con_accionistas=True)
    assert len(ficha.administradores) == 2 and len(ficha.accionistas) == 2 and not ficha.avisos


def test_accionistas_tabla_ausente():
    assert sc.leer_accionistas("<partial-response/>") is None
    assert sc.leer_accionistas('<tbody id="f:tblAccionistas_data"></tbody>') == []


def test_comando_accionistas(portal, monkeypatch, capsys):
    original = sc.consultar
    monkeypatch.setattr(sc, "consultar", lambda texto, **kw: original(texto, portal, **kw))
    assert main(["accionistas", "0990000001001"]) in (0, None)
    salida = capsys.readouterr().out
    assert "Accionistas (2, 2 personas naturales)" in salida
    assert "DE LA CRUZ PEREZ MARIA JOSE · 0900000001" in salida and "capital 7.500,00 · 75,00 % · con restricción" in salida
    monkeypatch.setattr(sc, "consultar", lambda texto, **kw: original(texto, sc.ConsultaSupercias(PortalSimulado(), espera=0), **kw))
    assert main(["accionistas", "0990000001001", "--json"]) in (0, None)
    datos = json.loads(capsys.readouterr().out)
    assert datos["ruc"] == "0990000001001" and datos["accionistas"][0]["porcentaje"] == 75.0


def test_nombre_ambiguo_y_exacto(portal):
    with pytest.raises(sc.VariasCoincidencias) as e:
        sc.consultar("importadora demo", portal)
    assert len(e.value.candidatos) == 2
    assert sc.consultar("Importadora Demo S.A.", sc.ConsultaSupercias(PortalSimulado(), espera=0)).general["R.U.C."] == "0990000001001"
    with pytest.raises(sc.SuperciasError):
        sc.consultar("no existe", sc.ConsultaSupercias(PortalSimulado(), espera=0))


def test_nombres():
    assert sc.nombre_natural("PEREZ LOPEZ JUAN CARLOS") == "Juan Carlos Perez Lopez"
    assert sc.nombre_natural("DEL POZO DE LA TORRE ANA") == "Ana del Pozo de la Torre"
    assert sc.nombre_natural("PEREZ LOPEZ") == "Perez Lopez"


def test_contrato_con_ruc(portal, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sc, "cliente_desde_supercias", lambda texto, sesion=None: sc.a_cliente(sc.consultar(texto, portal)))
    local = tmp_path / "c.yaml"
    local.write_text("tratamiento: la señora\ncorreos: [otro@demo.ec]\n", encoding="utf-8")
    assert main(["contrato", "devolucion_iva", "--ruc", "0990000001001", "--cliente", str(local),
                 "--var", "periodo=diciembre 2026", "--salida", str(tmp_path)]) == 0
    assert "Supercías (tiempo real): IMPORTADORA DEMO S.A." in capsys.readouterr().out
    texto = "\n".join(p.text for p in docx.Document(next(tmp_path.glob("*.docx"))).paragraphs)
    for esperado in ("IMPORTADORA DEMO S.A.", "0990000001001", "la señora Maria Jose de la Cruz Perez", "otro@demo.ec"):
        assert esperado in texto


def test_herramienta_mcp(portal, monkeypatch):
    pytest.importorskip("mcp")
    import importlib.util
    espec = importlib.util.spec_from_file_location("supercias_server", RAIZ / "adapters" / "mcp" / "supercias_server.py")
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    monkeypatch.setattr(modulo, "consultar", lambda texto: sc.consultar(texto, portal))
    r = modulo.consultar_supercias("0990000001001")
    assert r["estado"] == "ok" and r["cliente"]["ruc"] == "0990000001001" and r["avisos"]
    monkeypatch.setattr(modulo, "consultar", lambda texto: sc.consultar(texto, sc.ConsultaSupercias(PortalSimulado(), espera=0)))
    assert modulo.consultar_supercias("importadora demo")["estado"] == "varias_coincidencias"
    assert modulo.consultar_supercias("no existe")["estado"] == "error"


# ------------------------------------------------------------------ salidas (proxies propios)
class SinRed:
    def get(self, *a, **k):
        raise ConnectionError("Tunnel connection failed: 407 http://usuario:clave@10.0.0.9:3128")
    post = get


def test_lista_de_salidas(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPERCIAS_PROXIES", "http://u:c@1.1.1.1:8080, 2.2.2.2:3128 # comentario\n\n")
    assert sc.salidas() == ["http://u:c@1.1.1.1:8080", "http://2.2.2.2:3128"]
    monkeypatch.delenv("SUPERCIAS_PROXIES")
    archivo = tmp_path / "proxies.txt"
    archivo.write_text("# salidas Census\nhttp://a:b@3.3.3.3:80\n", encoding="utf-8")
    monkeypatch.setattr(sc, "ARCHIVO_SALIDAS", archivo)
    assert sc.salidas() == ["http://a:b@3.3.3.3:80"]
    assert sc._ocultar("ProxyError http://user:secreto@3.3.3.3:80") == "ProxyError http://***@3.3.3.3:80"


def test_turnos_y_castigo():
    b = sc.Balanceador(["A", "B", "C"])
    b.turno = 0
    assert [b.orden()[0] for _ in range(4)] == ["A", "B", "C", "A"]
    b.fallo("C")
    assert b.orden() == ["B", "A", "C"]          # la caída pasa al final
    b.exito("C")
    assert b.orden() == ["C", "A", "B"]


def test_failover_entre_salidas(monkeypatch):
    usadas = []

    class Portal(sc.ConsultaSupercias):
        def __init__(self, sesion=None, espera=0, timeout=40, proxy=None):
            usadas.append(proxy)
            super().__init__(SinRed() if "caida" in proxy else PortalSimulado(), espera=0, proxy=proxy)

    monkeypatch.setattr(sc, "ConsultaSupercias", Portal)
    monkeypatch.setattr(sc, "_BALANCEADOR", None)
    monkeypatch.setenv("SUPERCIAS_PROXIES", "http://u:c@caida:1,http://u:c@sana:2")
    sc.balanceador().turno = 0
    ficha = sc.consultar("0990000001001")
    assert usadas == ["http://u:c@caida:1", "http://u:c@sana:2"]
    assert ficha.salida == "http://***@sana:2" and ficha.general["R.U.C."] == "0990000001001"
    cliente, _ = sc.a_cliente(ficha)
    assert cliente["fuente"]["salida"] == "http://***@sana:2"
    usadas.clear()
    sc.consultar("0990000001001")                 # la caída quedó apartada: va directo a la sana
    assert usadas == ["http://u:c@sana:2"]

    monkeypatch.setattr(sc, "_BALANCEADOR", None)
    monkeypatch.setenv("SUPERCIAS_PROXIES", "http://u:c@caida:1")
    with pytest.raises(sc.SinConexion) as e:
        sc.consultar("0990000001001")
    assert "clave" not in str(e.value) and "***@" in str(e.value)


def test_conector_remoto_token():
    pytest.importorskip("mcp")
    pytest.importorskip("httpx")
    import importlib.util
    from starlette.testclient import TestClient
    espec = importlib.util.spec_from_file_location("servidor_remoto", RAIZ / "adapters" / "mcp" / "servidor_remoto.py")
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    with pytest.raises(SystemExit):
        modulo.crear_app("corto")
    token = "x" * 40
    with TestClient(modulo.crear_app(token)) as c:
        assert c.get("/salud").text == "ok"
        assert c.post("/mcp/otro-token", json={}).status_code == 404
        assert c.post("/mcp", json={}).status_code == 404
        r = c.post(f"/mcp/{token}", headers={"Accept": "application/json, text/event-stream"}, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}})
        assert r.status_code == 200 and "supercias-census" in r.text

"""Pruebas del Agente Comercial (usan solo datos ficticios)."""
from datetime import date
from pathlib import Path
import subprocess
import sys

import docx
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import conocimiento as kb  # noqa: E402
from core.contratos import armar_contrato, generar_contrato, letras, ordinal, usd  # noqa: E402
from core.informe_reader import a_numero, leer_informe, metricas  # noqa: E402
from core.oportunidades import analizar_grupo, evaluar_expresion, honorario_potencial  # noqa: E402

INFORME = RAIZ / "examples" / "informe_ejemplo.docx"
CLIENTE = {"razon_social": "EMPRESA DEMO S.A.", "ruc": "0990000000001", "representante": "Juan Pérez",
           "cargo": "Gerente General", "ciudad": "Guayaquil", "provincia": "Guayas", "correos": ["demo@demo.ec"]}


@pytest.fixture(scope="session")
def informe():
    if not INFORME.exists():
        subprocess.run([sys.executable, str(RAIZ / "examples" / "generar_informe_ejemplo.py")], check=True)
    return leer_informe(INFORME)


def test_numeros():
    assert a_numero("$ 1,226,322.14") == 1226322.14
    assert a_numero("($ 158,282.67)") == -158282.67
    assert a_numero("$ -") == 0.0
    assert a_numero("-") is None
    assert a_numero("799,0000") == 799.0


def test_lectura_informe(informe):
    assert informe.ruc_main == "0990000001001"
    assert informe.anio_ref == 2025
    assert len(informe.empresas) == 2
    m = metricas(informe.main, informe.anio_ref)
    assert m["isd_ref"] == 164000.0
    assert m["reg70_total"] == 310000.0
    assert m["proyeccion_devolucion_ir"] == 18500.0
    assert m["juicios_cobro_actor"] == 1
    assert m["accionistas_pn"] == 1        # identificación de 10 dígitos


def test_discrepancia_detectada(informe):
    assert any("REG 70" in d for d in informe.discrepancias)


def test_oportunidades(informe):
    r = analizar_grupo(informe)
    ids = {(o.ruc, o.servicio_id) for o in r["oportunidades"]}
    assert ("0990000001001", "planificacion_isd") in ids
    assert ("0990000001001", "deposito_aduanero") in ids
    assert ("0990000002001", "devolucion_iva") in ids
    assert ("0990000002001", "defensa_laboral") in ids
    # cobranza extrajudicial y judicial son alternativas: se cuenta solo la mayor
    total = honorario_potencial(r["oportunidades"])
    suma_simple = sum(o.honorario["monto"] or 0 for o in r["oportunidades"] if o.honorario["modelo"] != "mensual")
    assert total < suma_simple


def test_expresiones():
    assert evaluar_expresion("max(a - b, 0)", {"a": 5, "b": 8}) == 0
    with pytest.raises(ValueError):
        evaluar_expresion("__import__('os')", {})


def test_formatos():
    assert usd(450000) == "USD $450.000,00"
    assert letras(450000) == "Cuatrocientos Cincuenta Mil 00/100"
    assert ordinal(13) == "DÉCIMA TERCERA"


@pytest.mark.parametrize("sid", [s for s, d in kb.servicios().items() if d.get("clausulas")])
def test_todos_los_contratos(sid, tmp_path):
    variables = {k: m.get("ejemplo") for k, m in (kb.clausulas_servicio(sid).get("variables") or {}).items()}
    c = generar_contrato(sid, CLIENTE, variables, date(2026, 11, 9), tmp_path)
    assert c.archivo.exists()
    texto = "\n".join(p.text for p in docx.Document(str(c.archivo)).paragraphs)
    assert "PRIMERA: INTERVINIENTES" in texto
    assert "EMPRESA DEMO S.A." in texto
    assert "[COMPLETAR" not in texto, f"{sid}: quedaron marcadores con las variables de ejemplo"


def test_faltantes_se_marcan():
    c = armar_contrato("devolucion_iva", {"razon_social": "X S.A."}, {}, date(2026, 11, 9))
    assert "periodo" in c.pendientes
    assert "cliente.ruc" in " ".join(c.pendientes) or "ruc" in " ".join(c.pendientes)


def test_referencias_internas():
    c = armar_contrato("reclamo_aranceles_omc", CLIENTE, {"importaciones_desde": "enero 2024",
                                                         "importaciones_hasta": "diciembre 2025"})
    plazo = next(x for x in c.clausulas if x.clave == "plazo")
    assert "cláusula TERCERA" in plazo.parrafos[0]


def test_acuerdo_confidencialidad(tmp_path):
    from core.documentos import generar_documento
    cliente = {**CLIENTE, "representada_por": "REPRESENTACIONES DEMO CIA. LTDA.", "cedula": "0000000001"}
    d = generar_documento("acuerdo_confidencialidad", cliente, {"sector": "farmacéutico"}, date(2026, 10, 16), tmp_path)
    texto = d.texto()
    assert "quien a su vez es representada por Juan Pérez" in texto
    assert "farmacéutico" in texto
    assert "cinco (5) años" in texto
    assert "a los 16 días del mes de octubre de 2026" in d.cierre
    assert "CENSUSCONSULTORES”" not in texto        # una sola denominación de Census
    assert d.archivo.exists()


def test_confidencialidad_sin_cedula_queda_pendiente():
    from core.documentos import armar_documento
    d = armar_documento("acuerdo_confidencialidad", CLIENTE, {}, date(2026, 10, 16))
    assert "cédula del representante" in d.pendientes


@pytest.mark.parametrize("sid", [s for s, d in kb.servicios().items() if d.get("propuesta")])
def test_textos_de_propuesta(sid):
    import yaml
    from core.propuestas import armar_propuesta, plantilla_servicio
    variables = {k: m.get("ejemplo") for k, m in (plantilla_servicio(sid).get("variables") or {}).items()}
    p = armar_propuesta(sid, {"razon_social": "EMPRESA DEMO S.A."}, variables, date(2026, 11, 9))
    assert p.portada and p.objetivo and p.alcance and p.honorarios
    assert "[COMPLETAR" not in p.texto(), f"{sid}: {p.pendientes}"


def test_pptx_de_propuesta(tmp_path):
    from core.propuestas import PLANTILLA, generar_propuesta
    if not PLANTILLA.exists():
        pytest.skip("La plantilla de propuestas es privada (privado/plantillas/propuesta_base.pptx)")
    from pptx import Presentation
    p = generar_propuesta("control_posterior_aduanero", {"razon_social": "EMPRESA DEMO S.A."},
                          {"mercancia": "neumáticos", "periodo": "2024", "monto": 100000}, date(2026, 11, 9), tmp_path)
    prs = Presentation(str(p.archivo))
    textos = "\n".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    assert "EMPRESA DEMO S.A." in textos and "[COMPLETAR" not in textos and "<<" not in textos
    tabla = next(sh.table for s in prs.slides for sh in s.shapes if sh.has_table)
    assert len(tabla.rows) == 5          # cabecera + 4 etapas
    # PowerPoint ignora el texto que va después de <a:endParaRPr>: debe ser siempre el último
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for s in prs.slides:
        for par in s._element.iter(f"{ns}p"):
            hijos = [c.tag for c in par]
            if f"{ns}endParaRPr" in hijos:
                assert hijos.index(f"{ns}endParaRPr") == len(hijos) - 1


def test_propuesta_adicionales_y_notas_opcionales(tmp_path):
    from core.propuestas import PLANTILLA, armar_propuesta, generar_propuesta
    cliente = {"razon_social": "EMPRESA DEMO S.A."}
    sin = armar_propuesta("planificacion_tributaria", cliente, {"ejercicio": 2026}, date(2026, 11, 9))
    assert {c for c, _ in sin.por_confirmar} == {"gastos", "implementacion"} and not any("notariales" in n for n in sin.notas)
    con = armar_propuesta("planificacion_tributaria", cliente, {"ejercicio": 2026, "confirmadas": ["gastos"],
                          "antecedentes": ["Contexto dado por el usuario."]}, date(2026, 11, 9), ["planificacion_isd"])
    assert any("notariales" in n for n in con.notas) and con.antecedentes == ["Contexto dado por el usuario."]
    assert len(con.honorarios) == 2 and len(con.alcance) == 2 and " y " in con.referencia
    if not PLANTILLA.exists():
        return
    from pptx import Presentation
    p = generar_propuesta("devolucion_iva", cliente, {"periodo": "diciembre 2026"}, date(2026, 11, 9), tmp_path)
    prs = Presentation(str(p.archivo))
    textos = "\n".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    assert "<<" not in textos and "devolución de retenciones de IVA hasta diciembre 2026." in textos
    fuentes = {r.font.name for s in prs.slides for sh in s.shapes if sh.has_text_frame
               for par in sh.text_frame.paragraphs for r in par.runs if r.font.name}
    assert fuentes <= {"Arial"}


def test_fuente_del_documento(tmp_path):
    """Normal debe quedar en la fuente del formato (no Calibri de la plantilla)."""
    from core.documentos import generar_documento
    c = generar_contrato("devolucion_iva", CLIENTE, {"periodo": "diciembre 2026"}, date(2026, 11, 9), tmp_path)
    d = docx.Document(str(c.archivo))
    assert d.styles["Normal"].font.name == "Georgia" and d.styles["Normal"].font.size.pt == 10.5
    assert {r.font.name for p in d.paragraphs for r in p.runs} == {"Georgia"}   # título incluido
    n = generar_documento("acuerdo_confidencialidad", CLIENTE, {}, date(2026, 11, 9), tmp_path)
    assert docx.Document(str(n.archivo)).styles["Normal"].font.name == "Arial"


def test_exclusion_por_servicio_activo():
    from core.oportunidades import evaluar_empresa
    base = {"nombre": "X", "ruc": "1", "ct_iva_ref": 200000.0, "ct_ir_ref": 0.0, "proyeccion_devolucion_ir": 0.0}
    sin = {o.servicio_id for o in evaluar_empresa({**base, "servicios": []})}
    assert "devolucion_iva" in sin
    activo = [{"servicio": "Devoluciones", "estado": "Activo", "fecha": "2026-01-01"}]
    assert "devolucion_iva" not in {o.servicio_id for o in evaluar_empresa({**base, "servicios": activo})}
    gestion = [{"servicio": "Devoluciones", "estado": "En gestión comercial", "fecha": "2026-01-01"}]
    assert "devolucion_iva" not in {o.servicio_id for o in evaluar_empresa({**base, "servicios": gestion})}
    inactivo = [{"servicio": "Devoluciones", "estado": "Inactivo", "fecha": "2024-05-01"}]
    op = next(o for o in evaluar_empresa({**base, "servicios": inactivo}) if o.servicio_id == "devolucion_iva")
    assert any("inactivo desde 2024-05-01" in m for m in op.motivos)


def _base_ficticia(ruta):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.append(["Cliente", "RUC", "ESTADO RUC", "Grupo", "Nombres y Apellidos", "Cargo (administradores actuales)",
               "Nombres y Apellidos (accionistas)", "Cargo (accionistas)", "Referidor", "Ciudad",
               "ACTIVIDAD ECONOMICA PRINCIPAL", "Sector ", "Tipo de Actividad", "CRÉDITO TRIBUTARIO (IVA)\n2025",
               "CRÉDITO TRIBUTARIO (IR)\n2025", "IMP CAUSADO \n2025", "PROYECCION IR\n2025", "ISD 2025", "ISD 2026",
               "DEUDORES COMERCIALES Y OTRAS CUENTAS POR COBRAR NO RELACIONADOS", "GASTO DETERIORO",
               "SUELDOS Y BENEFICIOS SOCIALES", "SUELDOS, SALARIOS Y DEMÁS REMUNERACIONES",
               "ESTIMACION DE SUELDOS Y SALARIOS", "N° \nTrabajadores", "Estado  CENSUS", "Servicio", "Estado",
               "Última fecha", "OPORTUNIDADES", "OBSERVACIÓN COMERCIAL", "FECHA OBSERVACIÓN"])
    ws.append([None] * 32)
    ws.append(["DEMO HOTEL S.A.", "0990000003001", "ACTIVO", "NO", "PEREZ JUAN", "GERENTE GENERAL (RL)",
               "PEREZ JUAN\nINVERSIONES DEMO S.A.", "ACCIONISTA NACIONAL\nACCIONISTA NACIONAL", "", "Guayaquil",
               "ACTIVIDADES DE ALOJAMIENTO", "Hotelero", "Servicios", 250000, 0, 0, 0, 150000, 0, 1500000, 0, 0,
               0, 0, 150, "Activo", "", "", "", "", "", ""])
    s = wb.create_sheet("servicios")
    s.append(["Cliente", "RUC", "Servicio", "Estado", "Última fecha", "Fuentes", "Detalle"])
    s.append(["DEMO HOTEL S.A.", "0990000003001", "Devoluciones", "Activo", "2026-05-01", "Facturación", ""])
    s.append(["DEMO HOTEL S.A.", "0990000003001", "Cobranzas", "Inactivo", "2023-02-01", "Facturación", ""])
    wb.save(ruta)


def test_base_comercial_y_criterios(tmp_path):
    from core.base_clientes import cargar_base
    from core.oportunidades import evaluar_empresa
    ruta = tmp_path / "base.xlsx"
    _base_ficticia(ruta)
    b = cargar_base(ruta)
    c = b.por_ruc("0990000003001")
    assert c["sector"] == "Hotelero" and c["accionistas_pn"] == 1 and len(c["servicios"]) == 2
    ids = {o.servicio_id for o in evaluar_empresa(c)}
    assert "devolucion_iva" not in ids           # Devoluciones activo → excluida
    assert {"cobranza_extrajudicial", "planificacion_isd", "consultoria_laboral",
            "exoneracion_ir", "proteccion_patrimonial"} <= ids
    assert b.buscar("demo hotel")[0]["ruc"] == "0990000003001"


def test_cargo_gerente_siempre_gerente_general():
    from core.contratos import normalizar_cargo
    assert normalizar_cargo("Gerente") == "Gerente General"
    assert normalizar_cargo("GERENTE (RL)") == "Gerente General"
    assert normalizar_cargo("PRESIDENTE (ADM)") == "Presidente"
    assert normalizar_cargo("Gerente General") == "Gerente General"
    c = armar_contrato("devolucion_iva", {**CLIENTE, "cargo": "Gerente"}, {"periodo": "diciembre 2026"}, date(2026, 11, 9))
    assert "por intermedio de su Gerente General," in c.clausulas[0].parrafos[0]


def test_presentacion_cobranza(tmp_path):
    from core.presentacion_cobranzas import PLANTILLA, generar_presentacion
    if not PLANTILLA.exists():
        pytest.skip("La presentación de Census Cobranzas es privada (privado/plantillas/presentacion_cobranzas.pdf)")
    import pymupdf
    ruta = generar_presentacion("EMPRESA DEMO S.A.", "financiera", tmp_path)
    texto = "".join(p.get_text() for p in pymupdf.open(str(ruta))).replace("\xa0", " ")   # la Arial embebida mapea el espacio a NBSP
    assert "EMPRESA DEMO S.A." in texto and "Etatex" not in texto and "cooperativa" not in texto

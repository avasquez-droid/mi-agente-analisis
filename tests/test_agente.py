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
    assert m["isd_ref"] == 64000.0
    assert m["reg70_total"] == 310000.0
    assert m["proyeccion_devolucion_ir"] == 18500.0
    assert m["juicios_cobro_actor"] == 1


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

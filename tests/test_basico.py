import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from core.agent import ejecutar, explorar, listar_skills  # noqa: E402
from core.analyzer import analizar  # noqa: E402
from core.excel_reader import cargar_archivo, encontrar_columna  # noqa: E402
from core.metodologia import cargar_metodologia  # noqa: E402

EJEMPLO = RAIZ / "examples" / "datos_equipo.xlsx"


def test_listar_skills():
    assert "evaluacion-desempeno" in listar_skills()


def test_metodologia_pesos_normalizados():
    met = cargar_metodologia("evaluacion-desempeno")
    assert abs(sum(c.peso for c in met.criterios) - 1) < 1e-9
    assert met.bandas[0].nombre == "Sobresaliente"
    assert met.banda_para(90).nombre == "Sobresaliente"
    assert met.banda_para(10).nombre == "Requiere atención"


def test_encontrar_columna_ignora_acentos():
    df = pd.DataFrame({"Comunicacion": [1], "ÁREA": ["x"]})
    assert encontrar_columna(df, ["Comunicación"]) == "Comunicacion"
    assert encontrar_columna(df, ["Área"]) == "ÁREA"
    assert encontrar_columna(df, ["Inexistente"]) is None


def test_analisis_ejemplo():
    df = cargar_archivo(EJEMPLO)
    met = cargar_metodologia("evaluacion-desempeno")
    res = analizar(df, met)
    assert len(res.individuos) == 18
    assert res.individuos["Puntaje"].between(0, 100).all()
    assert set(res.individuos["Banda"]) <= {b.nombre for b in met.bandas}
    assert res.por_grupo is not None and "Ventas" in res.por_grupo.index
    assert not res.criterios_faltantes


def test_criterio_faltante_redistribuye():
    df = cargar_archivo(EJEMPLO).drop(columns=["Comunicación"])
    res = analizar(df, cargar_metodologia("evaluacion-desempeno"))
    assert res.criterios_faltantes == ["Comunicación"]
    assert any("redistribuyen" in a for a in res.advertencias)


def test_escala_0_100_detectada():
    df = cargar_archivo(EJEMPLO)
    for c in ["Productividad", "Calidad", "Puntualidad", "Trabajo en equipo", "Comunicación"]:
        df[c] = df[c] * 20
    res = analizar(df, cargar_metodologia("evaluacion-desempeno"))
    assert res.individuos["Puntaje"].max() <= 100
    assert any("escala" in a.lower() for a in res.advertencias)


def test_sin_criterios_lanza_error():
    df = pd.DataFrame({"Nombre": ["a"], "Otra": [1]})
    with pytest.raises(ValueError):
        analizar(df, cargar_metodologia("evaluacion-desempeno"))


def test_ejecutar_genera_archivos(tmp_path):
    r = ejecutar(EJEMPLO, formatos=["pdf", "xlsx", "docx", "md"], carpeta_salida=tmp_path)
    assert set(r.archivos) == {"pdf", "xlsx", "docx", "md"}
    for ruta in r.archivos.values():
        assert ruta.exists() and ruta.stat().st_size > 0
    assert "Plan de acción" in r.resumen_texto()
    hojas = pd.ExcelFile(r.archivos["xlsx"]).sheet_names
    assert {"Resumen", "Individuos", "Plan de acción"} <= set(hojas)


def test_explorar():
    perfil = explorar(EJEMPLO)
    assert perfil["filas"] == 18
    assert "Productividad" in perfil["columnas_numericas"]


def test_cli(tmp_path):
    out = subprocess.run(
        [sys.executable, "-m", "core.cli", "analizar", str(EJEMPLO), "--formatos", "md",
         "--salida", str(tmp_path)],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    assert "Puntaje global" in out.stdout
    out = subprocess.run([sys.executable, "-m", "core.cli", "explorar", str(EJEMPLO)],
                         cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    assert json.loads(out.stdout)["columnas"] >= 7

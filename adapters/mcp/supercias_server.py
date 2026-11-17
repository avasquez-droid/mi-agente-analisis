"""Servidor MCP local: consulta en tiempo real a la Superintendencia de Compañías.

Se instala en la app de escritorio de Claude (ver adapters/mcp/README.md) y corre en el PC del
usuario, por lo que sale a internet desde su red. Expone una sola herramienta, `consultar_supercias`,
que devuelve los datos del cliente listos para propuestas, contratos y acuerdos de confidencialidad.

Prueba manual:  python adapters/mcp/supercias_server.py   (queda esperando por stdio; Ctrl+C para salir)
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

try:                                    # SDK mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Servidor
except ImportError:                     # SDK mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Servidor

from core.supercias import SuperciasError, VariasCoincidencias, a_cliente, consultar, participaciones  # noqa: E402

servidor = _Servidor(
    "supercias-census",
    instructions=("Consulta pública de compañías en la Superintendencia de Compañías del Ecuador. Úsala para "
                  "obtener RUC, domicilio, correos y representante legal vigente antes de elaborar una "
                  "propuesta, contrato o acuerdo de confidencialidad."))


@servidor.tool()
def consultar_supercias(consulta: str) -> dict:
    """Consulta en tiempo real el portal de la Superintendencia de Compañías del Ecuador.

    Devuelve la ficha de la compañía (razón social, RUC, expediente, situación legal, provincia, cantón,
    ciudad, dirección, correos, teléfonos, objeto social, CIIU, capital) y sus administradores actuales
    (nombre, identificación, cargo, RL/ADM, nombramiento).

    Args:
        consulta: RUC (13 dígitos, preferido), número de expediente o nombre de la compañía.

    Returns:
        estado "ok": `cliente` (datos listos para el YAML de --cliente; `representante`, `cargo` y `cedula`
            son del representante legal elegido), `avisos` (leerlos al usuario: tratamiento por confirmar,
            nombramiento vencido, situación no ACTIVA) e `informacion_general` (todos los campos del portal).
        estado "varias_coincidencias": `candidatos` con ruc y nombre; pedir al usuario que elija y volver a
            consultar con el RUC.
        estado "error": `mensaje` (sin conexión, compañía inexistente o cambio del portal).
    """
    try:
        ficha = consultar(consulta)
    except VariasCoincidencias as e:
        return {"estado": "varias_coincidencias", "mensaje": str(e),
                "candidatos": [{"ruc": c.ruc, "expediente": c.expediente, "nombre": c.nombre} for c in e.candidatos]}
    except SuperciasError as e:
        return {"estado": "error", "mensaje": str(e)}
    cliente, avisos = a_cliente(ficha)
    return {"estado": "ok", "cliente": cliente, "avisos": avisos,
            "informacion_general": {k: v for k, v in ficha.general.items() if v}}



@servidor.tool()
def consultar_accionistas(consulta: str) -> dict:
    """Accionistas actuales de una compañía en la Superintendencia de Compañías del Ecuador (tiempo real).

    Úsala cuando pregunten por accionistas, socios o dueños de una compañía.

    Args:
        consulta: RUC (13 dígitos, preferido), número de expediente o nombre de la compañía.

    Returns:
        estado "ok": `compania`, `ruc`, `capital_suscrito` y `accionistas` (identificación, nombre, nacionalidad,
            tipo de inversión, capital en USD, porcentaje del capital, restricción y si es persona natural),
            ordenados de mayor a menor participación. Los accionistas con RUC de 13 dígitos son sociedades y
            pueden consultarse a su vez. Son datos personales: no los copies fuera del entregable.
        estado "varias_coincidencias": `candidatos`; pedir el RUC y volver a consultar.
        estado "error": `mensaje`.
    """
    try:
        ficha = consultar(consulta, con_administradores=False, con_accionistas=True)
    except VariasCoincidencias as e:
        return {"estado": "varias_coincidencias", "mensaje": str(e),
                "candidatos": [{"ruc": c.ruc, "expediente": c.expediente, "nombre": c.nombre} for c in e.candidatos]}
    except SuperciasError as e:
        return {"estado": "error", "mensaje": str(e)}
    g = ficha.general
    return {"estado": "ok", "compania": g.get("Nombre"), "ruc": g.get("R.U.C."),
            "capital_suscrito": g.get("Capital suscrito"), "avisos": ficha.avisos,
            "accionistas": [{"identificacion": a.identificacion, "nombre": a.nombre, "nacionalidad": a.nacionalidad,
                             "tipo_inversion": a.tipo_inversion, "capital_usd": a.capital_usd,
                             "porcentaje": round(p, 4), "restriccion": a.restriccion,
                             "persona_natural": a.persona_natural} for a, p in participaciones(ficha.accionistas)]}

if __name__ == "__main__":
    servidor.run()

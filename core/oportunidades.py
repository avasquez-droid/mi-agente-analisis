"""Cruce del informe de investigación con la cartera: servicios posibles, viabilidad y honorarios."""
from __future__ import annotations

import ast
import operator
import re
import unicodedata
from dataclasses import dataclass, field

from . import conocimiento as kb
from .informe_reader import InformeGrupo, metricas as metricas_empresa


# ----------------------------------------------------------- expresiones seguras
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.USub: operator.neg}
_FUNCS = {"max": max, "min": min, "abs": abs}


def evaluar_expresion(expr, datos: dict) -> float | None:
    """Evalúa expresiones simples como 'isd_ref * 1.0' o 'max(ct_ir_ref - ir_causado, 0)'."""
    if expr is None:
        return None
    if isinstance(expr, (int, float)):
        return float(expr)

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            v = datos.get(n.id)
            if v is None:
                raise KeyError(n.id)
            return float(v)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"Expresión no permitida: {expr}")

    return float(ev(ast.parse(str(expr), mode="eval")))


def _sin_acentos(t: str) -> str:
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().upper()


def cumple(cond: dict, datos: dict) -> bool:
    campo, op, valor = cond["campo"], cond["op"], cond.get("valor")
    actual = datos.get(campo)
    if op == "contiene":
        patron = "|".join(re.escape(_sin_acentos(p)) for p in str(valor).split("|"))
        return bool(re.search(patron, _sin_acentos(actual or "")))
    if actual is None:
        return False
    comparar = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
                "==": operator.eq, "!=": operator.ne}[op]
    return comparar(actual, valor)


# ----------------------------------------------------------- honorarios
def estimar_honorario(servicio_id: str, base: float | None) -> dict:
    """Devuelve {'texto', 'monto', 'porcentaje'} según el modelo del tarifario."""
    t = kb.tarifario().get(servicio_id, {})
    modelo = t.get("modelo")
    r = {"modelo": modelo, "porcentaje": None, "monto": None, "texto": "PENDIENTE en tarifario"}
    if modelo in {"porcentaje", "etapas"} and t.get("valor") is not None:
        r["porcentaje"] = float(t["valor"])
        r["texto"] = f"{t['valor']:g} % + IVA sobre lo recuperado/ahorrado"
        if t.get("anticipo_usd"):
            r["texto"] += f" (anticipo USD {t['anticipo_usd']:,.2f})"
    elif modelo == "escalonado":
        tramos = t.get("tramos", [])
        r["porcentaje"] = float(tramos[0]["valor"]) if tramos else None
        r["texto"] = " / ".join(
            f"{x['valor']:g} %" + (f" si se acredita en ≤{x['hasta_meses']} meses" if "hasta_meses" in x
                                    else f" después de {x['desde_meses']} meses")
            for x in tramos) + " + IVA"
    elif modelo == "por_via":
        r["porcentaje"] = float(t["administrativo"])
        r["texto"] = f"{t['administrativo']:g} % vía administrativa / {t['judicial']:g} % vía judicial + IVA"
    elif modelo == "fijo" and t.get("valor") is not None:
        r["monto"] = float(t["valor"])
        r["texto"] = f"USD {t['valor']:,.2f} + IVA ({t.get('anticipo_pct', 50)} % de anticipo)"
    elif modelo == "fijo_mas_exito":
        if t.get("valor") is not None:
            r["monto"] = float(t["valor"])
            r["texto"] = f"USD {t['valor']:,.2f} fijo + {t.get('exito_pct', 0):g} % del ahorro + IVA"
        else:
            r["porcentaje"] = float(t.get("fijo_pct_cuantia", 0))
            r["texto"] = f"{t.get('fijo_pct_cuantia', 0):g} % de la cuantía + {t.get('exito_pct', 0):g} % de éxito + IVA"
    elif modelo == "por_etapa":
        etapas = t.get("etapas", [])
        r["porcentaje"] = float(etapas[0]["valor"]) if etapas else None
        r["texto"] = " / ".join(f"{e['valor']:g} % {e['etapa'].split(' (')[0].lower()}" for e in etapas) + " + IVA"
    elif modelo == "mensual" and t.get("valor") is not None:
        r["monto"] = float(t["valor"])
        r["texto"] = f"USD {t['valor']:,.2f} mensuales + IVA"
    if r["porcentaje"] is not None and base:
        r["monto"] = round(base * r["porcentaje"] / 100, 2)
    return r


# ----------------------------------------------------------- oportunidades
@dataclass
class Oportunidad:
    servicio_id: str
    grupo: str              # servicios del mismo grupo son alternativos (p. ej. cobranza ext./judicial)
    servicio: str
    materia: str
    empresa: str
    ruc: str
    tipo_empresa: str
    base: float | None
    honorario: dict
    prioridad: str
    motivos: list[str] = field(default_factory=list)
    requiere_dato: str | None = None
    tiene_contrato_tipo: bool = False


def _motivo(cond: dict, datos: dict) -> str:
    v = datos.get(cond["campo"])
    if isinstance(v, bool):
        return f"{cond['campo']} = {'sí' if v else 'no'}"
    if isinstance(v, (int, float)):
        if 0 < abs(v) < 1:
            fmt = f"{v:.0%}"
        elif float(v).is_integer() and abs(v) < 1000:
            fmt = f"{int(v)}"
        else:
            fmt = f"{v:,.2f}"
        return f"{cond['campo']} = {fmt} ({cond['op']} {cond['valor']})"
    return f"{cond['campo']} {cond['op']} '{cond['valor']}'"


def evaluar_empresa(datos: dict) -> list[Oportunidad]:
    salida = []
    for sid, srv in kb.servicios().items():
        regla = kb.metricas().get(srv.get("metricas"))
        if not regla:
            continue
        resultados = [(c, cumple(c, datos)) for c in regla.get("condiciones", [])]
        ok = [c for c, r in resultados if r]
        aplica = (all(r for _, r in resultados) if regla.get("modo", "todas") == "todas"
                  else bool(ok))
        if not aplica:
            continue
        try:
            base = evaluar_expresion(regla.get("base"), datos)
        except KeyError:
            base = None
        umbral = regla.get("prioridad_alta_desde")
        if base and umbral and base >= umbral:
            prioridad = "Alta"
        elif regla.get("requiere_dato"):
            prioridad = "Por confirmar"
        else:
            prioridad = "Media"
        salida.append(Oportunidad(
            servicio_id=sid, grupo=srv.get("metricas", sid), servicio=srv["nombre"], materia=srv["materia"],
            empresa=datos["nombre"], ruc=datos["ruc"], tipo_empresa=datos.get("tipo", ""),
            base=base, honorario=estimar_honorario(sid, base), prioridad=prioridad,
            motivos=[_motivo(c, datos) for c in ok],
            requiere_dato=regla.get("requiere_dato"),
            tiene_contrato_tipo=bool(srv.get("clausulas")),
        ))
    orden = {"Alta": 0, "Media": 1, "Por confirmar": 2}
    salida.sort(key=lambda o: (orden[o.prioridad], -(o.honorario.get("monto") or 0)))
    return salida


def analizar_grupo(inf: InformeGrupo) -> dict:
    """Devuelve {'metricas': {ruc: dict}, 'oportunidades': [Oportunidad]} de todo el grupo."""
    mets, ops = {}, []
    for e in inf.empresas:
        d = metricas_empresa(e, inf.anio_ref)
        mets[e.ruc] = d
        ops.extend(evaluar_empresa(d))
    orden = {"Alta": 0, "Media": 1, "Por confirmar": 2}
    ops.sort(key=lambda o: (orden[o.prioridad], -(o.honorario.get("monto") or 0)))
    return {"metricas": mets, "oportunidades": ops}


def honorario_potencial(ops: list[Oportunidad]) -> float:
    """Suma de honorarios estimados sin fees mensuales y sin duplicar servicios alternativos
    (de cada grupo alternativo por empresa se toma el mayor)."""
    mejor: dict[tuple, float] = {}
    for o in ops:
        if o.honorario.get("modelo") == "mensual" or not o.honorario.get("monto"):
            continue
        clave = (o.ruc, o.grupo)
        mejor[clave] = max(mejor.get(clave, 0.0), o.honorario["monto"])
    return round(sum(mejor.values()), 2)

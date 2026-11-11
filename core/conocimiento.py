"""Carga de la base de conocimiento comercial (carpeta conocimiento/)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "conocimiento"


def plantilla(nombre: str) -> Path:
    """Plantilla visual: la de privado/plantillas/ si existe (versión local), si no la del repositorio
    (plantillas/census/), que no contiene datos de clientes."""
    local = RAIZ / "privado" / "plantillas" / nombre
    return local if local.exists() else RAIZ / "plantillas" / "census" / nombre


def _yaml(ruta: Path) -> dict:
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=None)
def servicios() -> dict:
    return _yaml(CARPETA / "servicios.yaml")


@lru_cache(maxsize=None)
def metricas() -> dict:
    return _yaml(CARPETA / "metricas.yaml")


@lru_cache(maxsize=None)
def tarifario() -> dict:
    return _yaml(CARPETA / "tarifario.yaml")


def _fusionar(base: dict, extra: dict) -> dict:
    salida = dict(base)
    for k, v in (extra or {}).items():
        salida[k] = _fusionar(salida[k], v) if isinstance(v, dict) and isinstance(salida.get(k), dict) else v
    return salida


@lru_cache(maxsize=None)
def entidades() -> dict:
    """Entidades Census. Los datos personales (p. ej. cédula del representante) no van al repo
    público: se agregan en privado/entidades_local.yaml, que se fusiona encima si existe."""
    base = _yaml(CARPETA / "entidades.yaml")
    local = RAIZ / "privado" / "entidades_local.yaml"
    return _fusionar(base, _yaml(local)) if local.exists() else base


@lru_cache(maxsize=None)
def documento(doc_id: str) -> dict:
    ruta = CARPETA / "documentos" / f"{doc_id}.yaml"
    if not ruta.exists():
        disponibles = ", ".join(p.stem for p in (CARPETA / "documentos").glob("*.yaml"))
        raise KeyError(f"Documento '{doc_id}' no existe. Disponibles: {disponibles}")
    return _yaml(ruta)


@lru_cache(maxsize=None)
def clausulas_comunes() -> dict:
    return _yaml(CARPETA / "clausulas" / "comunes.yaml")


def clausulas_servicio(servicio_id: str) -> dict:
    archivo = servicios()[servicio_id].get("clausulas")
    if not archivo:
        raise ValueError(
            f"El servicio '{servicio_id}' aún no tiene contrato tipo "
            "(campo 'clausulas' en conocimiento/servicios.yaml)."
        )
    return _yaml(CARPETA / "clausulas" / "servicios" / archivo)


def servicio(servicio_id: str) -> dict:
    cat = servicios()
    if servicio_id not in cat:
        raise KeyError(f"Servicio '{servicio_id}' no existe. Disponibles: {', '.join(cat)}")
    return cat[servicio_id]


def recargar() -> None:
    for f in (servicios, metricas, tarifario, entidades, clausulas_comunes, documento):
        f.cache_clear()

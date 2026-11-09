"""Carga de la base de conocimiento comercial (carpeta conocimiento/)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "conocimiento"


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


@lru_cache(maxsize=None)
def entidades() -> dict:
    return _yaml(CARPETA / "entidades.yaml")


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
    for f in (servicios, metricas, tarifario, entidades, clausulas_comunes):
        f.cache_clear()

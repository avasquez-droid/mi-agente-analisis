"""Carga de skills (metodologías) definidas en YAML dentro de la carpeta skills/."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_SKILLS = RAIZ / "skills"


@dataclass
class Criterio:
    nombre: str
    peso: float
    columnas: list[str] = field(default_factory=list)
    descripcion: str = ""


@dataclass
class Banda:
    nombre: str
    minimo: float
    maximo: float
    descripcion: str = ""
    acciones: list[str] = field(default_factory=list)


@dataclass
class Metodologia:
    id: str
    nombre: str
    descripcion: str
    escala_min: float
    escala_max: float
    criterios: list[Criterio]
    bandas: list[Banda]
    columna_nombre: list[str]
    columna_grupo: list[str]
    recomendaciones_por_criterio: dict[str, list[str]] = field(default_factory=dict)

    def banda_para(self, puntaje: float) -> Banda:
        for b in self.bandas:
            if b.minimo <= puntaje <= b.maximo:
                return b
        return self.bandas[-1]


def listar_skills() -> list[str]:
    """Devuelve los ids de las skills que tienen un archivo metodologia.yaml."""
    return sorted(p.parent.name for p in CARPETA_SKILLS.glob("*/metodologia.yaml"))


def cargar_metodologia(skill_id: str) -> Metodologia:
    ruta = CARPETA_SKILLS / skill_id / "metodologia.yaml"
    if not ruta.exists():
        disponibles = ", ".join(listar_skills()) or "ninguna"
        raise FileNotFoundError(
            f"La skill '{skill_id}' no tiene metodologia.yaml. Disponibles: {disponibles}"
        )
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))

    criterios = [
        Criterio(
            nombre=c["nombre"],
            peso=float(c.get("peso", 1)),
            columnas=c.get("columnas", [c["nombre"]]),
            descripcion=c.get("descripcion", ""),
        )
        for c in datos["criterios"]
    ]
    total = sum(c.peso for c in criterios)
    for c in criterios:  # normaliza los pesos para que sumen 1
        c.peso = c.peso / total

    bandas = [
        Banda(
            nombre=b["nombre"],
            minimo=float(b["min"]),
            maximo=float(b["max"]),
            descripcion=b.get("descripcion", ""),
            acciones=b.get("acciones", []),
        )
        for b in datos["bandas"]
    ]
    bandas.sort(key=lambda b: b.minimo, reverse=True)

    return Metodologia(
        id=skill_id,
        nombre=datos.get("nombre", skill_id),
        descripcion=datos.get("descripcion", ""),
        escala_min=float(datos.get("escala", {}).get("min", 1)),
        escala_max=float(datos.get("escala", {}).get("max", 5)),
        criterios=criterios,
        bandas=bandas,
        columna_nombre=datos.get("columna_nombre", ["Nombre", "Colaborador", "Empleado"]),
        columna_grupo=datos.get("columna_grupo", ["Área", "Departamento", "Equipo"]),
        recomendaciones_por_criterio=datos.get("recomendaciones_por_criterio", {}),
    )

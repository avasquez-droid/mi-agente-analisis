"""Aplicación de la metodología (skill) a los datos del Excel."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .excel_reader import encontrar_columna, perfilar
from .metodologia import Metodologia


@dataclass
class ResultadoAnalisis:
    metodologia: Metodologia
    columna_nombre: str
    columna_grupo: str | None
    mapeo_criterios: dict[str, str]          # criterio -> columna real del Excel
    criterios_faltantes: list[str]
    individuos: pd.DataFrame                 # una fila por persona con puntajes
    promedio_criterios: dict[str, float]     # promedio del equipo por criterio (0-100)
    por_grupo: pd.DataFrame | None           # promedio por área/departamento
    distribucion_bandas: dict[str, int]
    perfil: dict = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)

    @property
    def puntaje_global(self) -> float:
        return float(self.individuos["Puntaje"].mean()) if len(self.individuos) else 0.0


def _a_100(serie: pd.Series, minimo: float, maximo: float) -> pd.Series:
    """Convierte una serie en la escala de la metodología a 0-100."""
    rango = maximo - minimo
    if rango <= 0:
        return serie * 0
    return ((serie - minimo) / rango * 100).clip(0, 100)


def analizar(df: pd.DataFrame, met: Metodologia) -> ResultadoAnalisis:
    """Calcula puntajes ponderados, bandas y agregados por grupo."""
    advertencias: list[str] = []

    col_nombre = encontrar_columna(df, met.columna_nombre)
    if col_nombre is None:
        col_nombre = df.columns[0]
        advertencias.append(
            f"No se encontró una columna de nombre; se usa la primera columna ('{col_nombre}')."
        )
    col_grupo = encontrar_columna(df, met.columna_grupo)

    mapeo: dict[str, str] = {}
    faltantes: list[str] = []
    for crit in met.criterios:
        col = encontrar_columna(df, crit.columnas)
        if col is None or not pd.api.types.is_numeric_dtype(df[col]):
            faltantes.append(crit.nombre)
        else:
            mapeo[crit.nombre] = col
    if not mapeo:
        raise ValueError(
            "Ninguno de los criterios de la metodología coincide con columnas numéricas "
            f"del archivo. Criterios esperados: {[c.nombre for c in met.criterios]}. "
            f"Columnas del archivo: {list(df.columns)}"
        )
    if faltantes:
        advertencias.append(
            "Criterios sin columna en el archivo (se redistribuyen los pesos): "
            + ", ".join(faltantes)
        )

    criterios_activos = [c for c in met.criterios if c.nombre in mapeo]
    peso_total = sum(c.peso for c in criterios_activos)

    # Detecta si los datos vienen en una escala distinta a la de la metodología.
    maximo_datos = max(float(df[mapeo[c.nombre]].max()) for c in criterios_activos)
    esc_min, esc_max = met.escala_min, met.escala_max
    if maximo_datos > esc_max:
        esc_min, esc_max = 0.0, (10.0 if maximo_datos <= 10 else 100.0)
        advertencias.append(
            f"Los datos superan la escala {met.escala_min}-{met.escala_max}; "
            f"se asume escala 0-{esc_max:g}."
        )

    individuos = pd.DataFrame({"Nombre": df[col_nombre].astype(str)})
    if col_grupo:
        individuos["Grupo"] = df[col_grupo].astype(str)

    puntaje = pd.Series(0.0, index=df.index)
    for crit in criterios_activos:
        serie = pd.to_numeric(df[mapeo[crit.nombre]], errors="coerce")
        serie100 = _a_100(serie, esc_min, esc_max)
        individuos[crit.nombre] = serie100.round(1)
        puntaje += serie100.fillna(serie100.mean()) * (crit.peso / peso_total)

    individuos["Puntaje"] = puntaje.round(1)
    individuos["Banda"] = individuos["Puntaje"].apply(lambda p: met.banda_para(p).nombre)
    individuos["Ranking"] = individuos["Puntaje"].rank(ascending=False, method="min").astype(int)

    # Fortaleza y oportunidad de cada persona
    cols_crit = [c.nombre for c in criterios_activos]
    individuos["Fortaleza"] = individuos[cols_crit].idxmax(axis=1)
    individuos["Oportunidad"] = individuos[cols_crit].idxmin(axis=1)

    individuos = individuos.sort_values("Ranking").reset_index(drop=True)

    promedio_criterios = {c: round(float(individuos[c].mean()), 1) for c in cols_crit}

    por_grupo = None
    if col_grupo:
        por_grupo = (
            individuos.groupby("Grupo")[cols_crit + ["Puntaje"]]
            .mean()
            .round(1)
            .assign(Personas=individuos.groupby("Grupo").size())
            .sort_values("Puntaje", ascending=False)
        )

    distribucion = {b.nombre: int((individuos["Banda"] == b.nombre).sum()) for b in met.bandas}

    return ResultadoAnalisis(
        metodologia=met,
        columna_nombre=col_nombre,
        columna_grupo=col_grupo,
        mapeo_criterios=mapeo,
        criterios_faltantes=faltantes,
        individuos=individuos,
        promedio_criterios=promedio_criterios,
        por_grupo=por_grupo,
        distribucion_bandas=distribucion,
        perfil=perfilar(df),
        advertencias=advertencias,
    )

"""Generación de hallazgos (insights) y plan de acción a partir del análisis."""
from __future__ import annotations

from dataclasses import dataclass, field

from .analyzer import ResultadoAnalisis


@dataclass
class Insight:
    titulo: str
    detalle: str
    tipo: str = "info"  # fortaleza | alerta | info


@dataclass
class Accion:
    prioridad: str      # Alta | Media | Baja
    accion: str
    responsable: str
    plazo: str
    indicador: str
    dirigido_a: str = "Equipo"


@dataclass
class PlanAccion:
    objetivo: str
    acciones: list[Accion] = field(default_factory=list)


def generar_insights(res: ResultadoAnalisis) -> list[Insight]:
    met = res.metodologia
    ind = res.individuos
    insights: list[Insight] = []
    n = len(ind)

    # 1. Puntaje global
    banda_global = met.banda_para(res.puntaje_global)
    insights.append(
        Insight(
            "Desempeño global del equipo",
            f"El puntaje promedio es {res.puntaje_global:.1f}/100, nivel '{banda_global.nombre}'. "
            f"Se evaluaron {n} personas con {len(res.mapeo_criterios)} criterios.",
            "fortaleza" if res.puntaje_global >= 70 else "alerta" if res.puntaje_global < 55 else "info",
        )
    )

    # 2. Criterio más fuerte y más débil
    if res.promedio_criterios:
        mejor = max(res.promedio_criterios, key=res.promedio_criterios.get)
        peor = min(res.promedio_criterios, key=res.promedio_criterios.get)
        insights.append(
            Insight(
                f"Fortaleza principal: {mejor}",
                f"Es el criterio con mayor promedio ({res.promedio_criterios[mejor]:.1f}/100).",
                "fortaleza",
            )
        )
        insights.append(
            Insight(
                f"Área de mejora: {peor}",
                f"Es el criterio con menor promedio ({res.promedio_criterios[peor]:.1f}/100); "
                "concentrar aquí las acciones de desarrollo tendrá el mayor impacto.",
                "alerta",
            )
        )

    # 3. Distribución de bandas
    banda_baja = met.bandas[-1].nombre
    en_baja = res.distribucion_bandas.get(banda_baja, 0)
    if en_baja:
        pct = en_baja / n * 100
        nombres = ", ".join(ind.loc[ind["Banda"] == banda_baja, "Nombre"].head(5))
        insights.append(
            Insight(
                f"{en_baja} persona(s) en nivel '{banda_baja}' ({pct:.0f}%)",
                f"Requieren un plan de acompañamiento individual: {nombres}.",
                "alerta",
            )
        )
    banda_alta = met.bandas[0].nombre
    en_alta = res.distribucion_bandas.get(banda_alta, 0)
    if en_alta:
        nombres = ", ".join(ind.loc[ind["Banda"] == banda_alta, "Nombre"].head(5))
        insights.append(
            Insight(
                f"{en_alta} persona(s) en nivel '{banda_alta}'",
                f"Talento a reconocer y potenciar como referentes: {nombres}.",
                "fortaleza",
            )
        )

    # 4. Dispersión
    desv = float(ind["Puntaje"].std()) if n > 1 else 0.0
    if desv > 15:
        insights.append(
            Insight(
                "Alta dispersión en el desempeño",
                f"La desviación estándar es {desv:.1f} puntos: hay brechas grandes entre personas. "
                "Conviene estandarizar prácticas y reforzar la mentoría entre pares.",
                "alerta",
            )
        )
    elif n > 1:
        insights.append(
            Insight(
                "Desempeño homogéneo",
                f"La desviación estándar es {desv:.1f} puntos: el equipo tiene un nivel parejo.",
                "info",
            )
        )

    # 5. Grupos
    if res.por_grupo is not None and len(res.por_grupo) > 1:
        g = res.por_grupo["Puntaje"]
        insights.append(
            Insight(
                "Diferencias entre grupos",
                f"El grupo con mejor desempeño es '{g.idxmax()}' ({g.max():.1f}) y el de menor "
                f"es '{g.idxmin()}' ({g.min():.1f}); brecha de {g.max() - g.min():.1f} puntos.",
                "alerta" if (g.max() - g.min()) > 15 else "info",
            )
        )

    for adv in res.advertencias:
        insights.append(Insight("Advertencia sobre los datos", adv, "info"))

    return insights


def generar_plan_accion(res: ResultadoAnalisis) -> PlanAccion:
    met = res.metodologia
    ind = res.individuos
    acciones: list[Accion] = []

    # Acciones por criterio más débil del equipo
    if res.promedio_criterios:
        ordenados = sorted(res.promedio_criterios.items(), key=lambda kv: kv[1])
        for i, (crit, prom) in enumerate(ordenados[:2]):
            recomendaciones = met.recomendaciones_por_criterio.get(crit) or [
                f"Diseñar un programa de desarrollo enfocado en {crit}."
            ]
            for rec in recomendaciones[:2]:
                acciones.append(
                    Accion(
                        prioridad="Alta" if i == 0 else "Media",
                        accion=rec,
                        responsable="Líder del equipo / RR.HH.",
                        plazo="30 días" if i == 0 else "60 días",
                        indicador=f"Subir el promedio de {crit} de {prom:.0f} a {min(prom + 10, 100):.0f}",
                        dirigido_a="Equipo",
                    )
                )

    # Acciones por banda
    for banda in met.bandas:
        personas = ind.loc[ind["Banda"] == banda.nombre, "Nombre"].tolist()
        if not personas:
            continue
        for acc in banda.acciones[:2]:
            acciones.append(
                Accion(
                    prioridad="Alta" if banda is met.bandas[-1] else "Media" if banda is met.bandas[0] else "Baja",
                    accion=acc,
                    responsable="Líder directo",
                    plazo="30 días" if banda is met.bandas[-1] else "90 días",
                    indicador=f"Seguimiento trimestral del puntaje de las personas en '{banda.nombre}'",
                    dirigido_a=", ".join(personas[:6]) + (" y otros" if len(personas) > 6 else ""),
                )
            )

    # Acción transversal
    acciones.append(
        Accion(
            prioridad="Baja",
            accion="Repetir la evaluación con la misma metodología para medir la evolución.",
            responsable="RR.HH.",
            plazo="90 días",
            indicador="Comparativo de puntaje global entre periodos",
            dirigido_a="Equipo",
        )
    )

    orden = {"Alta": 0, "Media": 1, "Baja": 2}
    acciones.sort(key=lambda a: orden[a.prioridad])
    objetivo = (
        f"Elevar el puntaje global del equipo de {res.puntaje_global:.1f} a "
        f"{min(res.puntaje_global + 10, 100):.0f} puntos en el próximo periodo, "
        "cerrando las brechas en los criterios de menor desempeño."
    )
    return PlanAccion(objetivo=objetivo, acciones=acciones)

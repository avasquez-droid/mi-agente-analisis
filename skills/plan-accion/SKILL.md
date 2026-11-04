---
name: plan-accion
description: Convierte hallazgos en un plan de acción accionable (prioridad, acción, responsable, plazo, indicador). Úsala cuando el usuario pida "qué hacemos con esto", "plan de mejora", "próximos pasos" o "recomendaciones".
---

# Skill: Plan de acción

## Principios
- Cada acción responde a un hallazgo concreto; no hay acciones genéricas sin evidencia.
- Toda acción tiene: **prioridad** (Alta/Media/Baja), **responsable**, **plazo** y **indicador medible**.
- Máximo 8-10 acciones; es mejor pocas acciones que se cumplan que una lista larga.
- Prioridad Alta = impacto alto y urgencia (personas en banda baja, criterio más débil).

## Procedimiento (lo implementa `core/insights.py:generar_plan_accion`)
1. Tomar los dos criterios con menor promedio y proponer las recomendaciones definidas en
   `metodologia.yaml` → `recomendaciones_por_criterio`.
2. Para cada banda con personas, añadir las acciones de `bandas[].acciones`.
3. Añadir una acción de seguimiento: repetir la medición en 90 días.
4. Ordenar por prioridad y fijar un objetivo cuantificado (+10 puntos en el puntaje global).

## Cuando el usuario quiere ajustar el plan
- "Añade una acción para X" → agregarla en `recomendaciones_por_criterio` del YAML y re-ejecutar,
  o editar directamente el DOCX generado.
- "Cambia los plazos" → modificar los plazos en `core/insights.py` o en el documento.

## Formato de salida en el chat
Tabla Markdown con columnas Prioridad | Acción | Dirigido a | Plazo, seguida del objetivo.

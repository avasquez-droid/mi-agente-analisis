# Prompts y casos de uso

## Caso 1 — Informe completo de desempeño
> Carga `examples/datos_equipo.xlsx` y genera un informe de desempeño, extrae insights y un plan de acción.

Resultado: PDF (informe), XLSX (análisis), DOCX (plan de acción) y MD (resumen) en `salidas/`.

## Caso 2 — Solo el plan de acción en Word
> Analiza `datos_equipo.xlsx` con la skill de desempeño y dame únicamente el plan de acción en Word.

Comando equivalente: `python -m core.cli analizar examples/datos_equipo.xlsx --formatos docx`

## Caso 3 — Explorar un archivo desconocido
> ¿Qué contiene este archivo? Dame un resumen de las columnas y problemas de calidad.

Comando: `python -m core.cli explorar <archivo>` (skill `analisis-datos`).

## Caso 4 — Cambiar la metodología
> Quiero que Calidad pese 40 % y que el nivel "Sobresaliente" empiece en 90.

El agente edita `skills/evaluacion-desempeno/metodologia.yaml` (pesos y bandas) y vuelve a ejecutar.

## Caso 5 — Columnas con otros nombres
> Mi Excel tiene "Cumplimiento" en vez de "Productividad".

El agente añade `Cumplimiento` a la lista `columnas:` del criterio Productividad en el YAML.

## Caso 6 — Nueva metodología
> Crea una skill para evaluar proveedores con criterios Precio, Plazo de entrega y Calidad.

El agente crea `skills/evaluacion-proveedores/` siguiendo `docs/crear-skills.md`.

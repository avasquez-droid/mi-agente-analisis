# Ejemplos — evaluacion-desempeno

## Prompt
> Carga `examples/datos_equipo.xlsx` y genera un informe de desempeño, extrae insights y un plan de acción.

## Lo que hace el agente
1. Ejecuta `python -m core.cli analizar examples/datos_equipo.xlsx`.
2. Muestra el resumen Markdown en el chat.
3. Indica los archivos en `salidas/` (PDF, XLSX, DOCX, MD).

## Variantes
- "Solo quiero el PDF" → `--formatos pdf`
- "Usa la hoja 'Q3'" → `--hoja Q3`
- "Dale más peso a la calidad" → editar `metodologia.yaml` (peso de Calidad) y volver a ejecutar.

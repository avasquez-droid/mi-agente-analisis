# Guía de uso

## Flujo típico
1. Guarda tu Excel en cualquier carpeta (por ejemplo `examples/` o `datos/`).
2. Pide al agente lo que necesitas, o ejecuta el comando directamente.
3. Revisa el resumen en pantalla y abre los archivos de `salidas/`.

## Con el agente (Claude o GPT)
Ejemplos de peticiones:
- "Genera un informe de desempeño de `datos/equipo_q3.xlsx` con plan de acción."
- "Solo quiero el Excel de análisis."
- "¿Qué columnas tiene este archivo y cuántos nulos hay?"
- "Dale más peso a Calidad y vuelve a generar el informe."
- "Crea una skill para evaluar proveedores con Precio, Plazo y Calidad."

El agente ejecutará `python -m core.cli ...`, mostrará el resumen y las rutas de los archivos.

## Por línea de comandos
```bash
python -m core.cli analizar datos/equipo_q3.xlsx            # todo (pdf,xlsx,docx,md)
python -m core.cli analizar datos/equipo_q3.xlsx --formatos pdf
python -m core.cli analizar datos/equipo_q3.xlsx --hoja 2    # tercera hoja (índice 0)
python -m core.cli explorar datos/ventas.csv
```

## Entregables
| Archivo | Contenido |
|---|---|
| `*_informe.pdf` | Informe formal: resumen ejecutivo, criterios, grupos, hallazgos, plan, detalle. |
| `*_analisis.xlsx` | Hojas Resumen, Criterios, Por grupo, Individuos (escala de color), Hallazgos, Plan. |
| `*_plan_accion.docx` | Plan editable para compartir con líderes. |
| `*_resumen.md` | Texto para pegar en correo, Slack o una wiki. |

## Interpretar los resultados
- **Puntaje (0-100)**: promedio ponderado de los criterios normalizados.
- **Banda**: Sobresaliente ≥ 85 · Competente 70-84 · En desarrollo 55-69 · Requiere atención < 55.
- **Fortaleza / Oportunidad**: criterio más alto y más bajo de cada persona.
- **Hallazgos**: verde = fortaleza, rojo = alerta, azul = información.

## Ajustar la metodología
Edita `skills/evaluacion-desempeno/metodologia.yaml`:
- `peso` de cada criterio (se normalizan automáticamente).
- `columnas`: sinónimos para reconocer tus encabezados.
- `bandas`: límites, descripciones y acciones sugeridas.
- `recomendaciones_por_criterio`: acciones del plan por criterio.
Vuelve a ejecutar el comando; no hace falta tocar el código.

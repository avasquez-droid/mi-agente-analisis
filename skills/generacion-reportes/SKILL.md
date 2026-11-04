---
name: generacion-reportes
description: Reglas y formatos para producir los entregables (PDF, Excel, Word, Markdown). Úsala cuando el usuario pida "genera el informe", "expórtalo a Word/PDF/Excel" o quiera cambiar el formato o el estilo de un reporte.
---

# Skill: Generación de reportes

## Entregables estándar
| Formato | Módulo | Contenido |
|---|---|---|
| PDF | `core/report_pdf.py` | Resumen ejecutivo, criterios, grupos, hallazgos, plan, detalle individual. |
| XLSX | `core/report_excel.py` | Hojas: Resumen, Criterios, Por grupo, Individuos (con escala de color), Hallazgos, Plan de acción. |
| DOCX | `core/report_word.py` | Plan de acción editable: contexto, hallazgos, objetivo, acciones, acompañamiento, seguimiento. |
| MD | `templates/resumen_chat.md.j2` | Resumen para el chat y para pegar en correos o wikis. |

## Cómo generar
```bash
python -m core.cli analizar <archivo> --formatos pdf,xlsx,docx,md --titulo "Informe Q3"
```

## Estructura obligatoria de todo informe
1. Título, metodología, fecha y tamaño de la muestra.
2. Resumen ejecutivo con el resultado global en una frase.
3. Tablas de resultados (criterios, grupos).
4. Hallazgos ordenados: fortalezas, alertas, información.
5. Plan de acción con prioridad, acción, responsable, plazo e indicador.
6. Detalle individual al final (nunca al inicio).

## Estilo
- Español neutro, frases cortas, sin jerga técnica innecesaria.
- Color institucional azul `#1F3A5F`; verde para fortalezas, rojo para alertas.
- Los nombres de archivo llevan el nombre del archivo origen, la skill y la fecha.

## Personalización
- Cambiar logotipo, colores o secciones: editar el módulo `core/report_*.py` correspondiente.
- Cambiar el texto del resumen: editar la plantilla Jinja2 en `templates/`.

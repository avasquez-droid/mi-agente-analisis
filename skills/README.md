# Skills (metodologías reutilizables)

Cada skill es una carpeta con:

| Archivo | Para qué sirve |
|---|---|
| `SKILL.md` | Instrucciones en lenguaje natural para el agente (Claude o GPT): cuándo usarla, cómo interpretar los datos, qué entregar. |
| `metodologia.yaml` | (Opcional) Parámetros que el código lee: criterios, pesos, escala, bandas y recomendaciones. |
| `ejemplos.md` | (Opcional) Ejemplos de prompts y resultados esperados. |

Skills incluidas:

- `evaluacion-desempeno` — evalúa colaboradores con criterios ponderados y bandas de nivel.
- `analisis-datos` — exploración general de cualquier Excel (perfil, estadísticas, categorías).
- `generacion-reportes` — reglas para construir PDF, Excel y Word consistentes.
- `plan-accion` — cómo convertir hallazgos en acciones con responsable, plazo e indicador.

Para crear una nueva skill vea `docs/crear-skills.md`.

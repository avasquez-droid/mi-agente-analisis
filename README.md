# 🤖 Mi Agente de Análisis Inteligente

Una herramienta única, reutilizable y compatible con **Claude** (Claude Code, VS Code) y **GPT**
(Codex, ChatGPT). Procesa archivos Excel, aplica una metodología definida en *skills* y genera
informes en **PDF**, análisis en **Excel** y planes de acción en **Word**.

```
Usuario (Excel) ──▶ Agente (Claude o GPT) ──▶ core/ aplica la skill ──▶ PDF · XLSX · DOCX · MD
```

## Inicio rápido

```bash
git clone <url-del-repositorio> mi-agente-analisis
cd mi-agente-analisis
pip install -r requirements.txt
python -m core.cli analizar examples/datos_equipo.xlsx
```

Los resultados quedan en `salidas/`. Luego abre el proyecto con tu agente favorito:

| Entorno | Qué hacer |
|---|---|
| **Claude Code** | `claude` en la carpeta del proyecto. Lee `CLAUDE.md` y las skills en `.claude/skills/`. |
| **Codex (GPT)** | `codex` en la carpeta del proyecto. Lee `AGENTS.md`. |
| **ChatGPT / Claude web** | Pega las instrucciones del adaptador y sube las skills (ver `adapters/`). |

Y pide, por ejemplo:

> "Carga un archivo Excel con los datos de mi equipo y genera un informe de desempeño,
> extrae insights y un plan de acción."

## Arquitectura

```
mi-agente-analisis/
├── core/              # Lógica central (Python)
│   ├── excel_reader.py    # lee y perfila Excel/CSV
│   ├── metodologia.py     # carga skills/<id>/metodologia.yaml
│   ├── analyzer.py        # puntajes ponderados, bandas, agregados
│   ├── insights.py        # hallazgos y plan de acción
│   ├── report_pdf.py / report_excel.py / report_word.py
│   ├── agent.py           # orquestador: ejecutar(...)
│   └── cli.py             # python -m core.cli ...
├── skills/            # Metodologías reutilizables (SKILL.md + metodologia.yaml)
├── adapters/
│   ├── claude/        # CLAUDE.md + guía de instalación
│   └── codex/         # AGENTS.md + guía de instalación
├── examples/          # Excel de muestra y prompts
├── templates/         # Plantillas Jinja2 de los resúmenes
├── docs/              # Instalación, guía de uso, crear skills, FAQ
├── tests/             # Pruebas automáticas (pytest)
├── CLAUDE.md          # copia de adapters/claude/CLAUDE.md
├── AGENTS.md          # copia de adapters/codex/AGENTS.md
└── requirements.txt
```

## Comandos

```bash
python -m core.cli skills                        # skills disponibles
python -m core.cli hojas  archivo.xlsx           # hojas del Excel
python -m core.cli explorar archivo.xlsx         # perfil de los datos (JSON)
python -m core.cli analizar archivo.xlsx \
    --skill evaluacion-desempeno \
    --formatos pdf,xlsx,docx,md \
    --hoja "Evaluación" --titulo "Informe Q4" --salida ./resultados
```

Desde Python:

```python
from core.agent import ejecutar
r = ejecutar("examples/datos_equipo.xlsx", skill="evaluacion-desempeno", formatos=["pdf", "docx"])
print(r.resumen_texto())
print(r.archivos)
```

## Skills incluidas

| Skill | Uso |
|---|---|
| `evaluacion-desempeno` | Puntajes por persona y criterio → ranking, bandas, insights y plan. |
| `analisis-datos` | Exploración de cualquier archivo: columnas, nulos, estadísticas. |
| `generacion-reportes` | Reglas de formato y estilo de los entregables. |
| `plan-accion` | Cómo convertir hallazgos en acciones con responsable, plazo e indicador. |

Para añadir una metodología propia: [`docs/crear-skills.md`](docs/crear-skills.md).

## Formato del Excel esperado (skill de desempeño)

| Nombre | Área | Productividad | Calidad | Puntualidad | Trabajo en equipo | Comunicación |
|---|---|---|---|---|---|---|
| Ana Torres | Ventas | 4 | 5 | 3 | 4 | 4 |

- Escala 1-5 por defecto (si los datos van hasta 10 o 100 se detecta automáticamente).
- Los nombres de columna se reconocen sin importar mayúsculas ni acentos; se pueden añadir
  sinónimos en `metodologia.yaml`.
- Columnas extra (Cargo, Comentarios…) se ignoran.

## Documentación

- [Instalación paso a paso](docs/instalacion.md)
- [Guía de uso](docs/guia-uso.md)
- [Crear una nueva skill](docs/crear-skills.md)
- [Preguntas frecuentes](docs/faq.md)

## Pruebas

```bash
python -m pytest tests -q
```

## Licencia

MIT. Los datos de `examples/` son ficticios.

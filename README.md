# Agente Comercial — Census Consultores

Herramienta del área comercial, compatible con **Claude** (Claude Code, VS Code) y **GPT**
(Codex, ChatGPT). Lee los informes de investigación de prospectos, propone los servicios de la
cartera que el cliente puede contratar, calcula honorarios y genera los contratos en Word con el
membrete de Census.

```
Informe de investigación (Word) ──▶ métricas de viabilidad ──▶ servicios + honorarios ──▶ contrato .docx
                                        conocimiento/                                     (propuesta y correo: pendientes)
```

## Procesos que cubre

| Proceso | Estado | Dónde |
|---|---|---|
| Cartera de servicios, base legal y contexto | 15 servicios; bases legales por validar | `conocimiento/servicios.yaml` |
| Análisis del informe de investigación del cliente | Listo (formato Census, Word) | `core/informe_reader.py` |
| Métricas para saber si un cliente puede adquirir un servicio | Listo, **valores provisionales** | `conocimiento/metricas.yaml` |
| Cuantías y honorarios (tarifario) | Listo, **valores provisionales** | `conocimiento/tarifario.yaml` |
| Contratos | 10 servicios con contrato tipo | `conocimiento/clausulas/` |
| Propuestas | Pendiente de plantillas | `plantillas/propuestas/` |
| Correos | Pendiente de plantillas | `plantillas/correos/` |

## Inicio rápido

```bash
git clone https://github.com/avasquez-droid/mi-agente-analisis.git
cd mi-agente-analisis
pip install -r requirements.txt
python examples/generar_informe_ejemplo.py                       # informe ficticio de prueba
python -m core.cli analizar-cliente examples/informe_ejemplo.docx
python -m core.cli contrato devolucion_iva --cliente examples/cliente_ejemplo.yaml --var periodo="diciembre 2026"
```

Los resultados quedan en `salidas/` (resumen `.md`, Excel de oportunidades y contratos `.docx`).

Con el agente: abre la carpeta con `claude` (lee `CLAUDE.md`) o `codex` (lee `AGENTS.md`) y pide,
por ejemplo, *"Analiza este informe y dime qué servicios le ofrecemos"* o *"Haz el contrato de
devolución de IVA para IMPORTADORA DEMO"*.

## Estructura

```
conocimiento/            # lo que el agente "sabe" — se edita sin tocar código
  servicios.yaml         # cartera: materia, entidad que firma, contexto, base legal
  metricas.yaml          # cuándo un cliente califica para cada servicio (umbrales)
  tarifario.yaml         # honorarios por servicio (modelo, %, montos, forma de pago)
  entidades.yaml         # CENSUSCONSULTORES S.A.S. y CENSUS COBRANZAS S.A.
  clausulas/comunes.yaml # cláusulas estándar 2026
  clausulas/servicios/   # cláusulas propias de cada servicio
plantillas/contratos/base_census.docx   # membrete
core/                    # informe_reader, oportunidades, contratos, reporte, cli
skills/                  # instrucciones para el agente (también en .claude/skills/)
docs/                    # instalación, guía de uso, revisión de contratos, FAQ
examples/                # informe y cliente FICTICIOS
tests/                   # pytest
privado/                 # material real de clientes (ignorado por Git)
```

## Confidencialidad
Los informes y contratos reales tienen datos personales. **No se suben al repositorio** (que es
público): guárdalos en `privado/`. Los ejemplos de `examples/` son ficticios.

## Documentación
- [Instalación](docs/instalacion.md) · [Guía de uso](docs/guia-uso.md) · [FAQ](docs/faq.md)
- [Revisión de los 276 contratos y discrepancias a decidir](docs/revision-contratos.md)

## Pruebas
```bash
python -m pytest tests -q
```

Licencia MIT.

"""Núcleo del Agente Comercial de Census Consultores.

- informe_reader: lee el informe de investigación de prospecto (Word).
- conocimiento: carga cartera, métricas, tarifario, entidades y cláusulas (carpeta conocimiento/).
- oportunidades: cruza el informe con la cartera → servicios, viabilidad y honorarios.
- contratos: arma contratos .docx desde la biblioteca de cláusulas.
- reporte_oportunidades: resumen Markdown y Excel de oportunidades.
- cli: python -m core.cli ...
"""

__version__ = "2.0.0"

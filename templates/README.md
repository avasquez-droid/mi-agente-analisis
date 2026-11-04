# Plantillas

- `resumen_chat.md.j2`: resumen en Markdown que el agente muestra en el chat y guarda como `.md`.
  Usa Jinja2; las variables disponibles son `res` (ResultadoAnalisis), `insights`, `plan` y `archivos`.

Los formatos PDF, Excel y Word se construyen por código en `core/report_*.py`.
Para cambiar colores, títulos o secciones edite esos módulos o duplique esta plantilla.

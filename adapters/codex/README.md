# Adaptador para GPT (Codex CLI, Codex en ChatGPT, ChatGPT Projects)

## Codex CLI / Codex en la web
1. Codex lee automáticamente el `AGENTS.md` de la raíz (copia de `adapters/codex/AGENTS.md`).
2. Abre el repositorio con `codex` y pide, por ejemplo:
   *"Analiza examples/informe_ejemplo.docx y dime qué servicios le ofrecemos"*.

## ChatGPT (sin ejecución de código local)
1. Crea un Proyecto o GPT personalizado y pega el contenido de `adapters/codex/AGENTS.md`
   en las instrucciones.
2. Sube los archivos `skills/*/SKILL.md` y la carpeta `conocimiento/` como conocimiento.
3. Con el intérprete de código activado, sube también `core/`, `conocimiento/` y `plantillas/`
   comprimida en un .zip; ChatGPT podrá ejecutar `python -m core.cli ...` dentro de su sandbox.

## Sincronizar cambios
```bash
cp adapters/codex/AGENTS.md AGENTS.md
```

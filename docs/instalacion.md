# Instalación paso a paso

## Requisitos
- Python 3.10 o superior.
- Git.
- (Opcional) Claude Code o Codex CLI para usar el agente conversacionalmente.

## 1. Clonar el repositorio
```bash
git clone <url-del-repositorio> mi-agente-analisis
cd mi-agente-analisis
```

## 2. Crear un entorno virtual (recomendado)
```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

## 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

## 4. Verificar
```bash
python examples/generar_informe_ejemplo.py
python -m core.cli analizar-cliente examples/informe_ejemplo.docx
python -m pytest tests -q
```
Si ves el resumen en Markdown y las pruebas pasan, todo está listo.

## 5. Conectar el agente

### Claude Code
```bash
# Instalación: ver https://docs.claude.com/en/docs/claude-code
claude                   # dentro de la carpeta del proyecto
```
Claude leerá `CLAUDE.md` y encontrará las skills en `.claude/skills/`.

> Nota para Windows: `.claude/skills/` contiene enlaces simbólicos. Si Git no los
> reproduce, ejecute `python adapters/claude/sincronizar_skills.py` para copiarlas.

### Codex (GPT)
```bash
npm install -g @openai/codex
codex                    # dentro de la carpeta del proyecto
```
Codex leerá `AGENTS.md`.

### ChatGPT o Claude en el navegador
Consulte `adapters/codex/README.md` o `adapters/claude/README.md`.

## Problemas comunes
| Síntoma | Solución |
|---|---|
| `ModuleNotFoundError: yaml` | `pip install PyYAML` |
| `No module named core` | Ejecute los comandos desde la raíz del proyecto. |
| El informe es `.doc` antiguo | Ábralo en Word y guárdelo como `.docx`. |
| Acentos mal mostrados en Windows | `set PYTHONUTF8=1` antes de ejecutar. |

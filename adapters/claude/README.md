# Adaptador para Claude (Claude Code, Claude Desktop, VS Code)

## Claude Code (terminal o web)
1. Abre el repositorio: `claude` dentro de la carpeta del proyecto.
2. Claude lee automáticamente el `CLAUDE.md` de la raíz (copia de `adapters/claude/CLAUDE.md`).
3. Las skills del proyecto están enlazadas en `.claude/skills/`, así que puedes invocarlas con
   `/evaluacion-desempeno`, `/analisis-datos`, etc., o simplemente describir lo que necesitas.
4. Ejemplo: *"Carga examples/datos_equipo.xlsx y genera un informe de desempeño con plan de acción"*.

## Claude Desktop / claude.ai (proyectos)
1. Crea un Proyecto y pega el contenido de `adapters/claude/CLAUDE.md` en las instrucciones.
2. Sube los archivos `skills/*/SKILL.md` como conocimiento del proyecto.
3. Para que ejecute el código necesitas Claude Code o un entorno con Python; en la versión
   web sin código, Claude aplicará la metodología de forma manual siguiendo las SKILL.md.

## Sincronizar cambios
Si editas `adapters/claude/CLAUDE.md`, vuelve a copiarlo a la raíz:
```bash
cp adapters/claude/CLAUDE.md CLAUDE.md
```

# Preguntas frecuentes

**¿Funciona con Claude y con GPT a la vez?**
Sí. El código es el mismo; solo cambian las instrucciones: `CLAUDE.md` para Claude y `AGENTS.md`
para Codex/GPT. Ambas se mantienen en `adapters/`.

**¿Qué pasa si mi Excel tiene otros nombres de columna?**
Añade los sinónimos en `columnas:` del `metodologia.yaml`. El agente también puede hacerlo por ti.

**¿Y si falta un criterio?**
Se avisa y se redistribuyen los pesos entre los criterios presentes.

**¿Puedo usar escala 1-10 o 0-100?**
Sí. Si los datos superan la escala declarada se detecta automáticamente; también puedes fijarla
en `escala:` del YAML.

**¿Puedo cambiar colores o logotipo del PDF?**
Sí, en `core/report_pdf.py` (constante `AZUL`, estilos y encabezado).

**¿Dónde quedan los resultados?**
En `salidas/` (ignorada por Git) o en la carpeta que pases con `--salida`.

**¿El agente modifica mi archivo original?**
No. Solo lo lee.

**¿Cómo agrego una metodología nueva?**
Sigue `docs/crear-skills.md`.

**¿Puedo ejecutarlo sin agente?**
Sí, con `python -m core.cli ...` o importando `core.agent.ejecutar` desde Python.

**¿Los datos salen del equipo?**
Con la CLI, nunca. Con un agente en la nube (ChatGPT, claude.ai) los datos se envían al
proveedor; usa datos anonimizados si es necesario.

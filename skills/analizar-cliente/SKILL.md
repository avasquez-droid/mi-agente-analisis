---
name: analizar-cliente
description: Lee un informe de investigación de prospecto (Word, generado por Census) y propone los servicios de la cartera que el cliente podría contratar, con viabilidad y honorario estimado. Úsala cuando el usuario suba o mencione un "informe de investigación", "informe del grupo", "prospecto" o pida "qué servicios le ofrecemos".
---

# Skill: Analizar cliente

## Cuándo usarla
- El usuario entrega un informe de investigación de prospecto (.docx) de una empresa o grupo.
- Pide oportunidades, servicios posibles, potencial de honorarios o un resumen comercial del cliente.

## Cómo ejecutarla
```bash
python -m core.cli analizar-cliente <informe.docx>            # resumen + Excel en salidas/
python -m core.cli analizar-cliente <informe.docx> --json     # además, oportunidades en JSON
```

## Qué hace
1. Lee la ficha de cada empresa (Superintendencia, SRI, SERCOP, SATJE, OMC, Régimen 70/21).
2. Compara el cuadro resumen con las fichas y lista las **discrepancias** (la ficha manda).
3. Aplica `conocimiento/metricas.yaml` (skill `evaluar-viabilidad`) y `conocimiento/tarifario.yaml`
   (skill `cotizar`) a cada empresa.
4. Entrega: tabla de oportunidades por prioridad, honorario potencial (sin duplicar servicios
   alternativos) y Excel con hojas Oportunidades, Métricas y Discrepancias.

## Qué responder al usuario
- La tabla del resumen, empezando por prioridad **Alta**.
- Los **datos faltantes** que hay que pedir al cliente (columna "Falta").
- Las discrepancias del informe en una lista corta.
- Recordar que métricas y honorarios son provisionales mientras el área no los valide.

## Reglas
- No inventar cifras: todo sale del informe. Si un dato no está, decirlo.
- El informe contiene cédulas y datos personales: no copiarlos fuera de los entregables y no
  subir informes reales al repositorio.

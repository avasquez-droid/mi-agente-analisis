---
name: evaluacion-desempeno
description: Evalúa el desempeño de un equipo a partir de un Excel con puntajes por criterio. Úsala cuando el usuario pida "informe de desempeño", "evaluar al equipo", "ranking de colaboradores" o cargue un archivo con calificaciones por persona.
---

# Skill: Evaluación de desempeño

## Cuándo usarla
- El usuario carga un Excel/CSV con una fila por persona y columnas numéricas por criterio
  (productividad, calidad, puntualidad, trabajo en equipo, comunicación, etc.).
- Pide un informe, ranking, insights o plan de acción sobre el desempeño.

## Metodología (parámetros en `metodologia.yaml`)
1. **Mapear criterios**: cada criterio del YAML se busca en las columnas del archivo
   (sin distinguir mayúsculas ni acentos). Si falta uno, se avisa y se redistribuyen los pesos.
2. **Normalizar** cada criterio a 0-100 según la escala declarada (por defecto 1-5).
3. **Puntaje ponderado** = Σ (criterio normalizado × peso).
4. **Banda de nivel** según el puntaje: Sobresaliente / Competente / En desarrollo / Requiere atención.
5. **Agregados**: promedio por criterio, por grupo (área/departamento) y distribución de bandas.
6. **Insights**: fortaleza y oportunidad principal, personas en riesgo, talento destacado, dispersión, brechas entre grupos.
7. **Plan de acción**: acciones por criterio débil y por banda, con responsable, plazo e indicador.

## Cómo ejecutarla
```bash
python -m core.cli analizar <archivo.xlsx> --skill evaluacion-desempeno --formatos pdf,xlsx,docx,md
```
O desde Python: `from core.agent import ejecutar; r = ejecutar("archivo.xlsx")`.

## Qué entregar al usuario
1. El resumen Markdown que imprime el comando (puntaje global, tabla por criterio, hallazgos, plan).
2. Las rutas de los archivos generados en `salidas/`.
3. Si hubo advertencias (criterios faltantes, escala distinta), explicarlas en una frase.

## Reglas
- No inventar criterios ni puntajes: si una columna no existe, decirlo.
- Tratar los nombres de personas con respeto y confidencialidad; no exponer datos fuera de los entregables.
- Si el archivo tiene varias hojas, preguntar cuál usar o usar la primera e indicarlo.
- Si el usuario pide cambiar pesos o bandas, editar `metodologia.yaml` (o una copia) y volver a ejecutar.

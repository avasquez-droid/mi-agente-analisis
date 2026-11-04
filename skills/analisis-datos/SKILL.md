---
name: analisis-datos
description: Exploración general de cualquier Excel o CSV sin metodología fija. Úsala cuando el usuario pregunte "qué hay en este archivo", pida estadísticas, tendencias o un resumen de datos que no son de desempeño.
---

# Skill: Análisis de datos

## Cuándo usarla
- El usuario quiere entender un archivo (columnas, tipos, nulos, distribución).
- Pide estadísticas descriptivas, conteos por categoría o detectar problemas de calidad de datos.
- Los datos no encajan con ninguna otra skill.

## Procedimiento
1. `python -m core.cli hojas <archivo>` para listar hojas si es Excel.
2. `python -m core.cli explorar <archivo> [--hoja X]` → devuelve JSON con filas, columnas,
   nulos, estadísticas de columnas numéricas y conteos de categóricas.
3. Interpretar el perfil y responder en lenguaje claro: qué contiene, qué llama la atención,
   qué problemas de calidad existen (nulos, valores atípicos, duplicados).
4. Si el usuario quiere cálculos adicionales, escribir un script corto con pandas en
   `salidas/` y mostrar el resultado; no modificar el archivo original.
5. Si los datos parecen una evaluación por persona y criterios, sugerir la skill
   `evaluacion-desempeno`.

## Reglas
- Nunca cambiar ni sobreescribir el archivo de entrada.
- Reportar siempre el número de filas y columnas analizadas.
- Si una columna numérica tiene más del 30 % de nulos, advertirlo antes de sacar conclusiones.

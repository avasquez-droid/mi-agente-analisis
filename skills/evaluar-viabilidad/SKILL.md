---
name: evaluar-viabilidad
description: Explica o ajusta las métricas que deciden si un cliente puede adquirir un servicio (umbrales de crédito tributario, ISD, cartera, juicios, etc.). Úsala cuando el usuario pregunte por qué se sugirió (o no) un servicio, o pida cambiar un umbral.
---

# Skill: Evaluar viabilidad

Las reglas están en `conocimiento/metricas.yaml`, una entrada por servicio:

```yaml
devolucion_iva:
  modo: todas                 # todas | alguna
  condiciones:
    - {campo: ct_iva_ultimo, op: ">=", valor: 20000}
  base: ct_iva_ultimo         # monto sobre el que se calcula el honorario
  prioridad_alta_desde: 100000
  requiere_dato: ...          # lo que hay que pedir al cliente
```

- Los campos disponibles están listados al inicio del archivo.
- Para explicar un resultado: buscar la oportunidad en el resumen (columna "Motivos").
- Para cambiar un umbral: editar el `valor`, quitar la marca `# PROV` si el área lo validó y volver
  a correr `python -m core.cli analizar-cliente <informe>`.
- Para un servicio nuevo: agregarlo en `conocimiento/servicios.yaml` y su regla aquí.
- Correr `python -m pytest tests -q` después de cualquier cambio.

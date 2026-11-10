---
name: cotizar
description: Calcula honorarios de un servicio con el tarifario de Census (porcentaje sobre lo recuperado, escalonado, por vía administrativa/judicial, fijo o mensual). Úsala cuando pidan "cuánto cobramos", "honorarios", "cuantía" o una cotización.
---

# Skill: Cotizar

- Tarifario: `conocimiento/tarifario.yaml` (valor por defecto, rango observado en contratos 2024-2026,
  mínimo/máximo y forma de pago). Todos los honorarios son **más IVA**.
- Estimación rápida: el análisis de cliente ya calcula `base × porcentaje` o el monto fijo.
- Desde Python:
  ```python
  from core.oportunidades import estimar_honorario
  estimar_honorario("devolucion_iva", 119397.50)
  ```
- Si el usuario propone un porcentaje fuera de `minimo`–`maximo`, advertirlo: requiere aprobación.
- Servicios alternativos (cobranza extrajudicial vs. judicial) no se suman.

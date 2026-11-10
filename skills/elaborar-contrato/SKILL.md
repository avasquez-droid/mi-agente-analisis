---
name: elaborar-contrato
description: Genera el contrato de prestación de servicios en Word (membrete Census) a partir de la biblioteca de cláusulas, los datos del cliente y el tarifario. Úsala cuando pidan "haz el contrato", "contrato de devolución de IVA para X", o cuando una propuesta fue aceptada.
---

# Skill: Elaborar contrato

## Pasos
1. Identificar el servicio: `python -m core.cli servicios` (solo los que dicen "contrato tipo").
2. Ver qué variables necesita: `python -m core.cli variables <servicio>`.
3. Reunir los datos del cliente (razón social, RUC, representante, cargo, ciudad, provincia, correos).
   Si viene de un informe de investigación, tomarlos de la ficha de la empresa (administradores).
4. Generar:
   ```bash
   python -m core.cli contrato <servicio> --cliente cliente.yaml --var periodo="diciembre 2026" --var monto=119397.50
   ```
5. Entregar el .docx de `salidas/` y la lista de **pendientes** (marcados en amarillo en el Word).

## Reglas
- El cargo "Gerente" del representante se escribe siempre **"Gerente General"** (intervinientes y firmas);
  el agente lo corrige solo. Las marcas de la base como "(RL)" se quitan.
- No cambiar el texto de las cláusulas al vuelo: si el usuario pide una variación, preguntar si es
  solo para este contrato (editar el Word generado) o un cambio del estándar (editar
  `conocimiento/clausulas/...` y avisar que afecta a todos los contratos futuros).
- Las discrepancias conocidas entre contratos están en `docs/revision-contratos.md`; si el usuario
  pide una de las variantes, consultarlo antes de aplicarla.
- Honorario fuera del rango del tarifario → advertir.
- Servicios sin contrato tipo: decirlo y pedir el contrato modelo.

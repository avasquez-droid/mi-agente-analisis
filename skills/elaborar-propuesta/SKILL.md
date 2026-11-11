---
name: elaborar-propuesta
description: Elabora la propuesta de servicios profesionales en PowerPoint con la plantilla de Census (portada, carta, antecedentes, base legal, objetivo, alcance, honorarios, equipo, clientes). Úsala cuando pidan "propuesta", "presentación para el cliente" o después de analizar un informe de investigación.
---

# Skill: Elaborar propuesta

## Pasos
1. Elegir el servicio: `python -m core.cli servicios` (columna "propuesta").
2. Ver las variables: `python -m core.cli variables <servicio>`.
3. Tomar los datos del informe de investigación cuando existan (montos de ISD, crédito tributario,
   cartera, objeto social) — no inventarlos.
4. Generar:
   ```bash
   python -m core.cli propuesta planificacion_isd --cliente cliente.yaml \
       --var isd_por_anio="{2024: 92804.40, 2025: 45824.04}"
   ```
5. Entregar el .pptx de `salidas/` y los pendientes.

## Reglas
- Requiere la plantilla privada `privado/plantillas/propuesta_base.pptx` (una propuesta real de
  Census). Si no está, pedirla: no se sube al repo porque tiene fotos del equipo y logos de clientes.
- Honorarios: salen del tarifario (provisional). Si el usuario pide otro valor, pasarlo con --var.
- Textos por servicio en `conocimiento/propuestas/`; inconsistencias conocidas en `docs/revision-propuestas.md`.
- Después de la propuesta vienen el acuerdo de confidencialidad (si aún no se firmó) y, al aceptarse, el contrato.

## Presentación institucional de cobranzas (formato Census Cobranzas)
Para bancos, cooperativas o empresas que piden "la presentación de cobranzas":
```bash
python -m core.cli presentacion-cobranza "BANCO X S.A." --tipo financiera
```
Toma la presentación corporativa (privado/plantillas/presentacion_cobranzas.pdf, 27 láminas) y solo
cambia el nombre del cliente y las menciones al tipo de entidad. Sale en PDF.

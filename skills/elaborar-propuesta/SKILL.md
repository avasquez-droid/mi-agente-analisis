---
name: elaborar-propuesta
description: Elabora la propuesta de servicios profesionales en PowerPoint con la plantilla de Census (portada, carta, antecedentes, base legal, objetivo, alcance, honorarios, equipo, clientes). Úsala cuando pidan "propuesta", "presentación para el cliente" o después de analizar un informe de investigación.
---

# Skill: Elaborar propuesta

## Pasos
1. Elegir el servicio: `python -m core.cli servicios` (columna "propuesta").
2. Ver las variables y las notas opcionales: `python -m core.cli variables <servicio>`.
3. Tomar los datos del informe de investigación o de lo que diga el usuario (montos de ISD, crédito
   tributario, cartera, objeto social) — no inventarlos.
4. **Adaptar al contexto.** Si el usuario cuenta el caso (antecedentes, hechos, alcance especial),
   redacta los párrafos ajustados al servicio y pásalos en un YAML con `--variables`:
   `antecedentes` (lista, reemplaza los del servicio), `antecedentes_extra` (agrega), `objetivo` (texto o
   lista de objetivos; con varios o con uno largo se usa la lámina de objetivos numerados), `objetivo_intro`,
   `alcance` (lista, reemplaza), `alcance_extra` (agrega), `referencia` (texto de la carta tras
   "relacionados con los servicios de"), `tratamiento` (Señor / Señora / Señores; persona natural).
5. **Otros servicios en la misma propuesta.** Si la propuesta ofrece más de un servicio (p. ej.
   planificación tributaria + ISD), agrega `--adicional <servicio>` por cada uno: suma su alcance
   (con subtítulo) y su fila de honorarios. Con varios servicios o con notas, la lámina de honorarios
   es la de varios servicios (forma de pago en viñetas y cuadro de exclusiones).
6. **Notas opcionales: preguntar antes.** Las notas que excluyen cosas (gastos notariales, peritajes,
   implementación de figuras jurídicas, periodos sin Census...) NO se incluyen solas. Antes de generar,
   pregunta al usuario cuáles van y pásalas con `--confirmar <clave>` (p. ej. `--confirmar gastos`).
   El comando lista las que quedaron fuera.
7. Generar:
   ```bash
   python -m core.cli propuesta planificacion_tributaria --cliente cliente.yaml --var ejercicio=2026 \
       --adicional planificacion_isd --confirmar gastos --variables contexto.yaml
   ```
8. Entregar el .pptx de `salidas/`, los pendientes y las notas que no se incluyeron.

## Reglas
- Plantilla: `plantillas/census/propuesta_base.pptx` = PLANTILLA DE PROPUESTAS 2026. El formato es
  el de la plantilla al 100 % (texto, colores, fuente, tamaño): solo se reemplazan sus marcadores
  `<<...>>`. Nunca edites el PPTX a mano ni cambies textos fijos (carta, cierre, equipo).
  Si el contenido no cabe, el generador agrega láminas "(cont.)" en lugar de achicar la letra.
- Honorarios: salen del tarifario (provisional). Si el usuario pide otro valor, pasarlo con --var.
- Textos por servicio en `conocimiento/propuestas/`; inconsistencias conocidas en `docs/revision-propuestas.md`.
- Después de la propuesta vienen el acuerdo de confidencialidad (si aún no se firmó) y, al aceptarse, el contrato.

## Presentación institucional de cobranzas (formato Census Cobranzas)
Para bancos, cooperativas o empresas que piden "la presentación de cobranzas":
```bash
python -m core.cli presentacion-cobranza "BANCO X S.A." --tipo financiera
```
Toma la presentación corporativa (plantillas/census/presentacion_cobranzas.pdf, 27 láminas) y solo
cambia el nombre del cliente y las menciones al tipo de entidad. Sale en PDF.

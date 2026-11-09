---
name: acuerdo-confidencialidad
description: Genera el acuerdo de confidencialidad (NDA) entre CENSUSCONSULTORES y un prospecto o cliente, en Word con membrete Census. Úsala cuando pidan "acuerdo de confidencialidad", "NDA" o antes de compartir un informe, propuesta o estrategia con el cliente.
---

# Skill: Acuerdo de confidencialidad

## Cuándo
Antes de enviar al prospecto información estratégica (informe de investigación, propuesta,
análisis tributario). Es el primer documento del flujo comercial.

## Cómo
1. Datos del cliente en un YAML (o tomarlos del informe de investigación):
   ```yaml
   razon_social: EMPRESA S.A.
   ruc: "0990000000001"
   representada_por: REPRESENTACIONES X CIA. LTDA.   # solo si el representante es otra compañía
   representante: Nombre Apellido
   cedula: "0000000000"
   cargo: Gerente General
   persona: juridica          # natural si es persona natural
   ```
2. Generar:
   ```bash
   python -m core.cli confidencialidad --cliente cliente.yaml --var sector=farmacéutico
   ```
   Variables opcionales: `objeto` (asesoría tributaria), `sector` (industrial), `duracion_anios` (5),
   `ciudad_firma` (Samborondón), `centro_arbitraje`, `sede_arbitraje`.
3. Entregar el .docx de `salidas/` y los pendientes (resaltados en amarillo).

## Reglas
- La cédula del representante de Census se toma de `privado/entidades_local.yaml` (no va al repo).
- El acuerdo resuelve controversias por **arbitraje** (Cámara de Comercio de Guayaquil), a diferencia
  de los contratos de servicios (jueces civiles, trámite sumario). No cambiarlo sin consultar.
- Texto en `conocimiento/documentos/acuerdo_confidencialidad.yaml`.

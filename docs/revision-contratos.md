# Revisión de los contratos tipo (noviembre 2026)

Se revisaron **276 contratos .docx** (2024–2026) entregados en `Contratos.rar`, en las carpetas
Aduana, Cobranza, Devoluciones, Disminución autorretención, Planificación Tributaria, Reclamo y
demanda Aranceles y la raíz. Los contratos originales **no se suben al repositorio**; aquí solo
queda el resultado de la revisión.

## 1. Estructura estándar (contratos 2026)

| # | Cláusula | Uso |
|---|---|---|
| 1 | Intervinientes | todos |
| 2 | Antecedentes | todos |
| 3 | Prestación de servicios | todos |
| 4 | Plazo | todos |
| 5 | Honorarios | todos |
| — | Obligaciones de las partes | aduanero, aranceles OMC, tasa de seguridad, pago indebido ISD |
| — | Cambio de abogado y terminación anticipada | pago indebido ISD |
| — | Anticorrupción | aranceles OMC |
| 6+ | Terminación · Naturaleza jurídica y domicilio · Domicilio y notificación · Confidencialidad · Protección de datos · Aceptación | todos los de 2026 |

El agente arma los contratos con esa estructura (`conocimiento/clausulas/`), numera las cláusulas
automáticamente y ajusta las referencias internas ("cláusula TERCERA", "literal c)").

## 2. Discrepancias encontradas (para decidir el estándar)

| # | Tema | Variantes encontradas | Qué hace el agente hoy | Decidir |
|---|---|---|---|---|
| 1 | Trámite en "Naturaleza jurídica" | **sumario** (205 contratos) vs **ejecutivo** (36, aranceles OMC) | sumario; ejecutivo solo en aranceles OMC | ¿Se mantiene la diferencia? |
| 2 | Protección de datos | Falta en 50 contratos de 2024 y 24 de 2025; está en todos los de 2026 | Siempre la incluye | — |
| 3 | Confidencialidad | Versión corta (83) vs versión larga de "información reservada" (48, aranceles) | Versión corta | ¿Cuál es la oficial? |
| 4 | Denominación de las partes | "El Contratante / El Contratado" vs "EL CLIENTE / EL PATROCINADOR" en notificaciones (51); "La Contratante" (58) | Siempre "El Contratante / El Contratado" | — |
| 5 | Nombre de Census | "CENSUSCONSULTORES S.A.S." vs "CENSUS CONSULTORES S.A.S." (mezclados en 6 contratos de cobranza judicial) | CENSUSCONSULTORES S.A.S. | — |
| 6 | Quién firma la cobranza | Extrajudicial: CENSUS COBRANZAS S.A.; judicial 2026: CENSUSCONSULTORES S.A.S. | Igual que los contratos | ¿Correcto? Confirmar correo de notificaciones de Census Cobranzas |
| 7 | Referencias cruzadas | ~27 contratos (devoluciones de IR, IVA inmobiliario) remiten a un literal que no existe o a sí mismo; 4 de pago indebido ISD remiten a la cláusula SEXTA para honorarios cuando es la QUINTA | Calcula las referencias | — |
| 8 | Marcadores sin llenar | 15 contratos con "XX%" o "XXXX" (sobre todo planificación ISD y pago indebido ISD) | Marca en amarillo `[COMPLETAR: …]` y lo lista | — |
| 9 | Texto residual | "Final del formulario" pegado al final de los honorarios en 5 contratos de cobranza judicial; además dice "honorarios profesionales del CONTRATANTE" (debería ser del Contratado) | Corregido en la plantilla | — |
| 10 | Depósito aduanero | La cláusula de prestación termina en "las siguientes actividades:" sin enumerarlas | Propuesta de 4 actividades marcada como PROPUESTA | Validar actividades |
| 11 | Firma de Census | "Ab." vs "Abg." | "Ab." | — |
| 12 | Honorarios | Rangos amplios: aranceles OMC 4 %–40 %; devolución IVA 2 %–10 %; cobranza 4 %–25 % | Valor por defecto en `conocimiento/tarifario.yaml` | Fijar valores y topes |

## 3. Servicios sin contrato tipo todavía

`defensa_laboral`, `planificacion_tributaria`, `disminucion_autorretencion`,
`devolucion_iva_inmobiliario`, `revision_obligaciones`. Para cada uno basta elegir un contrato
modelo (sugeridos en `conocimiento/servicios.yaml`) y pasarlo a `conocimiento/clausulas/servicios/`.

## 4. Acuerdo de confidencialidad (formato oct-2026)

Plantilla en `conocimiento/documentos/acuerdo_confidencialidad.yaml`. Ajustes hechos al formato:

| # | En el formato original | En la plantilla del agente |
|---|---|---|
| 1 | Census se define como “CENSUS CONSULTORES” pero en el texto aparece “CENSUSCONSULTORES” | Una sola denominación (variable `alias_census`) |
| 2 | "…con cédula de ciudadanía No. …, la cual a su vez es, quien en adelante…" (frase incompleta) | "…en calidad de Gerente General, quien en adelante…" |
| 3 | "información de tipo industrial, farmacéutico…" (propio de ese cliente) | Sector variable (`sector`) |
| 4 | "esté o no incluida en la solicitud de oferta presentada" (resto de otra plantilla) | Eliminado |
| 5 | "en el desarrollo del presente contrato" (es un acuerdo, no un contrato) | "en el desarrollo de una relación profesional de {objeto}" |
| 6 | "«Información propia» los efectos" | "«Información propia» a los efectos" |

**A decidir:** el acuerdo resuelve controversias por **arbitraje** (Cámara de Comercio de Guayaquil,
3 árbitros), mientras que los contratos de servicios van a los **jueces civiles** en trámite
sumario/ejecutivo. ¿Se mantiene esa diferencia?

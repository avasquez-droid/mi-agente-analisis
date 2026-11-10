# Revisión de las propuestas (noviembre 2026)

Se leyeron 15 archivos (14 propuestas y la presentación corporativa de Census Cobranzas): Aduana (5),
Asesoría Tributaria (4), Devoluciones (4), Cobranzas (2). Los originales no se suben al repositorio.

## 1. Estructura estándar de una propuesta Census

1. Portada — "Propuesta de Servicios Profesionales" + nombre del servicio.
2. Introducción — carta al cliente (Señores / razón social / ciudad; REF.: Términos de referencia).
3. Nuestros socios.
4. Antecedentes (+ diapositivas opcionales: base legal, aplicación legal, requisitos, precedentes, plazos).
5. Objetivo.
6. Alcance del servicio ("Nuestro servicio comprenderá las siguientes actividades"), por fases si aplica.
7. Honorarios — tabla Tipo de asesoría | Honorario | Forma de pago + notas de gastos.
8. Gerentes y jefes · 9. Coordinadores · 10. Nuestros clientes · 11. Certificaciones · 12. Cierre.

El agente genera las diapositivas 1, 2, 4–7 con `conocimiento/propuestas/<servicio>.yaml`; las
diapositivas de equipo, clientes, certificaciones y cierre se toman tal cual de la plantilla
privada (`privado/plantillas/propuesta_base.pptx`).

## 2. Inconsistencias encontradas (para decidir el estándar)

| # | Tema | Lo encontrado | Qué hace el agente |
|---|---|---|---|
| 1 | Texto residual | Control posterior (2025): la diapositiva de honorarios repite dos veces "Asesoría Legal y Tributaria en la revisión del proceso coactivo No. DZ8-00353-2020 — honorario fijo USD 1000", que pertenece a otra propuesta | Plantilla limpia |
| 2 | Tamaño del equipo | "más de 90", "más de 100" y "más de 120 profesionales" según la propuesta | No lo menciona; **definir la cifra oficial** |
| 3 | Logros 2025 | "+ $41 millones" (tasa de seguridad, cobranza) vs "+ $46 millones" (presentación Census Cobranzas) recuperados en devoluciones | No lo menciona; **definir la cifra oficial** |
| 4 | Antigüedad | Census Cobranzas: "fundada en 2017… más de nueve años" y, en el mismo texto, "por más de ocho años" | — |
| 5 | Socios | Unas propuestas muestran 6 socios; otras 3 (incluye a Ec. Cinthia Uzcátegui, que no aparece en las de 6) | Usa la diapositiva de la plantilla; **confirmar cuál es la vigente** |
| 6 | Cargos | Paola Mora: "Jefe Legal Corporativo" vs "Gerente Legal Corporativo"; Paulina Rojas: "Coordinadora" vs "Jefe de Investigación Jurídica" | Igual que la plantilla |
| 7 | Honorarios distintos a contratos | Depósito aduanero USD 15.000 (propuesta) vs USD 20.000 (contrato); planificación ISD 10 % + retainer (propuesta) vs 6–7 % (contratos); devolución IVA 4,25 % vs 2–10 % | Propuesta usa el tarifario; quedó registrado en `tarifario.yaml` → `propuestas:` |
| 8 | Fechas internas | Devolución de IVA: la carta habla de "hasta diciembre 2026" y los antecedentes de "abril y septiembre de 2026" | Un solo periodo (variable `periodo`) |
| 9 | Diapositiva mal titulada | Planificación de utilidades (grupo de 3 compañías): el alcance se titula "Aumento capital" aunque no trata de eso (copiado de otra propuesta) | Títulos correctos |
| 10 | Frase incompleta | Planificación tributaria: "…según el siguiente esquema." sin esquema; números sueltos 1–4 | Eliminado |
| 11 | Objeto del cliente | Propuesta de ISD: la propuesta dice "fabricación de artículos de lona…", el informe de investigación dice "equipos e insumos para la supervivencia y seguridad" | Variable `actividad`; tomarla del informe |
| 12 | Ortografía | "inicidados", "comprenderá́", "Antecendentes", "tributariosoportunas", "Panificación", "Saldo conta", "los profesional que participarán", "cumplen" (el alcance… cumple) | Corregido en las plantillas |
| 13 | Áreas | "Patrocinio judicial – ejecución de acta transaccional" llegó en Aduana, pero es litigio civil | Marcado como "confirmar área" |

## 3. Nuevos servicios incorporados a la cartera
`control_posterior_aduanero`, `patrocinio_civil`, `planificacion_utilidades`,
`reestructuracion_societaria` (con su tarifa, métricas y textos de propuesta).

## 4. Bases legales incorporadas (citadas en propuestas)
Art. 152 COPCI y Arts. 144–146 de su Reglamento (depósito aduanero); Art. 159 num. 3 y Art. 156 de
la Ley Reformatoria para la Equidad Tributaria, Art. 14 del Reglamento del ISD, Art. 64 COMF,
Resolución JPRM-2021-004-M y Oficio SRI 917012021OCON001756 (ISD); Art. 122 del Código Tributario y
juicio 09501-2021-00625 (tasa de seguridad); Art. 72 de la Ley de Eficiencia Económica y
Resolución NAC-DGERCGC24-00000019 (IVA inmobiliario); Ley Orgánica de Transparencia Social
(utilidades no distribuidas). Ver `conocimiento/servicios.yaml`.

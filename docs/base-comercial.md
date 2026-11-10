# Base comercial de clientes

El agente lee la **BASE GENERAL COMERCIAL CENSUS** (Excel) desde `privado/base/` (fuera del
repositorio: contiene datos de clientes). Usa dos hojas:

- **Clientes**: datos de cada cliente (RUC, estado, grupo, referidor, sector, indicadores
  tributarios y financieros, administradores, accionistas, estado en Census).
- **servicios**: historial por cliente (servicio, estado Activo / Inactivo / En gestión comercial,
  última fecha, detalle).

Las hojas Dashboard, Ficha_Cliente, Base_Oportunidades y Listas son vistas del propio Excel y no
se leen. La hoja **Criterios** se incorporó a `conocimiento/metricas.yaml` (umbrales marcados `# CENSUS`).

```bash
python -m core.cli base resumen                  # totales de la base
python -m core.cli base cliente "NOMBRE O RUC"   # ficha de un cliente (por nombre o RUC)
```

Al analizar un informe de investigación, el agente busca cada RUC en la base: muestra cuáles ya
son clientes y **no sugiere** un servicio que el cliente ya tiene Activo o En gestión comercial.

## Correspondencia de columnas

| Columna de la base | Campo del agente |
|---|---|
| CRÉDITO TRIBUTARIO (IVA) 2025 / (IR) 2025 | `ct_iva_ref` / `ct_ir_ref` |
| IMP CAUSADO 2025 / PROYECCION IR 2025 | `ir_causado` / `proyeccion_devolucion_ir` |
| ISD 2025 / ISD 2026 | `isd_ref` / `isd_actual` |
| DEUDORES COMERCIALES… NO RELACIONADOS | `cxc_no_relacionadas` |
| N° Trabajadores | `trabajadores` (estimado, ver abajo) |
| Sector / ACTIVIDAD ECONÓMICA PRINCIPAL | `sector` / `objeto` |
| Nombres y Apellidos (accionistas) | `accionistas`, `accionistas_pn` |

## Criterios de oportunidad incorporados (hoja Criterios)

| Oportunidad | Condición | Excluye si está Activo o En gestión |
|---|---|---|
| Devoluciones | CT IVA o CT IR 2025 ≥ 100.000 | Devoluciones |
| Consultoría laboral | N.º trabajadores > 100 | Legal Laboral |
| Exoneración IR | Sector Hotelero o Turismo | — |
| Planificación ISD | ISD 2025 o ISD 2026 > 100.000 | — |
| Cobranza extrajudicial | Deudores comerciales > 1.000.000 | Cobranzas |
| Protección patrimonial | Al menos un accionista persona natural | Gestión Patrimonial |

Único ajuste del agente: en devolución de IR exige además que el crédito supere al IR causado
(proyección > 0); si no, no hay valor a devolver.

## Observaciones sobre la base (para depurar)

1. **124 clientes sin RUC** y 7 con RUC de longitud irregular (3 de 12 dígitos, 2 de 11, 1 de 9 y
   1 de 5). Sin RUC no se pueden cruzar con informes ni con la hoja servicios.
2. **N.º de trabajadores estimado**: la columna es una fórmula `(sueldos y salarios / 480) / 12`,
   da decimales y supone un sueldo de USD 480. Para 831 clientes vale 0 porque no hay sueldos
   reportados. Ejemplo: un cliente figura con 1 trabajador en la base y 9 en su informe de
   investigación. Conviene usar el número reportado a la Superintendencia cuando exista.
3. **Fecha de corte distinta al informe**: el ISD 2026 de un mismo cliente es USD 15.369,84 en la base y
   USD 19.188,59 en su informe del 5-nov-2026. Indicar la fecha de corte de cada columna.
4. **Hoja Criterios**: Protección patrimonial dice "columna AE = Sí", pero la columna AE de Clientes
   es OBSERVACIÓN COMERCIAL; esa columna de control ya no existe. El agente identifica a las
   personas naturales por el nombre (coincide con la base en 473 de 481 casos; las diferencias son
   sociedades con nombres sin sufijo societario).
5. 624 clientes sin administradores ni accionistas, y 177 con "-" en estado de RUC y sector.
6. 14 clientes figuran **Activos en Census con RUC suspendido o pasivo**.
7. Las columnas Servicio / Estado / Última fecha de Clientes repiten, en celdas de varias líneas,
   lo que ya está en la hoja servicios; el agente usa la hoja servicios.
8. El Dashboard muestra "160 oportunidades" porque está filtrado en Devoluciones; la hoja
   Base_Oportunidades tiene 1.159 filas en total.

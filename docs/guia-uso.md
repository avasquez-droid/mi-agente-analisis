# Guía de uso

## Pedidos típicos al agente (Claude Code / Codex)
- "Analiza este informe de investigación y dime qué servicios le ofrecemos al grupo."
- "¿Por qué no salió devolución de IVA para SERVICIOS DEMO?"
- "Haz el contrato de devolución de IVA para IMPORTADORA DEMO por el saldo a octubre 2026, 119.397,50."
- "Sube el umbral de cartera para cobranza a 200 mil."

## Línea de comandos
```bash
python -m core.cli servicios
python -m core.cli analizar-cliente privado/Informe_GRUPO_X.docx          # resultados en salidas/
python -m core.cli variables devolucion_iva
python -m core.cli contrato devolucion_iva --cliente examples/cliente_ejemplo.yaml \
       --var periodo="diciembre 2026" --var monto=119397.50 --fecha 2026-11-09
```

El contrato sale en `salidas/` con el membrete de Census. Lo que falte aparece como
`[COMPLETAR: …]` resaltado en amarillo y se lista en la consola.

## Dónde se ajusta cada cosa
| Quiero cambiar… | Archivo |
|---|---|
| Servicios, base legal, contexto | `conocimiento/servicios.yaml` |
| Cuándo se sugiere un servicio (umbrales) | `conocimiento/metricas.yaml` |
| Honorarios y formas de pago | `conocimiento/tarifario.yaml` |
| Representante, RUC o correo de Census | `conocimiento/entidades.yaml` |
| Cláusulas comunes (confidencialidad, datos, etc.) | `conocimiento/clausulas/comunes.yaml` |
| Cláusulas de un servicio | `conocimiento/clausulas/servicios/<servicio>.yaml` |
| Membrete del contrato | `plantillas/contratos/base_census.docx` |

Después de editar, correr `python -m pytest tests -q`.

## Agregar el contrato tipo de un servicio
1. Copiar un archivo de `conocimiento/clausulas/servicios/` como base.
2. Pegar el texto del contrato modelo en `antecedentes`, `prestacion`, `plazo`, `honorarios`
   (y `obligaciones` si aplica), cambiando los datos del cliente por variables Jinja
   (`{{ cliente.razon_social }}`, `{{ v.periodo }}`…) y declarándolas en `variables:`.
3. Poner el nombre del archivo en `clausulas:` del servicio en `conocimiento/servicios.yaml`.
4. Probar con `python -m core.cli contrato <servicio> --cliente examples/cliente_ejemplo.yaml ...`.

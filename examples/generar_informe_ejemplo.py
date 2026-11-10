"""Genera examples/informe_ejemplo.docx: un informe de investigación FICTICIO con el mismo
formato que el informe real de Census (cuadro resumen + una ficha por empresa).

Uso: python examples/generar_informe_ejemplo.py
"""
from pathlib import Path

import docx

SALIDA = Path(__file__).with_name("informe_ejemplo.docx")

EMPRESAS = [
    dict(ruc="0990000001001", nombre="IMPORTADORA DEMO S.A.", tipo="MAIN", objeto="IMPORTACION Y VENTA DE EQUIPOS INDUSTRIALES",
         trab=12, ventas=2_450_000.00, util=85_000.00, ir=42_500.00, imp=1_350_000.00, exp=0, cxc=820_000.00,
         ct={2025: (15_000.00, 61_000.00), 2024: (8_000.00, 40_000.00)}, isd={2024: 70_000.00, 2025: 64_000.00, 2026: 41_000.00},
         actor=[("09332202400001", "COBRO DE DINERO", "2024-03-10")], demandado=[], reg70={2025: 310_000.00}),
    dict(ruc="0990000002001", nombre="SERVICIOS DEMO S.A.S.", tipo="RELACIONADA", objeto="SERVICIOS DE TRANSPORTE Y LOGISTICA",
         trab=6, ventas=380_000.00, util=-12_000.00, ir=0.0, imp=0, exp=0, cxc=40_000.00,
         ct={2025: (95_000.00, 9_000.00), 2024: (60_000.00, 5_000.00)}, isd={2024: 0.0, 2025: 0.0, 2026: 0.0},
         actor=[], demandado=[("09359202500001", "INDEMNIZACIÓN POR DESPIDO INTEMPESTIVO", "2025-02-01")], reg70={}),
]


def _p(doc, texto, negrita=False):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    r.bold = negrita
    return p


def _tabla(doc, filas):
    t = doc.add_table(rows=len(filas), cols=len(filas[0]))
    for i, fila in enumerate(filas):
        for j, v in enumerate(fila):
            t.cell(i, j).text = str(v)


def _m(v):
    return "$ -" if not v else (f"(${abs(v):,.2f})" if v < 0 else f"$ {v:,.2f}")


def main():
    doc = docx.Document()
    doc.add_heading("INFORME CONSOLIDADO — GRUPO IMPORTADORA DEMO S.A.", 0)
    _p(doc, f"RUC MAIN: {EMPRESAS[0]['ruc']}", True)
    _p(doc, f"Total empresas consolidadas: {len(EMPRESAS)}   |   Fecha: 2026-11-05 10:00")
    doc.add_heading("Cuadro Resumen del Grupo", 1)
    _p(doc, "Tributario", True)
    _tabla(doc, [["RUC", "EMPRESA", "TIPO", "C.T. IVA 2025", "C.T. IR 2025", "ISD 2025", "ISD 2026", "ISD 2026 DIF", "OMC 2024-actual"]] +
           [[e["ruc"], e["nombre"], e["tipo"], f"${e['ct'][2025][0]:,.2f}", f"${e['ct'][2025][1]:,.2f}",
             f"${e['isd'][2025]:,.2f}", f"${e['isd'][2026]:,.2f}", "$0.00", "$0.00"] for e in EMPRESAS])
    _p(doc, "Legal corporativo", True)
    _tabla(doc, [["RUC", "EMPRESA", "TIPO", "N° Trab.", "Sueldos y beneficios", "Propiedad, planta y equipo"]] +
           [[e["ruc"], e["nombre"], e["tipo"], e["trab"], "$0.00", "$0.00"] for e in EMPRESAS])
    _p(doc, "Cobranzas", True)
    _tabla(doc, [["RUC", "EMPRESA", "TIPO", "Deudores comerciales y otras CxC no relac.", "Gastos deterioro"]] +
           [[e["ruc"], e["nombre"], e["tipo"], f"${e['cxc']:,.2f}", "$0.00"] for e in EMPRESAS])
    _p(doc, "Aduanero", True)
    _tabla(doc, [["RUC", "EMPRESA", "TIPO", "REG 21 TOTAL", "REG 70 TOTAL"]] +
           [[e["ruc"], e["nombre"], e["tipo"], "$0.00", "$0.00"] for e in EMPRESAS])   # discrepancia intencional en REG 70

    for e in EMPRESAS:
        _p(doc, f"RUC: {e['ruc']}", True)
        _p(doc, "INFORME INVESTIGACIÓN PROSPECTO CLIENTE", True)
        for linea in [f"Nombre comercial: {e['nombre']}", "Nombre propietario: PERSONA FICTICIA", "Información Superintendencia de Compañías",
                      f"Nombre compañía: {e['nombre']}", f"Ruc: {e['ruc']}", "Provincia: GUAYAS", "Ciudad: GUAYAQUIL",
                      f"Objeto compañía: {e['objeto']}", "Fecha de Constitución: 2015-01-01", f"Número de trabajadores: {e['trab']}",
                      f"Ingreso por ventas 2025: {_m(e['ventas'])}", f"Exportaciones: {_m(e['exp']) if e['exp'] else ''}",
                      f"Prestación de servicios: {_m(0)}", f"Venta de bienes: {_m(e['ventas'])}",
                      f"Importaciones de bienes no producidos: {_m(e['imp'])}", "Importaciones de materia prima: $ -",
                      f"Utilidad neta 2025: {_m(e['util'])}", f"Impuesto a la renta causado 2025: {_m(e['ir'])}",
                      f"Ingreso total 2025: {_m(e['ventas'])}", "Propiedad, planta y equipo: $ -", "Sueldos y beneficios sociales: $ -",
                      f"Deudores comerciales y otras cuentas por cobrar no relacionados: {_m(e['cxc'])}", "Gasto deterioro: $ -",
                      f"Crédito tributario a favor de la empresa (I.V.A) 2024: {_m(e['ct'][2024][0])}",
                      f"Crédito tributario a favor de la empresa (I.R) 2024: {_m(e['ct'][2024][1])}",
                      f"Crédito tributario a favor de la empresa (I.V.A) 2025: {_m(e['ct'][2025][0])}",
                      f"Crédito tributario a favor de la empresa (I.R) 2025: {_m(e['ct'][2025][1])}",
                      "Grandes Contribuyente: No"]:
            _p(doc, linea)
        _p(doc, "Administradores actuales de la compañía", True)
        _tabla(doc, [["IDENTIFICACIÓN", "NOMBRE", "NACIONALIDAD", "CARGO"], ["0000000000", "PERSONA FICTICIA", "ECUADOR", "GERENTE GENERAL"]])
        _p(doc, "Accionistas", True)
        _tabla(doc, [["N°", "IDENTIFICACIÓN", "NOMBRE", "NACIONALIDAD", "TIPO INVERSIÓN", "CAPITAL"],
                     ["1", "0000000000", "PERSONA FICTICIA", "ECUADOR", "NACIONAL", "800,0000"]])
        _p(doc, "Información Servicio de Rentas Internas", True)
        for anio, v in e["isd"].items():
            _p(doc, f"Impuesto salida de divisas {anio}: {_m(v)}")
        for titulo in ("Deudas Firmes:", "Deudas Impugnadas:", "Facilidades de Pago:"):
            _p(doc, titulo)
            _p(doc, "NO mantiene " + titulo[:-1].lower())
        _p(doc, "SERCOP", True)
        _p(doc, "Fuente: SERCOP Ínfima Cuantía (buscar por RUC proveedor adjudicado)")
        _p(doc, "SERCOP 2025: $ -")
        _p(doc, "Cuadro de evolución de crédito tributario IVA e IR", True)
        _tabla(doc, [["AÑO", "Crédito Tributario IVA", "Crédito Tributario IR"]] +
               [[a, _m(iva), _m(ir)] for a, (iva, ir) in sorted(e["ct"].items(), reverse=True)])
        _p(doc, "Cálculo de proyección de devolución del IR", True)
        ct_ir = e["ct"][2025][1]
        _tabla(doc, [["Concepto", "Valor 2025"], ["Crédito Tributario I.R.", _m(ct_ir)],
                     ["Impuesto a la Renta a Pagar", _m(e["ir"])], ["Proyección Devolución", _m(ct_ir - e["ir"])]])
        _p(doc, "SATJE — Juicios por Cobro", True)
        _p(doc, f"Actor / Ofendido — Total causas encontradas: {len(e['actor'])}")
        for c in e["actor"] or []:
            _p(doc, " | ".join(c))
        if not e["actor"]:
            _p(doc, "Sin causas encontradas.")
        _p(doc, f"Demandado / Procesado — Total causas encontradas: {len(e['demandado'])}")
        for c in e["demandado"]:
            _p(doc, " | ".join(c))
        if not e["demandado"]:
            _p(doc, "Sin causas encontradas.")
        _p(doc, "Partidas OMC", True)
        _p(doc, "SIN REGISTROS")
        _p(doc, "Régimen 70 (Depósito Aduanero Público)", True)
        if e["reg70"]:
            _p(doc, "Fuente: Datasur (columna REG 70 = SI, DEPOSITO ADUANERO PUBLICO).")
            _tabla(doc, [["AÑO", "TOTAL US$ FOB"]] + [[a, _m(v)] for a, v in e["reg70"].items()] +
                   [["TOTAL GENERAL", _m(sum(e["reg70"].values()))]])
        else:
            _p(doc, "SIN REGISTROS")
        _p(doc, "Régimen 21", True)
        _p(doc, "SIN REGISTROS")
        _p(doc, "TARIFA DIFERENCIADA ISD", True)
        _p(doc, "sin registro")
    doc.save(SALIDA)
    print(f"Generado: {SALIDA}")


if __name__ == "__main__":
    main()

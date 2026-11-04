"""Genera el archivo de ejemplo examples/datos_equipo.xlsx con datos ficticios.

Uso: python examples/generar_datos.py
"""
import random
from pathlib import Path

import pandas as pd

random.seed(42)
NOMBRES = ["Ana Torres", "Luis Pérez", "María Gómez", "Carlos Ruiz", "Sofía Vega", "Jorge Castro",
           "Lucía Mena", "Diego Salas", "Valeria Cruz", "Andrés Luna", "Paula Ríos", "Martín Vera",
           "Camila Ortiz", "Pedro Andrade", "Daniela Paz", "Rafael Mora", "Elena Silva", "Tomás Ibarra"]
AREAS = ["Ventas", "Operaciones", "Administración", "Tecnología"]
CARGOS = {"Ventas": "Ejecutivo comercial", "Operaciones": "Analista de operaciones",
          "Administración": "Asistente administrativo", "Tecnología": "Desarrollador"}

filas = []
for i, nombre in enumerate(NOMBRES):
    area = AREAS[i % len(AREAS)]
    base = random.uniform(2.2, 4.8)
    filas.append({
        "Nombre": nombre,
        "Área": area,
        "Cargo": CARGOS[area],
        "Productividad": round(min(5, max(1, base + random.uniform(-0.8, 0.8)))),
        "Calidad": round(min(5, max(1, base + random.uniform(-0.8, 0.8)))),
        "Puntualidad": round(min(5, max(1, base + random.uniform(-1.2, 1.0)))),
        "Trabajo en equipo": round(min(5, max(1, base + random.uniform(-0.8, 0.8)))),
        "Comunicación": round(min(5, max(1, base + random.uniform(-1.0, 0.8)))),
        "Comentarios": random.choice(["", "Participó en proyecto clave", "Llegadas tarde en marzo",
                                      "Lideró capacitación interna", "Pendiente curso de Excel"]),
    })

ruta = Path(__file__).parent / "datos_equipo.xlsx"
with pd.ExcelWriter(ruta, engine="openpyxl") as w:
    pd.DataFrame(filas).to_excel(w, sheet_name="Evaluación", index=False)
    pd.DataFrame({"Criterio": ["Productividad", "Calidad", "Puntualidad", "Trabajo en equipo", "Comunicación"],
                  "Escala": ["1-5"] * 5}).to_excel(w, sheet_name="Instrucciones", index=False)
print(f"Archivo generado: {ruta}")

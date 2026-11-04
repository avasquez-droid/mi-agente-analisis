# Crear una nueva skill

Una skill = una carpeta en `skills/` con un `SKILL.md` (instrucciones para el agente) y,
si usa el motor de puntajes, un `metodologia.yaml`.

## 1. Crear la carpeta
```bash
mkdir skills/evaluacion-proveedores
```

## 2. Escribir `SKILL.md`
```markdown
---
name: evaluacion-proveedores
description: Evalúa proveedores con criterios ponderados. Úsala cuando el usuario cargue un listado de proveedores con calificaciones.
---
# Skill: Evaluación de proveedores
## Cuándo usarla
...
## Cómo ejecutarla
python -m core.cli analizar <archivo> --skill evaluacion-proveedores
## Qué entregar
...
```
El bloque `---` inicial (frontmatter) es lo que Claude Code usa para listar la skill.

## 3. Escribir `metodologia.yaml`
```yaml
nombre: Evaluación de proveedores
descripcion: Modelo ponderado de proveedores.
escala: {min: 1, max: 10}
columna_nombre: [Proveedor, Empresa, Razón social]
columna_grupo: [Categoría, Rubro]
criterios:
  - nombre: Precio
    peso: 40
    columnas: [Precio, Competitividad de precio]
  - nombre: Plazo de entrega
    peso: 30
    columnas: [Plazo, Entrega, Cumplimiento de entrega]
  - nombre: Calidad
    peso: 30
    columnas: [Calidad, Conformidad]
bandas:
  - {nombre: Estratégico, min: 85, max: 100, descripcion: Proveedor preferente.,
     acciones: [Negociar contrato marco anual.]}
  - {nombre: Aprobado, min: 65, max: 84.99, descripcion: Cumple.,
     acciones: [Mantener y monitorear trimestralmente.]}
  - {nombre: Condicionado, min: 0, max: 64.99, descripcion: Riesgo.,
     acciones: [Plan de mejora o búsqueda de alternativa.]}
recomendaciones_por_criterio:
  Precio: [Solicitar cotizaciones comparativas.]
  Plazo de entrega: [Acordar penalidades por retraso.]
  Calidad: [Auditar el proceso del proveedor.]
```
Reglas:
- Los pesos se normalizan (pueden sumar 100, 1 o cualquier valor).
- Las bandas deben cubrir 0-100 sin huecos.
- `columnas` son los sinónimos que se buscan en el Excel (sin distinguir acentos ni mayúsculas).

## 4. Enlazar para Claude Code
```bash
ln -s ../../skills/evaluacion-proveedores .claude/skills/evaluacion-proveedores
# o en Windows: python adapters/claude/sincronizar_skills.py
```

## 5. Probar
```bash
python -m core.cli skills
python -m core.cli analizar mis_proveedores.xlsx --skill evaluacion-proveedores --formatos md
python -m pytest tests -q
```

## Skills sin motor de puntajes
Si la skill es solo un procedimiento (por ejemplo "analisis-datos"), basta con el `SKILL.md`.
El agente seguirá las instrucciones y usará `core.cli explorar` u otros scripts.

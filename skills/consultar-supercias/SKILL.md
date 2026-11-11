---
name: consultar-supercias
description: Consulta en tiempo real la Superintendencia de Compañías (portal consultaCompanias) para obtener la ficha de una compañía — RUC, situación legal, provincia, ciudad, dirección, correos, teléfonos, objeto social — y sus administradores actuales (representante legal, cargo, cédula, nombramiento). Úsala siempre antes de elaborar una propuesta, contrato o acuerdo de confidencialidad, o cuando pregunten "quién es el representante legal de X", "administradores de X", "datos de la compañía X".
---

# Skill: Consultar Supercías (tiempo real)

## Pasos
1. Consultar por RUC (preferido), expediente o nombre:
   ```bash
   python -m core.cli supercias 0990000001001            # ficha + administradores actuales
   python -m core.cli supercias "importadora demo"       # si hay varias coincidencias, lista RUC y nombre
   python -m core.cli supercias 0990000001001 --guardar  # guarda privado/clientes/<ruc>.yaml
   ```
2. Para generar documentos no hace falta armar el YAML a mano: pasar `--ruc`.
   ```bash
   python -m core.cli contrato devolucion_iva --ruc 0990000001001 --var periodo="diciembre 2026"
   python -m core.cli propuesta planificacion_isd --ruc 0990000001001
   python -m core.cli confidencialidad --ruc 0990000001001 --var sector=comercial
   ```
   Se puede combinar con `--cliente c.yaml`: lo que esté en el YAML (p. ej. `tratamiento: la señora`,
   otros correos, otro firmante) prevalece sobre el registro.
3. Informar al usuario los **avisos** que imprime el comando antes de entregar.

## Qué trae
- Compañía: razón social, RUC, expediente, tipo, situación legal, fecha de constitución, provincia, cantón,
  ciudad, dirección, referencia, correos, teléfonos, sitio web, objeto social, CIIU.
- Administradores actuales: nombre, identificación, cargo, RL/ADM, fecha de nombramiento, periodo,
  número y fecha de inscripción en el Registro Mercantil.
- Representante para firmar: el RL con cargo Gerente General; si no hay, el primer RL (con aviso).

## Reglas
- El registro escribe APELLIDOS NOMBRES, sin tildes y sin tratamiento: el nombre se reordena, pero el
  **tratamiento queda como [COMPLETAR]** y las tildes deben confirmarse con el usuario.
- Si el nombramiento aparece vencido o la situación legal no es ACTIVA, decirlo antes de generar.
- Nombre ambiguo → mostrar las coincidencias y pedir el RUC; no elegir por cuenta propia.
- El portal solo tiene compañías bajo control de la Superintendencia (no personas naturales, cooperativas
  ni bancos): en esos casos pedir los datos al usuario o tomarlos de la base comercial.
- Necesita internet hacia `appscvsgen.supercias.gob.ec` (funciona desde el PC del usuario). Si no hay
  conexión, decirlo y continuar con los datos del usuario/base, marcando lo demás como pendiente.
- Una consulta por cliente; no usar para descargas masivas. La información no constituye certificación.
- Los YAML guardados contienen cédulas: solo en `privado/` (ignorado por Git).

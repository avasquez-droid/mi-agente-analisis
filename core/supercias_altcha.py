# core/supercias_altcha.py
# ==============================================================================
# Solver de ALTCHA (proof-of-work) para el portal consultaCompanias de Supercías.
#
# Supercías reemplazó (2026-07) el captcha de imagen (6 dígitos, OCR) por ALTCHA:
# un proof-of-work donde el cliente debe encontrar un `number` tal que
#     SHA-256(salt + str(number)) == challenge
# El servidor entrega {algorithm, challenge, salt, signature, maxnumber} en
#     GET /consultaCompanias/altcha-challenge
# y el cliente devuelve, en el campo `altcha` del form, el base64 de
#     {algorithm, challenge, number, salt, signature}
#
# Ventaja sobre el captcha viejo: se resuelve en Python puro en ~20ms, sin OCR,
# sin Tesseract, sin 2Captcha, sin Claude Vision. Verificado en vivo 2026-07-03.
# ==============================================================================
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any


class AltchaError(Exception):
    pass


def resolver_challenge(challenge: dict[str, Any]) -> str:
    """Resuelve un challenge ALTCHA y devuelve el payload base64 listo para el form.

    Args:
        challenge: dict con las claves de ALTCHA:
            {algorithm, challenge, salt, signature, maxnumber}

    Returns:
        El base64 de {algorithm, challenge, number, salt, signature} — el valor
        que va en el campo `altcha` (y `payloadOculto`) del form JSF.

    Raises:
        AltchaError si el algoritmo no es SHA-256 o no se encuentra solución.
    """
    algorithm = challenge.get("algorithm", "SHA-256")
    if algorithm.upper().replace("-", "") != "SHA256":
        raise AltchaError(f"algoritmo no soportado: {algorithm!r}")

    salt = challenge["salt"]
    target = challenge["challenge"]
    maxnumber = int(challenge.get("maxnumber", 1_000_000))

    number = _resolver_pow(salt, target, maxnumber)
    if number is None:
        raise AltchaError(
            f"no se encontró solución en [0, {maxnumber}] (challenge={target[:16]}...)"
        )

    payload = {
        "algorithm": algorithm,
        "challenge": target,
        "number": number,
        "salt": salt,
        "signature": challenge["signature"],
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _resolver_pow(salt: str, target: str, maxnumber: int) -> int | None:
    """Fuerza bruta: encuentra n tal que SHA256(salt+str(n)) == target."""
    salt_b = salt.encode()
    for n in range(maxnumber + 1):
        if hashlib.sha256(salt_b + str(n).encode()).hexdigest() == target:
            return n
    return None


__all__ = ["resolver_challenge", "AltchaError"]

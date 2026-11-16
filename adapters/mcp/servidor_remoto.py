"""Conector REMOTO de Supercías para Claude (servidor MCP por HTTPS).

Corre en un servidor de Census (el mismo donde están los proxies, por ejemplo) y se registra en Claude
como "conector personalizado". La clave de los proxies queda solo en este servidor.

Acceso: la dirección del conector lleva un token secreto, https://<su-dominio>/mcp/<TOKEN>.
Cualquier otra ruta responde 404. El token no se escribe en los registros del servidor.

Variables de entorno:
  SUPERCIAS_TOKEN     (obligatoria) secreto de 32+ caracteres. Generar: python adapters/mcp/servidor_remoto.py --nuevo-token
  SUPERCIAS_PROXIES   (opcional) proxies separados por coma; si falta, se usa privado/proxies.txt o conexión directa
  SUPERCIAS_DOMINIO   (opcional) dominio público del servidor, p. ej. mcp.census.ec (restringe la cabecera Host)
  HOST, PORT          (opcional) por defecto 127.0.0.1 y 8000 (detrás de Cloudflare Tunnel, Caddy o nginx)

Arranque: python adapters/mcp/servidor_remoto.py
Guía completa: adapters/mcp/CONECTOR_REMOTO.md
"""
from __future__ import annotations

import logging
import os
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "adapters" / "mcp")]

log = logging.getLogger("supercias-remoto")


def crear_app(token: str, dominio: str | None = None):
    """Aplicación ASGI: MCP en /mcp/<token> y /salud para verificar que el servidor está arriba."""
    if len(token) < 32:
        raise SystemExit("SUPERCIAS_TOKEN debe tener al menos 32 caracteres (use --nuevo-token).")
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    from supercias_server import servidor          # misma herramienta que el conector local

    servidor.settings.streamable_http_path = f"/mcp/{token}"
    servidor.settings.stateless_http = True          # cada llamada es independiente (sin sesión en memoria)
    servidor.settings.json_response = True
    servidor.settings.transport_security = (
        TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                  allowed_hosts=[dominio, f"{dominio}:443"], allowed_origins=[f"https://{dominio}"])
        if dominio else TransportSecuritySettings(enable_dns_rebinding_protection=False))
    app = servidor.streamable_http_app()

    async def salud(_):
        return PlainTextResponse("ok")

    app.router.routes.append(Route("/salud", salud))
    return app


def _registrar_accesos(app, token: str):
    """Registro propio de accesos, sin el token (el registro de uvicorn queda desactivado)."""
    async def envoltura(scope, receive, send):
        if scope["type"] == "http":
            ruta = scope.get("path", "").replace(token, "***")
            ip = (scope.get("client") or ("?",))[0]
            estado = {}

            async def enviar(msg):
                if msg["type"] == "http.response.start":
                    estado["codigo"] = msg["status"]
                await send(msg)
            await app(scope, receive, enviar)
            log.info("%s %s %s -> %s", ip, scope.get("method"), ruta, estado.get("codigo"))
            return
        await app(scope, receive, send)
    return envoltura


def main() -> int:
    if "--nuevo-token" in sys.argv:
        print(secrets.token_urlsafe(32))
        return 0
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    token = os.environ.get("SUPERCIAS_TOKEN", "").strip()
    if not token:
        raise SystemExit("Falta SUPERCIAS_TOKEN. Genere uno con: python adapters/mcp/servidor_remoto.py --nuevo-token")
    dominio = os.environ.get("SUPERCIAS_DOMINIO") or None
    app = _registrar_accesos(crear_app(token, dominio), token)

    from core.supercias import salidas
    n = len(salidas())
    host, puerto = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    log.info("Conector Supercías en http://%s:%s/mcp/*** · salidas: %s", host, puerto,
             f"{n} proxy(s)" if n else "conexión directa")
    import uvicorn
    uvicorn.run(app, host=host, port=puerto, access_log=False, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())

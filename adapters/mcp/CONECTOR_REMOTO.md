# Conector remoto de Supercías (prueba en un servidor de Census)

Su servidor hace la consulta a la Superintendencia (con los proxies, si los hay) y Claude solo le pide el
resultado. La clave de los proxies y el token del conector se quedan en el servidor.

```
Claude ──HTTPS──> https://<dirección>/mcp/<TOKEN> ──> su servidor ──(proxies)──> Superintendencia
```

## 1. Instalar en el servidor (Linux)
```bash
git clone https://github.com/avasquez-droid/mi-agente-analisis.git
cd mi-agente-analisis
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r adapters/mcp/requirements.txt
python adapters/mcp/servidor_remoto.py --nuevo-token      # copie el resultado: es el TOKEN
```
En Windows: `py -m venv .venv`, `.venv\Scripts\activate` y los mismos comandos.

## 2. Configurar y arrancar
```bash
export SUPERCIAS_TOKEN='<TOKEN>'
export SUPERCIAS_PROXIES='http://usuario:clave@IP1:puerto,http://usuario:clave@IP2:puerto'   # opcional
python -m core.cli salidas                    # prueba cada proxy (opcional)
python adapters/mcp/servidor_remoto.py        # queda escuchando en 127.0.0.1:8000
```
En Windows (PowerShell): `$env:SUPERCIAS_TOKEN = '<TOKEN>'` y lo mismo para `SUPERCIAS_PROXIES`.
En lugar de la variable, los proxies pueden ir en `privado/proxies.txt` (uno por línea).
Escriba estas claves directamente en el servidor: nunca en el chat, el correo ni el repositorio.

## 3. Darle una dirección HTTPS
**Prueba rápida, sin cuenta ni abrir puertos** (en otra terminal del servidor):
```bash
cloudflared tunnel --url http://localhost:8000
```
Muestra una dirección como `https://palabras-al-azar.trycloudflare.com`. Cambia cada vez que se reinicia:
sirve para probar, no para el uso diario. Descarga de `cloudflared`: página oficial de Cloudflare.

Comprobar en el navegador: `https://palabras-al-azar.trycloudflare.com/salud` debe mostrar `ok`.

**Uso permanente**: un túnel con nombre de Cloudflare y un dominio de Census (p. ej. `mcp.census.ec`), o
Caddy/nginx con certificado. Agregue entonces `SUPERCIAS_DOMINIO=mcp.census.ec` para que el servidor solo
acepte peticiones dirigidas a ese dominio.

## 4. Registrar en Claude
Ajustes → Conectores → Añadir → Añadir conector personalizado:
- Nombre: `Supercías Census`
- URL del servidor MCP: `https://palabras-al-azar.trycloudflare.com/mcp/<TOKEN>`

Si la ventana no le deja guardar, su organización solo permite conectores agregados por el Owner: ahí sí
toca pedírselo, con esta misma URL.

## 5. Probar
En un chat nuevo, active el conector (menú de herramientas) y escriba:
«Consulta en Supercías el RUC 0993258571001». Debe devolver la ficha y el representante legal.
En el servidor verá líneas como `POST /mcp/*** -> 200` (el token nunca aparece en el registro).

## 6. Usarlo con el agente comercial
El agente (skill `agente-comercial-census` y `CLAUDE.md` del repositorio) usa la herramienta
`consultar_supercias` cuando no tiene conexión directa al portal. Pida, por ejemplo:
«Acuerdo de confidencialidad para DISPROVIEC, sector comercial».

## Seguridad
- El TOKEN es una contraseña: quien tenga la URL completa puede usar el conector. Compártala solo con el
  grupo y por un canal privado.
- Si se filtra: genere otro (`--nuevo-token`), reinicie el servidor y actualice la URL en Claude.
- Rutas distintas de `/mcp/<TOKEN>` responden 404. `/salud` no devuelve datos.
- Siguiente paso recomendado: inicio de sesión con las cuentas de Census (OAuth) en vez de token compartido.

## Dejarlo corriendo (Linux, systemd)
`/etc/systemd/system/supercias.service`:
```ini
[Unit]
Description=Conector Supercías Census
After=network-online.target

[Service]
WorkingDirectory=/opt/mi-agente-analisis
EnvironmentFile=/etc/supercias.env
ExecStart=/opt/mi-agente-analisis/.venv/bin/python adapters/mcp/servidor_remoto.py
Restart=always
User=supercias

[Install]
WantedBy=multi-user.target
```
`/etc/supercias.env` (permisos 600) con `SUPERCIAS_TOKEN=...` y `SUPERCIAS_PROXIES=...`.
Luego: `sudo systemctl enable --now supercias`.

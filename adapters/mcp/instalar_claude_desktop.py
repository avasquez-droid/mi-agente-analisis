"""Registra el servidor MCP de Supercías en la app de escritorio de Claude (Windows, macOS o Linux).

Uso: doble clic en adapters/mcp/instalar_supercias.bat  (o: python adapters/mcp/instalar_claude_desktop.py)

Qué hace: instala las dependencias, agrega la entrada "supercias-census" al archivo
claude_desktop_config.json (conserva lo que ya tenga; guarda una copia .bak) y verifica que el servidor arranca.
Después hay que cerrar Claude por completo y volver a abrirlo.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SERVIDOR = RAIZ / "adapters" / "mcp" / "supercias_server.py"
NOMBRE = "supercias-census"


def carpetas_config() -> list[Path]:
    casa = Path.home()
    if sys.platform == "win32":
        normal = Path(os.environ.get("APPDATA", casa / "AppData" / "Roaming")) / "Claude"
        paquetes = Path(os.environ.get("LOCALAPPDATA", casa / "AppData" / "Local")) / "Packages"
        tienda = [p / "LocalCache" / "Roaming" / "Claude" for p in paquetes.glob("*Claude*")] if paquetes.exists() else []
        return [c for c in tienda if c.exists()] + [normal]      # instalación de Microsoft Store primero
    if sys.platform == "darwin":
        return [casa / "Library" / "Application Support" / "Claude"]
    return [casa / ".config" / "Claude"]


def registrar(carpeta: Path) -> Path:
    archivo = carpeta / "claude_desktop_config.json"
    carpeta.mkdir(parents=True, exist_ok=True)
    config = {}
    if archivo.exists() and archivo.read_text(encoding="utf-8").strip():
        config = json.loads(archivo.read_text(encoding="utf-8"))
        shutil.copy2(archivo, archivo.with_suffix(".json.bak"))
    config.setdefault("mcpServers", {})[NOMBRE] = {
        "command": sys.executable, "args": [str(SERVIDOR)], "env": {"PYTHONUTF8": "1"}}
    archivo.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return archivo


def main() -> int:
    print("1/3 Instalando dependencias...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(RAIZ / "requirements.txt"),
                    "-r", str(RAIZ / "adapters" / "mcp" / "requirements.txt")], check=True)
    print("2/3 Comprobando que el servidor arranca...")
    r = subprocess.run([sys.executable, "-c", "import runpy,sys; sys.argv=['x']; "
                        f"m=runpy.run_path(r'{SERVIDOR}', run_name='comprobacion'); print('ok')"],
                       capture_output=True, text=True)
    if "ok" not in r.stdout:
        print("   No arrancó:\n" + r.stderr[-800:])
        return 1
    print("3/3 Registrando en Claude...")
    for carpeta in carpetas_config():
        print(f"   {registrar(carpeta)}")
    print(f"\nListo. Cierre Claude por completo (icono de la bandeja > Salir) y ábralo de nuevo.\n"
          f"En Ajustes > Desarrollador debe aparecer '{NOMBRE}'. Pruebe: «consulta en Supercías el RUC ...».")
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except Exception as e:                                   # que la ventana no se cierre sin explicación
        print(f"\nERROR: {e}")
        codigo = 1
    if sys.platform == "win32" and not os.environ.get("SIN_PAUSA"):
        input("\nPresione Enter para cerrar...")
    sys.exit(codigo)

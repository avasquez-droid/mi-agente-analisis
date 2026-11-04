"""Copia skills/ a .claude/skills/ para entornos donde los enlaces simbólicos no funcionan.

Uso: python adapters/claude/sincronizar_skills.py
"""
import shutil
from pathlib import Path

raiz = Path(__file__).resolve().parents[2]
origen = raiz / "skills"
destino = raiz / ".claude" / "skills"
destino.mkdir(parents=True, exist_ok=True)
for carpeta in origen.iterdir():
    if carpeta.is_dir() and (carpeta / "SKILL.md").exists():
        objetivo = destino / carpeta.name
        if objetivo.is_symlink() or objetivo.exists():
            if objetivo.is_symlink():
                objetivo.unlink()
            else:
                shutil.rmtree(objetivo)
        shutil.copytree(carpeta, objetivo)
        print(f"Copiada: {carpeta.name}")

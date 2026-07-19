"""
resumen_proyecto.py — Genera un resumen estructurado de tu app para pegar en un chat.
Uso: python resumen_proyecto.py
"""

import os
from pathlib import Path

# ============ CONFIGURA ESTO ============
PROJECT_ROOT = r"C:\Users\matib\Desktop\Apps\mundial-predictor"
OUTPUT_FILE = r"C:\Users\matib\Desktop\Apps\mundial-predictor\resumen_para_chat.txt"

# Archivos/carpetas a ignorar
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".streamlit", ".idea", ".vscode"}
SKIP_FILES = {".gitignore", "README.md", "resumen_para_chat.txt", "resumen_proyecto.py"}
SKIP_EXTS = {".pyc", ".pyo", ".sqlite", ".db", ".jpg", ".jpeg", ".png", ".gif", ".ico", ".woff", ".ttf", ".eot", ".svg", ".mp4", ".mp3", ".zip", ".tar", ".gz"}

# Archivos que SIEMPRE incluir (aunque estén en SKIP_FILES o SKIP_EXTS)
FORCE_INCLUDE = {"app.py", "poisson_model.py", "elo.py", "monte_carlo.py", "corners_cards.py", "h2h.py"}

# Límite de líneas por archivo (para no generar un texto gigante)
MAX_LINES_PER_FILE = 300
# ========================================

def should_include_file(filepath: Path, filename: str) -> bool:
    if filename in FORCE_INCLUDE:
        return True
    if filename in SKIP_FILES:
        return False
    if filepath.suffix.lower() in SKIP_EXTS:
        return False
    return True

def build_tree(directory: Path, prefix=""):
    """Genera el árbol de directorios tipo `tree`."""
    lines = []
    try:
        entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return lines

    dirs = [e for e in entries if e.is_dir() and e.name not in SKIP_DIRS]
    files = [e for e in entries if e.is_file()]

    all_entries = dirs + files
    for i, entry in enumerate(all_entries):
        is_last = i == len(all_entries) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(build_tree(entry, prefix + extension))
    return lines

def main():
    root = Path(PROJECT_ROOT)
    if not root.exists():
        print(f"No existe el directorio: {PROJECT_ROOT}")
        return

    out_lines = []
    out_lines.append("=" * 70)
    out_lines.append(f"RESUMEN DEL PROYECTO: {root.name}")
    out_lines.append(f"Ruta: {root}")
    out_lines.append("=" * 70)
    out_lines.append("")

    # 1. Árbol de directorios
    out_lines.append("# ESTRUCTURA DE DIRECTORIOS")
    out_lines.append("-" * 50)
    out_lines.append(root.name + "/")
    out_lines.extend(build_tree(root))
    out_lines.append("")

    # 2. Contenido de archivos
    out_lines.append("# CONTENIDO DE ARCHIVOS")
    out_lines.append("-" * 50)

    for filepath in sorted(root.rglob("*")):
        if filepath.is_dir():
            continue

        # Saltar directorios ignorados en la ruta
        if any(part in SKIP_DIRS for part in filepath.parts):
            continue

        if not should_include_file(filepath, filepath.name):
            continue

        rel_path = filepath.relative_to(root)
        out_lines.append("")
        out_lines.append(f"## {rel_path}")
        out_lines.append(f"```python")

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if len(lines) > MAX_LINES_PER_FILE:
                    content = "".join(lines[:MAX_LINES_PER_FILE])
                    content += f"\n\n# ... ({len(lines) - MAX_LINES_PER_FILE} líneas más truncadas)"
                else:
                    content = "".join(lines)
                out_lines.append(content.rstrip())
        except Exception as e:
            out_lines.append(f"# Error leyendo archivo: {e}")

        out_lines.append("```")

    out_lines.append("")
    out_lines.append("=" * 70)
    out_lines.append("FIN DEL RESUMEN")
    out_lines.append("=" * 70)

    output = "\n".join(out_lines)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    size_kb = len(output.encode("utf-8")) / 1024
    print(f"Resumen generado: {OUTPUT_FILE}")
    print(f"Tamaño: {size_kb:.1f} KB")
    print(f"Archivos incluidos: {output.count('## ')}")
    print("\nCopia el contenido del archivo y pégalo en el chat.")

if __name__ == "__main__":
    main()
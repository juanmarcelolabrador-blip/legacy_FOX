# -*- coding: utf-8 -*-
"""
run_prototipo.py
================
Lanzador del prototipo: inicia EN PARALELO las dos aplicaciones:
    * sistema_legacy_fox.py   (estética Visual FoxPro / Win95-98)
    * copiloto_jml_moderno.py (panel moderno oscuro)

Uso:
    python run_prototipo.py

Ambas ventanas comparten el archivo "codigo_seleccionado.json". Cierra las
dos ventanas para que este lanzador termine.
"""

import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
FOX = os.path.join(BASE, "sistema_legacy_fox.py")
COPILOTO = os.path.join(BASE, "copiloto_jml_moderno.py")

# Usar pythonw.exe si existe para evitar consolas extra en Windows
python = sys.executable
pythonw = os.path.join(os.path.dirname(python), "pythonw.exe")
interprete = pythonw if os.path.exists(pythonw) else python


def main():
    print("Iniciando prototipo JML (2 aplicaciones en paralelo)...")
    p1 = subprocess.Popen([interprete, FOX])
    p2 = subprocess.Popen([interprete, COPILOTO])
    print("  [1] Sistema Legacy  (FoxPro)   PID", p1.pid)
    print("  [2] Copiloto JML   (Moderno)   PID", p2.pid)
    print("Cierra ambas ventanas para terminar.")
    try:
        p1.wait()
        p2.wait()
    except KeyboardInterrupt:
        print("Terminado por el usuario.")


if __name__ == "__main__":
    main()

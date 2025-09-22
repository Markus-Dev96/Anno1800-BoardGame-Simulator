# main.py
"""
Hauptstartpunkt für den Anno 1800 Simulator
"""

import sys
import os

# Sicherstellen, dass das Projektverzeichnis im PYTHONPATH ist
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Jetzt können wir die UI starten
import tkinter as tk
from anno1800.ui.main_window import Anno1800App

def main():
    root = tk.Tk()
    app = Anno1800App(root)
    root.mainloop()

if __name__ == "__main__":
    main()

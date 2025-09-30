
# anno1800/ui/main_app.py
"""
Hauptanwendung mit Menü zur Auswahl zwischen verschiedenen Modi
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

from anno1800.ui.board_game_ui import BoardGameUI

logger = logging.getLogger(__name__)

class Anno1800App:
    """Hauptanwendung mit Spielmodusauswahl"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Anno 1800 - Das Brettspiel")
        self.root.geometry("800x600")
        
        # Anno 1800 Styling
        self.setup_styles()
        self.create_main_menu()
    
    def setup_styles(self):
        """Richtet das Anno 1800 Theme ein"""
        self.root.configure(bg="#2a1810")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Button Style
        style.configure(
            "Anno.TButton",
            background="#8b4513",
            foreground="white",
            borderwidth=3,
            relief="raised",
            font=("Arial", 12, "bold")
        )
        style.map("Anno.TButton",
            background=[('active', '#a0522d')],
            foreground=[('active', 'white')]
        )
    
    def create_main_menu(self):
        """Erstellt das Hauptmenü"""
        # Titel
        title_frame = tk.Frame(self.root, bg="#2a1810")
        title_frame.pack(pady=50)
        
        title_label = tk.Label(
            title_frame,
            text="ANNO",
            font=("Old English Text MT", 48, "bold"),
            bg="#2a1810",
            fg="#d4af37"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="1800",
            font=("Old English Text MT", 36),
            bg="#2a1810",
            fg="#d4af37"
        )
        subtitle_label.pack()
        
        board_label = tk.Label(
            title_frame,
            text="Das Brettspiel",
            font=("Arial", 18, "italic"),
            bg="#2a1810",
            fg="#daa520"
        )
        board_label.pack(pady=10)
        
        # Menü-Buttons
        menu_frame = tk.Frame(self.root, bg="#2a1810")
        menu_frame.pack(pady=50)
        
        buttons = [
            ("🎮 Einzelspieler gegen KI", self.start_singleplayer),
            ("🎲 Brettspiel-Modus", self.start_boardgame),
            ("🤖 KI Training", self.start_training),
            ("📊 Statistiken", self.show_statistics),
            ("⚙️ Einstellungen", self.show_settings),
            ("❌ Beenden", self.root.quit)
        ]
        
        for text, command in buttons:
            btn = tk.Button(
                menu_frame,
                text=text,
                command=command,
                font=("Arial", 14, "bold"),
                bg="#8b4513",
                fg="white",
                width=25,
                height=2,
                relief=tk.RAISED,
                bd=3,
                activebackground="#a0522d",
                activeforeground="white"
            )
            btn.pack(pady=10)
            
            # Hover-Effekt
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#a0522d"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#8b4513"))
    
    def start_singleplayer(self):
        """Startet Einzelspielermodus"""
        # Verstecke Hauptmenü
        for widget in self.root.winfo_children():
            widget.pack_forget()
        
        # Starte Brettspiel-UI
        game_ui = BoardGameUI(self.root)
        game_ui.start_new_game()
        
        # Zurück-Button
        back_btn = tk.Button(
            self.root,
            text="← Hauptmenü",
            command=lambda: self.return_to_menu(game_ui),
            font=("Arial", 10),
            bg="#8b4513",
            fg="white"
        )
        back_btn.place(x=10, y=10)
    
    def start_boardgame(self):
        """Startet lokalen Mehrspieler-Modus"""
        messagebox.showinfo(
            "Brettspiel-Modus",
            "Lokaler Mehrspieler-Modus:\n\n"
            "• 2-4 Spieler am selben Gerät\n"
            "• Reihum Aktionen ausführen\n"
            "• KI-Berater für jeden Spieler\n\n"
            "Kommt bald!"
        )
    
    def start_training(self):
        """Startet KI-Trainingsmodus"""
        messagebox.showinfo(
            "KI Training",
            "KI-Trainingsmodus:\n\n"
            "• Automatische Spiele für Trainingsdaten\n"
            "• Verschiedene KI-Strategien testen\n"
            "• ML-Modell verbessern\n\n"
            "Kommt bald!"
        )
    
    def show_statistics(self):
        """Zeigt Spielstatistiken"""
        messagebox.showinfo(
            "Statistiken",
            "Spielstatistiken:\n\n"
            "• Gespielte Spiele: 0\n"
            "• Siege: 0\n"
            "• Beste Punktzahl: 0\n"
            "• KI-Genauigkeit: N/A\n\n"
            "Noch keine Daten vorhanden!"
        )
    
    def show_settings(self):
        """Zeigt Einstellungen"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Einstellungen")
        settings_window.geometry("400x300")
        settings_window.configure(bg="#2a1810")
        
        tk.Label(
            settings_window,
            text="Einstellungen",
            font=("Arial", 16, "bold"),
            bg="#2a1810",
            fg="#d4af37"
        ).pack(pady=20)
        
        # KI-Schwierigkeit
        tk.Label(
            settings_window,
            text="KI-Schwierigkeit:",
            bg="#2a1810",
            fg="white"
        ).pack()
        
        difficulty = ttk.Combobox(
            settings_window,
            values=["Leicht", "Mittel", "Schwer", "Experte"],
            state="readonly"
        )
        difficulty.set("Mittel")
        difficulty.pack(pady=10)
        
        # Animationen
        animations_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_window,
            text="Animationen aktiviert",
            variable=animations_var,
            bg="#2a1810",
            fg="white",
            selectcolor="#8b4513"
        ).pack(pady=10)
        
        # Sound
        sound_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_window,
            text="Sound aktiviert",
            variable=sound_var,
            bg="#2a1810",
            fg="white",
            selectcolor="#8b4513"
        ).pack(pady=10)
    
    def return_to_menu(self, game_ui):
        """Kehrt zum Hauptmenü zurück"""
        # Verstecke Spiel-UI
        for widget in self.root.winfo_children():
            if hasattr(widget, 'destroy'):
                widget.destroy()
        
        # Zeige Hauptmenü wieder
        self.create_main_menu()
    
    def run(self):
        """Startet die Anwendung"""
        self.root.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = Anno1800App()
    app.run()
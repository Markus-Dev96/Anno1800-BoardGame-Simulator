# anno1800/ui/dialogs.py
"""
Dialog-Fenster für Anno 1800 UI
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List

class NewGameDialog:
    """Dialog für neues Spiel"""
    
    def __init__(self, parent):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Neues Spiel")
        self.window.geometry("450x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """Erstellt Widgets"""
        # Title
        title_label = ttk.Label(
            self.window,
            text="Neues Spiel konfigurieren",
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Number of players
        ttk.Label(main_frame, text="Anzahl Spieler:").grid(row=0, column=0, sticky='w', pady=5)
        self.num_players_var = tk.IntVar(value=4)
        player_spinbox = ttk.Spinbox(
            main_frame,
            from_=2,
            to=4,
            textvariable=self.num_players_var,
            width=10,
            command=self.update_player_list
        )
        player_spinbox.grid(row=0, column=1, sticky='w', pady=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=3, sticky='ew', pady=10
        )
        
        # Player strategies
        ttk.Label(main_frame, text="Spieler-Strategien:").grid(
            row=2, column=0, columnspan=2, sticky='w', pady=5
        )
        
        # Strategy frame
        self.strategy_frame = ttk.Frame(main_frame)
        self.strategy_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=5)
        
        self.strategy_vars = []
        self.strategy_combos = []
        
        strategies = ['human', 'aggressive', 'balanced', 'economic', 'explorer']
        
        for i in range(4):
            label = ttk.Label(self.strategy_frame, text=f"Spieler {i+1}:")
            label.grid(row=i, column=0, sticky='w', padx=(20, 10), pady=2)
            
            var = tk.StringVar(value='balanced' if i > 0 else 'human')
            combo = ttk.Combobox(
                self.strategy_frame,
                textvariable=var,
                values=strategies,
                state='readonly',
                width=15
            )
            combo.grid(row=i, column=1, pady=2)
            
            self.strategy_vars.append(var)
            self.strategy_combos.append((label, combo))
        
        # Additional options
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=4, column=0, columnspan=3, sticky='ew', pady=10
        )
        
        ttk.Label(main_frame, text="Zusätzliche Optionen:").grid(
            row=5, column=0, columnspan=2, sticky='w', pady=5
        )
        
        # Options
        self.collect_data_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text="Trainingsdaten sammeln",
            variable=self.collect_data_var
        ).grid(row=6, column=0, columnspan=2, sticky='w', padx=(20, 0))
        
        self.show_suggestions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text="KI-Vorschläge anzeigen",
            variable=self.show_suggestions_var
        ).grid(row=7, column=0, columnspan=2, sticky='w', padx=(20, 0))
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Spiel starten",
            command=self.start_game
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.cancel
        ).pack(side=tk.LEFT, padx=5)
        
        # Initial update
        self.update_player_list()
    
    def update_player_list(self):
        """Aktualisiert Spielerliste basierend auf Anzahl"""
        num_players = self.num_players_var.get()
        
        for i, (label, combo) in enumerate(self.strategy_combos):
            if i < num_players:
                label.grid()
                combo.grid()
            else:
                label.grid_remove()
                combo.grid_remove()
    
    def start_game(self):
        """Startet das Spiel mit gewählten Einstellungen"""
        num_players = self.num_players_var.get()
        strategies = [var.get() for var in self.strategy_vars[:num_players]]
        
        self.result = {
            'num_players': num_players,
            'strategies': strategies,
            'collect_data': self.collect_data_var.get(),
            'show_suggestions': self.show_suggestions_var.get()
        }
        
        self.window.destroy()
    
    def cancel(self):
        """Bricht ab"""
        self.result = None
        self.window.destroy()


class BatchTrainingDialog:
    """Dialog für Batch-Training"""
    
    def __init__(self, parent):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Batch Training")
        self.window.geometry("400x350")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        """Erstellt Widgets"""
        # Title
        title_label = ttk.Label(
            self.window,
            text="Batch Training konfigurieren",
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=10)
        
        # Info
        info_text = """Trainiere das ML-Modell mit vielen simulierten Spielen.
Je mehr Spiele, desto besser wird das Modell."""
        
        ttk.Label(self.window, text=info_text, justify=tk.LEFT).pack(pady=10, padx=20)
        
        # Settings frame
        settings_frame = ttk.Frame(self.window, padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Number of games
        ttk.Label(settings_frame, text="Anzahl Spiele:").grid(row=0, column=0, sticky='w', pady=5)
        self.num_games_var = tk.IntVar(value=500)
        ttk.Spinbox(
            settings_frame,
            from_=100,
            to=10000,
            increment=100,
            textvariable=self.num_games_var,
            width=15
        ).grid(row=0, column=1, pady=5)
        
        # Model type
        ttk.Label(settings_frame, text="Modell-Typ:").grid(row=1, column=0, sticky='w', pady=5)
        self.model_type_var = tk.StringVar(value='random_forest')
        ttk.Combobox(
            settings_frame,
            textvariable=self.model_type_var,
            values=['random_forest', 'gradient_boost', 'neural_network', 'deep_learning'],
            state='readonly',
            width=15
        ).grid(row=1, column=1, pady=5)
        
        # Strategies to test
        ttk.Label(settings_frame, text="Strategien:").grid(row=2, column=0, sticky='nw', pady=5)
        
        strategy_frame = ttk.Frame(settings_frame)
        strategy_frame.grid(row=2, column=1, pady=5)
        
        self.strategy_vars = {}
        strategies = ['aggressive', 'balanced', 'economic', 'explorer']
        
        for strategy in strategies:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                strategy_frame,
                text=strategy.capitalize(),
                variable=var
            ).pack(anchor='w')
            self.strategy_vars[strategy] = var
        
        # Time estimate
        self.time_label = ttk.Label(settings_frame, text="Geschätzte Zeit: ~5 Minuten")
        self.time_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Update time estimate
        self.num_games_var.trace('w', self.update_time_estimate)
        
        # Buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Training starten",
            command=self.start_training
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.cancel
        ).pack(side=tk.LEFT, padx=5)
    
    def update_time_estimate(self, *args):
        """Aktualisiert Zeitschätzung"""
        num_games = self.num_games_var.get()
        estimated_seconds = num_games * 0.6  # ~0.6 Sekunden pro Spiel
        
        if estimated_seconds < 60:
            time_str = f"{estimated_seconds:.0f} Sekunden"
        elif estimated_seconds < 3600:
            time_str = f"{estimated_seconds/60:.1f} Minuten"
        else:
            time_str = f"{estimated_seconds/3600:.1f} Stunden"
        
        self.time_label.config(text=f"Geschätzte Zeit: ~{time_str}")
    
    def start_training(self):
        """Startet Training"""
        selected_strategies = [s for s, var in self.strategy_vars.items() if var.get()]
        
        if not selected_strategies:
            tk.messagebox.showwarning("Warnung", "Bitte wähle mindestens eine Strategie")
            return
        
        self.result = {
            'num_games': self.num_games_var.get(),
            'model_type': self.model_type_var.get(),
            'strategies': selected_strategies
        }
        
        self.window.destroy()
    
    def cancel(self):
        """Bricht ab"""
        self.result = None
        self.window.destroy()


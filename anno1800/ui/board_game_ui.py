# anno1800/ui/board_game_ui.py
"""
Anno 1800 Brettspiel-UI mit virtuellem Spielbrett und KI-Unterstützung
"""

import tkinter as tk
from tkinter import ttk, messagebox, Canvas
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os

from anno1800.game.engine import GameEngine, GameAction, GamePhase
from anno1800.game.player import PlayerState
from anno1800.game.board import Island
from anno1800.ml.model import Anno1800MLModel
from anno1800.utils.constants import (
    ActionType, BuildingType, PopulationType, ResourceType,
    BUILDING_DEFINITIONS, WORKFORCE_COSTS, UPGRADE_COSTS
)

logger = logging.getLogger(__name__)

@dataclass
class UIConfig:
    """Konfiguration für die UI"""
    WINDOW_WIDTH: int = 1600
    WINDOW_HEIGHT: int = 900
    BOARD_WIDTH: int = 1000
    BOARD_HEIGHT: int = 700
    CARD_WIDTH: int = 80
    CARD_HEIGHT: int = 120
    ISLAND_SIZE: int = 200
    BUILDING_SIZE: int = 40
    TOKEN_SIZE: int = 30
    
    # Farben Anno 1800 Style
    BG_COLOR: str = "#2a1810"
    BOARD_COLOR: str = "#8b7355"
    WATER_COLOR: str = "#4682b4"
    LAND_COLOR: str = "#8b7355"
    COAST_COLOR: str = "#d2b48c"
    
    # Bevölkerungsfarben (wie im Brettspiel)
    POP_COLORS: Dict = None
    
    def __post_init__(self):
        self.POP_COLORS = {
            PopulationType.FARMER: "#90ee90",      # Grün
            PopulationType.WORKER: "#4169e1",      # Blau
            PopulationType.CRAFTSMAN: "#dc143c",   # Rot
            PopulationType.ENGINEER: "#9370db",    # Lila
            PopulationType.INVESTOR: "#40e0d0"     # Türkis
        }

class IslandWidget:
    """Widget für eine Insel auf dem Spielbrett"""
    
    def __init__(self, canvas: Canvas, x: int, y: int, island_data: Island, size: int = 200):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.island = island_data
        self.size = size
        self.buildings = []
        self.ships = []
        self.selected = False
        
        self.draw()
    
    def draw(self):
        """Zeichnet die Insel"""
        # Insel-Grundform
        self.base = self.canvas.create_rectangle(
            self.x, self.y, 
            self.x + self.size, self.y + self.size,
            fill=UIConfig.LAND_COLOR,
            outline="black",
            width=2 if self.selected else 1,
            tags=("island", f"island_{self.island.id}")
        )
        
        # Name der Insel
        self.canvas.create_text(
            self.x + self.size//2, self.y + 10,
            text=self.island.name,
            font=("Arial", 10, "bold"),
            fill="white"
        )
        
        # Zeichne Felder (3x3 Grid)
        self.draw_fields()
    
    def draw_fields(self):
        """Zeichnet die Inselfelder"""
        field_size = self.size // 3
        
        for row in range(3):
            for col in range(3):
                x = self.x + col * field_size
                y = self.y + 30 + row * field_size
                
                # Bestimme Feldtyp
                if row == 0 or (row == 1 and col == 1):
                    # Landfeld
                    color = UIConfig.LAND_COLOR
                    field_type = "land"
                elif row == 1:
                    # Küste
                    color = UIConfig.COAST_COLOR
                    field_type = "coast"
                else:
                    # Meer
                    color = UIConfig.WATER_COLOR
                    field_type = "sea"
                
                field = self.canvas.create_rectangle(
                    x, y, x + field_size, y + field_size,
                    fill=color,
                    outline="gray",
                    tags=(f"field_{self.island.id}_{row}_{col}", field_type)
                )
    
    def add_building(self, building_type: BuildingType, position: Tuple[int, int]):
        """Fügt ein Gebäude hinzu"""
        row, col = position
        field_size = self.size // 3
        x = self.x + col * field_size + field_size//2
        y = self.y + 30 + row * field_size + field_size//2
        
        # Gebäude-Symbol
        building = self.canvas.create_rectangle(
            x - 15, y - 15, x + 15, y + 15,
            fill="#8b4513",
            outline="black",
            tags=(f"building_{building_type.value}",)
        )
        
        # Gebäude-Initial
        self.canvas.create_text(
            x, y,
            text=building_type.value[:2].upper(),
            font=("Arial", 8, "bold"),
            fill="white"
        )
        
        self.buildings.append(building)

class BoardGameUI:
    """Hauptfenster für die Brettspiel-UI"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Anno 1800 - Das Brettspiel")
        self.root.geometry(f"{UIConfig.WINDOW_WIDTH}x{UIConfig.WINDOW_HEIGHT}")
        self.root.configure(bg=UIConfig.BG_COLOR)
        
        self.config = UIConfig()
        self.game_engine = None
        self.ml_model = Anno1800MLModel()
        self.current_player = None
        self.selected_action = None
        self.ai_suggestion = None
        
        # UI Komponenten
        self.island_widgets = {}
        self.hand_cards = []
        self.population_tokens = {}
        
        self.setup_ui()
        self.load_ml_model()
    
    def setup_ui(self):
        """Erstellt die UI-Komponenten"""
        # Hauptcontainer
        main_frame = tk.Frame(self.root, bg=UIConfig.BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Linke Seite - Spielbrett
        self.setup_board(main_frame)
        
        # Rechte Seite - Spieler-Dashboard
        self.setup_dashboard(main_frame)
        
        # Unterer Bereich - Aktionsleiste
        self.setup_action_bar()
    
    def setup_board(self, parent):
        """Erstellt das virtuelle Spielbrett"""
        board_frame = tk.Frame(parent, bg=UIConfig.BG_COLOR)
        board_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Titel
        title = tk.Label(
            board_frame,
            text="ANNO 1800 - SPIELBRETT",
            font=("Old English Text MT", 24, "bold"),
            bg=UIConfig.BG_COLOR,
            fg="#d4af37"
        )
        title.pack(pady=5)
        
        # Canvas für das Spielbrett
        self.board_canvas = Canvas(
            board_frame,
            width=self.config.BOARD_WIDTH,
            height=self.config.BOARD_HEIGHT,
            bg=UIConfig.WATER_COLOR,
            highlightthickness=3,
            highlightbackground="#8b4513"
        )
        self.board_canvas.pack(padx=10, pady=10)
        
        # Zeichne Ozean-Hintergrund
        self.draw_ocean_background()
        
        # Platzhalter für Inseln
        self.draw_island_slots()
    
    def draw_ocean_background(self):
        """Zeichnet den Ozean-Hintergrund"""
        # Wellen-Effekt
        for i in range(0, self.config.BOARD_WIDTH, 50):
            self.board_canvas.create_arc(
                i, 0, i + 100, 50,
                start=0, extent=180,
                fill="", outline="#5f9ea0", width=1
            )
    
    def draw_island_slots(self):
        """Zeichnet Platzhalter für Inseln"""
        # Heimatinsel (zentral)
        self.home_island_pos = (400, 250)
        self.board_canvas.create_rectangle(
            self.home_island_pos[0], self.home_island_pos[1],
            self.home_island_pos[0] + 200, self.home_island_pos[1] + 200,
            fill=UIConfig.LAND_COLOR,
            outline="black",
            width=2,
            tags=("home_island",)
        )
        
        # Slots für Alte-Welt-Inseln
        self.old_world_slots = [
            (150, 100), (650, 100),
            (150, 400), (650, 400)
        ]
        
        for x, y in self.old_world_slots:
            self.board_canvas.create_rectangle(
                x, y, x + 150, y + 150,
                fill="", outline="gray",
                dash=(5, 5),
                tags=("old_world_slot",)
            )
    
    def setup_dashboard(self, parent):
        """Erstellt das Spieler-Dashboard"""
        dashboard = tk.Frame(parent, bg="#3e2723", width=500)
        dashboard.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        dashboard.pack_propagate(False)
        
        # Spieler-Info
        self.setup_player_info(dashboard)
        
        # Ressourcen-Anzeige
        self.setup_resources(dashboard)
        
        # Handkarten
        self.setup_hand_cards(dashboard)
        
        # KI-Empfehlung
        self.setup_ai_suggestion(dashboard)
    
    def setup_player_info(self, parent):
        """Spieler-Informationen"""
        info_frame = tk.Frame(parent, bg="#5d4037", relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Spielername
        self.player_name_label = tk.Label(
            info_frame,
            text="Spieler 1",
            font=("Arial", 16, "bold"),
            bg="#5d4037",
            fg="white"
        )
        self.player_name_label.pack(pady=5)
        
        # Runde und Phase
        self.round_label = tk.Label(
            info_frame,
            text="Runde 1 | Hauptphase",
            font=("Arial", 12),
            bg="#5d4037",
            fg="white"
        )
        self.round_label.pack()
    
    def setup_resources(self, parent):
        """Ressourcen-Anzeige"""
        resources_frame = tk.LabelFrame(
            parent,
            text="RESSOURCEN & BEVÖLKERUNG",
            font=("Arial", 12, "bold"),
            bg="#5d4037",
            fg="white"
        )
        resources_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Gold-Anzeige
        gold_frame = tk.Frame(resources_frame, bg="#5d4037")
        gold_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(gold_frame, text="Gold:", bg="#5d4037", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.gold_label = tk.Label(gold_frame, text="0", bg="#5d4037", fg="#ffd700", font=("Arial", 14, "bold"))
        self.gold_label.pack(side=tk.LEFT, padx=10)
        
        # Marine-Plättchen
        marine_frame = tk.Frame(resources_frame, bg="#5d4037")
        marine_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(marine_frame, text="Handel:", bg="#5d4037", fg="white").pack(side=tk.LEFT)
        self.trade_label = tk.Label(marine_frame, text="0", bg="#5d4037", fg="white", font=("Arial", 11, "bold"))
        self.trade_label.pack(side=tk.LEFT, padx=5)
        
        tk.Label(marine_frame, text="Erkundung:", bg="#5d4037", fg="white").pack(side=tk.LEFT, padx=(20, 0))
        self.exploration_label = tk.Label(marine_frame, text="0", bg="#5d4037", fg="white", font=("Arial", 11, "bold"))
        self.exploration_label.pack(side=tk.LEFT, padx=5)
        
        # Bevölkerung
        self.setup_population_display(resources_frame)
    
    def setup_population_display(self, parent):
        """Bevölkerungsanzeige wie im Brettspiel"""
        pop_frame = tk.Frame(parent, bg="#5d4037")
        pop_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.population_displays = {}
        
        for pop_type in PopulationType:
            # Container für jeden Bevölkerungstyp
            type_frame = tk.Frame(pop_frame, bg="#5d4037")
            type_frame.pack(side=tk.LEFT, padx=5)
            
            # Farbiger Kreis für Bevölkerungstyp
            canvas = Canvas(type_frame, width=40, height=40, bg="#5d4037", highlightthickness=0)
            canvas.pack()
            
            color = self.config.POP_COLORS[pop_type]
            canvas.create_oval(5, 5, 35, 35, fill=color, outline="black", width=2)
            
            # Anzahl
            count_label = tk.Label(type_frame, text="0", bg="#5d4037", fg="white", font=("Arial", 10, "bold"))
            count_label.pack()
            
            self.population_displays[pop_type] = {
                'canvas': canvas,
                'label': count_label,
                'count': 0
            }
    
    def setup_hand_cards(self, parent):
        """Handkarten-Anzeige"""
        cards_frame = tk.LabelFrame(
            parent,
            text="HANDKARTEN",
            font=("Arial", 12, "bold"),
            bg="#5d4037",
            fg="white"
        )
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbare Kartenansicht
        self.cards_canvas = Canvas(cards_frame, bg="#5d4037", height=150)
        self.cards_canvas.pack(fill=tk.X, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(cards_frame, orient="horizontal", command=self.cards_canvas.xview)
        scrollbar.pack(fill=tk.X)
        self.cards_canvas.configure(xscrollcommand=scrollbar.set)
    
    def setup_ai_suggestion(self, parent):
        """KI-Empfehlungsbereich"""
        ai_frame = tk.LabelFrame(
            parent,
            text="🤖 KI-BERATER",
            font=("Arial", 12, "bold"),
            bg="#5d4037",
            fg="white"
        )
        ai_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Empfohlene Aktion
        self.ai_action_label = tk.Label(
            ai_frame,
            text="Analysiere Spielsituation...",
            font=("Arial", 11, "italic"),
            bg="#5d4037",
            fg="#90ee90",
            wraplength=450
        )
        self.ai_action_label.pack(pady=5)
        
        # Konfidenz-Anzeige
        conf_frame = tk.Frame(ai_frame, bg="#5d4037")
        conf_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(conf_frame, text="Konfidenz:", bg="#5d4037", fg="white").pack(side=tk.LEFT)
        self.confidence_bar = ttk.Progressbar(conf_frame, length=200, mode='determinate')
        self.confidence_bar.pack(side=tk.LEFT, padx=10)
        self.confidence_label = tk.Label(conf_frame, text="0%", bg="#5d4037", fg="white")
        self.confidence_label.pack(side=tk.LEFT)
        
        # Begründung
        self.ai_reasoning = tk.Text(ai_frame, height=3, bg="#6d4c41", fg="white", font=("Arial", 9))
        self.ai_reasoning.pack(fill=tk.X, padx=10, pady=5)
    
    def setup_action_bar(self):
        """Aktionsleiste am unteren Rand"""
        action_bar = tk.Frame(self.root, bg="#3e2723", height=100)
        action_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Aktions-Buttons (wie im Brettspiel)
        actions = [
            ("🏗️ Bauen", self.action_build),
            ("🎴 Karte spielen", self.action_play_card),
            ("🔄 Karten tauschen", self.action_exchange),
            ("👥 Arbeitskraft", self.action_workforce),
            ("⬆️ Aufsteigen", self.action_upgrade),
            ("🗺️ Alte Welt", self.action_explore_old),
            ("🌴 Neue Welt", self.action_explore_new),
            ("🏛️ Expedition", self.action_expedition),
            ("🎉 Stadtfest", self.action_festival)
        ]
        
        for text, command in actions:
            btn = tk.Button(
                action_bar,
                text=text,
                command=command,
                font=("Arial", 10, "bold"),
                bg="#8b4513",
                fg="white",
                activebackground="#a0522d",
                relief=tk.RAISED,
                bd=3,
                padx=10,
                pady=5
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        # KI-Vorschlag übernehmen
        tk.Button(
            action_bar,
            text="✅ KI-Vorschlag",
            command=self.accept_ai_suggestion,
            font=("Arial", 10, "bold"),
            bg="#2e7d32",
            fg="white",
            padx=15,
            pady=5
        ).pack(side=tk.RIGHT, padx=10)
    
    def start_new_game(self):
        """Startet ein neues Spiel"""
        # Initialisiere Game Engine
        self.game_engine = GameEngine(num_players=2)
        self.game_engine.setup_game(
            player_names=["Spieler", "KI-Gegner"],
            strategies=["human", "balanced"]
        )
        
        self.current_player = self.game_engine.get_current_player()
        self.update_display()
        self.draw_home_island()
        
        # Erste KI-Empfehlung
        self.update_ai_suggestion()
    
    def draw_home_island(self):
        """Zeichnet die Heimatinsel des Spielers"""
        if not self.current_player:
            return
        
        # Erstelle Heimatinsel-Widget
        home_island = Island(
            id="home",
            name="Heimatinsel",
            type="home",
            land_tiles=6,
            coast_tiles=2,
            sea_tiles=1
        )
        
        island_widget = IslandWidget(
            self.board_canvas,
            self.home_island_pos[0],
            self.home_island_pos[1],
            home_island
        )
        
        self.island_widgets["home"] = island_widget
        
        # Füge Startgebäude hinzu
        island_widget.add_building(BuildingType.POTATO_FARM, (0, 0))
        island_widget.add_building(BuildingType.SAWMILL, (0, 1))
        island_widget.add_building(BuildingType.BRICKYARD, (1, 0))
    
    def update_display(self):
        """Aktualisiert die Anzeige"""
        if not self.current_player:
            return
        
        # Update Player Info
        self.player_name_label.config(text=self.current_player.name)
        self.round_label.config(text=f"Runde {self.game_engine.round_number} | {self.game_engine.phase.value}")
        
        # Update Resources
        self.gold_label.config(text=str(self.current_player.gold))
        self.trade_label.config(text=str(self.current_player.trade_tokens))
        self.exploration_label.config(text=str(self.current_player.exploration_tokens))
        
        # Update Population
        for pop_type, display in self.population_displays.items():
            count = self.current_player.population.get(pop_type, 0)
            display['label'].config(text=str(count))
        
        # Update Hand Cards
        self.draw_hand_cards()
    
    def draw_hand_cards(self):
        """Zeichnet die Handkarten"""
        # Lösche alte Karten
        self.cards_canvas.delete("all")
        
        if not self.current_player:
            return
        
        x = 10
        for i, card in enumerate(self.current_player.hand_cards):
            # Karte zeichnen
            card_id = self.cards_canvas.create_rectangle(
                x, 10, x + self.config.CARD_WIDTH, 10 + self.config.CARD_HEIGHT,
                fill="#8b7355",
                outline="black",
                width=2,
                tags=(f"card_{i}",)
            )
            
            # Kartentyp
            card_type = card.get('type', 'unknown')
            color = "#3e8e41" if 'farmer' in card_type else "#1976d2" if 'craftsman' in card_type else "#fdd835"
            
            self.cards_canvas.create_rectangle(
                x + 5, 15, x + self.config.CARD_WIDTH - 5, 35,
                fill=color,
                outline=""
            )
            
            # Punkte
            points = "3" if 'farmer' in card_type else "8" if 'craftsman' in card_type else "5"
            self.cards_canvas.create_text(
                x + self.config.CARD_WIDTH // 2, 50,
                text=points,
                font=("Arial", 20, "bold"),
                fill="white"
            )
            
            # Klick-Event
            self.cards_canvas.tag_bind(f"card_{i}", "<Button-1>", lambda e, idx=i: self.select_card(idx))
            
            x += self.config.CARD_WIDTH + 10
        
        # Scrollbereich aktualisieren
        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))
    
    def update_ai_suggestion(self):
        """Aktualisiert die KI-Empfehlung"""
        if not self.game_engine or not self.current_player:
            return
        
        if self.current_player.strategy != "human":
            return
        
        try:
            if self.ml_model.is_trained:
                # Hole KI-Vorhersage
                action, confidence = self.ml_model.predict(self.game_engine, self.current_player)
                
                if action:
                    self.ai_suggestion = action
                    
                    # Zeige Empfehlung
                    action_text = self.get_action_description(action)
                    self.ai_action_label.config(text=f"Empfehlung: {action_text}")
                    
                    # Konfidenz
                    conf_percent = confidence * 100
                    self.confidence_bar['value'] = conf_percent
                    self.confidence_label.config(text=f"{conf_percent:.1f}%")
                    
                    # Begründung
                    reasoning = self.generate_reasoning(action)
                    self.ai_reasoning.delete('1.0', tk.END)
                    self.ai_reasoning.insert('1.0', reasoning)
                else:
                    self.ai_action_label.config(text="KI analysiert...")
            else:
                self.ai_action_label.config(text="KI-Modell nicht trainiert")
                
        except Exception as e:
            logger.error(f"Fehler bei KI-Vorhersage: {e}")
            self.ai_action_label.config(text="KI-Fehler")
    
    def get_action_description(self, action: ActionType) -> str:
        """Gibt eine Beschreibung der Aktion zurück"""
        descriptions = {
            ActionType.BUILD: "Gebäude bauen",
            ActionType.PLAY_CARD: "Bevölkerungskarte ausspielen",
            ActionType.EXCHANGE_CARDS: "Karten austauschen",
            ActionType.INCREASE_WORKFORCE: "Arbeitskraft erhöhen",
            ActionType.UPGRADE_POPULATION: "Bevölkerung aufwerten",
            ActionType.EXPLORE_OLD_WORLD: "Alte Welt erkunden",
            ActionType.EXPLORE_NEW_WORLD: "Neue Welt erkunden",
            ActionType.EXPEDITION: "Expedition starten",
            ActionType.CITY_FESTIVAL: "Stadtfest feiern"
        }
        return descriptions.get(action, str(action))
    
    def generate_reasoning(self, action: ActionType) -> str:
        """Generiert eine Begründung für die KI-Empfehlung"""
        if action == ActionType.BUILD:
            return "Erweitere deine Produktionskapazitäten für mehr Ressourcen."
        elif action == ActionType.PLAY_CARD:
            return f"Du hast {len(self.current_player.hand_cards)} Karten. Spiele sie für Punkte aus."
        elif action == ActionType.CITY_FESTIVAL:
            return "Setze deine Arbeiter zurück für neue Produktionsmöglichkeiten."
        else:
            return "Diese Aktion verbessert deine Position im Spiel."
    
    def accept_ai_suggestion(self):
        """Übernimmt den KI-Vorschlag"""
        if self.ai_suggestion and self.game_engine:
            # Erstelle und führe Aktion aus
            action = GameAction(
                player_id=self.current_player.id,
                action_type=self.ai_suggestion,
                parameters={}
            )
            
            success = self.game_engine.execute_action(action)
            
            if success:
                self.show_action_animation(self.ai_suggestion)
                self.update_display()
                self.update_ai_suggestion()
                messagebox.showinfo("Erfolg", f"{self.get_action_description(self.ai_suggestion)} ausgeführt!")
            else:
                messagebox.showwarning("Fehler", "Aktion konnte nicht ausgeführt werden.")
    
    def show_action_animation(self, action: ActionType):
        """Zeigt eine Animation für die ausgeführte Aktion"""
        # Highlight-Effekt auf dem Brett
        if action == ActionType.BUILD:
            # Blink-Effekt auf Heimatinsel
            self.board_canvas.itemconfig("home_island", outline="gold", width=4)
            self.root.after(500, lambda: self.board_canvas.itemconfig("home_island", outline="black", width=2))
    
    # Action Handler
    def action_build(self):
        self.show_build_dialog()
    
    def action_play_card(self):
        self.show_play_card_dialog()
    
    def action_exchange(self):
        self.execute_action(ActionType.EXCHANGE_CARDS)
    
    def action_workforce(self):
        self.show_workforce_dialog()
    
    def action_upgrade(self):
        self.show_upgrade_dialog()
    
    def action_explore_old(self):
        self.execute_action(ActionType.EXPLORE_OLD_WORLD)
    
    def action_explore_new(self):
        self.execute_action(ActionType.EXPLORE_NEW_WORLD)
    
    def action_expedition(self):
        self.execute_action(ActionType.EXPEDITION)
    
    def action_festival(self):
        self.execute_action(ActionType.CITY_FESTIVAL)
    
    def show_build_dialog(self):
        """Dialog zum Gebäudebau"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Gebäude bauen")
        dialog.geometry("400x500")
        dialog.configure(bg="#5d4037")
        
        tk.Label(dialog, text="Wähle ein Gebäude:", bg="#5d4037", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Liste verfügbarer Gebäude
        listbox = tk.Listbox(dialog, bg="#6d4c41", fg="white", font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        available_buildings = []
        if self.game_engine and self.current_player:
            for building_type in BuildingType:
                if self.game_engine.board.available_buildings.get(building_type, 0) > 0:
                    building_def = BUILDING_DEFINITIONS.get(building_type, {})
                    cost = building_def.get('cost', {})
                    
                    if self.current_player.can_afford_resources(cost):
                        cost_str = ", ".join([f"{v} {k.value}" for k, v in cost.items()])
                        listbox.insert(tk.END, f"{building_type.value} - Kosten: {cost_str}")
                        available_buildings.append(building_type)
        
        def build_selected():
            selection = listbox.curselection()
            if selection:
                building_type = available_buildings[selection[0]]
                action = GameAction(
                    player_id=self.current_player.id,
                    action_type=ActionType.BUILD,
                    parameters={'building_type': building_type.name}
                )
                
                if self.game_engine.execute_action(action):
                    # Füge Gebäude zur Insel hinzu
                    if "home" in self.island_widgets:
                        import random
                        pos = (random.randint(0, 2), random.randint(0, 2))
                        self.island_widgets["home"].add_building(building_type, pos)
                    
                    self.update_display()
                    self.update_ai_suggestion()
                    dialog.destroy()
                    messagebox.showinfo("Erfolg", f"{building_type.value} gebaut!")
        
        tk.Button(
            dialog,
            text="Bauen",
            command=build_selected,
            bg="#8b4513",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(pady=10)
    
    def show_play_card_dialog(self):
        """Dialog zum Kartenspielen"""
        if not self.current_player or not self.current_player.hand_cards:
            messagebox.showwarning("Keine Karten", "Du hast keine Handkarten!")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Karte ausspielen")
        dialog.geometry("500x400")
        dialog.configure(bg="#5d4037")
        
        tk.Label(dialog, text="Wähle eine Karte:", bg="#5d4037", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Canvas für Karten
        canvas = Canvas(dialog, bg="#6d4c41", height=200)
        canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        selected_card_idx = tk.IntVar(value=-1)
        
        x = 10
        for i, card in enumerate(self.current_player.hand_cards):
            # Zeichne Karte
            card_rect = canvas.create_rectangle(
                x, 20, x + 80, 140,
                fill="#8b7355",
                outline="black",
                width=2,
                tags=(f"dialog_card_{i}",)
            )
            
            # Klick-Handler
            def select(idx=i, rect=card_rect):
                selected_card_idx.set(idx)
                # Highlight selected card
                canvas.itemconfig(rect, outline="gold", width=3)
            
            canvas.tag_bind(f"dialog_card_{i}", "<Button-1>", lambda e, idx=i: select(idx))
            
            x += 90
        
        def play_selected():
            idx = selected_card_idx.get()
            if idx >= 0:
                card = self.current_player.hand_cards[idx]
                action = GameAction(
                    player_id=self.current_player.id,
                    action_type=ActionType.PLAY_CARD,
                    parameters={'card_id': card.get('id')}
                )
                
                if self.game_engine.execute_action(action):
                    self.update_display()
                    self.update_ai_suggestion()
                    dialog.destroy()
                    messagebox.showinfo("Erfolg", "Karte ausgespielt!")
        
        tk.Button(
            dialog,
            text="Ausspielen",
            command=play_selected,
            bg="#8b4513",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(pady=10)
    
    def show_workforce_dialog(self):
        """Dialog für Arbeitskraft erhöhen"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Arbeitskraft erhöhen")
        dialog.geometry("400x300")
        dialog.configure(bg="#5d4037")
        
        tk.Label(dialog, text="Wähle Bevölkerungstyp:", bg="#5d4037", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        selected_type = tk.StringVar()
        
        for pop_type in [PopulationType.FARMER, PopulationType.WORKER, PopulationType.CRAFTSMAN]:
            cost = WORKFORCE_COSTS.get(pop_type, {})
            cost_str = ", ".join([f"{v} {k.value}" for k, v in cost.items()])
            
            radio = tk.Radiobutton(
                dialog,
                text=f"{pop_type.value} - Kosten: {cost_str}",
                variable=selected_type,
                value=pop_type.name,
                bg="#5d4037",
                fg="white",
                selectcolor="#8b4513",
                font=("Arial", 10)
            )
            radio.pack(pady=5)
        
        def add_workforce():
            if selected_type.get():
                action = GameAction(
                    player_id=self.current_player.id,
                    action_type=ActionType.INCREASE_WORKFORCE,
                    parameters={'population_type': selected_type.get()}
                )
                
                if self.game_engine.execute_action(action):
                    self.update_display()
                    self.update_ai_suggestion()
                    dialog.destroy()
                    messagebox.showinfo("Erfolg", "Arbeitskraft erhöht!")
        
        tk.Button(
            dialog,
            text="Hinzufügen",
            command=add_workforce,
            bg="#8b4513",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(pady=20)
    
    def show_upgrade_dialog(self):
        """Dialog für Bevölkerungs-Upgrade"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Bevölkerung aufwerten")
        dialog.geometry("400x300")
        dialog.configure(bg="#5d4037")
        
        tk.Label(dialog, text="Wähle Upgrade:", bg="#5d4037", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        selected_upgrade = tk.StringVar()
        
        upgrades = [
            (PopulationType.FARMER, PopulationType.WORKER),
            (PopulationType.WORKER, PopulationType.CRAFTSMAN),
            (PopulationType.CRAFTSMAN, PopulationType.ENGINEER),
            (PopulationType.ENGINEER, PopulationType.INVESTOR)
        ]
        
        for from_type, to_type in upgrades:
            if self.current_player.get_available_population(from_type) > 0:
                cost = UPGRADE_COSTS.get((from_type, to_type), {})
                cost_str = ", ".join([f"{v} {k.value}" for k, v in cost.items()])
                
                radio = tk.Radiobutton(
                    dialog,
                    text=f"{from_type.value} → {to_type.value} - Kosten: {cost_str}",
                    variable=selected_upgrade,
                    value=f"{from_type.name},{to_type.name}",
                    bg="#5d4037",
                    fg="white",
                    selectcolor="#8b4513",
                    font=("Arial", 10)
                )
                radio.pack(pady=5)
        
        def do_upgrade():
            if selected_upgrade.get():
                from_str, to_str = selected_upgrade.get().split(',')
                action = GameAction(
                    player_id=self.current_player.id,
                    action_type=ActionType.UPGRADE_POPULATION,
                    parameters={
                        'from_type': from_str,
                        'to_type': to_str,
                        'amount': 1
                    }
                )
                
                if self.game_engine.execute_action(action):
                    self.update_display()
                    self.update_ai_suggestion()
                    dialog.destroy()
                    messagebox.showinfo("Erfolg", "Bevölkerung aufgewertet!")
        
        tk.Button(
            dialog,
            text="Aufwerten",
            command=do_upgrade,
            bg="#8b4513",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(pady=20)
    
    def execute_action(self, action_type: ActionType):
        """Führt eine einfache Aktion aus"""
        if not self.game_engine or not self.current_player:
            return
        
        action = GameAction(
            player_id=self.current_player.id,
            action_type=action_type,
            parameters={}
        )
        
        if self.game_engine.execute_action(action):
            # Spezielle Visualisierungen
            if action_type == ActionType.EXPLORE_OLD_WORLD:
                self.add_old_world_island()
            elif action_type == ActionType.EXPLORE_NEW_WORLD:
                self.add_new_world_island()
            elif action_type == ActionType.CITY_FESTIVAL:
                self.show_festival_animation()
            
            self.update_display()
            self.update_ai_suggestion()
            messagebox.showinfo("Erfolg", f"{self.get_action_description(action_type)} erfolgreich!")
        else:
            messagebox.showwarning("Fehler", f"{self.get_action_description(action_type)} nicht möglich!")
    
    def add_old_world_island(self):
        """Fügt eine Alte-Welt-Insel zum Brett hinzu"""
        if self.current_player and self.current_player.old_world_islands:
            # Finde freien Slot
            for i, (x, y) in enumerate(self.old_world_slots):
                slot_key = f"old_world_{i}"
                if slot_key not in self.island_widgets:
                    # Füge Insel hinzu
                    island = self.current_player.old_world_islands[-1]
                    island_widget = IslandWidget(
                        self.board_canvas,
                        x, y,
                        island,
                        size=150
                    )
                    self.island_widgets[slot_key] = island_widget
                    break
    
    def add_new_world_island(self):
        """Visualisiert eine Neue-Welt-Insel"""
        # Zeige Neue-Welt-Marker
        self.board_canvas.create_oval(
            50, 50, 100, 100,
            fill="#90ee90",
            outline="gold",
            width=3,
            tags=("new_world_marker",)
        )
        
        self.board_canvas.create_text(
            75, 75,
            text="🌴",
            font=("Arial", 24)
        )
    
    def show_festival_animation(self):
        """Zeigt Stadtfest-Animation"""
        # Feuerwerk-Effekt
        for _ in range(5):
            x = self.home_island_pos[0] + 100 + (50 - 100 * __import__('random').random())
            y = self.home_island_pos[1] + 100
            
            firework = self.board_canvas.create_oval(
                x - 5, y - 5, x + 5, y + 5,
                fill="gold",
                outline=""
            )
            
            # Explosion animation
            def explode(fw=firework, cx=x, cy=y):
                for i in range(1, 6):
                    self.board_canvas.coords(
                        fw,
                        cx - i*10, cy - i*10,
                        cx + i*10, cy + i*10
                    )
                    self.board_canvas.itemconfig(fw, outline="gold", width=2, fill="")
                    self.root.update()
                    self.root.after(50)
                self.board_canvas.delete(fw)
            
            self.root.after(200 * _, explode)
    
    def select_card(self, card_index: int):
        """Wählt eine Handkarte aus"""
        # Highlight ausgewählte Karte
        self.cards_canvas.itemconfig("all", outline="black", width=2)
        self.cards_canvas.itemconfig(f"card_{card_index}", outline="gold", width=3)
    
    def load_ml_model(self):
        """Lädt das trainierte ML-Modell"""
        model_path = "models/anno1800_model.pkl"
        if os.path.exists(model_path):
            try:
                self.ml_model.load(model_path)
                logger.info("ML-Modell geladen")
            except Exception as e:
                logger.warning(f"Konnte ML-Modell nicht laden: {e}")
        else:
            logger.info("Kein trainiertes ML-Modell gefunden")

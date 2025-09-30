# ================================================================================
# anno1800/ui/main_window.py
# ================================================================================
"""
Haupt-UI für Anno 1800 Simulator
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
from datetime import datetime
import json
import os
import logging
import random
import time
from typing import Dict, List, Optional, Tuple

from anno1800.game.engine import GameEngine, GameAction, GamePhase
from anno1800.game.player import PlayerState
from anno1800.ai.strategy import AIStrategy
from anno1800.ml.model import Anno1800MLModel
from anno1800.ui.dialogs import BatchTrainingDialog, NewGameDialog
from anno1800.utils.constants import ActionType, BuildingType, PopulationType

logger = logging.getLogger(__name__)

class Anno1800App:
    """Hauptanwendung für Anno 1800 Simulator"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Anno 1800 Brettspiel Simulator - KI Training & Analyse")
        self.root.geometry("1400x800")
        
        # Game components
        self.game_engine = None
        self.ml_model = Anno1800MLModel()
        self.ai_strategies = {}
        
        # UI state
        self.simulation_running = False
        self.update_queue = queue.Queue()
        
        # Statistics
        self.stats = {
            'games_played': 0,
            'training_data': [],
            'strategy_wins': {},
            'game_history': []
        }
        
        self.setup_ui()
        self.load_ml_model()
        self.process_queue()
        
    def setup_ui(self):
        """Erstellt die UI-Komponenten"""
        
        # Menu Bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Neues Spiel", command=self.new_game)
        file_menu.add_separator()
        file_menu.add_command(label="Modell laden", command=self.load_model_dialog)
        file_menu.add_command(label="Modell speichern", command=self.save_model_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)
        
        # Simulation Menu
        sim_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Simulation", menu=sim_menu)
        sim_menu.add_command(label="Simulation starten", command=self.start_simulation)
        sim_menu.add_command(label="Simulation stoppen", command=self.stop_simulation)
        sim_menu.add_separator()
        sim_menu.add_command(label="Batch-Training", command=self.batch_training)
        
        # Analysis Menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analyse", menu=analysis_menu)
        analysis_menu.add_command(label="Statistiken anzeigen", command=self.show_statistics)
        analysis_menu.add_command(label="Trainingsdaten exportieren", command=self.export_training_data)
        
        # Top Control Panel
        control_panel = ttk.Frame(self.root)
        control_panel.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_panel, text="🎮 Neues Spiel", command=self.new_game).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_panel, text="🤖 Simulation starten", command=self.start_simulation).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_panel, text="🛑 Simulation stoppen", command=self.stop_simulation).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_panel, text="🧠 ML Training", command=self.train_model).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_panel, text="📊 KI-Vorschlag", command=self.get_ai_suggestion).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_panel, text="📊 Daten-Status", command=self.check_training_data_status).pack(side=tk.LEFT, padx=2)
        
        self.status_label = ttk.Label(control_panel, text="Bereit", font=('Arial', 10, 'bold'))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Main Content Area
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left Panel - Game View
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=2)
        
        # Game Info
        game_frame = ttk.LabelFrame(left_frame, text="Spielinformation", padding=10)
        game_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Players TreeView
        self.players_tree = ttk.Treeview(
            game_frame,
            columns=('Strategy', 'Gold', 'Cards', 'Buildings', 'Islands', 'Score'),
            height=6
        )
        self.players_tree.heading('#0', text='Spieler')
        self.players_tree.heading('Strategy', text='Strategie')
        self.players_tree.heading('Gold', text='Gold')
        self.players_tree.heading('Cards', text='Karten')
        self.players_tree.heading('Buildings', text='Gebäude')
        self.players_tree.heading('Islands', text='Inseln')
        self.players_tree.heading('Score', text='Punkte')
        
        for col in ('Strategy', 'Gold', 'Cards', 'Buildings', 'Islands', 'Score'):
            self.players_tree.column(col, width=80)
        
        self.players_tree.pack(fill=tk.BOTH, expand=True)
        
        # Current Action Frame
        action_frame = ttk.LabelFrame(left_frame, text="Aktuelle Aktion", padding=5)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.action_label = ttk.Label(action_frame, text="Keine aktuelle Aktion", font=('Arial', 10))
        self.action_label.pack(pady=5)
        
        # Game Log
        log_frame = ttk.LabelFrame(left_frame, text="Spielverlauf", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.game_log = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.game_log.pack(fill=tk.BOTH, expand=True)
        
        # Middle Panel - AI Suggestions
        middle_frame = ttk.Frame(main_paned)
        main_paned.add(middle_frame, weight=1)
        
        # AI Suggestion
        ai_frame = ttk.LabelFrame(middle_frame, text="🤖 KI-Vorschlag", padding=10)
        ai_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.suggestion_label = ttk.Label(
            ai_frame,
            text="Keine Vorschläge verfügbar",
            font=('Arial', 12, 'bold'),
            wraplength=300
        )
        self.suggestion_label.pack(pady=10)
        
        # Confidence
        conf_frame = ttk.Frame(ai_frame)
        conf_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(conf_frame, text="Konfidenz:").pack(side=tk.LEFT)
        self.confidence_bar = ttk.Progressbar(conf_frame, length=200, mode='determinate')
        self.confidence_bar.pack(side=tk.LEFT, padx=10)
        self.confidence_label = ttk.Label(conf_frame, text="0%")
        self.confidence_label.pack(side=tk.LEFT)
        
        # Reasoning
        ttk.Label(ai_frame, text="Begründung:").pack(pady=(10, 5))
        self.reasoning_text = scrolledtext.ScrolledText(ai_frame, height=8, width=40)
        self.reasoning_text.pack(fill=tk.BOTH, expand=True)
        
        # Actions
        action_frame = ttk.Frame(ai_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="✅ Annehmen", command=self.accept_suggestion).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🔄 Neu berechnen", command=self.recalculate_suggestion).pack(side=tk.LEFT, padx=5)
        
        # Right Panel - Statistics
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # Statistics
        stats_frame = ttk.LabelFrame(right_frame, text="📊 Statistiken", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=15)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # ML Model Info
        ml_frame = ttk.LabelFrame(right_frame, text="🧠 ML-Modell", padding=10)
        ml_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.model_info_label = ttk.Label(ml_frame, text="Modell: Nicht trainiert")
        self.model_info_label.pack(pady=5)
        
        self.training_progress = ttk.Progressbar(ml_frame, mode='indeterminate')
        self.training_progress.pack(fill=tk.X, pady=5)
        
        # Simulation Progress
        sim_frame = ttk.LabelFrame(right_frame, text="📈 Simulationsfortschritt", padding=10)
        sim_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.sim_progress_label = ttk.Label(sim_frame, text="Keine Simulation aktiv")
        self.sim_progress_label.pack(pady=5)
        
        self.sim_progress_bar = ttk.Progressbar(sim_frame, mode='determinate')
        self.sim_progress_bar.pack(fill=tk.X, pady=5)
        
        # Bottom Status Bar
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_text = ttk.Label(status_bar, text="Bereit", relief=tk.SUNKEN, anchor=tk.W)
        self.status_text.pack(fill=tk.X, padx=2, pady=1)
    
    def new_game(self):
        """Startet ein neues Spiel"""
        dialog = NewGameDialog(self.root)
        self.root.wait_window(dialog.window)
        
        if dialog.result:
            self.start_new_game(dialog.result)
    
    def start_new_game(self, settings):
        """Initialisiert ein neues Spiel"""
        try:
            # Create game
            self.game_engine = GameEngine(settings['num_players'])
            
            # Setup players
            player_names = [f"Spieler {i+1}" for i in range(settings['num_players'])]
            self.game_engine.setup_game(player_names, settings['strategies'])
            
            # Create AI controllers
            self.ai_strategies = {}
            for i, strategy in enumerate(settings['strategies']):
                if strategy != 'human':
                    self.ai_strategies[i] = AIStrategy(strategy)
            
            # Update UI
            self.update_game_display()
            self.log_message("Neues Spiel gestartet")
            self.update_status("Spiel gestartet")
            
            # Start game loop if all AI
            if 'human' not in settings['strategies']:
                self.run_ai_game()
            
        except Exception as e:
            logger.error(f"Fehler beim Spielstart: {e}")
            messagebox.showerror("Fehler", f"Konnte Spiel nicht starten: {e}")
    
    def run_ai_game(self):
        """Führt ein Spiel mit KI-Spielern aus"""
        if not self.game_engine:
            return
        
        def game_loop():
            try:
                while (self.game_engine and 
                       self.game_engine.phase != GamePhase.ENDED and 
                       not self.game_engine.game_end_triggered):
                    
                    current_player = self.game_engine.get_current_player()
                    
                    if current_player.id in self.ai_strategies:
                        # AI player's turn
                        ai = self.ai_strategies[current_player.id]
                        action = ai.decide_action(self.game_engine, current_player)
                        
                        self.update_queue.put(('action', f"{current_player.name} führt aus: {action.action_type.value}"))
                        
                        success = self.game_engine.execute_action(action)
                        
                        if not success:
                            # Fallback to city festival
                            if ActionType.STADTFEST  in self.game_engine.get_available_actions(current_player):
                                fallback_action = GameAction(
                                    player_id=current_player.id,
                                    action_type=ActionType.STADTFEST ,
                                    parameters={}
                                )
                                self.game_engine.execute_action(fallback_action)
                    
                    self.update_queue.put(('update_display', None))
                    time.sleep(0.5)  # Pause for visibility
                
                # Game ended, calculate scores
                if self.game_engine:
                    winner = self.determine_winner(self.game_engine)
                    self.update_queue.put(('log', f"Spiel beendet! Gewinner: {winner}"))
                    self.update_queue.put(('update_display', None))
                    
            except Exception as e:
                logger.error(f"Fehler im Spielablauf: {e}")
                self.update_queue.put(('log', f"Fehler: {e}"))
        
        # Start game loop in thread
        thread = threading.Thread(target=game_loop, daemon=True)
        thread.start()
    
    def determine_winner(self, game):
        """Bestimmt den Gewinner des Spiels"""
        scores = {}
        for player in game.players:
            score = player.calculate_score()
            scores[player.name] = score
        
        max_score = max(scores.values())
        winners = [name for name, score in scores.items() if score == max_score]
        
        if len(winners) == 1:
            return winners[0]
        else:
            # Tiebreaker: most buildings
            building_counts = {}
            for player in game.players:
                if player.name in winners:
                    building_counts[player.name] = len(player.buildings)
            
            max_buildings = max(building_counts.values())
            final_winners = [name for name, count in building_counts.items() 
                            if count == max_buildings]
            
            return random.choice(final_winners) if final_winners else winners[0]
    
    def update_game_display(self):
        """Aktualisiert die Spielanzeige"""
        if not self.game_engine:
            return
        
        # Clear tree
        for item in self.players_tree.get_children():
            self.players_tree.delete(item)
        
        # Add players
        for player in self.game_engine.players:
            total_islands = len(player.old_world_islands) + len(player.new_world_islands)
            self.players_tree.insert('', 'end',
                text=player.name,
                values=(
                    player.strategy,
                    player.gold,
                    len(player.hand_cards),
                    len(player.buildings),
                    total_islands,
                    player.final_score
                )
            )
        
        # Update statistics
        self.update_statistics()
    
    def update_statistics(self):
        """Aktualisiert Statistiken"""
        stats_text = f"""
Gespielte Spiele: {self.stats['games_played']}

Aktuelles Spiel:
  Runde: {self.game_engine.round_number if self.game_engine else 0}
  Phase: {self.game_engine.phase.value if self.game_engine else 'N/A'}
  Aktiver Spieler: {self.game_engine.players[self.game_engine.current_player_idx].name if self.game_engine else 'N/A'}

Siegesstatistik:
"""
        for strategy, wins in self.stats.get('strategy_wins', {}).items():
            total = self.stats.get('games_played', 1) or 1
            win_rate = (wins / total) * 100 if total > 0 else 0
            stats_text += f"  {strategy}: {wins} Siege ({win_rate:.1f}%)\n"
        
        # ML Model Info
        if hasattr(self.ml_model, 'is_trained') and self.ml_model.is_trained:
            stats_text += f"\nML-Modell: {self.ml_model.model_type}\n"
            stats_text += f"Trainingsdaten: {len(self.stats.get('training_data', []))} Beispiele\n"
        
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats_text)
    
    def log_message(self, message: str, level: str = 'info'):
        """Fügt eine Nachricht zum Log hinzu"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {
            'info': 'black',
            'warning': 'orange',
            'error': 'red',
            'success': 'green'
        }.get(level, 'black')
        
        self.game_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.game_log.see(tk.END)
    
    def update_status(self, message: str):
        """Aktualisiert Statusleiste"""
        self.status_text.config(text=message)
    
    def process_queue(self):
        """Verarbeitet UI-Update Queue"""
        try:
            while True:
                msg_type, data = self.update_queue.get_nowait()
                
                if msg_type == 'status':
                    self.status_label.config(text=data)
                elif msg_type == 'log':
                    self.log_message(data)
                elif msg_type == 'action':
                    self.action_label.config(text=data)
                elif msg_type == 'update_display':
                    self.update_game_display()
                elif msg_type == 'training_complete':
                    self.on_training_complete(data)
                elif msg_type == 'simulation_progress':
                    self.update_simulation_progress(data)
                
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
    
    def start_simulation(self):
        """Startet Simulation"""
        if self.simulation_running:
            messagebox.showinfo("Info", "Simulation läuft bereits")
            return
        
        self.simulation_running = True
        self.log_message("Simulation gestartet")
        self.sim_progress_bar['value'] = 0
        self.sim_progress_label.config(text="Simulation läuft...")
        
        # Start in thread
        thread = threading.Thread(target=self.run_simulation, daemon=True)
        thread.start()
    
    def stop_simulation(self):
        """Stoppt Simulation"""
        self.simulation_running = False
        self.log_message("Simulation gestoppt")
        self.sim_progress_label.config(text="Simulation gestoppt")
    
    def run_simulation(self):
        """Führt Simulation aus"""
        num_games = 100
        
        for i in range(num_games):
            if not self.simulation_running:
                break
            
            self.update_queue.put(('status', f"Simulation: Spiel {i+1}/{num_games}"))
            self.update_queue.put(('simulation_progress', (i+1, num_games)))
            self.update_queue.put(('log', f"Starte Simulationsspiel {i+1}"))
            
            try:
                # Create game with random strategies
                strategies = self._get_random_strategies(4)
                game = GameEngine(4)
                player_names = [f"AI_{s}_{i+1}" for s in strategies]
                game.setup_game(player_names, strategies)
                
                # Play the game to completion
                game_result = self._play_game_to_completion(game)
                
                # Record statistics
                self._record_game_statistics(game_result)
                
                # Collect training data if ML model is available
                self._collect_training_data(game_result)
                
                self.update_queue.put(('log', f"Spiel {i+1} abgeschlossen - Sieger: {game_result['winner']}"))
                
            except Exception as e:
                logger.error(f"Fehler in Simulationsspiel {i+1}: {e}")
                self.update_queue.put(('log', f"Fehler in Spiel {i+1}: {e}"))
            
            # Small delay to prevent UI freezing
            time.sleep(0.1)
        
        self.simulation_running = False
        self.update_queue.put(('status', 'Bereit'))
        self.update_queue.put(('log', f'Simulation abgeschlossen - {num_games} Spiele gespielt'))
        self.update_queue.put(('update_display', None))
    
    def _get_random_strategies(self, num_players: int):
        """Gibt zufällige Strategien für Spieler zurück"""
        strategies = ['aggressive', 'balanced', 'economic', 'explorer']
        return [random.choice(strategies) for _ in range(num_players)]
    
    def _play_game_to_completion(self, game: GameEngine):
        """Spielt ein Spiel bis zum Ende und gibt Ergebnis zurück"""
        max_rounds = 50
        
        # Create AI controllers for all players
        ai_controllers = {}
        for i, player in enumerate(game.players):
            ai_controllers[i] = AIStrategy(player.strategy)
        
        # Game loop
        round_count = 0
        while (game.phase != GamePhase.ENDED and 
               not game.game_end_triggered and 
               round_count < max_rounds):
            
            try:
                current_player = game.get_current_player()
                
                # Skip if player has no actions
                available_actions = game.get_available_actions(current_player)
                if not available_actions:
                    game.next_turn()
                    round_count += 1
                    continue
                
                # Get AI decision
                ai_controller = ai_controllers[current_player.id]
                action = ai_controller.decide_action(game, current_player)
                
                # Execute action
                success = game.execute_action(action)
                
                if not success:
                    # Fallback: City Festival
                    if ActionType.STADTFEST in available_actions:
                        fallback_action = GameAction(
                            player_id=current_player.id,
                            action_type=ActionType.STADTFEST,
                            parameters={}
                        )
                        game.execute_action(fallback_action)
                    else:
                        game.next_turn()
                
                # Check for game end conditions
                self._check_game_end_conditions(game)
                
                round_count += 1
                
            except Exception as e:
                logger.error(f"Fehler in Spielrunde {round_count}: {e}")
                game.next_turn()
                round_count += 1
        
        # Calculate final scores
        winner = self.determine_winner(game)
        
        return {
            'game': game,
            'winner': winner,
            'rounds_played': round_count,
            'final_scores': {p.name: p.calculate_score() for p in game.players}
        }
    
    def _check_game_end_conditions(self, game: GameEngine):
        """Prüft Spielende-Bedingungen"""
        for player in game.players:
            if len(player.hand_cards) == 0 and not game.game_end_triggered:
                game._trigger_game_end(player)
                return
        
        if (hasattr(game.board, 'expedition_cards') and 
            len(game.board.expedition_cards) == 0):
            game.game_end_triggered = True
            game.phase = GamePhase.FINAL_ROUND
    
    def _record_game_statistics(self, game_result: Dict):
        """Zeichnet Spielstatistiken auf"""
        self.stats['games_played'] += 1
        
        winner = game_result['winner']
        winning_strategy = None
        
        for player in game_result['game'].players:
            if player.name == winner:
                winning_strategy = player.strategy
                break
        
        if winning_strategy:
            if winning_strategy not in self.stats['strategy_wins']:
                self.stats['strategy_wins'][winning_strategy] = 0
            self.stats['strategy_wins'][winning_strategy] += 1
        
        game_data = {
            'winner': winner,
            'winning_strategy': winning_strategy,
            'rounds': game_result['rounds_played'],
            'final_scores': game_result['final_scores'],
            'timestamp': datetime.now().isoformat()
        }
        
        self.stats['game_history'].append(game_data)
    
    def _collect_training_data(self, game_result: Dict):
        """Sammelt Trainingsdaten für ML-Modell"""
        if not hasattr(self, 'ml_model'):
            return

        try:
            game = game_result['game']

            # Collect state-action pairs from game history
            training_examples = []

            for action in game.action_history:
                if action.success and action.player_id < len(game.players):
                    player = game.players[action.player_id]

                    # Create training example
                    training_example = {
                        'game_id': f"game_{self.stats['games_played']}",
                        'player_id': player.id,
                        'player_name': player.name,
                        'strategy': player.strategy,
                        'action_type': action.action_type.name,
                        'round': game.round_number,
                        'player_state': {
                            'gold': player.gold,
                            'hand_cards': len(player.hand_cards),
                            'buildings': len(player.buildings),
                            'population': dict((k.value, v) for k, v in player.population.items()),
                            'islands': len(player.old_world_islands) + len(player.new_world_islands),
                            'score': player.final_score
                        },
                        'game_state': {
                            'round': game.round_number,
                            'phase': game.phase.value,
                            'available_buildings': sum(game.board.available_buildings.values()),
                            'remaining_islands': len(game.board.old_world_islands) + len(game.board.new_world_islands)
                        },
                        'result': 'win' if game_result['winner'] == player.name else 'lose',
                        'timestamp': datetime.now().isoformat()
                    }

                    training_examples.append(training_example)

            # Add to training data
            if 'training_data' not in self.stats:
                self.stats['training_data'] = []

            self.stats['training_data'].extend(training_examples)

            # Also add a simplified version for ML training
            simplified_data = self._create_simplified_training_data(training_examples)
            if 'ml_training_data' not in self.stats:
                self.stats['ml_training_data'] = []
            self.stats['ml_training_data'].extend(simplified_data)

            # Log data collection
            self.log_message(f"Gesammelte Trainingsdaten: {len(training_examples)} Beispiele")

            # Limit training data size to prevent memory issues
            max_training_data = 10000
            if len(self.stats['training_data']) > max_training_data:
                self.stats['training_data'] = self.stats['training_data'][-max_training_data:]
            if len(self.stats.get('ml_training_data', [])) > max_training_data:
                self.stats['ml_training_data'] = self.stats['ml_training_data'][-max_training_data:]

        except Exception as e:
            logger.error(f"Fehler beim Sammeln von Trainingsdaten: {e}")

    def _create_simplified_training_data(self, training_examples: List[Dict]) -> List[Dict]:
        """Erstellt vereinfachte Trainingsdaten für ML-Modell"""
        simplified_data = []

        for example in training_examples:
            simplified_example = {
                'features': [
                    example['player_state']['gold'],
                    example['player_state']['hand_cards'],
                    example['player_state']['buildings'],
                    example['player_state']['islands'],
                    example['game_state']['round'],
                    example['game_state']['available_buildings'],
                    example['game_state']['remaining_islands']
                ],
                'action': example['action_type'],
                'strategy': example['strategy'],
                'result': example['result']
            }
            simplified_data.append(simplified_example)

        return simplified_data

    
    def update_simulation_progress(self, progress_data):
        """Aktualisiert Simulationsfortschritt"""
        current, total = progress_data
        percentage = (current / total) * 100
        self.sim_progress_bar['value'] = percentage
        self.sim_progress_label.config(text=f"Simulation: {current}/{total} ({percentage:.1f}%)")
    
    def train_model(self):
      """Trainiert ML-Modell"""
      # Check available data sources
      training_data = self.stats.get('ml_training_data', [])
      if not training_data:
          # Fallback to regular training data
          training_data = self.stats.get('training_data', [])
      
      if len(training_data) < 100:
          messagebox.showwarning(
              "Warnung", 
              f"Nicht genug Trainingsdaten (benötigt: 100, vorhanden: {len(training_data)})\n"
              f"Führen Sie zuerst Simulationen durch, um Daten zu sammeln."
          )
          return
      
      self.log_message(f"Starte ML-Training mit {len(training_data)} Datenpunkten...")
      self.training_progress.start()
      
      # Train in thread
      thread = threading.Thread(target=self._train_model_thread, daemon=True, args=(training_data,))
      thread.start()


    
    def _train_model_thread(self, training_data: List[Dict] = None):
       """Thread-Funktion für Modell-Training"""
       try:
           # Use provided training_data or fallback to stored data
           if training_data is None:
               training_data = self.stats.get('ml_training_data', [])
               if not training_data:
                   training_data = self.stats.get('training_data', [])
           
           if not training_data:
               self.update_queue.put(('log', "Keine Trainingsdaten verfügbar"))
               return
           
           self.update_queue.put(('log', f"Starte Training mit {len(training_data)} Datenpunkten..."))
           
           # Train the model
           result = self.ml_model.train(training_data)
           self.update_queue.put(('training_complete', result))
           
       except Exception as e:
           logger.error(f"Training fehlgeschlagen: {e}")
           self.update_queue.put(('log', f"Training fehlgeschlagen: {e}"))

#    Add a method to check training data status:
    def check_training_data_status(self):
        """Überprüft den Status der Trainingsdaten"""
        training_data_count = len(self.stats.get('training_data', []))
        ml_training_data_count = len(self.stats.get('ml_training_data', []))
        game_history_count = len(self.stats.get('game_history', []))

        status_message = (
        f"Trainingsdaten Status:\n"
        f"- Detaillierte Daten: {training_data_count}\n"
        f"- ML-optimierte Daten: {ml_training_data_count}\n"
        f"- Gespielte Spiele: {game_history_count}\n"
        f"- Gesamt-Datenpunkte: {training_data_count + ml_training_data_count}"
    )

        messagebox.showinfo("Trainingsdaten Status", status_message)
    
    def on_training_complete(self, result):
        """Callback nach Training"""
        self.training_progress.stop()
        accuracy = result.get('accuracy', 0)
        self.model_info_label.config(text=f"Modell: {result['model_type']} (Genauigkeit: {accuracy:.2%})")
        self.log_message(f"Training abgeschlossen - Genauigkeit: {accuracy:.2%}")
    
    def get_ai_suggestion(self):
        """Holt KI-Vorschlag für aktuellen Spieler"""
        if not self.game_engine or not self.ml_model.is_trained:
            messagebox.showinfo("Info", "Kein aktives Spiel oder Modell nicht trainiert")
            return
        
        current_player = self.game_engine.get_current_player()
        
        try:
            action, confidence = self.ml_model.predict(self.game_engine, current_player)
            
            if action:
                self.suggestion_label.config(text=f"Empfohlene Aktion: {action.value}")
                confidence_percent = confidence * 100
                self.confidence_bar['value'] = confidence_percent
                self.confidence_label.config(text=f"{confidence_percent:.1f}%")
                
                # Generate reasoning
                reasoning = self._generate_reasoning(action, current_player)
                self.reasoning_text.delete('1.0', tk.END)
                self.reasoning_text.insert('1.0', reasoning)
            else:
                self.suggestion_label.config(text="Keine Vorschläge verfügbar")
                
        except Exception as e:
            logger.error(f"Fehler bei KI-Vorschlag: {e}")
            messagebox.showerror("Fehler", f"Konnte KI-Vorschlag nicht generieren: {e}")
    
    def _generate_reasoning(self, action: ActionType, player: PlayerState) -> str:
        """Generiert Begründung für KI-Vorschlag"""
        reasoning = {
            ActionType.AUSBAUEN: "Bau von Gebäuden erweitert Ihre Produktionskapazitäten.",
            ActionType.BEVÖLKERUNG_AUSSPIELEN: "Karten spielen bringt sofortige Vorteile und Punkte.",
            ActionType.ARBEITSKRAFT_ERHÖHEN: "Mehr Bevölkerung bedeutet mehr Produktion.",
            ActionType.AUFSTEIGEN: "Höhere Bevölkerungsschichten produzieren wertvollere Güter.",
            ActionType.ALTE_WELT_ERSCHLIESSEN: "Neue Inseln bieten zusätzliche Ressourcen.",
            ActionType.NEUE_WELT_ERKUNDEN: "Die Neue Welt bietet exklusive Ressourcen.",
            ActionType.EXPEDITION: "Expeditionen bringen Siegpunkte und Bonusse.",
            ActionType.STADTFEST: "Stadtfeste setzen Arbeiter zurück für mehr Produktion."
        }
        
        return reasoning.get(action, "Diese Aktion passt gut zu Ihrer aktuellen Strategie.")
    
    def accept_suggestion(self):
        """Nimmt KI-Vorschlag an"""
        if not self.game_engine:
            return
        
        current_player = self.game_engine.get_current_player()
        suggestion_text = self.suggestion_label.cget('text')
        
        if "Empfohlene Aktion:" not in suggestion_text:
            messagebox.showinfo("Info", "Kein aktiver Vorschlag verfügbar")
            return
        
        # Extract action type from suggestion text
        action_name = suggestion_text.split(": ")[1]
        try:
            action_type = ActionType(action_name)
            
            # Create and execute action
            action = GameAction(
                player_id=current_player.id,
                action_type=action_type,
                parameters={}
            )
            
            success = self.game_engine.execute_action(action)
            
            if success:
                self.log_message(f"{current_player.name} führt KI-Vorschlag aus: {action_type.value}")
                self.update_game_display()
            else:
                messagebox.showwarning("Warnung", "Aktion konnte nicht ausgeführt werden")
                
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Aktion")
    
    def recalculate_suggestion(self):
        """Berechnet Vorschlag neu"""
        self.get_ai_suggestion()
    
    def load_ml_model(self):
        """Lädt gespeichertes ML-Modell"""
        model_path = 'data/models/latest_model.pkl'
        if os.path.exists(model_path):
            try:
                self.ml_model.load(model_path)
                self.model_info_label.config(text="Modell: Geladen ✓")
                self.log_message("ML-Modell geladen")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Modells: {e}")
    
    def load_model_dialog(self):
        """Dialog zum Laden eines Modells"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="Modell laden",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.ml_model.load(filename)
                self.model_info_label.config(text="Modell: Geladen ✓")
                self.log_message(f"Modell geladen: {filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Modell nicht laden: {e}")
    
    def save_model_dialog(self):
        """Dialog zum Speichern des Modells"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            title="Modell speichern",
            defaultextension=".pkl",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.ml_model.save(filename)
                self.log_message(f"Modell gespeichert: {filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Modell nicht speichern: {e}")
    
    def batch_training(self):
        """Batch-Training mit vielen Spielen"""
        dialog = BatchTrainingDialog(self.root)
        self.root.wait_window(dialog.window)
        
        if dialog.result:
            self.run_batch_training(dialog.result)
    
    def run_batch_training(self, settings):
        """Führt Batch-Training durch"""
        num_games = settings.get('num_games', 100)
        strategies = settings.get('strategies', ['aggressive', 'balanced', 'economic', 'explorer'])

        self.log_message(f"Starte Batch-Training mit {num_games} Spielen...")
        self.training_progress.start()

        # Reset training data for clean batch
        self.stats['training_data'] = []
        self.stats['ml_training_data'] = []
        self.stats['game_history'] = []

        thread = threading.Thread(target=self._batch_training_thread, 
                                 args=(num_games, strategies), daemon=True)
        thread.start()
    
    def _batch_training_thread(self, num_games: int, strategies: List[str]):
        """Thread für Batch-Training"""
        try:
            for i in range(num_games):
                if not self.simulation_running:
                    break
                
                # Create and play game
                game_strategies = [random.choice(strategies) for _ in range(4)]
                game = GameEngine(4)
                player_names = [f"Train_{s}_{i}" for s in game_strategies]
                game.setup_game(player_names, game_strategies)

                game_result = self._play_game_to_completion(game)

                # Record statistics
                self._record_game_statistics(game_result)

                # ALWAYS collect training data
                self._collect_training_data(game_result)

                # Update progress
                progress = (i + 1, num_games)
                total_data = len(self.stats.get('ml_training_data', []))
                self.update_queue.put(('simulation_progress', progress))
                self.update_queue.put(('log', f"Batch: {i+1}/{num_games} - Daten: {total_data}"))

                time.sleep(0.05)

            # Train model with collected data
            training_data = self.stats.get('ml_training_data', [])
            if training_data:
                self.log_message(f"Batch-Training abgeschlossen. Starte ML-Training mit {len(training_data)} Datenpunkten...")

                # Start training in a separate thread with the collected data
                training_thread = threading.Thread(
                    target=self._train_model_thread, 
                    daemon=True, 
                    args=(training_data,)
                )
                training_thread.start()
            else:
                self.update_queue.put(('log', "Batch-Training abgeschlossen, aber keine Trainingsdaten gesammelt"))

        except Exception as e:
            logger.error(f"Batch-Training fehlgeschlagen: {e}")
            self.update_queue.put(('log', f"Batch-Training fehlgeschlagen: {e}"))
        finally:
            self.training_progress.stop()
            self.simulation_running = False
    
    def _extract_training_data(self, game_result: Dict) -> List[Dict]:
        """Extrahiert Trainingsdaten aus Spielergebnissen"""
        training_data = []
        game = game_result['game']
        
        for action in game.action_history:
            if action.success and action.player_id < len(game.players):
                player = game.players[action.player_id]
                
                # Simplified feature extraction for training
                features = [
                    player.gold,
                    len(player.hand_cards),
                    len(player.buildings),
                    len(player.old_world_islands) + len(player.new_world_islands),
                    game.round_number
                ]
                
                training_example = {
                    'features': features,
                    'action': action.action_type.name,
                    'result': 'win' if game_result['winner'] == player.name else 'lose'
                }
                
                training_data.append(training_example)
        
        return training_data
    
    def show_statistics(self):
        """Zeigt detaillierte Statistiken"""
        if not self.stats['game_history']:
            messagebox.showinfo("Statistiken", "Noch keine Spieldaten verfügbar")
            return
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Detaillierte Statistiken")
        stats_window.geometry("600x400")
        
        text_area = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        stats_text = "=== DETAILLIERTE STATISTIKEN ===\n\n"
        
        # Basic stats
        stats_text += f"Gesamte Spiele: {self.stats['games_played']}\n\n"
        
        # Strategy performance
        stats_text += "STRATEGIE-LEISTUNG:\n"
        for strategy, wins in self.stats['strategy_wins'].items():
            win_rate = (wins / self.stats['games_played']) * 100
            stats_text += f"  {strategy}: {wins} Siege ({win_rate:.1f}%)\n"
        
        # Recent games
        stats_text += f"\nLETZTE 10 SPIELE:\n"
        recent_games = self.stats['game_history'][-10:]
        for i, game in enumerate(recent_games):
            stats_text += f"  Spiel {i+1}: {game['winner']} ({game['winning_strategy']}) - {game['rounds']} Runden\n"
        
        text_area.insert('1.0', stats_text)
        text_area.config(state=tk.DISABLED)
    
    def export_training_data(self):
        """Exportiert Trainingsdaten"""
        if not self.stats.get('training_data'):
            messagebox.showinfo("Export", "Keine Trainingsdaten verfügbar")
            return
        
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            title="Trainingsdaten exportieren",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.stats['training_data'], f, indent=2)
                self.log_message(f"Trainingsdaten exportiert: {filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Daten nicht exportieren: {e}")

def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = Anno1800App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
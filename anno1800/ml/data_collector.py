# ml/data_collector.py
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DataCollector:
    """Sammelt und verwaltet Trainingsdaten für das ML-System"""
    
    def __init__(self, data_dir: str = 'data/training'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.collected_games = []
        self.current_game_data = None
        self.total_moves = 0
        
        # Statistiken
        self.strategy_stats = {
            'aggressive': {'games': 0, 'wins': 0, 'total_score': 0},
            'balanced': {'games': 0, 'wins': 0, 'total_score': 0},
            'economic': {'games': 0, 'wins': 0, 'total_score': 0},
            'explorer': {'games': 0, 'wins': 0, 'total_score': 0}
        }
        
        self.action_counts = {}
        
        # Lade existierende Daten
        self.load_existing_data()
    
    def start_game_collection(self, game_id: str = None):
        """Startet die Datensammlung für ein neues Spiel"""
        if not game_id:
            game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_game_data = {
            'game_id': game_id,
            'timestamp': datetime.now().isoformat(),
            'moves': [],
            'players': [],
            'result': None
        }
    
    def collect_move(self, game_state, player, action: str, features: np.ndarray = None):
        """Sammelt Daten für einen einzelnen Zug"""
        if not self.current_game_data:
            self.start_game_collection()
        
        move_data = {
            'round': game_state.round_number,
            'player_id': player.id,
            'player_strategy': player.strategy,
            'action': action,
            'features': features.tolist() if features is not None else None,
            'game_state': self._extract_game_state(game_state),
            'player_state': self._extract_player_state(player)
        }
        
        self.current_game_data['moves'].append(move_data)
        self.total_moves += 1
        
        # Update action counts
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
    
    def collect_game_data(self, game_engine, result: Dict):
        """Sammelt Daten eines kompletten Spiels"""
        if not self.current_game_data:
            self.start_game_collection()
        
        # Füge Spielergebnis hinzu
        self.current_game_data['result'] = result
        
        # Extrahiere Spielerdaten
        for player_data in result['players']:
            self.current_game_data['players'].append({
                'name': player_data['name'],
                'strategy': player_data['strategy'],
                'final_score': player_data['score'],
                'rank': player_data['rank']
            })
            
            # Update Statistiken
            strategy = player_data['strategy']
            if strategy in self.strategy_stats:
                self.strategy_stats[strategy]['games'] += 1
                self.strategy_stats[strategy]['total_score'] += player_data['score']
                if player_data['rank'] == 1:
                    self.strategy_stats[strategy]['wins'] += 1
        
        # Speichere Spiel
        self.collected_games.append(self.current_game_data)
        
        # Speichere auf Disk wenn genug Spiele gesammelt
        if len(self.collected_games) >= 10:
            self.save_batch()
        
        # Reset für nächstes Spiel
        self.current_game_data = None
    
    def _extract_game_state(self, game_state) -> Dict:
        """Extrahiert relevante Informationen aus dem Spielzustand"""
        return {
            'round': game_state.round_number,
            'phase': game_state.phase.value if hasattr(game_state.phase, 'value') else str(game_state.phase),
            'game_end_triggered': game_state.game_end_triggered,
            'current_player': game_state.current_player_idx
        }
    
    def _extract_player_state(self, player) -> Dict:
        """Extrahiert relevante Informationen aus dem Spielerzustand"""
        return {
            'gold': player.gold,
            'trade_tokens': player.trade_tokens,
            'exploration_tokens': player.exploration_tokens,
            'hand_size': len(player.hand),
            'played_cards': len(player.played_cards),
            'buildings': len(player.buildings),
            'population': dict(player.population),
            'ships': dict(player.ships)
        }
    
    def save_batch(self):
        """Speichert gesammelte Spiele auf Disk"""
        if not self.collected_games:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.data_dir, f'games_batch_{timestamp}.json')
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.collected_games, f, indent=2)
        
        logger.info(f"Saved {len(self.collected_games)} games to {filename}")
        self.collected_games = []
    
    def load_existing_data(self):
        """Lädt existierende Trainingsdaten"""
        if not os.path.exists(self.data_dir):
            return
        
        loaded_games = 0
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        games = json.load(f)
                        self.collected_games.extend(games)
                        loaded_games += len(games)
                except Exception as e:
                    logger.error(f"Error loading {filepath}: {e}")
        
        if loaded_games > 0:
            logger.info(f"Loaded {loaded_games} existing games")
            self._update_statistics()
    
    def _update_statistics(self):
        """Aktualisiert Statistiken basierend auf geladenen Daten"""
        for game in self.collected_games:
            for move in game.get('moves', []):
                self.total_moves += 1
                action = move.get('action')
                if action:
                    self.action_counts[action] = self.action_counts.get(action, 0) + 1
    
    def get_training_data(self) -> List[Dict]:
        """Gibt alle Trainingsdaten zurück"""
        # Speichere aktuelle Batch
        if self.collected_games:
            self.save_batch()
        
        # Lade alle Daten
        all_games = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    games = json.load(f)
                    all_games.extend(games)
        
        return all_games
    
    def has_sufficient_data(self) -> bool:
        """Prüft ob genug Daten für Training vorhanden sind"""
        total_games = len(self.collected_games)
        
        # Zähle gespeicherte Spiele
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    games = json.load(f)
                    total_games += len(games)
        
        return total_games >= 100
    
    def get_statistics(self) -> Dict:
        """Gibt Statistiken über gesammelte Daten zurück"""
        total_games = len(self.collected_games)
        
        # Zähle alle Spiele
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        games = json.load(f)
                        total_games += len(games)
                except:
                    pass
        
        # Berechne Siegesraten
        win_rates = {}
        avg_scores = {}
        
        for strategy, stats in self.strategy_stats.items():
            if stats['games'] > 0:
                win_rates[strategy] = stats['wins'] / stats['games']
                avg_scores[strategy] = stats['total_score'] / stats['games']
            else:
                win_rates[strategy] = 0
                avg_scores[strategy] = 0
        
        # Top Aktionen
        common_actions = sorted(
            self.action_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_games': total_games,
            'total_moves': self.total_moves,
            'win_rates': win_rates,
            'avg_scores': avg_scores,
            'common_actions': common_actions,
            'strategy_stats': self.strategy_stats
        }



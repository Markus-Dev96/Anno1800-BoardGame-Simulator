# anno1800/ml/data_collector.py - Optimized Version
"""
Optimierter Datenkollektor für ML-Training
"""

import json
import os
import gzip
import pickle
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import numpy as np
import logging
from collections import defaultdict, deque
from pathlib import Path
import threading
import queue

logger = logging.getLogger(__name__)

@dataclass
class GameStats:
    """Statistiken für ein Spiel"""
    game_id: str
    timestamp: str
    num_players: int
    winner_strategy: str
    rounds_played: int
    final_scores: Dict[str, int]
    strategies: List[str]
    
@dataclass
class MoveData:
    """Daten für einen einzelnen Spielzug"""
    round: int
    player_id: int
    player_strategy: str
    action: str
    features: Optional[List[float]]
    game_state: Dict
    player_state: Dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class OptimizedDataCollector:
    """Optimierter Datenkollektor mit verbesserter Performance und Fehlerbehandlung"""
    
    def __init__(self, data_dir: str = 'data/training', 
                 max_buffer_size: int = 1000,
                 compression: bool = True):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_buffer_size = max_buffer_size
        self.use_compression = compression
        
        # Buffers
        self.move_buffer = deque(maxlen=max_buffer_size)
        self.game_buffer = deque(maxlen=100)
        self.current_game_data = None
        
        # Statistiken
        self.strategy_stats = defaultdict(lambda: {
            'games': 0, 'wins': 0, 'total_score': 0, 
            'avg_rounds': 0, 'win_rate': 0.0
        })
        self.action_counts = defaultdict(int)
        self.feature_stats = {
            'mean': None,
            'std': None,
            'min': None,
            'max': None
        }
        
        # Threading für asynchrones Speichern
        self.save_queue = queue.Queue()
        self.save_thread = None
        self._stop_thread = threading.Event()
        
        # Lade existierende Daten und Statistiken
        self._load_existing_statistics()
        
        logger.info(f"DataCollector initialisiert: {self.data_dir}")
    
    def start_game_collection(self, game_id: str = None, num_players: int = 4):
        """Startet die Datensammlung für ein neues Spiel"""
        if not game_id:
            game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{np.random.randint(1000, 9999)}"
        
        self.current_game_data = {
            'game_id': game_id,
            'timestamp': datetime.now().isoformat(),
            'num_players': num_players,
            'moves': [],
            'players': [],
            'result': None,
            'metadata': {
                'collector_version': '2.0',
                'feature_version': '1.1'
            }
        }
        
        logger.debug(f"Neue Spielsammlung gestartet: {game_id}")
    
    def collect_move(self, game_state: Any, player: Any, action: str, 
                    features: Optional[np.ndarray] = None) -> bool:
        """Sammelt Daten für einen einzelnen Zug mit Fehlerbehandlung"""
        try:
            if not self.current_game_data:
                self.start_game_collection()
            
            # Erstelle MoveData Objekt
            move_data = MoveData(
                round=game_state.round_number,
                player_id=player.id,
                player_strategy=getattr(player, 'strategy', 'unknown'),
                action=action,
                features=features.tolist() if features is not None else None,
                game_state=self._extract_game_state(game_state),
                player_state=self._extract_player_state(player)
            )
            
            # Füge zu Buffer hinzu
            self.move_buffer.append(move_data)
            self.current_game_data['moves'].append(asdict(move_data))
            
            # Update Statistiken
            self.action_counts[action] += 1
            
            # Update Feature-Statistiken
            if features is not None:
                self._update_feature_stats(features)
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Sammeln von Zugdaten: {e}")
            return False
    
    def collect_game_data(self, game_engine: Any, result: Dict) -> bool:
        """Sammelt Daten eines kompletten Spiels"""
        try:
            if not self.current_game_data:
                logger.warning("Keine aktuellen Spieldaten zum Sammeln")
                return False
            
            # Füge Spielergebnis hinzu
            self.current_game_data['result'] = result
            
            # Extrahiere erweiterte Spielerdaten
            for player_data in result.get('players', []):
                player_info = {
                    'id': player_data.get('id'),
                    'name': player_data.get('name'),
                    'strategy': player_data.get('strategy'),
                    'final_score': player_data.get('score', 0),
                    'rank': player_data.get('rank', 0),
                    'buildings_count': player_data.get('buildings', 0),
                    'cards_played': player_data.get('cards_played', 0)
                }
                self.current_game_data['players'].append(player_info)
                
                # Update Strategie-Statistiken
                self._update_strategy_stats(player_info, result)
            
            # Füge zu Game-Buffer hinzu
            self.game_buffer.append(self.current_game_data)
            
            # Speichere wenn Buffer voll
            if len(self.game_buffer) >= 10:
                self._schedule_save()
            
            # Reset für nächstes Spiel
            self.current_game_data = None
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Sammeln von Spieldaten: {e}")
            return False
    
    def _extract_game_state(self, game_state: Any) -> Dict:
        """Extrahiert relevante Informationen aus dem Spielzustand"""
        try:
            return {
                'round': getattr(game_state, 'round_number', 0),
                'phase': str(getattr(game_state, 'phase', 'unknown')),
                'game_end_triggered': getattr(game_state, 'game_end_triggered', False),
                'current_player': getattr(game_state, 'current_player_idx', -1),
                'num_players': getattr(game_state, 'num_players', 0)
            }
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren des Spielzustands: {e}")
            return {}
    
    def _extract_player_state(self, player: Any) -> Dict:
        """Extrahiert relevante Informationen aus dem Spielerzustand"""
        try:
            return {
                'gold': getattr(player, 'gold', 0),
                'trade_tokens': getattr(player, 'trade_tokens', 0),
                'exploration_tokens': getattr(player, 'exploration_tokens', 0),
                'hand_size': len(getattr(player, 'hand_cards', [])),
                'played_cards': len(getattr(player, 'played_cards', [])),
                'buildings': len(getattr(player, 'buildings', [])),
                'population': dict(getattr(player, 'population', {})),
                'ships': dict(getattr(player, 'ships', {})),
                'islands': len(getattr(player, 'old_world_islands', [])) + 
                          len(getattr(player, 'new_world_islands', []))
            }
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren des Spielerzustands: {e}")
            return {}
    
    def _update_feature_stats(self, features: np.ndarray):
        """Aktualisiert Feature-Statistiken für Normalisierung"""
        if self.feature_stats['mean'] is None:
            self.feature_stats['mean'] = features.copy()
            self.feature_stats['std'] = np.zeros_like(features)
            self.feature_stats['min'] = features.copy()
            self.feature_stats['max'] = features.copy()
            self.feature_stats['count'] = 1
        else:
            # Inkrementelle Statistik-Updates
            n = self.feature_stats['count']
            
            # Update Mean
            delta = features - self.feature_stats['mean']
            self.feature_stats['mean'] += delta / (n + 1)
            
            # Update Std (Welford's algorithm)
            delta2 = features - self.feature_stats['mean']
            self.feature_stats['std'] += delta * delta2
            
            # Update Min/Max
            self.feature_stats['min'] = np.minimum(self.feature_stats['min'], features)
            self.feature_stats['max'] = np.maximum(self.feature_stats['max'], features)
            
            self.feature_stats['count'] += 1
    
    def _update_strategy_stats(self, player_info: Dict, result: Dict):
        """Aktualisiert Strategie-Statistiken"""
        strategy = player_info.get('strategy', 'unknown')
        stats = self.strategy_stats[strategy]
        
        stats['games'] += 1
        stats['total_score'] += player_info.get('final_score', 0)
        
        if player_info.get('rank') == 1:
            stats['wins'] += 1
        
        # Update Durchschnittswerte
        stats['win_rate'] = stats['wins'] / stats['games'] if stats['games'] > 0 else 0.0
        stats['avg_score'] = stats['total_score'] / stats['games'] if stats['games'] > 0 else 0.0
        
        # Runden-Statistik
        rounds = result.get('rounds_played', 0)
        if rounds > 0:
            stats['avg_rounds'] = (stats['avg_rounds'] * (stats['games'] - 1) + rounds) / stats['games']
    
    def _schedule_save(self):
        """Plant das Speichern der Daten"""
        if not self.save_thread or not self.save_thread.is_alive():
            self.save_thread = threading.Thread(target=self._save_worker, daemon=True)
            self.save_thread.start()
        
        # Füge zu Save-Queue hinzu
        self.save_queue.put(list(self.game_buffer))
        self.game_buffer.clear()
    
    def _save_worker(self):
        """Worker-Thread für asynchrones Speichern"""
        while not self._stop_thread.is_set():
            try:
                # Warte auf Daten (Timeout um Thread beenden zu können)
                games = self.save_queue.get(timeout=1.0)
                self._save_batch(games)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Fehler im Save-Worker: {e}")
    
    def _save_batch(self, games: List[Dict]):
        """Speichert eine Batch von Spielen"""
        if not games:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"games_batch_{timestamp}_{len(games)}.json"
        
        if self.use_compression:
            filename += '.gz'
            filepath = self.data_dir / filename
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                json.dump(games, f, indent=2)
        else:
            filepath = self.data_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(games, f, indent=2)
        
        logger.info(f"Saved {len(games)} games to {filepath}")
        
        # Speichere auch Statistiken
        self._save_statistics()
    
    def _save_statistics(self):
        """Speichert aktuelle Statistiken"""
        stats_file = self.data_dir / 'statistics.json'
        
        stats = {
            'last_updated': datetime.now().isoformat(),
            'strategy_stats': dict(self.strategy_stats),
            'action_counts': dict(self.action_counts),
            'feature_stats': self._serialize_feature_stats(),
            'total_games': sum(s['games'] for s in self.strategy_stats.values()),
            'total_moves': sum(self.action_counts.values())
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
    
    def _serialize_feature_stats(self) -> Dict:
        """Serialisiert Feature-Statistiken für JSON"""
        if self.feature_stats['mean'] is None:
            return {}
        
        # Berechne finale Standardabweichung
        n = self.feature_stats['count']
        std = np.sqrt(self.feature_stats['std'] / n) if n > 1 else np.zeros_like(self.feature_stats['mean'])
        
        return {
            'mean': self.feature_stats['mean'].tolist(),
            'std': std.tolist(),
            'min': self.feature_stats['min'].tolist(),
            'max': self.feature_stats['max'].tolist(),
            'count': n
        }
    
    def _load_existing_statistics(self):
        """Lädt existierende Statistiken"""
        stats_file = self.data_dir / 'statistics.json'
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                
                # Lade Strategie-Statistiken
                for strategy, data in stats.get('strategy_stats', {}).items():
                    self.strategy_stats[strategy].update(data)
                
                # Lade Action-Counts
                self.action_counts.update(stats.get('action_counts', {}))
                
                # Lade Feature-Statistiken
                feature_stats = stats.get('feature_stats', {})
                if feature_stats:
                    self.feature_stats['mean'] = np.array(feature_stats.get('mean', []))
                    self.feature_stats['std'] = np.array(feature_stats.get('std', []))
                    self.feature_stats['min'] = np.array(feature_stats.get('min', []))
                    self.feature_stats['max'] = np.array(feature_stats.get('max', []))
                    self.feature_stats['count'] = feature_stats.get('count', 0)
                
                logger.info(f"Statistiken geladen: {stats.get('total_games', 0)} Spiele, "
                          f"{stats.get('total_moves', 0)} Züge")
                
            except Exception as e:
                logger.error(f"Fehler beim Laden der Statistiken: {e}")
    
    def get_training_data(self, limit: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Gibt Trainingsdaten als numpy Arrays zurück"""
        X = []
        y = []
        
        # Lade alle Dateien
        files = sorted(self.data_dir.glob('games_batch_*.json*'))
        
        for file in files[:limit] if limit else files:
            try:
                if file.suffix == '.gz':
                    with gzip.open(file, 'rt', encoding='utf-8') as f:
                        games = json.load(f)
                else:
                    with open(file, 'r', encoding='utf-8') as f:
                        games = json.load(f)
                
                # Extrahiere Features und Labels
                for game in games:
                    for move in game.get('moves', []):
                        if move.get('features'):
                            X.append(move['features'])
                            y.append(move['action'])
                
            except Exception as e:
                logger.error(f"Fehler beim Laden von {file}: {e}")
                continue
        
        if not X:
            logger.warning("Keine Trainingsdaten gefunden")
            return np.array([]), np.array([])
        
        return np.array(X, dtype=np.float32), np.array(y)
    
    def get_normalized_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Gibt normalisierte Trainingsdaten zurück"""
        X, y = self.get_training_data()
        
        if len(X) == 0:
            return X, y
        
        # Normalisiere Features
        if self.feature_stats['mean'] is not None:
            mean = self.feature_stats['mean']
            std = np.sqrt(self.feature_stats['std'] / self.feature_stats['count'])
            std[std == 0] = 1.0  # Vermeide Division durch 0
            
            X = (X - mean) / std
        
        return X, y
    
    def has_sufficient_data(self, min_games: int = 100) -> bool:
        """Prüft ob genug Daten für Training vorhanden sind"""
        total_games = sum(s['games'] for s in self.strategy_stats.values())
        return total_games >= min_games
    
    def get_statistics(self) -> Dict:
        """Gibt detaillierte Statistiken zurück"""
        total_games = sum(s['games'] for s in self.strategy_stats.values())
        total_moves = sum(self.action_counts.values())
        
        # Berechne Top-Aktionen
        top_actions = sorted(
            self.action_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Berechne Strategie-Rankings
        strategy_rankings = sorted(
            [(s, stats['win_rate']) for s, stats in self.strategy_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'total_games': total_games,
            'total_moves': total_moves,
            'strategy_rankings': strategy_rankings,
            'strategy_stats': dict(self.strategy_stats),
            'top_actions': top_actions,
            'data_files': len(list(self.data_dir.glob('games_batch_*.json*'))),
            'buffer_status': {
                'moves': len(self.move_buffer),
                'games': len(self.game_buffer)
            }
        }
    
    def export_for_analysis(self, output_file: str):
        """Exportiert Daten für externe Analyse (z.B. Pandas/Jupyter)"""
        all_data = []
        
        for file in self.data_dir.glob('games_batch_*.json*'):
            try:
                if file.suffix == '.gz':
                    with gzip.open(file, 'rt', encoding='utf-8') as f:
                        games = json.load(f)
                else:
                    with open(file, 'r', encoding='utf-8') as f:
                        games = json.load(f)
                
                all_data.extend(games)
            except Exception as e:
                logger.error(f"Fehler beim Laden von {file}: {e}")
        
        # Speichere als pickle für schnelleres Laden
        with open(output_file, 'wb') as f:
            pickle.dump(all_data, f)
        
        logger.info(f"Exported {len(all_data)} games to {output_file}")
    
    def cleanup(self):
        """Räumt auf und speichert alle verbleibenden Daten"""
        # Speichere verbleibende Daten
        if self.game_buffer:
            self._save_batch(list(self.game_buffer))
            self.game_buffer.clear()
        
        # Stoppe Save-Thread
        self._stop_thread.set()
        if self.save_thread and self.save_thread.is_alive():
            self.save_thread.join(timeout=5.0)
        
        # Speichere finale Statistiken
        self._save_statistics()
        
        logger.info("DataCollector cleanup completed")
    
    def __del__(self):
        """Destruktor - stelle sicher dass Daten gespeichert werden"""
        try:
            self.cleanup()
        except:
            pass
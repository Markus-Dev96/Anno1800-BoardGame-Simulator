# anno1800/ai/strategy.py - Complete corrected version

"""
KI-Strategien für Computer-Spieler
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random
import math
import logging

from anno1800.utils.constants import ActionType, PopulationType, BuildingType, BUILDING_DEFINITIONS, UPGRADE_COSTS
from anno1800.game.engine import GameEngine, GameAction
from anno1800.game.player import PlayerState

logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    """Konfiguration für eine Strategie"""
    name: str
    build_priority: float = 0.25
    card_priority: float = 0.25
    expand_priority: float = 0.25
    upgrade_priority: float = 0.25
    risk_tolerance: float = 0.5
    
    # Spezifische Präferenzen
    preferred_buildings: List[BuildingType] = None
    focus_new_world: bool = False
    rush_endgame: bool = False

class AIStrategy:
    """Basis-Klasse für KI-Strategien"""
    
    STRATEGIES = {
        'aggressive': StrategyConfig(
            name='Aggressive',
            build_priority=0.4,
            card_priority=0.2,
            expand_priority=0.3,
            upgrade_priority=0.1,
            risk_tolerance=0.8,
            preferred_buildings=[BuildingType.WEAPONS_FACTORY, BuildingType.STEELWORKS],
            rush_endgame=True
        ),
        'balanced': StrategyConfig(
            name='Balanced',
            build_priority=0.25,
            card_priority=0.25,
            expand_priority=0.25,
            upgrade_priority=0.25,
            risk_tolerance=0.5
        ),
        'economic': StrategyConfig(
            name='Economic',
            build_priority=0.35,
            card_priority=0.15,
            expand_priority=0.15,
            upgrade_priority=0.35,
            risk_tolerance=0.3,
            preferred_buildings=[BuildingType.WAREHOUSE, BuildingType.BREWERY]
        ),
        'explorer': StrategyConfig(
            name='Explorer',
            build_priority=0.15,
            card_priority=0.2,
            expand_priority=0.5,
            upgrade_priority=0.15,
            risk_tolerance=0.6,
            focus_new_world=True
        )
    }
    
    def __init__(self, strategy_name: str = 'balanced'):
        if strategy_name not in self.STRATEGIES:
            strategy_name = 'balanced'
        self.config = self.STRATEGIES.get(strategy_name, self.STRATEGIES['balanced'])
        self.decision_history = []
        
    def decide_action(self, game: GameEngine, player: PlayerState) -> GameAction:
        """Entscheidet die nächste Aktion"""
        available_actions = game.get_available_actions(player)
        
        if not available_actions:
            return GameAction(
                player_id=player.id,
                action_type=ActionType.CITY_FESTIVAL,
                parameters={}
            )
        
        # Bewerte alle verfügbaren Aktionen
        action_scores = self._evaluate_actions(game, player, available_actions)
        
        # Wähle beste Aktion (mit etwas Zufälligkeit)
        best_action = self._select_action(action_scores)
        
        # Erstelle konkrete Aktion mit Parametern
        return self._create_action(game, player, best_action)
    
    def _evaluate_actions(self, game: GameEngine, player: PlayerState, 
                         actions: List[ActionType]) -> Dict[ActionType, float]:
        """Bewertet verfügbare Aktionen"""
        scores = {}
        
        for action in actions:
            base_score = 0.0  # Immer mit 0.0 initialisieren
            
            if action == ActionType.BUILD:
                base_score = self._evaluate_build(game, player)
            elif action == ActionType.PLAY_CARD:
                base_score = self._evaluate_play_card(player)
            elif action == ActionType.EXCHANGE_CARDS:
                base_score = self._evaluate_exchange_cards(player)
            elif action == ActionType.INCREASE_WORKFORCE:
                base_score = self._evaluate_workforce(player)
            elif action == ActionType.UPGRADE_POPULATION:
                base_score = self._evaluate_upgrade(player)
            elif action in [ActionType.EXPLORE_OLD_WORLD, ActionType.EXPLORE_NEW_WORLD]:
                base_score = self._evaluate_exploration(game, player, action)
            elif action == ActionType.EXPEDITION:
                base_score = self._evaluate_expedition(game, player)
            elif action == ActionType.CITY_FESTIVAL:
                base_score = self._evaluate_city_festival(player)
            else:
                base_score = 0.1  # Fallback für unbekannte Aktionen
            
            # Sicherstellen, dass base_score ein float ist
            base_score = float(base_score) if base_score is not None else 0.1
            
            # Modifikation basierend auf Spielphase
            phase_modifier = self._get_phase_modifier(game, action)
            scores[action] = base_score * phase_modifier * self.config.risk_tolerance
        
        return scores
    
    def _evaluate_build(self, game: GameEngine, player: PlayerState) -> float:
        """Bewertet Bau-Option"""
        score = float(self.config.build_priority)
        
        # Bevorzuge fehlende wichtige Gebäude
        essential_buildings = [
            BuildingType.WAREHOUSE,
            BuildingType.STEELWORKS,
            BuildingType.BREWERY
        ]
        
        for building in essential_buildings:
            if building not in player.buildings:
                score += 0.2
        
        # Bevorzuge Strategie-spezifische Gebäude
        if self.config.preferred_buildings:
            for building in self.config.preferred_buildings:
                if building not in player.buildings:
                    score += 0.3
        
        return min(score, 1.0)
    
    def _evaluate_play_card(self, player: PlayerState) -> float:
        """Bewertet Karten-Spiel-Option"""
        if not player.hand_cards:
            return 0.0
        
        score = float(self.config.card_priority)
        
        # Höhere Bewertung bei vielen Handkarten
        hand_size_factor = len(player.hand_cards) / 10.0
        score *= (1.0 + hand_size_factor)
        
        # Prüfe spielbare Karten
        playable = sum(1 for card in player.hand_cards 
                      if player.can_afford_resources(card.get('requirements', {})))
        
        if playable > 0:
            score += 0.2 * (playable / len(player.hand_cards))
        
        return min(score, 1.0)
    
    def _evaluate_exchange_cards(self, player: PlayerState) -> float:
        """Bewertet Karten-Tausch-Option"""
        if not player.hand_cards:
            return 0.0
        
        score = 0.1  # Basiswert
        
        # Höhere Bewertung bei vielen unspielbaren Karten
        unplayable = sum(1 for card in player.hand_cards 
                        if not player.can_afford_resources(card.get('requirements', {})))
        
        if unplayable > 0:
            score += 0.2 * (unplayable / len(player.hand_cards))
        
        return min(score, 1.0)
    
    def _evaluate_workforce(self, player: PlayerState) -> float:
        """Bewertet Arbeitskraft-Erhöhungs-Option"""
        score = float(self.config.expand_priority) * 0.5
        
        # Bevorzuge wenn wenig Bevölkerung verfügbar
        total_population = sum(player.population.values())
        if total_population < 10:
            score += 0.3
        
        return min(score, 1.0)
    
    def _evaluate_upgrade(self, player: PlayerState) -> float:
        """Bewertet Upgrade-Option"""
        score = float(self.config.upgrade_priority)
        
        # Economic-Strategie bevorzugt Upgrades
        if self.config.name == 'Economic':
            score += 0.2
        
        # Bewerte basierend auf Bevölkerungsstruktur
        available_farmers = player.get_available_population(PopulationType.FARMER)
        if available_farmers > 0:
            score += 0.1 * available_farmers
        
        return min(score, 1.0)
    
    def _evaluate_exploration(self, game: GameEngine, player: PlayerState, 
                            action: ActionType) -> float:
        """Bewertet Erkundungs-Option"""
        score = float(self.config.expand_priority)
        
        # Explorer-Strategie bevorzugt Erkundung
        if self.config.focus_new_world and action == ActionType.EXPLORE_NEW_WORLD:
            score += 0.3
        
        # Bewerte basierend auf bereits erkundeten Inseln
        total_islands = len(player.old_world_islands) + len(player.new_world_islands)
        if total_islands < 2:
            score += 0.2
        
        return min(score, 1.0)
    
    def _evaluate_expedition(self, game: GameEngine, player: PlayerState) -> float:
        """Bewertet Expeditions-Option"""
        score = float(self.config.expand_priority) * 0.7
        
        # Bevorzuge wenn Expeditionen verfügbar sind
        if hasattr(game.board, 'expedition_cards') and game.board.expedition_cards:
            score += 0.2
        
        return min(score, 1.0)
    
    def _evaluate_city_festival(self, player: PlayerState) -> float:
        """Bewertet Stadtfest-Option"""
        score = 0.1  # Basiswert
        
        # Bevorzuge wenn viele Arbeiter erschöpft sind
        total_exhausted = sum(player.exhausted_population.values())
        if total_exhausted > 5:
            score += 0.3
        
        return min(score, 1.0)
    
    def _get_phase_modifier(self, game: GameEngine, action: ActionType) -> float:
        """Gibt Phasen-Modifikator für Aktion zurück"""
        round_num = game.round_number
        
        # Frühphase (Runden 1-5)
        if round_num <= 5:
            if action in [ActionType.BUILD, ActionType.INCREASE_WORKFORCE]:
                return 1.3
            elif action == ActionType.EXPEDITION:
                return 0.7
        
        # Mittelphase (Runden 6-15)
        elif round_num <= 15:
            if action in [ActionType.PLAY_CARD, ActionType.UPGRADE_POPULATION]:
                return 1.2
            elif action == ActionType.EXPLORE_OLD_WORLD:
                return 1.1
        
        # Endphase (Runden 16+)
        else:
            if action in [ActionType.PLAY_CARD, ActionType.EXPEDITION]:
                return 1.4
            elif action == ActionType.BUILD:
                return 0.8
        
        return 1.0
    
    def _select_action(self, action_scores: Dict[ActionType, float]) -> ActionType:
        """Wählt Aktion basierend auf Bewertungen aus"""
        if not action_scores:
            return ActionType.CITY_FESTIVAL
        
        # Konvertiere zu Liste für die Auswahl
        actions = list(action_scores.keys())
        scores = list(action_scores.values())
        
        # Sicherstellen, dass alle Scores positiv sind
        min_score = min(scores)
        if min_score <= 0:
            scores = [score - min_score + 0.1 for score in scores]
        
        # Softmax für Wahrscheinlichkeiten
        try:
            exp_scores = [math.exp(score) for score in scores]
            sum_exp_scores = sum(exp_scores)
            probabilities = [score / sum_exp_scores for score in exp_scores]
            
            # Wähle Aktion basierend auf Wahrscheinlichkeiten
            return random.choices(actions, weights=probabilities)[0]
        except:
            # Fallback: wähle Aktion mit höchstem Score
            max_score = max(scores)
            best_actions = [action for action, score in action_scores.items() if score == max_score]
            return random.choice(best_actions) if best_actions else ActionType.CITY_FESTIVAL
    
    def _create_action(self, game: GameEngine, player: PlayerState, action_type: ActionType) -> GameAction:
        """Erstellt konkrete Aktion mit Parametern"""
        parameters = {}
        
        if action_type == ActionType.BUILD:
            parameters = self._get_build_parameters(game, player)
        elif action_type == ActionType.PLAY_CARD:
            parameters = self._get_play_card_parameters(player)
        elif action_type == ActionType.UPGRADE_POPULATION:
            parameters = self._get_upgrade_parameters(player)
        elif action_type in [ActionType.EXPLORE_OLD_WORLD, ActionType.EXPLORE_NEW_WORLD, ActionType.EXPEDITION]:
            parameters = {'use_tokens': 1}  # Standard-Parameter für Erkundung
        
        return GameAction(
            player_id=player.id,
            action_type=action_type,
            parameters=parameters
        )
    
    def _get_build_parameters(self, game: GameEngine, player: PlayerState) -> Dict:
        """Bestimmt Bau-Parameter"""
        # Finde verfügbare und bezahlbare Gebäude
        available_buildings = []
        for building_type in BuildingType:
            if (hasattr(game.board, 'available_buildings') and 
                game.board.available_buildings.get(building_type, 0) > 0 and
                building_type not in player.buildings):
                
                building_def = BUILDING_DEFINITIONS.get(building_type)
                if building_def and player.can_afford_resources(building_def.get('cost', {})):
                    available_buildings.append(building_type)
        
        if available_buildings:
            # Bevorzuge Strategie-spezifische Gebäude
            if self.config.preferred_buildings:
                for building in self.config.preferred_buildings:
                    if building in available_buildings:
                        return {'building_type': building}
            
            # Ansonsten wähle zufällig
            return {'building_type': random.choice(available_buildings)}
        
        return {}
    
    def _get_play_card_parameters(self, player: PlayerState) -> Dict:
        """Bestimmt Karten-Spiel-Parameter"""
        playable_cards = []
        for card in player.hand_cards:
            if player.can_afford_resources(card.get('requirements', {})):
                playable_cards.append(card)
        
        if playable_cards:
            # Wähle die erste spielbare Karte
            return {'card_id': playable_cards[0].get('id')}
        
        return {}
    
    def _get_upgrade_parameters(self, player: PlayerState) -> Dict:
        """Bestimmt Upgrade-Parameter"""
        # Finde verfügbare Upgrades
        for (from_type, to_type), cost in UPGRADE_COSTS.items():
            if (player.get_available_population(from_type) > 0 and
                player.can_afford_resources(cost)):
                return {
                    'from_type': from_type,
                    'to_type': to_type,
                    'amount': 1
                }
        
        return {}
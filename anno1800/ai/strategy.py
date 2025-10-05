# anno1800/ai/strategy.py
"""
KI-Strategien für Computer-Spieler
Angepasst an die korrekten Brettspiel-Regeln
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

    def __post_init__(self):
        """Initialisiert Standardwerte für preferred_buildings"""
        if self.preferred_buildings is None:
            self.preferred_buildings = []

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
            preferred_buildings=[BuildingType.KANONENGIESEREI, BuildingType.STAHLWERK],
            rush_endgame=True
        ),
        'balanced': StrategyConfig(
            name='Balanced',
            build_priority=0.25,
            card_priority=0.25,
            expand_priority=0.25,
            upgrade_priority=0.25,
            risk_tolerance=0.5,
            preferred_buildings=[BuildingType.LAGERHAUS, BuildingType.BRAUEREI]
        ),
        'economic': StrategyConfig(
            name='Economic',
            build_priority=0.35,
            card_priority=0.15,
            expand_priority=0.15,
            upgrade_priority=0.35,
            risk_tolerance=0.3,
            preferred_buildings=[BuildingType.LAGERHAUS, BuildingType.BRAUEREI, BuildingType.WERFT_1]
        ),
        'explorer': StrategyConfig(
            name='Explorer',
            build_priority=0.15,
            card_priority=0.2,
            expand_priority=0.5,
            upgrade_priority=0.15,
            risk_tolerance=0.6,
            preferred_buildings=[BuildingType.WERFT_1, BuildingType.HANDELSSCHIFF_1],
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
                action_type=ActionType.STADTFEST,
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
            base_score = 0.0
            
            if action == ActionType.AUSBAUEN:
                base_score = self._evaluate_build(game, player)
            elif action == ActionType.BEVÖLKERUNG_AUSSPIELEN:
                base_score = self._evaluate_play_card(player)
            elif action == ActionType.KARTEN_AUSTAUSCHEN:
                base_score = self._evaluate_exchange_cards(player)
            elif action == ActionType.ARBEITSKRAFT_ERHÖHEN:
                base_score = self._evaluate_workforce(player)
            elif action == ActionType.AUFSTEIGEN:
                base_score = self._evaluate_upgrade(player)
            elif action in [ActionType.ALTE_WELT_ERSCHLIESSEN, ActionType.NEUE_WELT_ERKUNDEN]:
                base_score = self._evaluate_exploration(game, player, action)
            elif action == ActionType.EXPEDITION:
                base_score = self._evaluate_expedition(game, player)
            elif action == ActionType.STADTFEST:
                base_score = self._evaluate_city_festival(player)
            else:
                base_score = 0.1
            
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
            BuildingType.LAGERHAUS,
            BuildingType.STAHLWERK,
            BuildingType.BRAUEREI
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
                      if self._can_afford_card(player, card))
        
        if playable > 0:
            score += 0.2 * (playable / len(player.hand_cards))
        
        return min(score, 1.0)
    
    def _can_afford_card(self, player: PlayerState, card: Dict) -> bool:
        """Prüft ob Karte bezahlbar ist"""
        requirements = card.get('requirements', {})
        for resource, amount in requirements.items():
            if not player.can_produce_resource(resource, amount):
                return False
        return True
    
    def _evaluate_exchange_cards(self, player: PlayerState) -> float:
        """Bewertet Karten-Tausch-Option"""
        if not player.hand_cards:
            return 0.0
        
        score = 0.1
        
        # Höhere Bewertung bei vielen unspielbaren Karten
        unplayable = sum(1 for card in player.hand_cards 
                        if not self._can_afford_card(player, card))
        
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
        available_farmers = player.get_available_population(PopulationType.BAUER)
        if available_farmers > 0:
            score += 0.1 * min(available_farmers, 3)
        
        return min(score, 1.0)
    
    def _evaluate_exploration(self, game: GameEngine, player: PlayerState, 
                            action: ActionType) -> float:
        """Bewertet Erkundungs-Option"""
        score = float(self.config.expand_priority)
        
        # Explorer-Strategie bevorzugt Erkundung
        if self.config.focus_new_world and action == ActionType.NEUE_WELT_ERKUNDEN:
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
        score = 0.1
        
        # Bevorzuge wenn viele Arbeiter erschöpft sind
        total_exhausted = sum(player.exhausted_population.values()) if hasattr(player, 'exhausted_population') else 0
        workers_on_buildings = len(player.workers_on_buildings) if hasattr(player, 'workers_on_buildings') else 0
        
        if total_exhausted + workers_on_buildings > 5:
            score += 0.3
        
        # Auch wenn viele Marine-Plättchen erschöpft sind
        exhausted_trade = player.erschöpfte_handels_plättchen if hasattr(player, 'erschöpfte_handels_plättchen') else 0
        exhausted_exploration = player.erschöpfte_erkundungs_plättchen if hasattr(player, 'erschöpfte_erkundungs_plättchen') else 0
        
        if exhausted_trade + exhausted_exploration > 3:
            score += 0.2
        
        return min(score, 1.0)
    
    def _get_phase_modifier(self, game: GameEngine, action: ActionType) -> float:
        """Gibt Phasen-Modifikator für Aktion zurück"""
        round_num = game.round_number
        
        # Frühphase (Runden 1-5)
        if round_num <= 5:
            if action in [ActionType.AUSBAUEN, ActionType.ARBEITSKRAFT_ERHÖHEN]:
                return 1.3
            elif action == ActionType.EXPEDITION:
                return 0.7
        
        # Mittelphase (Runden 6-15)
        elif round_num <= 15:
            if action in [ActionType.BEVÖLKERUNG_AUSSPIELEN, ActionType.AUFSTEIGEN]:
                return 1.2
            elif action == ActionType.ALTE_WELT_ERSCHLIESSEN:
                return 1.1
        
        # Endphase (Runden 16+)
        else:
            if action in [ActionType.BEVÖLKERUNG_AUSSPIELEN, ActionType.EXPEDITION]:
                return 1.4
            elif action == ActionType.AUSBAUEN:
                return 0.8
        
        return 1.0
    
    def _select_action(self, action_scores: Dict[ActionType, float]) -> ActionType:
        """Wählt Aktion basierend auf Bewertungen aus"""
        if not action_scores:
            return ActionType.STADTFEST
        
        # Konvertiere zu Liste für die Auswahl
        actions = list(action_scores.keys())
        scores = list(action_scores.values())
        
        # Sicherstellen, dass alle Scores positiv sind
        min_score = min(scores) if scores else 0
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
            return random.choice(best_actions) if best_actions else ActionType.STADTFEST
    
    def _create_action(self, game: GameEngine, player: PlayerState, action_type: ActionType) -> GameAction:
        """Erstellt konkrete Aktion mit Parametern"""
        parameters = {}
        
        if action_type == ActionType.AUSBAUEN:
            parameters = self._get_build_parameters(game, player)
        elif action_type == ActionType.BEVÖLKERUNG_AUSSPIELEN:
            parameters = self._get_play_card_parameters(player)
        elif action_type == ActionType.KARTEN_AUSTAUSCHEN:
            parameters = self._get_exchange_cards_parameters(player)
        elif action_type == ActionType.ARBEITSKRAFT_ERHÖHEN:
            parameters = self._get_workforce_parameters(player)
        elif action_type == ActionType.AUFSTEIGEN:
            parameters = self._get_upgrade_parameters(player)
        
        return GameAction(
            player_id=player.id,
            action_type=action_type,
            parameters=parameters
        )
    
    def _get_build_parameters(self, game: GameEngine, player: PlayerState) -> Dict:
        """Bestimmt Bau-Parameter"""
        buildable = []
        
        # Prüfe alle Gebäudetypen
        for building_type in BuildingType:
            if game.board.available_buildings.get(building_type, 0) <= 0:
                continue
                
            building_def = BUILDING_DEFINITIONS.get(building_type)
            if not building_def:
                continue
                
            # Prüfe ob Spieler es sich leisten kann
            if not player.can_afford_building_cost(building_type):
                continue
                
            # Prüfe ob es eine Industrie ist die er noch nicht hat
            if building_def.get('produces') and building_type in player.buildings:
                continue  # Industrie bereits vorhanden
                
            buildable.append(building_type)
        
        if buildable:
            # Bevorzuge Strategie-spezifische Gebäude
            if self.config.preferred_buildings:
                for building in self.config.preferred_buildings:
                    if building in buildable:
                        return {'buildings': [building]}
            
            # Wähle zufällig
            return {'buildings': [random.choice(buildable)]}
        
        return {}
    
    def _prioritize_buildings(self, buildings: List[BuildingType], player: PlayerState) -> List[BuildingType]:
        """Priorisiert Gebäude basierend auf Strategie und aktueller Situation"""
        scores = {}
        
        for building in buildings:
            score = 0
            building_def = BUILDING_DEFINITIONS.get(building, {})
            
            # Grundpriorität basierend auf Strategie
            if self.config.preferred_buildings and building in self.config.preferred_buildings:
                score += 3
                
            # Fehlende essentielle Gebäude
            essential = [BuildingType.LAGERHAUS, BuildingType.STAHLWERK, BuildingType.BRAUEREI]
            if building in essential and building not in player.buildings:
                score += 2
                
            # Produktionsgebäude für benötigte Ressourcen
            produces = building_def.get('produces')
            if produces:
                # Höhere Priorität für Ressourcen die für Karten benötigt werden
                for card in player.hand_cards:
                    requirements = card.get('requirements', {})
                    if produces in requirements:
                        score += requirements[produces] * 0.5
            
            scores[building] = score
        
        return sorted(buildings, key=lambda b: scores.get(b, 0), reverse=True)
    
    def _get_play_card_parameters(self, player: PlayerState) -> Dict:
        """Bestimmt Karten-Spiel-Parameter"""
        playable_cards = []
        for card in player.hand_cards:
            if self._can_afford_card(player, card):
                playable_cards.append(card)
        
        if playable_cards:
            return {'card_id': playable_cards[0].get('id')}
        
        return {}
    
    def _get_exchange_cards_parameters(self, player: PlayerState) -> Dict:
        """Bestimmt Karten-Austausch-Parameter"""
        # Tausche unspielbare Karten
        cards_to_exchange = []
        for card in player.hand_cards[:3]:  # Max 3 Karten
            if not self._can_afford_card(player, card):
                cards_to_exchange.append(card.get('id'))
        
        if cards_to_exchange:
            return {'cards': cards_to_exchange}
        
        # Tausche zufällige Karten wenn keine unspielbaren
        if len(player.hand_cards) >= 3:
            return {'cards': [c.get('id') for c in player.hand_cards[:3]]}
        
        return {}
    
    def _get_workforce_parameters(self, player: PlayerState) -> Dict:
        """Bestimmt Arbeitskraft-Parameter"""
        from anno1800.utils.constants import WORKFORCE_COSTS
        
        increases = []
        
        # Versuche bis zu 3 Bevölkerung hinzuzufügen
        for pop_type in [PopulationType.BAUER, PopulationType.ARBEITER, PopulationType.HANDWERKER]:
            if len(increases) >= 3:
                break
                
            # Prüfe ob Spieler sich die Kosten leisten kann
            cost = WORKFORCE_COSTS.get(pop_type, {})
            can_afford = True
            for resource, amount in cost.items():
                if not player.can_produce_resource(resource, amount):
                    can_afford = False
                    break
            
            if can_afford:
                increases.append(pop_type)
        
        if increases:
            return {'increases': increases}
        
        return {}
    
    def _get_upgrade_parameters(self, player: PlayerState) -> Dict:
        """Bestimmt Upgrade-Parameter"""
        upgrades = []
        
        # Finde mögliche Upgrades
        for (from_type, to_type), cost in UPGRADE_COSTS.items():
            if player.get_available_population(from_type) > 0:
                can_afford = True
                for resource, amount in cost.items():
                    if not player.can_produce_resource(resource, amount):
                        can_afford = False
                        break
                
                if can_afford:
                    upgrades.append({
                        'from': from_type,
                        'to': to_type
                    })
                    if len(upgrades) >= 3:
                        break
        
        if upgrades:
            return {'upgrades': upgrades[:3]}
        
        return {}
# anno1800/game/engine.py - Optimized Version

"""
Hauptspiellogik und Game Engine - Optimierte Version
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import random
import logging
from collections import defaultdict

# Optimierung: Spezifischere Imports für bessere Performance
from anno1800.game.player import PlayerState
from anno1800.utils.constants import (
    ActionType, PopulationType, BuildingType, ResourceType,
    BUILDING_DEFINITIONS, STARTING_RESOURCES, 
    UPGRADE_COSTS, WORKFORCE_COSTS, SCORING,
    MAX_LIMITS, EXPLORATION_COSTS
)

logger = logging.getLogger(__name__)

class GamePhase(Enum):
    """Spielphasen"""
    SETUP = "setup"
    MAIN_GAME = "main_game"
    FINAL_ROUND = "final_round"
    SCORING = "scoring"
    ENDED = "ended"

@dataclass
class GameAction:
    """Repräsentiert eine Spielaktion"""
    player_id: int
    action_type: ActionType
    parameters: Dict = field(default_factory=dict)
    timestamp: float = 0
    success: bool = False
    result: Optional[Dict] = None
    
    def __str__(self):
        return f"Action({self.action_type.value}, Player {self.player_id})"

class GameEngine:
    """Hauptspiellogik für Anno 1800 mit Optimierungen"""
    
    # Klassenkonstanten für bessere Performance
    MIN_PLAYERS = 2
    MAX_PLAYERS = 4
    MAX_ROUNDS = 100  # Sicherheitslimit
    
    def __init__(self, num_players: int = 4):
        if not self.MIN_PLAYERS <= num_players <= self.MAX_PLAYERS:
            raise ValueError(f"Ungültige Spielerzahl: {num_players} ({self.MIN_PLAYERS}-{self.MAX_PLAYERS} erlaubt)")
        
        self.num_players = num_players
        self.players: List['PlayerState'] = []
        self.board = None  # Wird in setup_game initialisiert
        
        self.current_player_idx = 0
        self.round_number = 0
        self.phase = GamePhase.SETUP
        
        self.game_end_triggered = False
        self.final_round_trigger_player = None
        
        # Optimierung: Verwende deque für bessere Performance bei häufigen Anfügen
        self.action_history: List[GameAction] = []
        
        # Cache für häufig verwendete Berechnungen
        self._action_cache: Dict[int, Set[ActionType]] = {}
        self._last_cache_round = -1
        
        logger.info(f"Game Engine initialisiert für {num_players} Spieler")
    
    def setup_game(self, player_names: List[str], strategies: List[str]):
        """Bereitet das Spiel vor mit Fehlerbehandlung"""
        if len(player_names) != self.num_players:
            raise ValueError(f"Anzahl Namen ({len(player_names)}) stimmt nicht mit Spielerzahl ({self.num_players}) überein")
        
        if len(strategies) != self.num_players:
            raise ValueError(f"Anzahl Strategien ({len(strategies)}) stimmt nicht mit Spielerzahl ({self.num_players}) überein")
        
        # Lazy Import um zirkuläre Abhängigkeiten zu vermeiden
        from anno1800.game.player import PlayerState
        from anno1800.game.board import GameBoard
        
        # Initialisiere Board
        self.board = GameBoard()
        
        # Erstelle Spieler mit Fehlerbehandlung
        for i, (name, strategy) in enumerate(zip(player_names, strategies)):
            try:
                player = PlayerState(
                    id=i,
                    name=name or f"Spieler {i+1}",
                    strategy=strategy,
                    gold=STARTING_RESOURCES['gold'][i] if i < len(STARTING_RESOURCES['gold']) else 0
                )
                
                # Ziehe Startkarten mit Fehlerbehandlung
                self._draw_starting_cards(player)
                self.players.append(player)
                
            except Exception as e:
                logger.error(f"Fehler beim Erstellen von Spieler {i}: {e}")
                raise
        
        # Bestimme Startspieler
        self.current_player_idx = random.randint(0, self.num_players - 1)
        
        self.phase = GamePhase.MAIN_GAME
        self.round_number = 1
        
        logger.info(f"Spiel gestartet. Startspieler: {self.players[self.current_player_idx].name}")
    
    def _draw_starting_cards(self, player: 'PlayerState'):
        """Zieht Startkarten für einen Spieler mit Fehlerbehandlung"""
        cards_to_draw = {
            'farmer_worker': STARTING_RESOURCES['hand_cards'].get('farmer_worker', 7),
            'craftsman_engineer_investor': STARTING_RESOURCES['hand_cards'].get('craftsman_engineer_investor', 2)
        }
        
        for card_type, count in cards_to_draw.items():
            for _ in range(count):
                card = self.board.draw_population_card(card_type)
                if card:
                    player.hand_cards.append(card)
                else:
                    logger.warning(f"Konnte Karte {card_type} nicht ziehen - Stapel leer?")
    
    def get_current_player(self) -> Optional['PlayerState']:
        """Gibt aktuellen Spieler zurück mit Fehlerbehandlung"""
        if 0 <= self.current_player_idx < len(self.players):
            return self.players[self.current_player_idx]
        logger.error(f"Ungültiger Spielerindex: {self.current_player_idx}")
        return None
    
    def get_available_actions(self, player: 'PlayerState') -> List[ActionType]:
        """Gibt verfügbare Aktionen für einen Spieler zurück (mit Cache)"""
        if not player:
            return []
        
        # Cache-Invalidierung bei neuer Runde
        if self.round_number != self._last_cache_round:
            self._action_cache.clear()
            self._last_cache_round = self.round_number
        
        # Prüfe Cache
        if player.id in self._action_cache:
            return list(self._action_cache[player.id])
        
        actions = set()
        
        # Stadtfest ist immer möglich
        actions.add(ActionType.CITY_FESTIVAL)
        
        # Karten-Aktionen
        if player.hand_cards:
            actions.add(ActionType.EXCHANGE_CARDS)
            
            # Prüfe ob Karten spielbar (optimiert: nur einmal prüfen)
            if self._has_playable_cards(player):
                actions.add(ActionType.PLAY_CARD)
        
        # Bauen
        if self._can_build_anything(player):
            actions.add(ActionType.BUILD)
        
        # Bevölkerung
        if self._has_available_population(player):
            actions.add(ActionType.INCREASE_WORKFORCE)
            
            # Upgrades
            if player.get_available_population(PopulationType.FARMER) > 0:
                if self._can_upgrade_population(player):
                    actions.add(ActionType.UPGRADE_POPULATION)
        
        # Erkundung
        available_exploration = player.exploration_tokens - player.exhausted_exploration_tokens
        if available_exploration > 0:
            if self.board.old_world_islands:
                actions.add(ActionType.EXPLORE_OLD_WORLD)
            if self.board.new_world_islands:
                actions.add(ActionType.EXPLORE_NEW_WORLD)
            if self.board.expedition_cards and available_exploration >= 2:
                actions.add(ActionType.EXPEDITION)
        
        # Handel
        if player.trade_tokens - player.exhausted_trade_tokens > 0:
            actions.add(ActionType.TRADE)
        
        # Cache das Ergebnis
        self._action_cache[player.id] = actions
        
        return list(actions)
    
    def _has_playable_cards(self, player: 'PlayerState') -> bool:
        """Prüft ob Spieler spielbare Karten hat (optimiert)"""
        for card in player.hand_cards:
            requirements = card.get('requirements', {})
            if player.can_afford_resources(requirements):
                return True
        return False
    
    def _can_build_anything(self, player: 'PlayerState') -> bool:
        """Prüft ob Spieler etwas bauen kann (optimiert)"""
        for building_type in BuildingType:
            if self.board.available_buildings.get(building_type, 0) > 0:
                building_def = BUILDING_DEFINITIONS.get(building_type)
                if building_def and player.can_afford_resources(building_def.get('cost', {})):
                    return True
        return False
    
    def _has_available_population(self, player: 'PlayerState') -> bool:
        """Prüft ob Spieler verfügbare Bevölkerung hat"""
        return any(player.get_available_population(pt) > 0 for pt in PopulationType)
    
    def _can_upgrade_population(self, player: 'PlayerState') -> bool:
        """Prüft ob Spieler Bevölkerung upgraden kann"""
        for upgrade_key, cost in UPGRADE_COSTS.items():
            from_type, _ = upgrade_key
            if player.get_available_population(from_type) > 0:
                if player.can_afford_resources(cost):
                    return True
        return False
    
    def execute_action(self, action: GameAction) -> bool:
        """Führt eine Spielaktion aus mit verbesserter Fehlerbehandlung"""
        # Validierung
        if not self._validate_action(action):
            return False
        
        player = self.players[action.player_id]
        
        # Action-Handler Mapping für bessere Wartbarkeit
        action_handlers = {
            ActionType.BUILD: self._handle_build_action,
            ActionType.PLAY_CARD: self._handle_play_card_action,
            ActionType.EXCHANGE_CARDS: self._handle_exchange_cards_action,
            ActionType.INCREASE_WORKFORCE: self._handle_increase_workforce_action,
            ActionType.UPGRADE_POPULATION: self._handle_upgrade_action,
            ActionType.EXPLORE_OLD_WORLD: self._handle_explore_old_world_action,
            ActionType.EXPLORE_NEW_WORLD: self._handle_explore_new_world_action,
            ActionType.EXPEDITION: self._handle_expedition_action,
            ActionType.CITY_FESTIVAL: self._handle_city_festival_action,
            ActionType.TRADE: self._handle_trade_action,
            ActionType.BUILD_SHIP: self._handle_build_ship_action
        }
        
        handler = action_handlers.get(action.action_type)
        if not handler:
            logger.warning(f"Unbekannte Aktion: {action.action_type}")
            return False
        
        # Führe Aktion aus
        try:
            success = handler(player, action.parameters)
            action.success = success
            
            if success:
                # Cache invalidieren
                if player.id in self._action_cache:
                    del self._action_cache[player.id]
                
                # Prüfe Spielende
                if len(player.hand_cards) == 0 and not self.game_end_triggered:
                    self._trigger_game_end(player)
                
                # Nächster Spieler
                self.next_turn()
            
        except Exception as e:
            logger.error(f"Fehler bei Aktion {action.action_type}: {e}")
            action.success = False
            success = False
        
        # Aktion zur Historie hinzufügen
        self.action_history.append(action)
        
        return success
    
    def _validate_action(self, action: GameAction) -> bool:
        """Validiert eine Aktion"""
        if action.player_id < 0 or action.player_id >= len(self.players):
            logger.error(f"Ungültige Spieler-ID: {action.player_id}")
            return False
        
        # Prüfe ob Spieler am Zug
        if self.phase == GamePhase.MAIN_GAME:
            if action.player_id != self.current_player_idx:
                logger.warning(f"Spieler {action.player_id} ist nicht am Zug")
                return False
        
        return True
    
    def _handle_build_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Bau-Aktion mit Validierung"""
        building_type = params.get('building_type')
        if not building_type:
            logger.warning("Kein Gebäudetyp angegeben")
            return False
        
        # Prüfe Verfügbarkeit
        available = self.board.available_buildings.get(building_type, 0)
        if available <= 0:
            logger.warning(f"Gebäude {building_type} nicht verfügbar")
            return False
        
        # Baue Gebäude
        if player.build_building(building_type):
            self.board.available_buildings[building_type] -= 1
            logger.info(f"{player.name} baut {building_type.value}")
            return True
        
        return False
    
    def _handle_play_card_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Karte-spielen-Aktion"""
        card_id = params.get('card_id')
        if not card_id:
            return False
        
        # Finde Karte mit optimierter Suche
        card = next((c for c in player.hand_cards if c.get('id') == card_id), None)
        
        if not card:
            logger.warning(f"Karte {card_id} nicht in Hand")
            return False
        
        # Prüfe und bezahle Kosten
        requirements = card.get('requirements', {})
        if not player.can_afford_resources(requirements):
            return False
        
        if not player.pay_resources(requirements):
            return False
        
        # Spiele Karte
        player.hand_cards.remove(card)
        player.played_cards.append(card)
        
        # Wende Effekt an
        self._apply_card_effect(player, card.get('effect', {}))
        
        logger.info(f"{player.name} spielt Karte {card_id}")
        return True
    
    def _handle_exchange_cards_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Karten-Tausch-Aktion"""
        num_cards = params.get('num_cards', min(3, len(player.hand_cards)))
        cards_to_exchange = params.get('cards', [])
        
        if num_cards == 0 or not player.hand_cards:
            return False
        
        # Wenn spezifische Karten angegeben
        if cards_to_exchange:
            # Entferne spezifische Karten
            for card_id in cards_to_exchange[:num_cards]:
                card = next((c for c in player.hand_cards if c.get('id') == card_id), None)
                if card:
                    player.hand_cards.remove(card)
        else:
            # Entferne zufällige Karten
            for _ in range(min(num_cards, len(player.hand_cards))):
                player.hand_cards.pop(random.randrange(len(player.hand_cards)))
        
        # Ziehe neue Karten
        deck_types = ['farmer_worker', 'craftsman_engineer_investor', 'new_world']
        for _ in range(num_cards):
            deck_type = random.choice(deck_types)
            new_card = self.board.draw_population_card(deck_type)
            if new_card:
                player.hand_cards.append(new_card)
        
        logger.info(f"{player.name} tauscht {num_cards} Karten")
        return True
    
    def _handle_increase_workforce_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Arbeitskraft-Erhöhungs-Aktion"""
        pop_type = params.get('population_type', PopulationType.FARMER)
        amount = min(params.get('amount', 1), MAX_LIMITS['population_per_action'])
        
        if amount <= 0:
            return False
        
        cost = WORKFORCE_COSTS.get(pop_type, {})
        if not cost:
            logger.warning(f"Keine Kosten für {pop_type} definiert")
            return False
        
        # Berechne Gesamtkosten
        total_cost = {}
        for resource, base_amount in cost.items():
            total_cost[resource] = base_amount * amount
        
        if player.can_afford_resources(total_cost):
            if player.pay_resources(total_cost):
                player.population[pop_type] = player.population.get(pop_type, 0) + amount
                
                # Ziehe entsprechende Karten
                card_type = self._get_card_type_for_population(pop_type)
                for _ in range(amount):
                    card = self.board.draw_population_card(card_type)
                    if card:
                        player.hand_cards.append(card)
                    else:
                        # Zahle Gold wenn Stapel leer
                        player.gold = max(0, player.gold - 1)
                
                logger.info(f"{player.name} erhält {amount} {pop_type.value}")
                return True
        
        return False
    
    def _get_card_type_for_population(self, pop_type: PopulationType) -> str:
        """Gibt den Kartentyp für einen Bevölkerungstyp zurück"""
        if pop_type in [PopulationType.FARMER, PopulationType.WORKER]:
            return 'farmer_worker'
        else:
            return 'craftsman_engineer_investor'
    
    def _handle_upgrade_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Upgrade-Aktion"""
        from_type = params.get('from_type')
        to_type = params.get('to_type')
        amount = min(params.get('amount', 1), MAX_LIMITS['upgrades_per_action'])
        
        if not from_type or not to_type or amount <= 0:
            return False
        
        upgrade_key = (from_type, to_type)
        cost = UPGRADE_COSTS.get(upgrade_key)
        
        if not cost:
            logger.warning(f"Kein Upgrade-Pfad von {from_type} zu {to_type}")
            return False
        
        if player.get_available_population(from_type) < amount:
            return False
        
        # Berechne Gesamtkosten
        total_cost = {}
        for resource, base_amount in cost.items():
            total_cost[resource] = base_amount * amount
        
        if player.can_afford_resources(total_cost):
            if player.pay_resources(total_cost):
                player.population[from_type] -= amount
                player.population[to_type] = player.population.get(to_type, 0) + amount
                logger.info(f"{player.name} verbessert {amount} {from_type.value} zu {to_type.value}")
                return True
        
        return False
    
    def _handle_explore_old_world_action(self, player: 'PlayerState', params: Dict = None) -> bool:
        """Behandelt Alte-Welt-Erkundungs-Aktion"""
        # Berechne benötigte Erkundungsmarker
        islands_owned = len(player.old_world_islands)
        if islands_owned >= MAX_LIMITS['old_world_islands']:
            logger.warning("Maximale Anzahl Alte-Welt-Inseln erreicht")
            return False
        
        required_tokens = EXPLORATION_COSTS['old_world'][min(islands_owned, 3)]
        
        if player.exploration_tokens - player.exhausted_exploration_tokens < required_tokens:
            return False
        
        if not self.board.old_world_islands:
            return False
        
        # Verbrauche Erkundungsmarker
        player.exhausted_exploration_tokens += required_tokens
        
        # Erhalte Insel
        island = self.board.get_old_world_island()
        if island:
            player.old_world_islands.append(island)
            logger.info(f"{player.name} erkundet Alte-Welt-Insel: {island.name}")
            return True
        
        return False
    
    def _handle_explore_new_world_action(self, player: 'PlayerState', params: Dict = None) -> bool:
        """Behandelt Neue-Welt-Erkundungs-Aktion"""
        # Berechne benötigte Erkundungsmarker
        islands_owned = len(player.new_world_islands)
        if islands_owned >= MAX_LIMITS['new_world_islands']:
            logger.warning("Maximale Anzahl Neue-Welt-Inseln erreicht")
            return False
        
        required_tokens = EXPLORATION_COSTS['new_world'][min(islands_owned, 3)]
        
        if player.exploration_tokens - player.exhausted_exploration_tokens < required_tokens:
            return False
        
        if not self.board.new_world_islands:
            return False
        
        # Verbrauche Erkundungsmarker
        player.exhausted_exploration_tokens += required_tokens
        
        # Erhalte Insel
        island = self.board.get_new_world_island()
        if island:
            player.new_world_islands.append(island)
            
            # Ziehe Neue-Welt-Karten
            for _ in range(3):
                card = self.board.draw_population_card('new_world')
                if card:
                    player.hand_cards.append(card)
            
            logger.info(f"{player.name} erkundet Neue-Welt-Insel: {island.name}")
            return True
        
        return False
    
    def _handle_expedition_action(self, player: 'PlayerState', params: Dict = None) -> bool:
        """Behandelt Expeditions-Aktion"""
        required_tokens = EXPLORATION_COSTS.get('expedition', 2)
        
        if player.exploration_tokens - player.exhausted_exploration_tokens < required_tokens:
            return False
        
        if not self.board.expedition_cards:
            return False
        
        # Verbrauche Erkundungsmarker
        player.exhausted_exploration_tokens += required_tokens
        
        # Ziehe Expeditionskarten
        cards_to_draw = min(MAX_LIMITS['expedition_cards_per_action'], len(self.board.expedition_cards))
        expedition_cards = self.board.draw_expedition_cards(cards_to_draw)
        
        for card in expedition_cards:
            player.expedition_cards.append(card)
        
        logger.info(f"{player.name} startet Expedition und zieht {len(expedition_cards)} Karten")
        return len(expedition_cards) > 0
    
    def _handle_city_festival_action(self, player: 'PlayerState', params: Dict = None) -> bool:
        """Behandelt Stadtfest-Aktion"""
        player.reset_workers()
        return True
    
    def _handle_trade_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Handels-Aktion"""
        resource = params.get('resource')
        amount = params.get('amount', 1)
        target_player_id = params.get('target_player')
        
        if not resource or amount <= 0:
            return False
        
        # Implementiere Handelslogik
        # TODO: Vollständige Implementierung
        return False
    
    def _handle_build_ship_action(self, player: 'PlayerState', params: Dict) -> bool:
        """Behandelt Schiffsbau-Aktion"""
        ship_type = params.get('ship_type')
        if not ship_type:
            return False
        
        return player.build_ship(ship_type)
    
    def _apply_card_effect(self, player: 'PlayerState', effect: Dict):
        """Wendet Karteneffekt an mit Fehlerbehandlung"""
        if not effect:
            return
        
        effect_type = effect.get('type')
        value = effect.get('value', 0)
        
        effect_handlers = {
            'gain_gold': lambda: setattr(player, 'gold', player.gold + value),
            'gain_trade': lambda: setattr(player, 'trade_tokens', player.trade_tokens + value),
            'gain_exploration': lambda: setattr(player, 'exploration_tokens', player.exploration_tokens + value),
            'gain_population': lambda: self._add_random_population(player, value),
            'extra_action': lambda: logger.info(f"{player.name} erhält eine Extra-Aktion"),
            'free_upgrade': lambda: logger.info(f"{player.name} erhält kostenloses Upgrade")
        }
        
        handler = effect_handlers.get(effect_type)
        if handler:
            try:
                handler()
                logger.info(f"Effekt angewendet: {effect_type} = {value}")
            except Exception as e:
                logger.error(f"Fehler beim Anwenden von Effekt {effect_type}: {e}")
    
    def _add_random_population(self, player: 'PlayerState', amount: int):
        """Fügt zufällige Bevölkerung hinzu"""
        pop_types = [PopulationType.FARMER, PopulationType.WORKER, PopulationType.CRAFTSMAN]
        for _ in range(amount):
            pop_type = random.choice(pop_types)
            player.population[pop_type] = player.population.get(pop_type, 0) + 1
    
    def next_turn(self):
        """Wechselt zum nächsten Spieler mit Rundenzählung"""
        if self.phase == GamePhase.ENDED:
            return
        
        self.current_player_idx = (self.current_player_idx + 1) % self.num_players
        
        # Neue Runde wenn alle Spieler dran waren
        if self.current_player_idx == 0:
            self.round_number += 1
            logger.info(f"Runde {self.round_number} beginnt")
            
            # Sicherheitscheck für Endlosschleifen
            if self.round_number > self.MAX_ROUNDS:
                logger.warning(f"Maximale Rundenzahl ({self.MAX_ROUNDS}) erreicht - Spiel wird beendet")
                self.phase = GamePhase.ENDED
                self._end_game()
                return
            
            # Prüfe auf Spielende in Finalrunde
            if self.phase == GamePhase.FINAL_ROUND:
                if self.current_player_idx == self.final_round_trigger_player:
                    self.phase = GamePhase.ENDED
                    self._end_game()
    
    def _trigger_game_end(self, player: 'PlayerState'):
        """Löst Spielende aus"""
        if not self.game_end_triggered:
            self.game_end_triggered = True
            self.final_round_trigger_player = player.id
            self.phase = GamePhase.FINAL_ROUND
            player.has_fireworks = True  # Feuerwerk-Bonus
            logger.info(f"Spielende ausgelöst durch {player.name} - Finalrunde beginnt")
    
    def _end_game(self):
        """Beendet das Spiel und berechnet Punkte"""
        self.phase = GamePhase.SCORING
        
        # Berechne Punkte für alle Spieler
        scores = []
        for player in self.players:
            score = player.calculate_score()
            scores.append((player.name, score))
            logger.info(f"{player.name}: {score} Punkte")
        
        # Sortiere nach Punkten
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Setze Ränge
        for i, player in enumerate(self.players):
            for rank, (name, _) in enumerate(scores, 1):
                if player.name == name:
                    player.rank = rank
                    break
        
        self.phase = GamePhase.ENDED
        logger.info(f"Spiel beendet - Sieger: {scores[0][0]} mit {scores[0][1]} Punkten")
    
    def get_game_state(self) -> Dict:
        """Gibt den aktuellen Spielzustand zurück"""
        return {
            'phase': self.phase.value,
            'round': self.round_number,
            'current_player': self.current_player_idx,
            'game_end_triggered': self.game_end_triggered,
            'players': [
                {
                    'id': p.id,
                    'name': p.name,
                    'score': p.final_score,
                    'rank': p.rank,
                    'hand_size': len(p.hand_cards),
                    'gold': p.gold,
                    'buildings': len(p.buildings)
                }
                for p in self.players
            ],
            'available_buildings': sum(self.board.available_buildings.values()) if self.board else 0,
            'actions_played': len(self.action_history)
        }
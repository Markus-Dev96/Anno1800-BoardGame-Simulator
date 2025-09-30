# anno1800/game/engine.py
"""
Game Engine für Anno 1800 Brettspiel - Vollständige Implementation
Basiert auf den offiziellen Spielregeln
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import random
import logging

from anno1800.game.player import PlayerState
from anno1800.game.board import GameBoard
from anno1800.utils.constants import (
    ActionType, PopulationType, BuildingType, ResourceType,
    BUILDING_DEFINITIONS, STARTING_RESOURCES, 
    UPGRADE_COSTS, WORKFORCE_COSTS, SCORING,
    EXPLORATION_COSTS, NEW_WORLD_RESOURCES, BASE_RESOURCES
)

logger = logging.getLogger(__name__)

class GamePhase(Enum):
    """Spielphasen"""
    SETUP = "setup"
    MAIN_GAME = "main_game"
    FINAL_ROUND = "final_round"  # Letzte Runde nach Spielende-Auslösung
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

class GameEngine:
    """Hauptspiellogik für Anno 1800 Brettspiel"""
    
    def __init__(self, num_players: int = 4):
        if not 2 <= num_players <= 4:
            raise ValueError(f"Ungültige Spielerzahl: {num_players} (2-4 erlaubt)")
        
        self.num_players = num_players
        self.players: List[PlayerState] = []
        self.board = GameBoard()
        
        self.current_player_idx = 0
        self.round_number = 0
        self.phase = GamePhase.SETUP
        
        self.game_end_triggered = False
        self.final_round_trigger_player = None
        
        self.action_history: List[GameAction] = []
        
        logger.info(f"Game Engine initialisiert für {num_players} Spieler")
    
    def setup_game(self, player_names: List[str], strategies: List[str]):
        """Bereitet das Spiel vor"""
        if len(player_names) != self.num_players:
            raise ValueError("Anzahl Namen stimmt nicht mit Spielerzahl überein")
        
        # Erstelle Spieler
        for i, (name, strategy) in enumerate(zip(player_names, strategies)):
            player = PlayerState(
                id=i,
                name=name,
                strategy=strategy,
                gold=STARTING_RESOURCES['gold'][i]  # Startgold nach Position
            )
            
            # Ziehe Startkarten
            for _ in range(STARTING_RESOURCES['hand_cards']['farmer_worker']):
                card = self.board.draw_population_card('farmer_worker')
                if card:
                    player.hand_cards.append(card)
            
            for _ in range(STARTING_RESOURCES['hand_cards']['craftsman_engineer_investor']):
                card = self.board.draw_population_card('craftsman_engineer_investor')
                if card:
                    player.hand_cards.append(card)
            
            self.players.append(player)
        
        # Bestimme Startspieler
        self.current_player_idx = random.randint(0, self.num_players - 1)
        
        self.phase = GamePhase.MAIN_GAME
        self.round_number = 1
        
        logger.info(f"Spiel gestartet. Startspieler: {self.players[self.current_player_idx].name}")
    
    def get_current_player(self) -> Optional[PlayerState]:
        """Gibt aktuellen Spieler zurück"""
        if 0 <= self.current_player_idx < len(self.players):
            return self.players[self.current_player_idx]
        return None
    
    def get_available_actions(self, player: PlayerState) -> List[ActionType]:
        """Gibt verfügbare Aktionen für einen Spieler zurück"""
        if not player:
            return []
        
        actions = []
        
        # Stadtfest ist immer möglich
        actions.append(ActionType.STADTFEST)
        
        # Karten austauschen wenn Handkarten vorhanden
        if player.hand_cards:
            actions.append(ActionType.KARTEN_AUSTAUSCHEN)
            
            # Karten ausspielen wenn erfüllbar
            for card in player.hand_cards:
                if self._can_play_card(player, card):
                    actions.append(ActionType.BEVÖLKERUNG_AUSSPIELEN)
                    break
        
        # Ausbauen wenn möglich
        if self._can_build_anything(player):
            actions.append(ActionType.AUSBAUEN)
        
        # Arbeitskraft erhöhen
        if self._can_increase_workforce(player):
            actions.append(ActionType.ARBEITSKRAFT_ERHÖHEN)
        
        # Aufsteigen
        if self._can_upgrade_population(player):
            actions.append(ActionType.AUFSTEIGEN)
        
        # Erkundung
        available_exploration = player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen
        if available_exploration > 0:
            # Alte Welt
            if self.board.old_world_islands and len(player.old_world_islands) < 4:
                needed = EXPLORATION_COSTS['old_world'][min(len(player.old_world_islands), 3)]
                if available_exploration >= needed:
                    actions.append(ActionType.ALTE_WELT_ERSCHLIESSEN)
            
            # Neue Welt
            if self.board.new_world_islands and len(player.new_world_islands) < 4:
                needed = EXPLORATION_COSTS['new_world'][min(len(player.new_world_islands), 3)]
                if available_exploration >= needed:
                    actions.append(ActionType.NEUE_WELT_ERKUNDEN)
            
            # Expedition
            if self.board.expedition_cards and available_exploration >= 2:
                actions.append(ActionType.EXPEDITION)
        
        return list(set(actions))
    
    def _can_play_card(self, player: PlayerState, card: Dict) -> bool:
        """Prüft ob eine Karte gespielt werden kann"""
        requirements = card.get('requirements', {})
        
        for resource, amount in requirements.items():
            if not player.can_produce_resource(resource, amount):
                # Prüfe Handel
                can_trade = False
                for other_player in self.players:
                    if other_player.id != player.id:
                        if player.can_trade_resource(resource, other_player):
                            can_trade = True
                            break
                if not can_trade:
                    return False
        return True
    
    def _can_build_anything(self, player: PlayerState) -> bool:
        """Prüft ob Spieler etwas bauen kann"""
        for building_type in BuildingType:
            if self.board.available_buildings.get(building_type, 0) > 0:
                if player.can_afford_building_cost(building_type):
                    return True
        return False
    
    def _can_increase_workforce(self, player: PlayerState) -> bool:
        """Prüft ob Arbeitskraft erhöht werden kann"""
        for pop_type in PopulationType:
            cost = WORKFORCE_COSTS.get(pop_type, {})
            can_afford = True
            for resource, amount in cost.items():
                if not player.can_produce_resource(resource, amount):
                    can_afford = False
                    break
            if can_afford:
                return True
        return False
    
    def _can_upgrade_population(self, player: PlayerState) -> bool:
        """Prüft ob Bevölkerung verbessert werden kann"""
        for upgrade_key, cost in UPGRADE_COSTS.items():
            from_type, to_type = upgrade_key
            if player.get_available_population(from_type) > 0:
                can_afford = True
                for resource, amount in cost.items():
                    if not player.can_produce_resource(resource, amount):
                        can_afford = False
                        break
                if can_afford:
                    return True
        return False
    
    def execute_action(self, action: GameAction) -> bool:
        """Führt eine Spielaktion aus"""
        if not self._validate_action(action):
            return False
        
        player = self.players[action.player_id]
        
        # Action Handler
        action_handlers = {
            ActionType.AUSBAUEN: self._handle_ausbauen,
            ActionType.BEVÖLKERUNG_AUSSPIELEN: self._handle_karte_ausspielen,
            ActionType.KARTEN_AUSTAUSCHEN: self._handle_karten_austauschen,
            ActionType.ARBEITSKRAFT_ERHÖHEN: self._handle_arbeitskraft_erhöhen,
            ActionType.AUFSTEIGEN: self._handle_aufsteigen,
            ActionType.ALTE_WELT_ERSCHLIESSEN: self._handle_alte_welt,
            ActionType.NEUE_WELT_ERKUNDEN: self._handle_neue_welt,
            ActionType.EXPEDITION: self._handle_expedition,
            ActionType.STADTFEST: self._handle_stadtfest
        }
        
        handler = action_handlers.get(action.action_type)
        if not handler:
            logger.warning(f"Unbekannte Aktion: {action.action_type}")
            return False
        
        # Führe Aktion aus
        success = handler(player, action.parameters)
        action.success = success
        
        if success:
            # Prüfe Spielende
            if len(player.hand_cards) == 0 and not self.game_end_triggered:
                self._trigger_game_end(player)
            
            # Nächster Spieler
            self.next_turn()
        
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
    
    def _handle_ausbauen(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Ausbauen-Aktion (Industrien, Werften oder Schiffe)"""
        buildings_to_build = params.get('buildings', [])
        if not buildings_to_build:
            return False
        
        # Werften zählen für Schiffsbau
        num_shipyards = sum(player.shipyards.values())
        ships_built = 0
        
        for building_type in buildings_to_build:
            building_def = BUILDING_DEFINITIONS.get(building_type)
            if not building_def:
                continue
            
            # Prüfe Verfügbarkeit
            if self.board.available_buildings.get(building_type, 0) <= 0:
                logger.warning(f"Gebäude {building_type} nicht verfügbar")
                continue
            
            # Spezialbehandlung für Schiffe
            if building_def.get('type') == 'ship':
                if ships_built >= num_shipyards:
                    logger.warning("Nicht genug Werften für weitere Schiffe")
                    continue
                ships_built += 1
            
            # Baue Gebäude
            if player.build_building(building_type):
                self.board.available_buildings[building_type] -= 1
                logger.info(f"{player.name} baut {building_type.value}")
        
        return ships_built > 0 or len(buildings_to_build) == 1
    
    def _handle_karte_ausspielen(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Bevölkerungs-Karte ausspielen"""
        card_id = params.get('card_id')
        if not card_id:
            return False
        
        # Finde Karte
        card = None
        for c in player.hand_cards:
            if c.get('id') == card_id:
                card = c
                break
        
        if not card:
            return False
        
        # Prüfe und bezahle Kosten
        requirements = card.get('requirements', {})
        for resource, amount in requirements.items():
            if not player.produce_resource(resource, amount):
                # Versuche Handel
                traded = False
                for other_player in self.players:
                    if other_player.id != player.id:
                        if player.trade_resource(resource, other_player):
                            traded = True
                            break
                if not traded:
                    return False
        
        # Spiele Karte aus
        player.hand_cards.remove(card)
        player.played_cards.append(card)
        
        logger.info(f"{player.name} spielt Karte {card_id} aus")
        return True
    
    def _handle_karten_austauschen(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Karten austauschen"""
        cards_to_exchange = params.get('cards', [])
        if not cards_to_exchange or len(cards_to_exchange) > 3:
            return False
        
        # Sortiere Karten nach Deck-Typ
        cards_by_deck = {}
        for card_id in cards_to_exchange:
            card = None
            for c in player.hand_cards:
                if c.get('id') == card_id:
                    card = c
                    break
            
            if card:
                deck_type = card.get('deck_type', card.get('type'))
                if deck_type not in cards_by_deck:
                    cards_by_deck[deck_type] = []
                cards_by_deck[deck_type].append(card)
        
        # Lege Karten zurück und ziehe neue
        for deck_type, cards in cards_by_deck.items():
            for card in cards:
                player.hand_cards.remove(card)
                self.board.return_card(deck_type, card)
            
            # Ziehe neue Karten
            for _ in range(len(cards)):
                new_card = self.board.draw_population_card(deck_type)
                if new_card:
                    player.hand_cards.append(new_card)
        
        logger.info(f"{player.name} tauscht {len(cards_to_exchange)} Karten aus")
        return True
    
    def _handle_arbeitskraft_erhöhen(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Arbeitskraft erhöhen"""
        increases = params.get('increases', [])
        if not increases or len(increases) > 3:
            return False
        
        total_cards_needed = {'farmer_worker': 0, 'craftsman_engineer_investor': 0}
        gold_needed = 0
        
        for pop_type in increases:
            # Füge Bevölkerung hinzu
            if not player.add_population(pop_type):
                return False
            
            # Bestimme welche Karte gezogen werden muss
            if pop_type in [PopulationType.BAUER, PopulationType.ARBEITER]:
                deck_type = 'farmer_worker'
            else:
                deck_type = 'craftsman_engineer_investor'
            
            # Ziehe Karte oder zahle Gold
            card = self.board.draw_population_card(deck_type)
            if card:
                player.hand_cards.append(card)
            else:
                # Kein Kartenstapel mehr - zahle Gold
                if pop_type in [PopulationType.BAUER, PopulationType.ARBEITER]:
                    gold_needed += 1
                else:
                    gold_needed += 2
        
        # Zahle Gold wenn nötig
        if gold_needed > 0:
            if player.gold < gold_needed:
                logger.warning(f"{player.name} hat nicht genug Gold für fehlende Karten")
                return False
            player.gold -= gold_needed
            logger.info(f"{player.name} zahlt {gold_needed} Gold für fehlende Karten")
        
        logger.info(f"{player.name} erhöht Arbeitskraft um {len(increases)}")
        return True
    
    def _handle_aufsteigen(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Aufsteigen"""
        upgrades = params.get('upgrades', [])
        if not upgrades or len(upgrades) > 3:
            return False
        
        for upgrade in upgrades:
            from_type = upgrade.get('from')
            to_type = upgrade.get('to')
            
            if not from_type or not to_type:
                continue
            
            if not player.upgrade_population(from_type, to_type):
                return False
        
        logger.info(f"{player.name} führt {len(upgrades)} Verbesserungen durch")
        return True
    
    def _handle_alte_welt(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Alte Welt erschließen"""
        # Prüfe Kosten
        num_islands = len(player.old_world_islands)
        if num_islands >= 4:
            return False
        
        needed_exploration = EXPLORATION_COSTS['old_world'][num_islands]
        available = player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen
        
        if available < needed_exploration:
            return False
        
        # Erschöpfe Plättchen
        player.erschöpfte_erkundungs_plättchen += needed_exploration
        
        # Ziehe Insel
        island = self.board.get_old_world_island()
        if not island:
            return False
        
        player.old_world_islands.append(island)
        
        # Wende Effekt an
        if island.effect:
            self._apply_island_effect(player, island.effect)
        
        logger.info(f"{player.name} erschließt Alte-Welt-Insel: {island.name}")
        return True
    
    def _handle_neue_welt(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Neue Welt erkunden"""
        # Prüfe Kosten
        num_islands = len(player.new_world_islands)
        if num_islands >= 4:
            return False
        
        needed_exploration = EXPLORATION_COSTS['new_world'][num_islands]
        available = player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen
        
        if available < needed_exploration:
            return False
        
        # Erschöpfe Plättchen
        player.erschöpfte_erkundungs_plättchen += needed_exploration
        
        # Ziehe Insel
        island = self.board.get_new_world_island()
        if not island:
            return False
        
        player.new_world_islands.append({
            'name': island.name,
            'resources': island.resources
        })
        
        # Ziehe 3 Neue-Welt-Karten
        for _ in range(3):
            card = self.board.draw_population_card('new_world')
            if card:
                player.hand_cards.append(card)
        
        logger.info(f"{player.name} erkundet Neue-Welt-Insel: {island.name}")
        return True
    
    def _handle_expedition(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Expeditions-Karten nehmen"""
        available = player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen
        
        if available < 2:
            return False
        
        # Erschöpfe 2 Erkundungsplättchen
        player.erschöpfte_erkundungs_plättchen += 2
        
        # Ziehe bis zu 3 Expeditionskarten
        cards_drawn = 0
        for _ in range(3):
            card = self.board.draw_expedition_card()
            if card:
                player.expedition_cards.append(card)
                cards_drawn += 1
        
        logger.info(f"{player.name} nimmt {cards_drawn} Expeditions-Karten")
        return cards_drawn > 0
    
    def _handle_stadtfest(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Stadtfest feiern"""
        player.city_festival()
        return True
    
    def _apply_island_effect(self, player: PlayerState, effect: Dict):
        """Wendet Insel-Effekt an"""
        effect_type = effect.get('type')
        
        if effect_type == 'gold':
            amount = effect.get('amount', 0)
            player.gold += amount
            logger.info(f"{player.name} erhält {amount} Gold von Insel")
        
        elif effect_type == 'population':
            pop_type = effect.get('population_type')
            amount = effect.get('amount', 1)
            if pop_type:
                player.population[pop_type] = player.population.get(pop_type, 0) + amount
                logger.info(f"{player.name} erhält {amount} {pop_type.value} von Insel")
        
        elif effect_type == 'building':
            building_type = effect.get('building_type')
            if building_type and building_type not in player.buildings:
                player.buildings.append(building_type)
                logger.info(f"{player.name} erhält {building_type.value} von Insel")
        
        elif effect_type == 'expedition_cards':
            amount = effect.get('amount', 1)
            for _ in range(amount):
                card = self.board.draw_expedition_card()
                if card:
                    player.expedition_cards.append(card)
            logger.info(f"{player.name} erhält {amount} Expeditions-Karten von Insel")
    
    def next_turn(self):
        """Wechselt zum nächsten Spieler"""
        if self.phase == GamePhase.ENDED:
            return
        
        self.current_player_idx = (self.current_player_idx + 1) % self.num_players
        
        # Neue Runde wenn alle Spieler dran waren
        if self.current_player_idx == 0:
            self.round_number += 1
            logger.info(f"Runde {self.round_number} beginnt")
            
            # Prüfe auf Spielende in Finalrunde
            if self.phase == GamePhase.FINAL_ROUND:
                # War das die letzte Runde?
                if self.final_round_trigger_player is not None:
                    self._end_game()
    
    def _trigger_game_end(self, player: PlayerState):
        """Löst Spielende aus"""
        if not self.game_end_triggered:
            self.game_end_triggered = True
            self.final_round_trigger_player = player.id
            player.has_fireworks = True
            self.phase = GamePhase.FINAL_ROUND
            logger.info(f"Spielende ausgelöst durch {player.name} - Nach dieser Runde folgt noch eine letzte Runde")
    
    def _end_game(self):
        """Beendet das Spiel und berechnet Punkte"""
        self.phase = GamePhase.SCORING
        
        # Berechne Punkte für alle Spieler
        for player in self.players:
            player.calculate_score()
        
        # Bestimme Ränge
        sorted_players = sorted(self.players, key=lambda p: p.final_score, reverse=True)
        for i, player in enumerate(sorted_players):
            player.rank = i + 1
        
        self.phase = GamePhase.ENDED
        logger.info("Spiel beendet - Punkte berechnet")
    
    def get_winner(self) -> Optional[PlayerState]:
        """Gibt den Gewinner zurück"""
        if self.phase != GamePhase.ENDED:
            return None
        
        return max(self.players, key=lambda p: p.final_score)
# anno1800/game/engine.py - Complete with all action handlers

"""
Hauptspiellogik und Game Engine
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random
import logging

from anno1800.game.player import PlayerState
from anno1800.game.board import GameBoard, Island
from anno1800.utils.constants import *

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
    parameters: Dict
    timestamp: float = 0
    success: bool = False
    result: Optional[Dict] = None

class GameEngine:
    """Hauptspiellogik für Anno 1800"""
    
    def __init__(self, num_players: int = 4):
        if num_players < 2 or num_players > 4:
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
    
    def get_current_player(self) -> PlayerState:
        """Gibt aktuellen Spieler zurück"""
        return self.players[self.current_player_idx]
    
    def get_available_actions(self, player: PlayerState) -> List[ActionType]:
        """Gibt verfügbare Aktionen für einen Spieler zurück"""
        actions = [ActionType.CITY_FESTIVAL]  # Immer möglich
        
        # Karten-Aktionen
        if player.hand_cards:
            actions.append(ActionType.EXCHANGE_CARDS)
            
            # Prüfe ob Karten spielbar
            for card in player.hand_cards:
                if player.can_afford_resources(card.get('requirements', {})):
                    actions.append(ActionType.PLAY_CARD)
                    break
        
        # Bauen
        for building_type in BuildingType:
            if self.board.available_buildings.get(building_type, 0) > 0:
                building_def = BUILDING_DEFINITIONS.get(building_type)
                if building_def and player.can_afford_resources(building_def.get('cost', {})):
                    actions.append(ActionType.BUILD)
                    break
        
        # Bevölkerung
        if any(player.get_available_population(pt) > 0 for pt in PopulationType):
            actions.append(ActionType.INCREASE_WORKFORCE)
            
            # Upgrades
            if player.get_available_population(PopulationType.FARMER) > 0:
                actions.append(ActionType.UPGRADE_POPULATION)
        
        # Erkundung
        if player.exploration_tokens - player.exhausted_exploration_tokens > 0:
            if self.board.old_world_islands:
                actions.append(ActionType.EXPLORE_OLD_WORLD)
            if self.board.new_world_islands:
                actions.append(ActionType.EXPLORE_NEW_WORLD)
            if self.board.expedition_cards:
                actions.append(ActionType.EXPEDITION)
        
        return list(set(actions))  # Duplikate entfernen
    
    def execute_action(self, action: GameAction) -> bool:
        """Führt eine Spielaktion aus"""
        if action.player_id < 0 or action.player_id >= len(self.players):
            logger.error(f"Ungültige Spieler-ID: {action.player_id}")
            return False
        
        player = self.players[action.player_id]
        
        # Prüfe ob Spieler am Zug
        if action.player_id != self.current_player_idx and self.phase == GamePhase.MAIN_GAME:
            logger.warning(f"Spieler {player.name} ist nicht am Zug")
            return False
        
        # Führe Aktion aus
        success = False
        
        if action.action_type == ActionType.BUILD:
            success = self._handle_build_action(player, action.parameters)
        elif action.action_type == ActionType.PLAY_CARD:
            success = self._handle_play_card_action(player, action.parameters)
        elif action.action_type == ActionType.EXCHANGE_CARDS:
            success = self._handle_exchange_cards_action(player, action.parameters)
        elif action.action_type == ActionType.INCREASE_WORKFORCE:
            success = self._handle_increase_workforce_action(player, action.parameters)
        elif action.action_type == ActionType.UPGRADE_POPULATION:
            success = self._handle_upgrade_action(player, action.parameters)
        elif action.action_type == ActionType.EXPLORE_OLD_WORLD:
            success = self._handle_explore_old_world_action(player)
        elif action.action_type == ActionType.EXPLORE_NEW_WORLD:
            success = self._handle_explore_new_world_action(player)
        elif action.action_type == ActionType.EXPEDITION:
            success = self._handle_expedition_action(player)
        elif action.action_type == ActionType.CITY_FESTIVAL:
            success = self._handle_city_festival_action(player)
        else:
            logger.warning(f"Unbekannte Aktion: {action.action_type}")
        
        action.success = success
        self.action_history.append(action)
        
        if success:
            # Prüfe Spielende
            if len(player.hand_cards) == 0 and not self.game_end_triggered:
                self._trigger_game_end(player)
            
            # Nächster Spieler
            self.next_turn()
        
        return success
    
    def _handle_build_action(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Bau-Aktion"""
        building_type = params.get('building_type')
        if not building_type:
            return False
        
        # Prüfe Verfügbarkeit
        if self.board.available_buildings.get(building_type, 0) <= 0:
            logger.warning(f"Gebäude {building_type} nicht verfügbar")
            return False
        
        # Baue Gebäude
        if player.build_building(building_type):
            self.board.available_buildings[building_type] -= 1
            return True
        
        return False
    
    def _handle_play_card_action(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Karte-spielen-Aktion"""
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
    
    def _handle_exchange_cards_action(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Karten-Tausch-Aktion"""
        # Vereinfachte Implementierung: Tausche bis zu 3 Karten
        cards_to_discard = min(3, len(player.hand_cards))
        
        if cards_to_discard == 0:
            return False
        
        # Entferne Karten
        for _ in range(cards_to_discard):
            if player.hand_cards:
                player.hand_cards.pop(0)
        
        # Ziehe neue Karten
        for _ in range(cards_to_discard):
            # Ziehe zufällig aus einem der Decks
            deck_types = ['farmer_worker', 'craftsman_engineer_investor', 'new_world']
            deck_type = random.choice(deck_types)
            new_card = self.board.draw_population_card(deck_type)
            if new_card:
                player.hand_cards.append(new_card)
        
        logger.info(f"{player.name} tauscht {cards_to_discard} Karten")
        return True
    
    def _handle_increase_workforce_action(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Arbeitskraft-Erhöhungs-Aktion"""
        pop_type = params.get('population_type', PopulationType.FARMER)
        amount = params.get('amount', 1)
        
        # Vereinfachte Implementierung: Füge Bevölkerung hinzu
        if pop_type == PopulationType.FARMER:
            cost = WORKFORCE_COSTS[PopulationType.FARMER]
        elif pop_type == PopulationType.WORKER:
            cost = WORKFORCE_COSTS[PopulationType.WORKER]
        else:
            # Für höhere Stufen benötigen wir Upgrades
            return False
        
        if player.can_afford_resources(cost):
            if player.pay_resources(cost):
                player.population[pop_type] = player.population.get(pop_type, 0) + amount
                logger.info(f"{player.name} erhält {amount} {pop_type.value}")
                return True
        
        return False
    
    def _handle_upgrade_action(self, player: PlayerState, params: Dict) -> bool:
        """Behandelt Upgrade-Aktion"""
        from_type = params.get('from_type')
        to_type = params.get('to_type')
        amount = params.get('amount', 1)
        
        if not from_type or not to_type:
            return False
        
        upgrade_key = (from_type, to_type)
        cost = UPGRADE_COSTS.get(upgrade_key)
        
        if not cost:
            return False
        
        if player.get_available_population(from_type) < amount:
            return False
        
        if player.can_afford_resources(cost):
            if player.pay_resources(cost):
                player.population[from_type] -= amount
                player.population[to_type] = player.population.get(to_type, 0) + amount
                logger.info(f"{player.name} verbessert {amount} {from_type.value} zu {to_type.value}")
                return True
        
        return False
    
    def _handle_explore_old_world_action(self, player: PlayerState) -> bool:
        """Behandelt Alte-Welt-Erkundungs-Aktion"""
        if player.exploration_tokens - player.exhausted_exploration_tokens <= 0:
            return False
        
        if not self.board.old_world_islands:
            return False
        
        # Verbrauche Erkundungsmarker
        player.exhausted_exploration_tokens += 1
        
        # Erhalte Insel
        island = self.board.get_old_world_island()
        if island:
            player.old_world_islands.append(island)
            logger.info(f"{player.name} erkundet Alte-Welt-Insel: {island.name}")
            return True
        
        return False
    
    def _handle_explore_new_world_action(self, player: PlayerState) -> bool:
        """Behandelt Neue-Welt-Erkundungs-Aktion"""
        if player.exploration_tokens - player.exhausted_exploration_tokens <= 0:
            return False
        
        if not self.board.new_world_islands:
            return False
        
        # Verbrauche Erkundungsmarker
        player.exhausted_exploration_tokens += 1
        
        # Erhalte Insel
        island = self.board.get_new_world_island()
        if island:
            player.new_world_islands.append(island)
            logger.info(f"{player.name} erkundet Neue-Welt-Insel: {island.name}")
            return True
        
        return False
    
    def _handle_expedition_action(self, player: PlayerState) -> bool:
        """Behandelt Expeditions-Aktion"""
        if player.exploration_tokens - player.exhausted_exploration_tokens <= 0:
            return False
        
        if not self.board.expedition_cards:
            return False
        
        # Verbrauche Erkundungsmarker
        tokens_used = min(2, player.exploration_tokens - player.exhausted_exploration_tokens)
        player.exhausted_exploration_tokens += tokens_used
        
        # Ziehe Expeditionskarten (bis zu 3)
        cards_to_draw = min(3, tokens_used * 2)  # Bis zu 3 Karten für 2 Marker
        expedition_cards = self.board.draw_expedition_cards(cards_to_draw)
        
        for card in expedition_cards:
            player.expedition_cards.append(card)
        
        logger.info(f"{player.name} startet Expedition und zieht {len(expedition_cards)} Karten")
        return len(expedition_cards) > 0
    
    def _handle_city_festival_action(self, player: PlayerState) -> bool:
        """Behandelt Stadtfest-Aktion"""
        # Setze alle Arbeiter zurück
        player.reset_workers()
        logger.info(f"{player.name} feiert Stadtfest - alle Arbeiter zurückgesetzt")
        return True
    
    def _apply_card_effect(self, player: PlayerState, effect: Dict):
        """Wendet Karteneffekt an"""
        effect_type = effect.get('type')
        value = effect.get('value', 0)
        
        if effect_type == 'gain_gold':
            player.gold += value
            logger.info(f"{player.name} erhält {value} Gold")
        elif effect_type == 'gain_population':
            # Füge zufällige Bevölkerung hinzu
            pop_types = [PopulationType.FARMER, PopulationType.WORKER, PopulationType.CRAFTSMAN]
            pop_type = random.choice(pop_types)
            player.population[pop_type] = player.population.get(pop_type, 0) + value
            logger.info(f"{player.name} erhält {value} {pop_type.value}")
        elif effect_type == 'gain_trade':
            player.trade_tokens += value
            logger.info(f"{player.name} erhält {value} Handelsmarker")
        elif effect_type == 'gain_exploration':
            player.exploration_tokens += value
            logger.info(f"{player.name} erhält {value} Erkundungsmarker")
        elif effect_type == 'extra_action':
            # Extra Aktion - aktueller Spieler darf nochmal
            logger.info(f"{player.name} erhält eine Extra-Aktion")
            # Implementierung würde hier den Spielzug wiederholen
        elif effect_type == 'free_upgrade':
            # Kostenloses Upgrade
            logger.info(f"{player.name} erhält kostenloses Upgrade")
    
    def next_turn(self):
        """Wechselt zum nächsten Spieler"""
        if self.phase == GamePhase.ENDED:
            return
        
        self.current_player_idx = (self.current_player_idx + 1) % self.num_players
        
        # Neue Runde wenn alle Spieler dran waren
        if self.current_player_idx == 0:
            self.round_number += 1
            self.log_message(f"Runde {self.round_number} beginnt")
            
            # Prüfe auf Spielende in Finalrunde
            if self.phase == GamePhase.FINAL_ROUND:
                if self.current_player_idx == self.final_round_trigger_player:
                    self.phase = GamePhase.ENDED
                    self._end_game()
    
    def _end_game(self):
        """Beendet das Spiel und berechnet Punkte"""
        self.phase = GamePhase.SCORING
        
        # Berechne Punkte für alle Spieler
        for player in self.players:
            player.calculate_score()
        
        self.phase = GamePhase.ENDED
        self.log_message("Spiel beendet - Punkte berechnet")
    
    def _trigger_game_end(self, player: PlayerState):
        """Löst Spielende aus"""
        if not self.game_end_triggered:
            self.game_end_triggered = True
            self.final_round_trigger_player = player.id
            self.phase = GamePhase.FINAL_ROUND
            self.log_message(f"Spielende ausgelöst durch {player.name} - Finalrunde beginnt")
    
    def log_message(self, message: str):
        """Loggt eine Nachricht"""
        logger.info(message)
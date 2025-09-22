# anno1800/game/player.py
"""
Spieler-Klasse mit vollständiger Spiellogik
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import logging

from anno1800.utils.constants import (
    PopulationType, ResourceType, BuildingType, 
    BUILDING_DEFINITIONS, STARTING_RESOURCES,
    SHIFT_END_COSTS, WORKFORCE_COSTS, UPGRADE_COSTS
)

logger = logging.getLogger(__name__)

@dataclass
class PlayerState:
    """Kompletter Spielerzustand"""
    id: int
    name: str
    strategy: str = "human"
    
    # Ressourcen
    gold: int = 0
    trade_tokens: int = 0
    exploration_tokens: int = 0
    
    # Bevölkerung (verfügbar)
    population: Dict[PopulationType, int] = field(default_factory=dict)
    
    # Bevölkerung (eingesetzt/erschöpft)
    exhausted_population: Dict[PopulationType, int] = field(default_factory=dict)
    
    # Gebäude
    buildings: List[BuildingType] = field(default_factory=list)
    building_workers: Dict[str, PopulationType] = field(default_factory=dict)  # Gebäude -> Arbeiter
    
    # Inseln
    old_world_islands: List[Dict] = field(default_factory=list)
    new_world_islands: List[Dict] = field(default_factory=list)
    
    # Schiffe
    ships: Dict[str, int] = field(default_factory=dict)
    exhausted_trade_tokens: int = 0
    exhausted_exploration_tokens: int = 0
    
    # Karten
    hand_cards: List[Dict] = field(default_factory=list)
    played_cards: List[Dict] = field(default_factory=list)
    expedition_cards: List[Dict] = field(default_factory=list)
    
    # Spielstatus
    has_fireworks: bool = False
    final_score: int = 0
    rank: int = 0
    
    def __post_init__(self):
        """Initialisiere Startwerte"""
        if not self.population:
            self.population = STARTING_RESOURCES['population'].copy()
        if not self.exhausted_population:
            self.exhausted_population = {pt: 0 for pt in PopulationType}
        if not self.buildings:
            self.buildings = STARTING_RESOURCES['buildings'].copy()
        if not self.ships:
            self.ships = STARTING_RESOURCES['ships'].copy()
            
    def get_available_population(self, pop_type: PopulationType) -> int:
        """Gibt verfügbare Bevölkerung zurück"""
        total = self.population.get(pop_type, 0)
        exhausted = self.exhausted_population.get(pop_type, 0)
        return max(0, total - exhausted)
    
    def can_produce_resource(self, resource: ResourceType, amount: int = 1) -> bool:
        """Prüft ob Ressource produziert werden kann"""
        # Finde Gebäude die diese Ressource produzieren
        for building in self.buildings:
            building_def = BUILDING_DEFINITIONS.get(building)
            if building_def and building_def.get('produces') == resource:
                # Prüfe ob Arbeiter verfügbar
                worker_type = building_def.get('worker')
                if self.get_available_population(worker_type) >= amount:
                    return True
        
        # Alternativ: Handel
        if resource not in [ResourceType.GOLD_ORE, ResourceType.PEARLS]:  # Neue Welt Ressourcen
            return self.trade_tokens - self.exhausted_trade_tokens >= amount
        
        # Neue Welt Ressourcen von eigenen Inseln
        for island in self.new_world_islands:
            if resource in island.get('resources', []):
                return self.trade_tokens - self.exhausted_trade_tokens >= 1
        
        return False
    
    def produce_resource(self, resource: ResourceType, amount: int = 1) -> bool:
        """Produziert eine Ressource"""
        # Finde passendes Gebäude
        for building in self.buildings:
            building_def = BUILDING_DEFINITIONS.get(building)
            if building_def and building_def.get('produces') == resource:
                worker_type = building_def.get('worker')
                
                # Prüfe und setze Arbeiter ein
                if self.get_available_population(worker_type) >= amount:
                    self.exhausted_population[worker_type] += amount
                    building_key = f"{building}_{self.buildings.index(building)}"
                    self.building_workers[building_key] = worker_type
                    logger.debug(f"{self.name} produziert {amount}x {resource.value}")
                    return True
        
        return False
    
    def can_afford_resources(self, cost: Dict[ResourceType, int]) -> bool:
        """Prüft ob Ressourcenkosten bezahlt werden können"""
        for resource, amount in cost.items():
            if resource == ResourceType.GOLD_ORE:
                if self.gold < amount:
                    return False
            elif not self.can_produce_resource(resource, amount):
                return False
        return True
    
    def pay_resources(self, cost: Dict[ResourceType, int]) -> bool:
        """Bezahlt Ressourcenkosten"""
        # Erst prüfen
        if not self.can_afford_resources(cost):
            return False
        
        # Dann bezahlen
        for resource, amount in cost.items():
            if resource == ResourceType.GOLD_ORE:
                self.gold -= amount
            else:
                if not self.produce_resource(resource, amount):
                    # Fallback: Handel
                    self.exhausted_trade_tokens += amount
        
        return True
    
    def reset_workers(self):
        """Setzt alle Arbeiter zurück (Stadtfest)"""
        for pop_type in PopulationType:
            self.exhausted_population[pop_type] = 0
        self.exhausted_trade_tokens = 0
        self.exhausted_exploration_tokens = 0
        self.building_workers.clear()
        logger.info(f"{self.name} feiert Stadtfest - alle Arbeiter zurückgesetzt")
    
    def add_population(self, pop_type: PopulationType, amount: int = 1) -> bool:
        """Fügt Bevölkerung hinzu"""
        cost = WORKFORCE_COSTS.get(pop_type, {})
        
        if self.can_afford_resources(cost):
            if self.pay_resources(cost):
                self.population[pop_type] = self.population.get(pop_type, 0) + amount
                logger.info(f"{self.name} erhält {amount} {pop_type.value}")
                return True
        
        return False
    
    def upgrade_population(self, from_type: PopulationType, to_type: PopulationType, amount: int = 1) -> bool:
        """Verbessert Bevölkerung"""
        upgrade_key = (from_type, to_type)
        cost = UPGRADE_COSTS.get(upgrade_key, {})
        
        if self.get_available_population(from_type) < amount:
            return False
        
        if self.can_afford_resources(cost):
            if self.pay_resources(cost):
                self.population[from_type] -= amount
                self.population[to_type] = self.population.get(to_type, 0) + amount
                logger.info(f"{self.name} verbessert {amount} {from_type.value} zu {to_type.value}")
                return True
        
        return False
    
    def build_building(self, building_type: BuildingType) -> bool:
        """Baut ein Gebäude"""
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if not building_def:
            return False
        
        cost = building_def.get('cost', {})
        
        # Prüfe ob bereits gebaut (Industrien nur 1x)
        if building_def.get('produces') and building_type in self.buildings:
            logger.warning(f"{self.name} hat {building_type.value} bereits gebaut")
            return False
        
        if self.can_afford_resources(cost):
            if self.pay_resources(cost):
                self.buildings.append(building_type)
                logger.info(f"{self.name} baut {building_type.value}")
                return True
        
        return False
    
    def build_ship(self, ship_type: str) -> bool:
        """Baut ein Schiff"""
        from anno1800.utils.constants import SHIP_TYPES
        
        ship_def = SHIP_TYPES.get(ship_type)
        if not ship_def:
            return False
        
        # Prüfe ob Werft vorhanden
        required_size = ship_def.get('size', 1)
        has_shipyard = False
        
        for building in self.buildings:
            building_def = BUILDING_DEFINITIONS.get(building)
            if building_def and building_def.get('type') == 'shipyard':
                if building_def.get('max_ship_size', 0) >= required_size:
                    has_shipyard = True
                    break
        
        if not has_shipyard:
            logger.warning(f"{self.name} hat keine passende Werft für {ship_type}")
            return False
        
        cost = ship_def.get('cost', {})
        if self.can_afford_resources(cost):
            if self.pay_resources(cost):
                self.ships[ship_type] = self.ships.get(ship_type, 0) + 1
                
                # Füge Tokens hinzu
                if 'trade' in ship_type:
                    self.trade_tokens += ship_def.get('trade_capacity', 0)
                if 'exploration' in ship_type:
                    self.exploration_tokens += ship_def.get('exploration_capacity', 0)
                
                logger.info(f"{self.name} baut Schiff: {ship_type}")
                return True
        
        return False
    
    def calculate_score(self) -> int:
        """Berechnet Endpunkte"""
        from anno1800.utils.constants import SCORING
        
        score = 0
        
        # Punkte für ausgespielte Karten
        for card in self.played_cards:
            card_type = card.get('type', '')
            score += SCORING['cards'].get(card_type, 0)
        
        # Punkte für Expeditionskarten
        for exp_card in self.expedition_cards:
            # Vereinfacht: 2 Punkte pro Karte
            score += 2
        
        # Gold
        score += self.gold // SCORING['gold_per_point']
        
        # Feuerwerk
        if self.has_fireworks:
            score += SCORING['fireworks']
        
        # Gebäude (1 Punkt pro 2 Gebäude)
        score += len(self.buildings) // 2
        
        self.final_score = score
        return score

# ================================================================================
# anno1800/game/board.py
# ================================================================================
"""
Spielbrett und Insel-Management
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random

from anno1800.utils.constants import ResourceType

@dataclass
class Island:
    """Repräsentiert eine Insel"""
    id: str
    name: str
    type: str  # 'home', 'old_world', 'new_world'
    land_tiles: int = 0
    coast_tiles: int = 0
    sea_tiles: int = 0
    
    # Spezielle Eigenschaften
    resources: List[ResourceType] = field(default_factory=list)
    bonus: Optional[Dict] = None
    
    # Bebaute Felder
    buildings: List[Tuple[int, int]] = field(default_factory=list)
    ships: List[Tuple[int, int]] = field(default_factory=list)

class IslandGenerator:
    """Generiert zufällige Inseln"""
    
    OLD_WORLD_TEMPLATES = [
        {
            'name': 'Handelshafen',
            'land': 4, 'coast': 2, 'sea': 2,
            'bonus': {'type': 'building', 'value': 'warehouse'}
        },
        {
            'name': 'Bergbauinsel',
            'land': 5, 'coast': 1, 'sea': 2,
            'bonus': {'type': 'resource', 'value': ResourceType.COAL}
        },
        {
            'name': 'Fruchtbare Ebene',
            'land': 6, 'coast': 2, 'sea': 1,
            'bonus': {'type': 'population', 'value': PopulationType.FARMER}
        },
        {
            'name': 'Küstenfestung',
            'land': 3, 'coast': 3, 'sea': 3,
            'bonus': {'type': 'defense', 'value': 2}
        },
        {
            'name': 'Industriegebiet',
            'land': 4, 'coast': 2, 'sea': 2,
            'bonus': {'type': 'building', 'value': 'steelworks'}
        }
    ]
    
    NEW_WORLD_TEMPLATES = [
        {
            'name': 'Kaffeeplantage',
            'resources': [ResourceType.COFFEE, ResourceType.SUGAR],
            'bonus': {'type': 'trade', 'value': 2}
        },
        {
            'name': 'Tabakfelder',
            'resources': [ResourceType.TOBACCO, ResourceType.COTTON],
            'bonus': {'type': 'trade', 'value': 2}
        },
        {
            'name': 'Goldmine',
            'resources': [ResourceType.GOLD_ORE, ResourceType.PEARLS],
            'bonus': {'type': 'gold', 'value': 3}
        },
        {
            'name': 'Kautschukplantage',
            'resources': [ResourceType.RUBBER, ResourceType.COCOA],
            'bonus': {'type': 'production', 'value': 1}
        }
    ]
    
    @classmethod
    def generate_old_world_island(cls) -> Island:
        """Generiert eine Alte-Welt-Insel"""
        template = random.choice(cls.OLD_WORLD_TEMPLATES)
        return Island(
            id=f"old_world_{random.randint(1000, 9999)}",
            name=template['name'],
            type='old_world',
            land_tiles=template['land'],
            coast_tiles=template['coast'],
            sea_tiles=template['sea'],
            bonus=template.get('bonus')
        )
    
    @classmethod
    def generate_new_world_island(cls) -> Island:
        """Generiert eine Neue-Welt-Insel"""
        template = random.choice(cls.NEW_WORLD_TEMPLATES)
        return Island(
            id=f"new_world_{random.randint(1000, 9999)}",
            name=template['name'],
            type='new_world',
            resources=template['resources'],
            bonus=template.get('bonus')
        )

@dataclass
class GameBoard:
    """Spielbrett mit allen Komponenten"""
    
    # Verfügbare Gebäude (Anzahl)
    available_buildings: Dict[BuildingType, int] = field(default_factory=dict)
    
    # Kartenstapel
    population_cards: Dict[str, List[Dict]] = field(default_factory=dict)
    expedition_cards: List[Dict] = field(default_factory=list)
    contract_cards: List[Dict] = field(default_factory=list)
    
    # Inselstapel
    old_world_islands: List[Island] = field(default_factory=list)
    new_world_islands: List[Island] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialisiert das Spielbrett"""
        self._init_buildings()
        self._init_cards()
        self._init_islands()
    
    def _init_buildings(self):
        """Initialisiert verfügbare Gebäude"""
        # 2 von jeder Industrie
        for building_type in BuildingType:
            if building_type.value.startswith('shipyard'):
                # Werften: 4x klein, 6x mittel, 4x groß
                if '1' in building_type.value:
                    self.available_buildings[building_type] = 4
                elif '2' in building_type.value:
                    self.available_buildings[building_type] = 6
                else:
                    self.available_buildings[building_type] = 4
            else:
                self.available_buildings[building_type] = 2
    
    def _init_cards(self):
        """Initialisiert Kartenstapel"""
        # Bevölkerungskarten
        self.population_cards = {
            'farmer_worker': self._create_population_cards('farmer_worker', 46),
            'craftsman_engineer_investor': self._create_population_cards('craftsman_engineer_investor', 32),
            'new_world': self._create_population_cards('new_world', 24)
        }
        
        # Expeditionskarten
        self.expedition_cards = self._create_expedition_cards(22)
        
        # Auftragskarten (5 zufällige)
        all_contracts = self._create_all_contract_cards()
        self.contract_cards = random.sample(all_contracts, min(5, len(all_contracts)))
    
    def _create_population_cards(self, card_type: str, count: int) -> List[Dict]:
        """Erstellt Bevölkerungskarten"""
        cards = []
        for i in range(count):
            card = {
                'id': f"{card_type}_{i}",
                'type': card_type,
                'requirements': self._generate_card_requirements(card_type),
                'effect': self._generate_card_effect(card_type)
            }
            cards.append(card)
        
        random.shuffle(cards)
        return cards
    
    def _generate_card_requirements(self, card_type: str) -> Dict:
        """Generiert Kartenanforderungen"""
        if card_type == 'farmer_worker':
            options = [
                {ResourceType.BEER: 1},
                {ResourceType.BREAD: 1},
                {ResourceType.SOAP: 1},
                {ResourceType.BEER: 1, ResourceType.BREAD: 1}
            ]
        elif card_type == 'craftsman_engineer_investor':
            options = [
                {ResourceType.BEER: 2, ResourceType.BREAD: 1},
                {ResourceType.COFFEE: 1, ResourceType.SOAP: 1},
                {ResourceType.CLOTHES: 1, ResourceType.GOODS: 2}
            ]
        else:  # new_world
            options = [
                {ResourceType.COFFEE: 1, ResourceType.TOBACCO: 1},
                {ResourceType.SUGAR: 1, ResourceType.COTTON: 1},
                {ResourceType.COCOA: 1, ResourceType.RUBBER: 1}
            ]
        
        return random.choice(options)
    
    def _generate_card_effect(self, card_type: str) -> Dict:
        """Generiert Karteneffekte"""
        effects = [
            {'type': 'gain_population', 'value': random.randint(1, 2)},
            {'type': 'gain_gold', 'value': random.randint(2, 5)},
            {'type': 'gain_trade', 'value': random.randint(1, 2)},
            {'type': 'gain_exploration', 'value': random.randint(1, 2)},
            {'type': 'extra_action'},
            {'type': 'free_upgrade', 'value': random.randint(1, 2)}
        ]
        return random.choice(effects)
    
    def _create_expedition_cards(self, count: int) -> List[Dict]:
        """Erstellt Expeditionskarten"""
        cards = []
        animals = ['Löwe', 'Elefant', 'Giraffe', 'Papagei', 'Affe', 'Tiger', 'Krokodil', 'Nashorn']
        artifacts = ['Vase', 'Statue', 'Maske', 'Schmuck', 'Schriftrolle', 'Waffe', 'Münzen', 'Krone']
        
        for i in range(count):
            card = {
                'id': f"expedition_{i}",
                'animal': random.choice(animals),
                'artifact': random.choice(artifacts),
                'requirements': {
                    PopulationType.CRAFTSMAN: random.randint(0, 2),
                    PopulationType.ENGINEER: random.randint(0, 1),
                    PopulationType.INVESTOR: random.randint(0, 1)
                }
            }
            cards.append(card)
        
        random.shuffle(cards)
        return cards
    
    def _create_all_contract_cards(self) -> List[Dict]:
        """Erstellt alle Auftragskarten"""
        return [
            {
                'name': 'Alonso Graves',
                'type': 'effect',
                'description': '3 Erkundung + 3 Gold = Zusätzliche Aktion',
                'effect': 'extra_action'
            },
            {
                'name': 'Universität',
                'type': 'majority',
                'target': 'engineers',
                'points': {'first': 10, 'second': 4}
            },
            {
                'name': 'Zoo',
                'type': 'expedition_bonus',
                'description': '+1 Punkt pro Zoo-Tier',
                'bonus': 1
            },
            {
                'name': 'Isabel Sarmento',
                'type': 'island_bonus',
                'description': '6 Punkte pro Neue-Welt-Insel',
                'points_per_island': 6
            },
            {
                'name': 'Edvard Goode',
                'type': 'building_bonus',
                'target': BuildingType.STEELWORKS,
                'points': 6
            },
            {
                'name': 'Die Königin',
                'type': 'building_set',
                'targets': [BuildingType.BREWERY, BuildingType.TEXTILE_MILL],
                'points': 10
            },
            {
                'name': 'Pyrphorier',
                'type': 'penalty',
                'description': '-2 Punkte pro Handkarte',
                'points_per_card': -2
            }
        ]
    
    def _init_islands(self):
        """Initialisiert Inselstapel"""
        # Generiere 12 Alte-Welt-Inseln
        for _ in range(12):
            self.old_world_islands.append(IslandGenerator.generate_old_world_island())
        
        # Generiere 8 Neue-Welt-Inseln
        for _ in range(8):
            self.new_world_islands.append(IslandGenerator.generate_new_world_island())
    
    def draw_population_card(self, deck_type: str) -> Optional[Dict]:
        """Zieht eine Bevölkerungskarte"""
        if deck_type in self.population_cards and self.population_cards[deck_type]:
            return self.population_cards[deck_type].pop(0)
        return None
    
    def draw_expedition_cards(self, count: int) -> List[Dict]:
        """Zieht Expeditionskarten"""
        cards = []
        for _ in range(min(count, len(self.expedition_cards))):
            if self.expedition_cards:
                cards.append(self.expedition_cards.pop(0))
        return cards
    
    def get_old_world_island(self) -> Optional[Island]:
        """Gibt eine Alte-Welt-Insel"""
        if self.old_world_islands:
            return self.old_world_islands.pop(0)
        return None
    
    def get_new_world_island(self) -> Optional[Island]:
        """Gibt eine Neue-Welt-Insel"""
        if self.new_world_islands:
            return self.new_world_islands.pop(0)
        return None

# ================================================================================
# anno1800/game/engine.py
# ================================================================================
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
    
    def _apply_card_effect(self, player: PlayerState, effect: Dict):
        """Wendet Karteneffekt an"""
        effect_type = effect.get('type')
        value = effect.get('value', 0)
        
        if effect_type == 'gain_gold':
            player.gold += value
        elif effect_type == 'gain_population':
            # Füge zufällige Bevölkerung hinzu
            pop_type = random.choice(list(PopulationType)[:3])  # Nur Farmer, Worker, Craftsman
            player.population[pop_type] += value
        elif effect_type == 'gain_trade':
            player.trade_tokens += value
        elif effect_type == 'gain_exploration':
            player.exploration_tokens += value
        # Weitere Effekte...
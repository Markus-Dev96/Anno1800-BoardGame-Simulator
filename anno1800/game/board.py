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

from anno1800.utils.constants import BuildingType, PopulationType, ResourceType

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
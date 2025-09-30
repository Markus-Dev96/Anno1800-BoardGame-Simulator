# anno1800/game/board.py
"""
Spielbrett und Insel-Management für Anno 1800 Brettspiel
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from anno1800.utils.constants import (
    BuildingType, PopulationType, ResourceType, 
    BUILDING_DEFINITIONS, NEW_WORLD_RESOURCES
)

@dataclass
class Island:
    """Repräsentiert eine Insel"""
    id: str
    name: str
    type: str  # 'home', 'old_world', 'new_world'
    
    # Alte Welt Inseln
    land_tiles: int = 0
    coast_tiles: int = 0
    sea_tiles: int = 0
    effect: Optional[Dict] = None
    
    # Neue Welt Inseln
    resources: List[ResourceType] = field(default_factory=list)

class IslandGenerator:
    """Generiert zufällige Inseln gemäß Brettspiel"""
    
    # Alte Welt Insel-Templates (basierend auf Brettspiel)
    OLD_WORLD_TEMPLATES = [
        {
            'name': 'Handelshafen',
            'land': 4, 'coast': 2, 'sea': 2,
            'effect': {'type': 'building', 'building_type': BuildingType.LAGERHAUS}
        },
        {
            'name': 'Bergbauinsel',
            'land': 5, 'coast': 1, 'sea': 2,
            'effect': {'type': 'gold', 'amount': 3}
        },
        {
            'name': 'Fruchtbare Ebene',
            'land': 6, 'coast': 2, 'sea': 1,
            'effect': {'type': 'population', 'population_type': PopulationType.BAUER, 'amount': 2}
        },
        {
            'name': 'Küstenfestung',
            'land': 3, 'coast': 3, 'sea': 3,
            'effect': {'type': 'expedition_cards', 'amount': 2}
        },
        {
            'name': 'Industriegebiet',
            'land': 4, 'coast': 2, 'sea': 2,
            'effect': {'type': 'building', 'building_type': BuildingType.STAHLWERK}
        }
    ]
    
    # Neue Welt Insel-Templates (3 Ressourcen pro Insel)
    NEW_WORLD_TEMPLATES = [
        {
            'name': 'Kaffeeplantage',
            'resources': [ResourceType.KAFFEEBOHNEN, ResourceType.ZUCKER, ResourceType.BAUMWOLLE]
        },
        {
            'name': 'Tabakfelder',
            'resources': [ResourceType.TABAK, ResourceType.BAUMWOLLE, ResourceType.ZUCKER]
        },
        {
            'name': 'Zuckerrohrplantage',
            'resources': [ResourceType.ZUCKER, ResourceType.KAKAO, ResourceType.KAFFEEBOHNEN]
        },
        {
            'name': 'Kautschukplantage',
            'resources': [ResourceType.KAUTSCHUK, ResourceType.KAKAO, ResourceType.TABAK]
        },
        {
            'name': 'Kakaoplantage',
            'resources': [ResourceType.KAKAO, ResourceType.KAFFEEBOHNEN, ResourceType.KAUTSCHUK]
        },
        {
            'name': 'Baumwollfelder',
            'resources': [ResourceType.BAUMWOLLE, ResourceType.TABAK, ResourceType.ZUCKER]
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
            effect=template.get('effect')
        )
    
    @classmethod
    def generate_new_world_island(cls) -> Island:
        """Generiert eine Neue-Welt-Insel"""
        template = random.choice(cls.NEW_WORLD_TEMPLATES)
        return Island(
            id=f"new_world_{random.randint(1000, 9999)}",
            name=template['name'],
            type='new_world',
            resources=template['resources']
        )

@dataclass
class GameBoard:
    """Spielbrett mit allen Komponenten"""
    
    # Verfügbare Gebäude (Anzahl auf dem Spielplan)
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
        """Initialisiert verfügbare Gebäude gemäß Brettspiel"""
        # Jede Industrie gibt es 2x
        # Werften: 4x klein, 6x mittel, 4x groß  
        # Schiffe: je 6x
        for building_type in BuildingType:
            building_def = BUILDING_DEFINITIONS.get(building_type)
            if not building_def:
                continue
                
            if building_def.get('type') == 'shipyard':
                # Werften
                if '1' in building_type.value:
                    self.available_buildings[building_type] = 4
                elif '2' in building_type.value:
                    self.available_buildings[building_type] = 6
                else:
                    self.available_buildings[building_type] = 4
            elif building_def.get('type') == 'ship':
                # Schiffe
                self.available_buildings[building_type] = 6
            else:
                # Industrien
                self.available_buildings[building_type] = 2
    
    def _init_cards(self):
        """Initialisiert Kartenstapel"""
        # 46 Bauern/Arbeiter-Karten
        self.population_cards['farmer_worker'] = self._create_population_cards('farmer_worker', 46)
        
        # 32 Handwerker/Ingenieur/Investor-Karten
        self.population_cards['craftsman_engineer_investor'] = self._create_population_cards('craftsman_engineer_investor', 32)
        
        # 24 Neue-Welt-Karten
        self.population_cards['new_world'] = self._create_population_cards('new_world', 24)
        
        # 22 Expeditions-Karten
        self.expedition_cards = self._create_expedition_cards(22)
        
        # Auftrags-Karten (vereinfacht)
        self.contract_cards = self._create_contract_cards()
    
    def _create_population_cards(self, card_type: str, count: int) -> List[Dict]:
        """Erstellt Bevölkerungskarten"""
        cards = []
        
        for i in range(count):
            card = {
                'id': f"{card_type}_{i}",
                'type': card_type,
                'deck_type': card_type,  # Für Rückgabe ins richtige Deck
                'requirements': self._generate_card_requirements(card_type),
                'effect': self._generate_card_effect(card_type)
            }
            cards.append(card)
        
        random.shuffle(cards)
        return cards
    
    def _generate_card_requirements(self, card_type: str) -> Dict:
        """Generiert realistische Kartenanforderungen basierend auf Brettspiel"""
        if card_type == 'farmer_worker':
            # 3 Einfluss-Punkte Karten
            options = [
                {ResourceType.BIER: 1},
                {ResourceType.BROT: 1},
                {ResourceType.SCHNAPS: 1},
                {ResourceType.SEIFE: 1},
                {ResourceType.WURST: 1}
            ]
        elif card_type == 'craftsman_engineer_investor':
            # 8 Einfluss-Punkte Karten
            options = [
                {ResourceType.BIER: 2, ResourceType.BROT: 1},
                {ResourceType.KAFFEE: 1, ResourceType.SEIFE: 1},
                {ResourceType.ARBEITSKLEIDUNG: 1, ResourceType.WAREN: 2},
                {ResourceType.FENSTER: 1, ResourceType.CHAMPAGNER: 1},
                {ResourceType.BRILLEN: 1, ResourceType.TASCHENUHREN: 1}
            ]
        else:  # new_world
            # 5 Einfluss-Punkte Karten
            options = [
                {ResourceType.KAFFEE: 1, ResourceType.RUM: 1},
                {ResourceType.ZIGARREN: 1, ResourceType.SCHOKOLADE: 1},
                {ResourceType.BAUMWOLLSTOFF: 1, ResourceType.PELZMÄNTEL: 1}
            ]
        
        return random.choice(options)
    
    def _generate_card_effect(self, card_type: str) -> Dict:
        """Generiert Karten-Effekte gemäß Brettspiel"""
        effects = [
            {'type': 'gain_population', 'value': random.randint(1, 2)},
            {'type': 'gain_gold', 'value': random.randint(2, 5)},
            {'type': 'gain_trade', 'value': random.randint(1, 2)},
            {'type': 'gain_exploration', 'value': random.randint(1, 2)},
            {'type': 'extra_action'},
            {'type': 'free_upgrade', 'value': random.randint(1, 2)},
            {'type': 'expedition_cards', 'value': 2}
        ]
        return random.choice(effects)
    
    def _create_expedition_cards(self, count: int) -> List[Dict]:
        """Erstellt Expeditionskarten"""
        cards = []
        
        # Zoo-Tiere und Museum-Artefakte
        animals = ['Löwe', 'Elefant', 'Giraffe', 'Papagei', 'Affe', 'Tiger', 'Krokodil', 'Nashorn']
        artifacts = ['Vase', 'Statue', 'Maske', 'Schmuck', 'Schriftrolle', 'Waffe', 'Münzen', 'Krone']
        
        for i in range(count):
            card = {
                'id': f"expedition_{i}",
                'animal': random.choice(animals),
                'artifact': random.choice(artifacts),
                'requirements': {
                    PopulationType.HANDWERKER: random.randint(0, 2),
                    PopulationType.INGENIEUR: random.randint(0, 1),
                    PopulationType.INVESTOR: random.randint(0, 1)
                }
            }
            cards.append(card)
        
        random.shuffle(cards)
        return cards
    
    def _create_contract_cards(self) -> List[Dict]:
        """Erstellt Auftrags-Karten (vereinfacht)"""
        return [
            {
                'name': 'Alonso Graves',
                'type': 'effect',
                'description': '3 Erkundung + 3 Gold = Zusätzliche Aktion'
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
                'bonus': 1
            },
            {
                'name': 'Isabel Sarmento',
                'type': 'island_bonus',
                'points_per_island': 6
            },
            {
                'name': 'Edvard Goode',
                'type': 'building_bonus',
                'target': BuildingType.HOCHRÄDERFABRIK,
                'points': 6
            }
        ]
    
    def _init_islands(self):
        """Initialisiert Inselstapel"""
        # 12 Alte-Welt-Inseln
        for _ in range(12):
            self.old_world_islands.append(IslandGenerator.generate_old_world_island())
        
        # 8 Neue-Welt-Inseln
        for _ in range(8):
            self.new_world_islands.append(IslandGenerator.generate_new_world_island())
    
    def draw_population_card(self, deck_type: str) -> Optional[Dict]:
        """Zieht eine Bevölkerungskarte"""
        if deck_type in self.population_cards and self.population_cards[deck_type]:
            return self.population_cards[deck_type].pop(0)
        return None
    
    def return_card(self, deck_type: str, card: Dict):
        """Legt eine Karte zurück unter den Stapel"""
        if deck_type in self.population_cards:
            self.population_cards[deck_type].append(card)
    
    def draw_expedition_card(self) -> Optional[Dict]:
        """Zieht eine Expeditionskarte"""
        if self.expedition_cards:
            return self.expedition_cards.pop(0)
        return None
    
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
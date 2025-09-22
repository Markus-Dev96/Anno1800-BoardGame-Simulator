# anno1800/utils/constants.py
"""
Vollständige Spielkonstanten und Konfiguration für Anno 1800
"""

from enum import Enum
from typing import Dict, List, Tuple

class ResourceType(Enum):
    """Alle Ressourcentypen im Spiel"""
    # Basis-Ressourcen
    WOOD = "wood"
    BRICKS = "bricks"
    STEEL = "steel"
    COAL = "coal"
    GLASS = "glass"
    GOODS = "goods"
    
    # Schiffbau
    SAILS = "sails"
    WEAPONS = "weapons"
    
    # Konsumgüter
    BEER = "beer"
    BREAD = "bread"
    SOAP = "soap"
    CLOTHES = "clothes"
    
    # Neue Welt Ressourcen
    COFFEE = "coffee"
    TOBACCO = "tobacco"
    SUGAR = "sugar"
    COTTON = "cotton"
    COCOA = "cocoa"
    RUBBER = "rubber"
    GOLD_ORE = "gold_ore"
    PEARLS = "pearls"
    
    # Spezial
    GRAIN = "grain"
    POTATOES = "potatoes"
    FISH = "fish"
    OIL = "oil"

class PopulationType(Enum):
    """Bevölkerungstypen"""
    FARMER = "farmer"
    WORKER = "worker"
    CRAFTSMAN = "craftsman"
    ENGINEER = "engineer"
    INVESTOR = "investor"

class ActionType(Enum):
    """Alle möglichen Aktionstypen"""
    BUILD = "build"
    PLAY_CARD = "play_card"
    EXCHANGE_CARDS = "exchange_cards"
    INCREASE_WORKFORCE = "increase_workforce"
    UPGRADE_POPULATION = "upgrade"
    EXPLORE_OLD_WORLD = "explore_old_world"
    EXPLORE_NEW_WORLD = "explore_new_world"
    EXPEDITION = "expedition"
    CITY_FESTIVAL = "city_festival"
    TRADE = "trade"
    BUILD_SHIP = "build_ship"
    PASS = "pass"

class BuildingType(Enum):
    """Alle Gebäudetypen"""
    # Basis-Produktion
    LUMBERJACK = "lumberjack"
    SAWMILL = "sawmill"
    BRICKYARD = "brickyard"
    STEELWORKS = "steelworks"
    COAL_MINE = "coal_mine"
    WAREHOUSE = "warehouse"
    
    # Nahrung
    POTATO_FARM = "potato_farm"
    GRAIN_FARM = "grain_farm"
    FISHERY = "fishery"
    BAKERY = "bakery"
    BREWERY = "brewery"
    
    # Erweiterte Produktion
    GLASSWORKS = "glassworks"
    SOAP_FACTORY = "soap_factory"
    TEXTILE_MILL = "textile_mill"
    OIL_REFINERY = "oil_refinery"
    
    # Marine
    SAILMAKERS = "sailmakers"
    WEAPONS_FACTORY = "weapons_factory"
    
    # Werften
    SHIPYARD_1 = "shipyard_1"
    SHIPYARD_2 = "shipyard_2"
    SHIPYARD_3 = "shipyard_3"
    
    # Spezialgebäude
    MARKETPLACE = "marketplace"
    BANK = "bank"
    UNIVERSITY = "university"
    MUSEUM = "museum"
    ZOO = "zoo"

# Gebäude-Definitionen mit vollständigen Daten
BUILDING_DEFINITIONS: Dict = {
    # Basis-Produktion
    BuildingType.LUMBERJACK: {
        'name': 'Holzfäller',
        'cost': {},
        'produces': ResourceType.WOOD,
        'worker': PopulationType.FARMER,
        'production': 1,
        'limit': 2
    },
    BuildingType.SAWMILL: {
        'name': 'Sägewerk',
        'cost': {},  # Kostenlos als Startgebäude
        'produces': ResourceType.WOOD,
        'worker': PopulationType.FARMER,
        'production': 2,
        'limit': 2
    },
    BuildingType.BRICKYARD: {
        'name': 'Ziegelei',
        'cost': {ResourceType.WOOD: 1},
        'produces': ResourceType.BRICKS,
        'worker': PopulationType.WORKER,
        'production': 1,
        'limit': 2
    },
    BuildingType.STEELWORKS: {
        'name': 'Stahlwerk',
        'cost': {ResourceType.BRICKS: 1, ResourceType.COAL: 1},
        'produces': ResourceType.STEEL,
        'worker': PopulationType.CRAFTSMAN,
        'production': 1,
        'limit': 2
    },
    BuildingType.COAL_MINE: {
        'name': 'Kohlemine',
        'cost': {ResourceType.WOOD: 2},
        'produces': ResourceType.COAL,
        'worker': PopulationType.WORKER,
        'production': 1,
        'limit': 2
    },
    BuildingType.WAREHOUSE: {
        'name': 'Lagerhaus',
        'cost': {ResourceType.WOOD: 1, ResourceType.BRICKS: 1},
        'produces': ResourceType.GOODS,
        'worker': PopulationType.WORKER,
        'production': 1,
        'limit': 2
    },
    
    # Nahrung
    BuildingType.POTATO_FARM: {
        'name': 'Kartoffelhof',
        'cost': {},
        'produces': ResourceType.POTATOES,
        'worker': PopulationType.FARMER,
        'production': 1,
        'limit': 2
    },
    BuildingType.GRAIN_FARM: {
        'name': 'Getreidefarm',
        'cost': {ResourceType.WOOD: 1},
        'produces': ResourceType.GRAIN,
        'worker': PopulationType.FARMER,
        'production': 1,
        'limit': 2
    },
    BuildingType.FISHERY: {
        'name': 'Fischerei',
        'cost': {ResourceType.WOOD: 1},
        'produces': ResourceType.FISH,
        'worker': PopulationType.FARMER,
        'production': 1,
        'limit': 2
    },
    BuildingType.BAKERY: {
        'name': 'Bäckerei',
        'cost': {ResourceType.BRICKS: 1},
        'produces': ResourceType.BREAD,
        'worker': PopulationType.WORKER,
        'production': 1,
        'limit': 2
    },
    BuildingType.BREWERY: {
        'name': 'Brauerei',
        'cost': {ResourceType.WOOD: 1, ResourceType.GLASS: 1},
        'produces': ResourceType.BEER,
        'worker': PopulationType.WORKER,
        'production': 1,
        'limit': 2
    },
    
    # Erweiterte Produktion
    BuildingType.GLASSWORKS: {
        'name': 'Glashütte',
        'cost': {ResourceType.BRICKS: 1},
        'produces': ResourceType.GLASS,
        'worker': PopulationType.WORKER,
        'production': 1,
        'limit': 2
    },
    BuildingType.SOAP_FACTORY: {
        'name': 'Seifensiederei',
        'cost': {ResourceType.WOOD: 1, ResourceType.BRICKS: 1},
        'produces': ResourceType.SOAP,
        'worker': PopulationType.CRAFTSMAN,
        'production': 1,
        'limit': 2
    },
    BuildingType.TEXTILE_MILL: {
        'name': 'Weberei',
        'cost': {ResourceType.COTTON: 1},
        'produces': ResourceType.CLOTHES,
        'worker': PopulationType.CRAFTSMAN,
        'production': 1,
        'limit': 2
    },
    BuildingType.OIL_REFINERY: {
        'name': 'Ölraffinerie',
        'cost': {ResourceType.STEEL: 1, ResourceType.GLASS: 1},
        'produces': ResourceType.OIL,
        'worker': PopulationType.ENGINEER,
        'production': 1,
        'limit': 2
    },
    
    # Marine
    BuildingType.SAILMAKERS: {
        'name': 'Segelmacherei',
        'cost': {ResourceType.COTTON: 1},
        'produces': ResourceType.SAILS,
        'worker': PopulationType.CRAFTSMAN,
        'production': 1,
        'limit': 2
    },
    BuildingType.WEAPONS_FACTORY: {
        'name': 'Waffenfabrik',
        'cost': {ResourceType.STEEL: 1, ResourceType.COAL: 1},
        'produces': ResourceType.WEAPONS,
        'worker': PopulationType.ENGINEER,
        'production': 1,
        'limit': 2
    },
    
    # Werften
    BuildingType.SHIPYARD_1: {
        'name': 'Kleine Werft',
        'cost': {ResourceType.WOOD: 1},
        'max_ship_size': 1,
        'type': 'shipyard',
        'limit': 4
    },
    BuildingType.SHIPYARD_2: {
        'name': 'Mittlere Werft',
        'cost': {ResourceType.WOOD: 2, ResourceType.BRICKS: 1},
        'max_ship_size': 2,
        'type': 'shipyard',
        'limit': 6
    },
    BuildingType.SHIPYARD_3: {
        'name': 'Große Werft',
        'cost': {ResourceType.WOOD: 2, ResourceType.BRICKS: 1, ResourceType.STEEL: 1},
        'max_ship_size': 3,
        'type': 'shipyard',
        'limit': 4
    },
    
    # Spezialgebäude
    BuildingType.MARKETPLACE: {
        'name': 'Marktplatz',
        'cost': {ResourceType.WOOD: 1, ResourceType.GOODS: 1},
        'effect': 'trade_bonus',
        'limit': 1
    },
    BuildingType.BANK: {
        'name': 'Bank',
        'cost': {ResourceType.BRICKS: 2, ResourceType.STEEL: 1},
        'effect': 'gold_generation',
        'limit': 1
    },
    BuildingType.UNIVERSITY: {
        'name': 'Universität',
        'cost': {ResourceType.BRICKS: 2, ResourceType.GLASS: 2},
        'effect': 'research_bonus',
        'limit': 1
    }
}

# Schiffs-Definitionen
SHIP_TYPES = {
    'trade_1': {
        'name': 'Kleines Handelsschiff',
        'cost': {ResourceType.WOOD: 1, ResourceType.SAILS: 1},
        'trade_capacity': 2,
        'size': 1
    },
    'trade_2': {
        'name': 'Mittleres Handelsschiff',
        'cost': {ResourceType.WOOD: 2, ResourceType.SAILS: 1, ResourceType.GOODS: 1},
        'trade_capacity': 4,
        'size': 2
    },
    'trade_3': {
        'name': 'Großes Handelsschiff',
        'cost': {ResourceType.WOOD: 3, ResourceType.SAILS: 2, ResourceType.STEEL: 1},
        'trade_capacity': 6,
        'size': 3
    },
    'exploration_1': {
        'name': 'Kleines Erkundungsschiff',
        'cost': {ResourceType.WOOD: 1, ResourceType.WEAPONS: 1},
        'exploration_capacity': 2,
        'size': 1
    },
    'exploration_2': {
        'name': 'Mittleres Erkundungsschiff',
        'cost': {ResourceType.WOOD: 2, ResourceType.WEAPONS: 1, ResourceType.STEEL: 1},
        'exploration_capacity': 4,
        'size': 2
    },
    'exploration_3': {
        'name': 'Großes Erkundungsschiff',
        'cost': {ResourceType.WOOD: 3, ResourceType.WEAPONS: 2, ResourceType.STEEL: 2},
        'exploration_capacity': 6,
        'size': 3
    }
}

# Spieler-Startressourcen
STARTING_RESOURCES = {
    'population': {
        PopulationType.FARMER: 4,
        PopulationType.WORKER: 3,
        PopulationType.CRAFTSMAN: 2,
        PopulationType.ENGINEER: 0,
        PopulationType.INVESTOR: 0
    },
    'gold': [0, 1, 2, 3],  # Nach Spielerreihenfolge
    'buildings': [
        BuildingType.POTATO_FARM,
        BuildingType.SAWMILL,
        BuildingType.BRICKYARD
    ],
    'ships': {
        'trade_1': 2,
        'exploration_1': 1
    },
    'trade_tokens': 2,
    'exploration_tokens': 1,
    'hand_cards': {
        'farmer_worker': 7,
        'craftsman_engineer_investor': 2
    }
}

# Punkte-Konfiguration
SCORING = {
    'cards': {
        'farmer_worker': 3,
        'craftsman_engineer_investor': 8,
        'new_world': 5
    },
    'fireworks': 7,
    'gold_per_point': 3,  # 3 Gold = 1 Punkt
    'buildings_per_point': 2,  # 2 Gebäude = 1 Punkt
    'expedition': {
        PopulationType.CRAFTSMAN: [1, 2],
        PopulationType.ENGINEER: [2, 3],
        PopulationType.INVESTOR: [3, 4]
    }
}

# Upgrade-Pfade und Kosten
UPGRADE_COSTS = {
    (PopulationType.FARMER, PopulationType.WORKER): {
        ResourceType.BRICKS: 1
    },
    (PopulationType.WORKER, PopulationType.CRAFTSMAN): {
        ResourceType.COAL: 1,
        ResourceType.GOODS: 1
    },
    (PopulationType.CRAFTSMAN, PopulationType.ENGINEER): {
        ResourceType.STEEL: 1,
        ResourceType.GLASS: 1
    },
    (PopulationType.ENGINEER, PopulationType.INVESTOR): {
        ResourceType.GOLD_ORE: 1,
        ResourceType.COFFEE: 1
    }
}

# Kosten für neue Arbeitskraft
WORKFORCE_COSTS = {
    PopulationType.FARMER: {
        ResourceType.BREAD: 1
    },
    PopulationType.WORKER: {
        ResourceType.BREAD: 1,
        ResourceType.BEER: 1
    },
    PopulationType.CRAFTSMAN: {
        ResourceType.BREAD: 1,
        ResourceType.BEER: 1,
        ResourceType.SOAP: 1
    },
    PopulationType.ENGINEER: {
        ResourceType.BREAD: 1,
        ResourceType.COFFEE: 1,
        ResourceType.CLOTHES: 1
    },
    PopulationType.INVESTOR: {
        ResourceType.COFFEE: 2,
        ResourceType.TOBACCO: 1,
        ResourceType.PEARLS: 1
    }
}

# Erkundungskosten
EXPLORATION_COSTS = {
    'old_world': [1, 2, 3, 4],  # Kosten für 1., 2., 3., 4. Insel
    'new_world': [1, 2, 3, 4],
    'expedition': 2  # 2 Erkundungsmarker für bis zu 3 Karten
}

# Schichtende-Kosten (Gold pro Arbeiter)
SHIFT_END_COSTS = {
    PopulationType.FARMER: 1,
    PopulationType.WORKER: 2,
    PopulationType.CRAFTSMAN: 3,
    PopulationType.ENGINEER: 4,
    PopulationType.INVESTOR: 5
}

# Handels-Kosten (Handelsmarker pro Ressource)
TRADE_COSTS = {
    PopulationType.FARMER: 1,     # Ressourcen von Bauern kosten 1 Handelsmarker
    PopulationType.WORKER: 1,     # Ressourcen von Arbeitern kosten 1 Handelsmarker
    PopulationType.CRAFTSMAN: 2,  # Ressourcen von Handwerkern kosten 2 Handelsmarker
    PopulationType.ENGINEER: 3,   # Ressourcen von Ingenieuren kosten 3 Handelsmarker
    PopulationType.INVESTOR: 4    # Ressourcen von Investoren kosten 4 Handelsmarker
}

# Maximale Anzahlen
MAX_LIMITS = {
    'old_world_islands': 4,
    'new_world_islands': 4,
    'expedition_cards_per_action': 3,
    'cards_exchange_per_action': 3,
    'population_per_action': 3,
    'upgrades_per_action': 3,
    'ships_per_shipyard_per_action': 1
}

# Karten-Effekt-Typen
CARD_EFFECTS = [
    'gain_population',
    'gain_gold',
    'gain_trade',
    'gain_exploration',
    'extra_action',
    'free_upgrade',
    'free_building',
    'draw_cards',
    'expedition_cards',
    'immediate_points'
]

# Neue-Welt-Ressourcen Gruppen
NEW_WORLD_RESOURCES = {
    'plantation': [ResourceType.COFFEE, ResourceType.TOBACCO, ResourceType.SUGAR, ResourceType.COTTON],
    'exotic': [ResourceType.COCOA, ResourceType.RUBBER],
    'precious': [ResourceType.GOLD_ORE, ResourceType.PEARLS]
}

# Spielphasen-Konfiguration
GAME_PHASES = {
    'early': (1, 5),    # Runden 1-5
    'mid': (6, 15),     # Runden 6-15
    'late': (16, 25),   # Runden 16-25
    'final': (26, 99)   # Ab Runde 26 oder wenn Spielende ausgelöst
}
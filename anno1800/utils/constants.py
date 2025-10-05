# anno1800/utils/constants.py
"""
Spielkonstanten für Anno 1800 Brettspiel - Korrigierte Version
Basiert auf den offiziellen Brettspiel-Regeln
"""

from enum import Enum
from typing import Dict, List, Tuple

class ResourceType(Enum):
    """Alle Ressourcentypen im Brettspiel"""
    
    # === BASIS-RESSOURCEN (ohne eigene Produktionsgebäude) ===
    GETREIDE = "grain"  # Für Brot und Bier
    KARTOFFELN = "potatoes"  # Für Schnaps
    SCHWEIN = "pig"  # Für Wurst, Seife, Fleischkonserven
    
    # === PRODUKTIONS-RESSOURCEN ===
    # Grundressourcen
    BRETTER = "wood"  
    KOHLE = "coal"
    ZIEGELSTEINE = "bricks"
    GARN = "yarn"
    
    # Verarbeitete Ressourcen
    WAREN = "goods"
    STAHLTRÄGER = "steel"
    GLAS = "glass"
    MESSING = "brass"
    FENSTER = "windows"
    DAMPFMASCHINE = "steam_engine"
    
    # === KONSUMGÜTER ===
    BIER = "beer"
    BROT = "bread"
    SCHNAPS = "schnapps"
    SEIFE = "soap"
    WURST = "sausage"
    KAFFEE = "coffee"
    BAUMWOLLSTOFF = "cotton_fabric"
    ARBEITSKLEIDUNG = "work_clothes"
    FLEISCHKONSERVEN = "canned_meat"
    
    # === LUXUSGÜTER ===
    CHAMPAGNER = "champagne"
    SEGEL = "sails"
    BRILLEN = "glasses"
    TASCHENUHREN = "pocket_watches"
    NÄHMASCHINEN = "sewing_machines"
    PELZMÄNTEL = "fur_coats"
    
    # === MILITÄR & MARINE ===
    KANONEN = "cannons"
    DYNAMIT = "dynamite"
    GESCHÜTZE = "artillery"
    
    # === NEUE WELT ROHSTOFFE ===
    BAUMWOLLE = "cotton"
    KAFFEEBOHNEN = "coffee_beans"
    TABAK = "tobacco"
    ZUCKER = "sugar"
    KAKAO = "cocoa"
    KAUTSCHUK = "rubber"
    
    # === NEUE WELT VERARBEITET ===
    RUM = "rum"
    ZIGARREN = "cigars"
    SCHOKOLADE = "chocolate"
    
    # === HOCHTECHNOLOGIE ===
    DAMPFWAGEN = "steam_carriage"
    HOCHRÄDER = "high_wheelers"
    GLÜHBIRNEN = "light_bulbs"
    GRAMMOPHONE = "gramophones"

class PopulationType(Enum):
    """Bevölkerungstypen"""
    BAUER = "farmer"  # Grün
    ARBEITER = "worker"  # Blau
    HANDWERKER = "craftsman"  # Rot
    INGENIEUR = "engineer"  # Lila
    INVESTOR = "investor"  # Türkis

class ActionType(Enum):
    """Alle möglichen Aktionstypen"""
    AUSBAUEN = "build"  # Industrien, Werften oder Schiffe bauen
    BEVÖLKERUNG_AUSSPIELEN = "play_card"  # Bevölkerungs-Karten ausspielen
    KARTEN_AUSTAUSCHEN = "exchange_cards"  # Bevölkerungs-Karten austauschen
    ARBEITSKRAFT_ERHÖHEN = "increase_workforce"  # Neue Bevölkerungs-Steine
    AUFSTEIGEN = "upgrade"  # Bevölkerung verbessern
    ALTE_WELT_ERSCHLIESSEN = "explore_old_world"
    NEUE_WELT_ERKUNDEN = "explore_new_world"
    EXPEDITION = "expedition"
    STADTFEST = "city_festival"  # Arbeiter zurücksetzen

class BuildingType(Enum):
    """Gebäudetypen aus dem Brettspiel"""
    
    # === ARBEITER-GEBÄUDE (Blaue Karten) ===
    SÄGEWERK = "sawmill"  # Bretter (kostenlos)
    KÖHLEREI = "coal_mine"  # Kohle
    ZIEGELEI = "brickyard"  # Ziegelsteine
    BRAUEREI = "brewery"  # Bier
    BÄCKEREI = "bakery"  # Brot
    LAGERHAUS = "warehouse"  # Waren
    STAHLWERK = "steelworks"  # Stahlträger
    SEGELMACHEREI = "sailmakers"  # Segel
    SCHNAPSBRENNEREI = "distillery"  # Schnaps
    GLASHÜTTE = "glassworks"  # Glas
    BAUMWOLLWEBEREI_ALT = "cotton_mill_alt"  # Baumwollstoff (Alternative)
    KAFFEERÖSTEREI = "coffee_roastery"  # Kaffee
    WURSTFABRIK = "sausage_factory"  # Wurst
    SEIFENSIEDEREI = "soap_factory"  # Seife
    FLEISCHKONSERVENFABRIK = "canning_plant"  # Fleischkonserven
    ARBEITSKLEIDUNGSFABRIK = "clothing_factory"  # Arbeitskleidung
    SPINNEREI = "yarn"  # Garn (Startfeld)
    
    # === HANDWERKER-GEBÄUDE (Rote Karten) ===
    MESSINGHÜTTE = "brass_foundry"  # Messing
    FENSTERFABRIK = "window_factory"  # Fenster
    SEKTKELLEREI = "champagne_cellar"  # Champagner
    BRILLENFABRIK = "glasses_factory"  # Brillen
    TASCHENUHRENFABRIK = "pocket_watch_factory"  # Taschenuhren
    NÄHMASCHINENFABRIK = "sewing_machine_factory"  # Nähmaschinen
    PELZHÄNDLER = "fur_dealer"  # Pelzmäntel
    DYNAMITFABRIK = "dynamite_factory"  # Dynamit
    KANONENGIESEREI = "cannon_foundry"  # Kanonen
    RUMBRENNEREI = "rum_distillery"  # Rum
    ZIGARRENFABRIK = "cigar_factory"  # Zigarren
    SCHOKOLADENFABRIK = "chocolate_factory"  # Schokolade
    BAUMWOLLWEBEREI = "cotton_mill"  # Baumwollstoff
    
    # === INGENIEUR-GEBÄUDE (Lila Karten) ===
    MOTORENFABRIK = "motor_factory"  # Dampfmaschinen
    DAMPFWAGENFABRIK = "steam_carriage_factory"  # Dampfwagen
    HOCHRÄDERFABRIK = "high_wheeler_factory"  # Hochräder
    GLÜHLAMPENFABRIK = "light_bulb_factory"  # Glühbirnen
    GRAMMOPHONFABRIK = "gramophone_factory"  # Grammophone
    GESCHÜTZFABRIK = "artillery_factory"  # Geschütze/Artillerie
    
    # === WERFTEN ===
    WERFT_1 = "shipyard_1"  # Stärke 1
    WERFT_2 = "shipyard_2"  # Stärke 2
    WERFT_3 = "shipyard_3"  # Stärke 3
    
    # === SCHIFFE ===
    HANDELSSCHIFF_1 = "trade_ship_1"
    HANDELSSCHIFF_2 = "trade_ship_2"
    HANDELSSCHIFF_3 = "trade_ship_3"
    ERKUNDUNGSSCHIFF_1 = "exploration_ship_1"
    ERKUNDUNGSSCHIFF_2 = "exploration_ship_2"
    ERKUNDUNGSSCHIFF_3 = "exploration_ship_3"

# Gebäude-Definitionen mit Kosten
BUILDING_DEFINITIONS: Dict = {
    
    # ========== ARBEITER-GEBÄUDE (Blaue Karten) ==========
    BuildingType.SÄGEWERK: {
        'name': 'Sägewerk',
        'cost': {},  # KOSTENLOS!
        'produces': ResourceType.BRETTER,
        'worker': PopulationType.ARBEITER,
        'alternative_exists': True  # Hat Bauern-Alternative
    },
    BuildingType.KÖHLEREI: {
        'name': 'Köhlerei',
        'cost': {ResourceType.BRETTER: 1},
        'produces': ResourceType.KOHLE,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.ZIEGELEI: {
        'name': 'Ziegelei',
        'cost': {ResourceType.KOHLE: 1},
        'produces': ResourceType.ZIEGELSTEINE,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.BRAUEREI: {
        'name': 'Brauerei',
        'cost': {ResourceType.GETREIDE: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.BIER,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.BÄCKEREI: {
        'name': 'Bäckerei',
        'cost': {ResourceType.GETREIDE: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.BROT,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.LAGERHAUS: {
        'name': 'Lagerhaus',
        'cost': {
            ResourceType.ZIEGELSTEINE: 1,
            'exhausted_population': {PopulationType.HANDWERKER: 1}  # Handwerker erschöpfen!
        },
        'produces': ResourceType.WAREN,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.STAHLWERK: {
        'name': 'Stahlwerk',
        'cost': {ResourceType.ZIEGELSTEINE: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.STAHLTRÄGER,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.SPINNEREI: {
        'name': 'Spinnerei (Startfeld)',
        'cost': {},  # Kostenlos auf Startfeld
        'produces': ResourceType.GARN,
        'worker': PopulationType.ARBEITER,
        'type': 'industry',
        'requires_coast': False,
        'start_building': True  # Kann überbaut werden
    },
    BuildingType.SEGELMACHEREI: {
        'name': 'Segelmacherei',
        'cost': {ResourceType.GARN: 1, ResourceType.BRETTER: 1},
        'produces': ResourceType.SEGEL,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.SCHNAPSBRENNEREI: {
        'name': 'Schnapsbrennerei',
        'cost': {ResourceType.KARTOFFELN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.SCHNAPS,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.GLASHÜTTE: {
        'name': 'Glashütte',
        'cost': {ResourceType.WAREN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.GLAS,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.BAUMWOLLWEBEREI_ALT: {
        'name': 'Baumwollweberei (Alternative)',
        'cost': {ResourceType.BAUMWOLLE: 1, ResourceType.DAMPFMASCHINE: 1},
        'produces': ResourceType.BAUMWOLLSTOFF,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.KAFFEERÖSTEREI: {
        'name': 'Kaffeerösterei',
        'cost': {ResourceType.KAFFEEBOHNEN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.KAFFEE,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.WURSTFABRIK: {
        'name': 'Wurstfabrik',
        'cost': {ResourceType.SCHWEIN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.WURST,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.SEIFENSIEDEREI: {
        'name': 'Seifensiederei',
        'cost': {ResourceType.SCHWEIN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.SEIFE,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.FLEISCHKONSERVENFABRIK: {
        'name': 'Fleischkonservenfabrik',
        'cost': {ResourceType.STAHLTRÄGER: 1, ResourceType.SCHWEIN: 1},
        'produces': ResourceType.FLEISCHKONSERVEN,
        'worker': PopulationType.ARBEITER
    },
    BuildingType.ARBEITSKLEIDUNGSFABRIK: {
        'name': 'Arbeitskleidungsfabrik',
        'cost': {ResourceType.GARN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.ARBEITSKLEIDUNG,
        'worker': PopulationType.ARBEITER
    },
    
    # ========== HANDWERKER-GEBÄUDE (Rote Karten) ==========
    BuildingType.MESSINGHÜTTE: {
        'name': 'Messinghütte',
        'cost': {ResourceType.WAREN: 1, ResourceType.KOHLE: 1},
        'produces': ResourceType.MESSING,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.FENSTERFABRIK: {
        'name': 'Fensterfabrik',
        'cost': {ResourceType.BRETTER: 1, ResourceType.GLAS: 1},
        'produces': ResourceType.FENSTER,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.SEKTKELLEREI: {
        'name': 'Sektkellerei',
        'cost': {
            ResourceType.GLAS: 1,
            ResourceType.WAREN: 1,
            'exhausted_population': {PopulationType.INGENIEUR: 1}
        },
        'produces': ResourceType.CHAMPAGNER,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.BRILLENFABRIK: {
        'name': 'Brillenfabrik',
        'cost': {
            ResourceType.MESSING: 1,
            ResourceType.GLAS: 1,
            'exhausted_population': {PopulationType.INGENIEUR: 1}
        },
        'produces': ResourceType.BRILLEN,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.TASCHENUHRENFABRIK: {
        'name': 'Taschenuhrenfabrik',
        'cost': {
            ResourceType.MESSING: 1,
            ResourceType.GLAS: 1,
            'exhausted_population': {PopulationType.INGENIEUR: 1}
        },
        'produces': ResourceType.TASCHENUHREN,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.NÄHMASCHINENFABRIK: {
        'name': 'Nähmaschinenfabrik',
        'cost': {
            ResourceType.MESSING: 1,
            ResourceType.STAHLTRÄGER: 1,
            'exhausted_population': {PopulationType.INGENIEUR: 1}
        },
        'produces': ResourceType.NÄHMASCHINEN,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.PELZHÄNDLER: {
        'name': 'Pelzhändler',
        'cost': {
            ResourceType.BAUMWOLLSTOFF: 1,
            ResourceType.WAREN: 1,
            ResourceType.NÄHMASCHINEN: 1
        },
        'produces': ResourceType.PELZMÄNTEL,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.DYNAMITFABRIK: {
        'name': 'Dynamitfabrik',
        'cost': {
            ResourceType.WAREN: 1,
            ResourceType.ZIEGELSTEINE: 1,
            ResourceType.SCHWEIN: 1
        },
        'produces': ResourceType.DYNAMIT,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.KANONENGIESEREI: {
        'name': 'Kanonengießerei',
        'cost': {
            ResourceType.STAHLTRÄGER: 1,
            ResourceType.WAREN: 1,
            'exhausted_population': {PopulationType.INGENIEUR: 1}
        },
        'produces': ResourceType.KANONEN,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.RUMBRENNEREI: {
        'name': 'Rumbrennerei',
        'cost': {ResourceType.BRETTER: 1, ResourceType.ZUCKER: 1},
        'produces': ResourceType.RUM,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.ZIGARRENFABRIK: {
        'name': 'Zigarrenfabrik',
        'cost': {ResourceType.BRETTER: 1, ResourceType.TABAK: 1},
        'produces': ResourceType.ZIGARREN,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.SCHOKOLADENFABRIK: {
        'name': 'Schokoladenfabrik',
        'cost': {ResourceType.SCHWEIN: 1, ResourceType.KAKAO: 1},
        'produces': ResourceType.SCHOKOLADE,
        'worker': PopulationType.HANDWERKER
    },
    BuildingType.BAUMWOLLWEBEREI: {
        'name': 'Baumwollweberei',
        'cost': {ResourceType.BAUMWOLLE: 1, ResourceType.BRETTER: 1},
        'produces': ResourceType.BAUMWOLLSTOFF,
        'worker': PopulationType.HANDWERKER
    },
    
    # ========== INGENIEUR-GEBÄUDE (Lila Karten) ==========
    BuildingType.MOTORENFABRIK: {
        'name': 'Motorenfabrik',
        'cost': {
            ResourceType.STAHLTRÄGER: 1,
            ResourceType.MESSING: 1,
            'exhausted_population': {PopulationType.INVESTOR: 1}
        },
        'produces': ResourceType.DAMPFMASCHINE,
        'worker': PopulationType.INGENIEUR
    },
    BuildingType.DAMPFWAGENFABRIK: {
        'name': 'Dampfwagenfabrik',
        'cost': {
            ResourceType.DAMPFMASCHINE: 1,
            ResourceType.KAUTSCHUK: 1,
            'exhausted_population': {PopulationType.INVESTOR: 1}
        },
        'produces': ResourceType.DAMPFWAGEN,
        'worker': PopulationType.INGENIEUR
    },
    BuildingType.HOCHRÄDERFABRIK: {
        'name': 'Hochräderfabrik',
        'cost': {
            ResourceType.STAHLTRÄGER: 1,
            ResourceType.KAUTSCHUK: 1,
            'exhausted_population': {PopulationType.INVESTOR: 1}
        },
        'produces': ResourceType.HOCHRÄDER,
        'worker': PopulationType.INGENIEUR
    },
    BuildingType.GLÜHLAMPENFABRIK: {
        'name': 'Glühlampenfabrik',
        'cost': {
            ResourceType.GLAS: 1,
            ResourceType.KOHLE: 1,
            'exhausted_population': {PopulationType.INVESTOR: 1}
        },
        'produces': ResourceType.GLÜHBIRNEN,
        'worker': PopulationType.INGENIEUR
    },
    BuildingType.GRAMMOPHONFABRIK: {
        'name': 'Grammophonfabrik',
        'cost': {
            ResourceType.BRETTER: 1,
            ResourceType.MESSING: 1,
            'exhausted_population': {PopulationType.INVESTOR: 1}
        },
        'produces': ResourceType.GRAMMOPHONE,
        'worker': PopulationType.INGENIEUR
    },
    BuildingType.GESCHÜTZFABRIK: {
        'name': 'Geschützfabrik',
        'cost': {
            ResourceType.STAHLTRÄGER: 1,
            ResourceType.DYNAMIT: 1,
            'exhausted_population': {PopulationType.INVESTOR: 1}
        },
        'produces': ResourceType.GESCHÜTZE,
        'worker': PopulationType.INGENIEUR
    },
    
    # ========== WERFTEN ==========
    BuildingType.WERFT_1: {
        'name': 'Werft (Stärke 1)',
        'cost': {ResourceType.BRETTER: 1},
        'type': 'shipyard',
        'max_ship_strength': 1
    },
    BuildingType.WERFT_2: {
        'name': 'Werft (Stärke 2)',
        'cost': {ResourceType.BRETTER: 2, ResourceType.ZIEGELSTEINE: 1},
        'type': 'shipyard',
        'max_ship_strength': 2
    },
    BuildingType.WERFT_3: {
        'name': 'Werft (Stärke 3)',
        'cost': {ResourceType.BRETTER: 2, ResourceType.ZIEGELSTEINE: 1, ResourceType.STAHLTRÄGER: 1},
        'type': 'shipyard',
        'max_ship_strength': 3
    },
    
    # ========== SCHIFFE ==========
    BuildingType.HANDELSSCHIFF_1: {
        'name': 'Handels-Schiff (Stärke 1)',
        'cost': {ResourceType.SEGEL: 1, ResourceType.BRETTER: 1},
        'type': 'ship',
        'ship_type': 'trade',
        'strength': 1
    },
    BuildingType.HANDELSSCHIFF_2: {
        'name': 'Handels-Schiff (Stärke 2)',
        'cost': {ResourceType.SEGEL: 1, ResourceType.WAREN: 1, ResourceType.BRETTER: 1},
        'type': 'ship',
        'ship_type': 'trade',
        'strength': 2
    },
    BuildingType.HANDELSSCHIFF_3: {
        'name': 'Handels-Schiff (Stärke 3)',
        'cost': {ResourceType.SEGEL: 1, ResourceType.WAREN: 1, ResourceType.DAMPFMASCHINE: 1},
        'type': 'ship',
        'ship_type': 'trade',
        'strength': 3
    },
    BuildingType.ERKUNDUNGSSCHIFF_1: {
        'name': 'Erkundungs-Schiff (Stärke 1)',
        'cost': {ResourceType.SEGEL: 1, ResourceType.BRETTER: 1, ResourceType.KANONEN: 1},
        'type': 'ship',
        'ship_type': 'exploration',
        'strength': 1
    },
    BuildingType.ERKUNDUNGSSCHIFF_2: {
        'name': 'Erkundungs-Schiff (Stärke 2)',
        'cost': {ResourceType.SEGEL: 1, ResourceType.KANONEN: 1, ResourceType.KOHLE: 1},
        'type': 'ship',
        'ship_type': 'exploration',
        'strength': 2
    },
    BuildingType.ERKUNDUNGSSCHIFF_3: {
        'name': 'Erkundungs-Schiff (Stärke 3)',
        'cost': {ResourceType.SEGEL: 1, ResourceType.KANONEN: 1, ResourceType.DAMPFMASCHINE: 1},
        'type': 'ship',
        'ship_type': 'exploration',
        'strength': 3
    }
}

# Start-Ressourcen
STARTING_RESOURCES = {
    'population': {
        PopulationType.BAUER: 4,
        PopulationType.ARBEITER: 3,
        PopulationType.HANDWERKER: 2,
        PopulationType.INGENIEUR: 0,
        PopulationType.INVESTOR: 0
    },
    'gold': [0, 1, 2, 3],  # Nach Spielerreihenfolge
    'hand_cards': {
        'farmer_worker': 7,
        'craftsman_engineer_investor': 2
    },
    'marine_tokens': {
        'trade': 2,  # Auf 2 Handelsschiffen
        'exploration': 1  # Auf 1 Erkundungsschiff
    }
}

# Startgebäude auf Heimatinsel (vorgedruckt)
HOME_ISLAND_BUILDINGS = [
    # Diese sind bereits auf der Heimatinsel vorgedruckt
    # und können mit alternativen Versionen überbaut werden
]

# Kosten für neue Arbeitskraft
WORKFORCE_COSTS = {
    PopulationType.BAUER: {
        ResourceType.BRETTER: 1
    },
    PopulationType.ARBEITER: {
        ResourceType.BRETTER: 1,
        ResourceType.ZIEGELSTEINE: 1
    },
    PopulationType.HANDWERKER: {
        ResourceType.BRETTER: 1,
        ResourceType.ZIEGELSTEINE: 1,
        ResourceType.KOHLE: 1
    },
    PopulationType.INGENIEUR: {
        ResourceType.BRETTER: 1,
        ResourceType.KOHLE: 1,
        ResourceType.WAREN: 1,
        ResourceType.STAHLTRÄGER: 1,
        ResourceType.FENSTER: 1
    },
    PopulationType.INVESTOR: {
        ResourceType.FENSTER: 1,
        ResourceType.CHAMPAGNER: 1,
        ResourceType.GLÜHBIRNEN: 1,
        ResourceType.DAMPFWAGEN: 1
    }
}

# Upgrade-Kosten
UPGRADE_COSTS = {
    (PopulationType.BAUER, PopulationType.ARBEITER): {
        ResourceType.ZIEGELSTEINE: 1
    },
    (PopulationType.ARBEITER, PopulationType.HANDWERKER): {
        ResourceType.KOHLE: 1,
        ResourceType.WAREN: 1
    },
    (PopulationType.HANDWERKER, PopulationType.INGENIEUR): {
        ResourceType.STAHLTRÄGER: 1,
        ResourceType.GLAS: 1
    },
    (PopulationType.INGENIEUR, PopulationType.INVESTOR): {
        ResourceType.KAFFEE: 1,
        ResourceType.ZIGARREN: 1
    }
}

# Schichtende-Kosten (Gold pro Arbeiter)
SHIFT_END_COSTS = {
    PopulationType.BAUER: 1,
    PopulationType.ARBEITER: 2,
    PopulationType.HANDWERKER: 3,
    PopulationType.INGENIEUR: 4,
    PopulationType.INVESTOR: 5
}

# Handel-Kosten (Handelsplättchen pro Ressource)
TRADE_COSTS = {
    PopulationType.BAUER: 1,
    PopulationType.ARBEITER: 1,
    PopulationType.HANDWERKER: 2,
    PopulationType.INGENIEUR: 3
}

# Erkundungskosten
EXPLORATION_COSTS = {
    'old_world': [1, 2, 3, 4],  # 1., 2., 3., 4. Insel
    'new_world': [1, 2, 3, 4],
    'expedition': 2  # 2 Erkundungsplättchen für bis zu 3 Karten
}

# Punkte
SCORING = {
    'cards': {
        'farmer_worker': 3,
        'craftsman_engineer_investor': 8,
        'new_world': 5
    },
    'fireworks': 7,
    'gold_per_point': 3,  # 3 Gold = 1 Punkt
}

# Neue Welt Ressourcen
NEW_WORLD_RESOURCES = [
    ResourceType.BAUMWOLLE,
    ResourceType.KAFFEEBOHNEN,
    ResourceType.TABAK,
    ResourceType.ZUCKER,
    ResourceType.KAKAO,
    ResourceType.KAUTSCHUK
]

# Basis-Ressourcen (ohne eigene Produktionsgebäude)
BASE_RESOURCES = [
    ResourceType.GETREIDE,
    ResourceType.KARTOFFELN,
    ResourceType.SCHWEIN
]

# Maximale Anzahlen
MAX_LIMITS = {
    'old_world_islands': 4,
    'new_world_islands': 4,
    'expedition_cards_per_action': 3,
    'buildings_per_type': 1,  # Jede Industrie nur 1x pro Spieler
    'shipyards_per_type': 999,  # Werften unbegrenzt
    'ships_per_type': 999,  # Schiffe unbegrenzt
}
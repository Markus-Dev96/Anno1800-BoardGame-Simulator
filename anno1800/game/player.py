# anno1800/game/player.py
"""
Spieler-Klasse für Anno 1800 Brettspiel - Korrigierte Version
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import logging

from anno1800.utils.constants import (
    PopulationType, ResourceType, BuildingType, 
    BUILDING_DEFINITIONS, STARTING_RESOURCES,
    SHIFT_END_COSTS, WORKFORCE_COSTS, UPGRADE_COSTS,
    TRADE_COSTS, NEW_WORLD_RESOURCES, BASE_RESOURCES
)

logger = logging.getLogger(__name__)

@dataclass
class PlayerState:
    """Spielerzustand gemäß Brettspielregeln"""
    id: int
    name: str
    strategy: str = "human"
    
    # Ressourcen
    gold: int = 0
    
    # Marine-Plättchen (nicht Trade/Exploration tokens!)
    handels_plättchen: int = 0  # Auf Handelsschiffen
    erkundungs_plättchen: int = 0  # Auf Erkundungsschiffen
    erschöpfte_handels_plättchen: int = 0
    erschöpfte_erkundungs_plättchen: int = 0
    
    # Bevölkerung (verfügbar in Wohnvierteln)
    population: Dict[PopulationType, int] = field(default_factory=dict)
    
    # Bevölkerung (eingesetzt auf Arbeitsplätzen oder erschöpft)
    workers_on_buildings: Dict[str, PopulationType] = field(default_factory=dict)  # Gebäude-ID -> Arbeiter
    exhausted_population: Dict[PopulationType, int] = field(default_factory=dict)
    
    # Gebäude
    buildings: List[BuildingType] = field(default_factory=list)
    
    # Inseln
    old_world_islands: List[Dict] = field(default_factory=list)
    new_world_islands: List[Dict] = field(default_factory=list)
    
    # Schiffe
    ships: Dict[BuildingType, int] = field(default_factory=dict)
    shipyards: Dict[BuildingType, int] = field(default_factory=dict)
    
    # Karten
    hand_cards: List[Dict] = field(default_factory=list)
    played_cards: List[Dict] = field(default_factory=list)
    expedition_cards: List[Dict] = field(default_factory=list)
    
    # Spielstatus
    has_fireworks: bool = False
    final_score: int = 0
    rank: int = 0
    
    # Basis-Ressourcen (immer verfügbar ohne Produktion)
    base_resources_available: Dict[ResourceType, bool] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialisiere Startwerte"""
        if not self.population:
            self.population = STARTING_RESOURCES['population'].copy()
        if not self.exhausted_population:
            self.exhausted_population = {pt: 0 for pt in PopulationType}
            
        # Basis-Ressourcen sind immer verfügbar
        for resource in BASE_RESOURCES:
            self.base_resources_available[resource] = True
            
        # Start-Marine-Plättchen
        self.handels_plättchen = STARTING_RESOURCES['marine_tokens']['trade']
        self.erkundungs_plättchen = STARTING_RESOURCES['marine_tokens']['exploration']
    
    def get_available_population(self, pop_type: PopulationType) -> int:
        """Gibt verfügbare Bevölkerung in Wohnvierteln zurück"""
        total = self.population.get(pop_type, 0)
        exhausted = self.exhausted_population.get(pop_type, 0)
        # Auch Arbeiter auf Gebäuden abziehen
        workers_on_buildings = sum(1 for worker in self.workers_on_buildings.values() if worker == pop_type)
        return max(0, total - exhausted - workers_on_buildings)
    
    def can_produce_resource(self, resource: ResourceType, amount: int = 1) -> bool:
        """Prüft ob Ressource produziert werden kann"""
        
        # Basis-Ressourcen sind immer verfügbar
        if resource in BASE_RESOURCES:
            return True
        
        # Neue Welt Ressourcen
        if resource in NEW_WORLD_RESOURCES:
            # Prüfe ob eigene Neue-Welt-Insel diese Ressource hat
            for island in self.new_world_islands:
                if resource in island.get('resources', []):
                    # Prüfe ob genug Handelsplättchen verfügbar
                    available_trade = self.handels_plättchen - self.erschöpfte_handels_plättchen
                    return available_trade >= amount
            return False
        
        # Normale Produktion: Prüfe ob Gebäude vorhanden
        for building in self.buildings:
            building_def = BUILDING_DEFINITIONS.get(building)
            if building_def and building_def.get('produces') == resource:
                # Prüfe ob Arbeiter verfügbar
                worker_type = building_def.get('worker')
                if self.get_available_population(worker_type) >= amount:
                    return True
        
        return False
    
    def produce_resource(self, resource: ResourceType, amount: int = 1) -> bool:
        """Produziert eine Ressource"""
        
        # Basis-Ressourcen benötigen keine Produktion
        if resource in BASE_RESOURCES:
            return True
        
        # Neue Welt Ressourcen
        if resource in NEW_WORLD_RESOURCES:
            for island in self.new_world_islands:
                if resource in island.get('resources', []):
                    self.erschöpfte_handels_plättchen += amount
                    logger.debug(f"{self.name} produziert {amount}x {resource.value} von Neuer Welt")
                    return True
            return False
        
        # Normale Produktion
        for building in self.buildings:
            building_def = BUILDING_DEFINITIONS.get(building)
            if building_def and building_def.get('produces') == resource:
                worker_type = building_def.get('worker')
                
                if self.get_available_population(worker_type) >= amount:
                    # Setze Arbeiter auf Arbeitsplatz
                    for _ in range(amount):
                        self.population[worker_type] -= 1
                        building_key = f"{building}_{len(self.workers_on_buildings)}"
                        self.workers_on_buildings[building_key] = worker_type
                    logger.debug(f"{self.name} produziert {amount}x {resource.value}")
                    return True
        
        return False
    
    def can_afford_building_cost(self, building_type: BuildingType) -> bool:
        """Prüft ob Gebäude gebaut werden kann (inkl. erschöpfter Bevölkerung)"""
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if not building_def:
            return False
        
        cost = building_def.get('cost', {})
        
        # Prüfe normale Ressourcenkosten
        for resource, amount in cost.items():
            if resource == 'exhausted_population':
                continue  # Separat prüfen
            if not self.can_produce_resource(resource, amount):
                return False
        
        # Prüfe erschöpfte Bevölkerung
        exhausted_pop = cost.get('exhausted_population', {})
        for pop_type, amount in exhausted_pop.items():
            if self.get_available_population(pop_type) < amount:
                return False
        
        return True
    
    def pay_building_cost(self, building_type: BuildingType) -> bool:
        """Bezahlt die Kosten für ein Gebäude"""
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if not building_def:
            return False
        
        cost = building_def.get('cost', {})
        
        # Bezahle normale Ressourcen
        for resource, amount in cost.items():
            if resource == 'exhausted_population':
                continue
            if not self.produce_resource(resource, amount):
                return False
        
        # Erschöpfe benötigte Bevölkerung
        exhausted_pop = cost.get('exhausted_population', {})
        for pop_type, amount in exhausted_pop.items():
            self.population[pop_type] -= amount
            self.exhausted_population[pop_type] += amount
            logger.debug(f"{self.name} erschöpft {amount} {pop_type.value} für Gebäude")
        
        return True
    
    def can_trade_resource(self, resource: ResourceType, partner_player: 'PlayerState') -> bool:
        """Prüft ob Ressource gehandelt werden kann"""
        # Neue Welt Ressourcen können nicht gehandelt werden
        if resource in NEW_WORLD_RESOURCES:
            return False
        
        # Prüfe ob Partner die Ressource produzieren kann
        if not partner_player.has_production_building(resource):
            return False
        
        # Finde benötigte Handelsplättchen
        for building_type in BuildingType:
            building_def = BUILDING_DEFINITIONS.get(building_type)
            if building_def and building_def.get('produces') == resource:
                worker_type = building_def.get('worker')
                required_tokens = TRADE_COSTS.get(worker_type, 0)
                available_tokens = self.handels_plättchen - self.erschöpfte_handels_plättchen
                return available_tokens >= required_tokens
        
        return False
    
    def has_production_building(self, resource: ResourceType) -> bool:
        """Prüft ob Spieler ein Gebäude hat das diese Ressource produziert"""
        for building in self.buildings:
            building_def = BUILDING_DEFINITIONS.get(building)
            if building_def and building_def.get('produces') == resource:
                return True
        return False
    
    def trade_resource(self, resource: ResourceType, partner_player: 'PlayerState') -> bool:
        """Handelt eine Ressource mit einem Mitspieler"""
        if not self.can_trade_resource(resource, partner_player):
            return False
        
        # Finde benötigte Handelsplättchen
        for building_type in BuildingType:
            building_def = BUILDING_DEFINITIONS.get(building_type)
            if building_def and building_def.get('produces') == resource:
                worker_type = building_def.get('worker')
                required_tokens = TRADE_COSTS.get(worker_type, 0)
                
                # Erschöpfe Handelsplättchen
                self.erschöpfte_handels_plättchen += required_tokens
                
                # Partner erhält 1 Gold
                partner_player.gold += 1
                
                logger.info(f"{self.name} handelt {resource.value} von {partner_player.name}")
                return True
        
        return False
    
    def city_festival(self):
        """Stadtfest - alle Arbeiter und Plättchen zurücksetzen"""
        # Arbeiter von Gebäuden zurück in Wohnviertel
        for building_key, worker_type in self.workers_on_buildings.items():
            self.population[worker_type] += 1
        self.workers_on_buildings.clear()
        
        # Erschöpfte Bevölkerung zurücksetzen
        for pop_type in PopulationType:
            self.population[pop_type] += self.exhausted_population.get(pop_type, 0)
            self.exhausted_population[pop_type] = 0
        
        # Marine-Plättchen zurücksetzen
        self.erschöpfte_handels_plättchen = 0
        self.erschöpfte_erkundungs_plättchen = 0
        
        logger.info(f"{self.name} feiert Stadtfest - alle Arbeiter zurückgesetzt")
    
    def shift_end_worker(self, pop_type: PopulationType) -> bool:
        """Schichtende für einen Arbeiter"""
        cost = SHIFT_END_COSTS.get(pop_type, 0)
        if self.gold < cost:
            return False
        
        # Suche Arbeiter (erschöpft oder auf Gebäude)
        if self.exhausted_population.get(pop_type, 0) > 0:
            self.gold -= cost
            self.exhausted_population[pop_type] -= 1
            self.population[pop_type] += 1
            logger.debug(f"{self.name} Schichtende für erschöpften {pop_type.value}")
            return True
        
        # Suche auf Gebäuden
        for building_key, worker in list(self.workers_on_buildings.items()):
            if worker == pop_type:
                self.gold -= cost
                del self.workers_on_buildings[building_key]
                self.population[pop_type] += 1
                logger.debug(f"{self.name} Schichtende für {pop_type.value} auf Gebäude")
                return True
        
        return False
    
    def add_population(self, pop_type: PopulationType) -> bool:
        """Fügt neue Bevölkerung hinzu (Arbeitskraft erhöhen)"""
        cost = WORKFORCE_COSTS.get(pop_type, {})
        
        # Prüfe und bezahle Kosten
        for resource, amount in cost.items():
            if not self.produce_resource(resource, amount):
                return False
        
        # Füge Bevölkerung hinzu
        self.population[pop_type] = self.population.get(pop_type, 0) + 1
        logger.info(f"{self.name} erhält 1 {pop_type.value}")
        
        # Ziehe entsprechende Karte (muss in game engine behandelt werden)
        return True
    
    def upgrade_population(self, from_type: PopulationType, to_type: PopulationType) -> bool:
        """Verbessert Bevölkerung (Aufsteigen)"""
        upgrade_key = (from_type, to_type)
        cost = UPGRADE_COSTS.get(upgrade_key, {})
        
        if self.get_available_population(from_type) < 1:
            return False
        
        # Prüfe und bezahle Kosten
        for resource, amount in cost.items():
            if not self.produce_resource(resource, amount):
                return False
        
        # Führe Upgrade durch
        self.population[from_type] -= 1
        self.population[to_type] = self.population.get(to_type, 0) + 1
        logger.info(f"{self.name} verbessert 1 {from_type.value} zu {to_type.value}")
        
        return True
    
    def build_building(self, building_type: BuildingType) -> bool:
        """Baut ein Gebäude"""
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if not building_def:
            return False
        
        # Prüfe ob Industrie bereits vorhanden (max 1 pro Typ)
        if building_def.get('produces') and building_type in self.buildings:
            logger.warning(f"{self.name} hat {building_type.value} bereits gebaut")
            return False
        
        # Bezahle Kosten
        if not self.pay_building_cost(building_type):
            return False
        
        self.buildings.append(building_type)
        logger.info(f"{self.name} baut {building_type.value}")
        
        # Spezialbehandlung für Werften und Schiffe
        if building_def.get('type') == 'shipyard':
            self.shipyards[building_type] = self.shipyards.get(building_type, 0) + 1
        elif building_def.get('type') == 'ship':
            self.ships[building_type] = self.ships.get(building_type, 0) + 1
            # Füge Marine-Plättchen hinzu
            if building_def.get('ship_type') == 'trade':
                self.handels_plättchen += building_def.get('strength', 0)
            elif building_def.get('ship_type') == 'exploration':
                self.erkundungs_plättchen += building_def.get('strength', 0)
        
        return True
    
    def calculate_score(self) -> int:
        """Berechnet Endpunkte"""
        from anno1800.utils.constants import SCORING
        
        score = 0
        
        # Punkte für ausgespielte Karten
        for card in self.played_cards:
            card_type = card.get('type', '')
            score += SCORING['cards'].get(card_type, 0)
        
        # Punkte für Expeditionskarten (vereinfacht)
        score += len(self.expedition_cards) * 2
        
        # Gold
        score += self.gold // SCORING['gold_per_point']
        
        # Feuerwerk
        if self.has_fireworks:
            score += SCORING['fireworks']
        
        self.final_score = score
        return score
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
       """Initialisiere Startwerte mit erweiterten Startfeld-Ressourcen"""
       # Start-Bevölkerung
       if not self.population:
           self.population = STARTING_RESOURCES['population'].copy()
       if not self.exhausted_population:
           self.exhausted_population = {pt: 0 for pt in PopulationType}
           
       # Erweiterte Basis-Ressourcen (Startfeld-Produktionen)
       self.base_resources_available = {
           # Grundressourcen (kostenlos verfügbar)
           ResourceType.GETREIDE: True,    # Für Brot und Bier
           ResourceType.KARTOFFELN: True,  # Für Schnaps  
           ResourceType.SCHWEIN: True,     # Für Wurst, Seife, Fleischkonserven
           ResourceType.BRETTER: True,     # Sägewerk auf Startfeld
           ResourceType.GARN: True,        # Spinnerei auf Startfeld
           ResourceType.KOHLE: True,       # Kohlemine auf Startfeld
           ResourceType.ZIEGELSTEINE: True, # Ziegelei auf Startfeld
           ResourceType.WAREN: True,       # Warenproduktion auf Startfeld
           ResourceType.STAHLTRÄGER: True, # Stahlwerk auf Startfeld  
           ResourceType.SEGEL: True,       # Segelmacher auf Startfeld
       }
       
       # Start-Gebäude auf Heimatinsel (vorgedruckt)
       self.start_buildings = [
           BuildingType.SÄGEWERK,      # Produziert BRETTER (Arbeiter)
           BuildingType.SPINNEREI,     # Produziert GARN (Arbeiter)  
           BuildingType.KÖHLEREI,     # Produziert KOHLE (Arbeiter)
           BuildingType.ZIEGELEI,      # Produziert ZIEGELSTEINE (Arbeiter)
           BuildingType.LAGERHAUS,     # Produziert WAREN (Arbeiter)
           BuildingType.STAHLWERK,     # Produziert STAHLTRÄGER (Arbeiter)
           BuildingType.SEGELMACHEREI, # Produziert SEGEL (Arbeiter)
           BuildingType.WERFT_1,       # Hafen Stufe 1
       ]
       
       # Bauplätze auf Heimatinsel
       self.available_land_tiles = 4    # 4 normale Bauplätze
       self.available_coast_tiles = 4   # 4 Küstenplätze (davon 1 für Werft belegt)
       self.used_land_tiles = 0
       self.used_coast_tiles = 1        # Werft belegt 1 Küstenplatz
       
       # Start-Marine-Plättchen
       self.handels_plättchen = STARTING_RESOURCES['marine_tokens']['trade']
       self.erkundungs_plättchen = STARTING_RESOURCES['marine_tokens']['exploration']
       
       # Start-Gold basierend auf Spielerposition
       if self.gold == 0:
           self.gold = STARTING_RESOURCES['gold'][min(self.id, 3)]
       
       logger.info(f"Spieler {self.name} initialisiert mit {self.gold} Gold, {len(self.start_buildings)} Startgebäuden und {self.available_land_tiles + self.available_coast_tiles} Bauplätzen")
    
    def get_available_population(self, pop_type: PopulationType) -> int:
        """Gibt verfügbare Bevölkerung in Wohnvierteln zurück"""
        total = self.population.get(pop_type, 0)
        exhausted = self.exhausted_population.get(pop_type, 0)
        # Auch Arbeiter auf Gebäuden abziehen
        workers_on_buildings = sum(1 for worker in self.workers_on_buildings.values() if worker == pop_type)
        return max(0, total - exhausted - workers_on_buildings)
    
    def can_produce_resource(self, resource: ResourceType, amount: int = 1) -> bool:
      """Prüft ob Ressource produziert werden kann inkl. Basis-Ressourcen"""
    
      # Basis-Ressourcen (Startfeld) sind immer verfügbar
      if resource in self.base_resources_available and self.base_resources_available[resource]:
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
              # Prüfe ob Arbeiter verfügbar UND erschöpft werden kann
              worker_type = building_def.get('worker')
              if self.get_available_population(worker_type) >= amount:
                  return True
    
      return False
    
    def produce_resource(self, resource: ResourceType, amount: int = 1) -> bool:
      """Produziert eine Ressource und erschöpft dabei Arbeiter"""
      
      # Basis-Ressourcen benötigen keine Produktion (kostenlos vom Startfeld)
      if resource in self.base_resources_available and self.base_resources_available[resource]:
          logger.debug(f"{self.name} verwendet Basis-Ressource {resource.value} vom Startfeld")
          return True
      
      # Neue Welt Ressourcen
      if resource in NEW_WORLD_RESOURCES:
          for island in self.new_world_islands:
              if resource in island.get('resources', []):
                  # Erschöpfe Handelsplättchen für Neue-Welt-Ressourcen
                  self.erschöpfte_handels_plättchen += amount
                  logger.debug(f"{self.name} produziert {amount}x {resource.value} von Neuer Welt (Handelsplättchen erschöpft)")
                  return True
          return False
      
      # Normale Produktion mit Arbeiter-Erschöpfung
      for building in self.buildings:
          building_def = BUILDING_DEFINITIONS.get(building)
          if building_def and building_def.get('produces') == resource:
              worker_type = building_def.get('worker')
              
              if self.get_available_population(worker_type) >= amount:
                  # ERschöpfe Arbeiter für die Produktion
                  for _ in range(amount):
                      # Reduziere verfügbare Bevölkerung und erhöhe erschöpfte Bevölkerung
                      if worker_type in self.population:
                          self.population[worker_type] -= 1
                          self.exhausted_population[worker_type] = self.exhausted_population.get(worker_type, 0) + 1
                          
                          # Setze Arbeiter auch auf Arbeitsplatz (für spätere Rückstellung)
                          building_key = f"{building}_{len(self.workers_on_buildings)}"
                          self.workers_on_buildings[building_key] = worker_type
                  
                  logger.debug(f"{self.name} produziert {amount}x {resource.value} und erschöpft {amount} {worker_type.value}")
                  return True
    
      return False
    
    def can_afford_building_cost(self, building_type: BuildingType) -> bool:
      """Prüft detailliert ob Gebäude gebaut werden kann"""
      building_def = BUILDING_DEFINITIONS.get(building_type)
      if not building_def:
          return False
      
      cost = building_def.get('cost', {})
      
      # Prüfe normale Ressourcenkosten
      for resource, amount in cost.items():
          if resource == 'exhausted_population':
              continue
            
          # Prüfe ob Ressource produziert werden kann
          if not self.can_produce_resource(resource, amount):
              logger.debug(f"Kann {amount} {resource.value} nicht produzieren")
              return False
      
      # Prüfe erschöpfte Bevölkerung
      exhausted_pop = cost.get('exhausted_population', {})
      for pop_type, amount in exhausted_pop.items():
          available = self.get_available_population(pop_type)
          if available < amount:
              logger.debug(f"Nicht genug {pop_type.value} verfügbar ({available}/{amount})")
              return False
      
      # Prüfe Bauplätze
      requires_coast = building_def.get('requires_coast', False)
      is_shipyard = building_def.get('type') == 'shipyard'
      
      if requires_coast or is_shipyard:
          if self.used_coast_tiles >= self.available_coast_tiles:
              logger.debug("Keine Küsten-Bauplätze mehr verfügbar")
              return False
      else:
          if self.used_land_tiles >= self.available_land_tiles:
              logger.debug("Keine Land-Bauplätze mehr verfügbar")
              return False
      
      return True
    
    def pay_building_cost(self, building_type: BuildingType) -> bool:
        """Bezahlt die Kosten für ein Gebäude mit Ressourcen- und Arbeiter-Erschöpfung"""
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if not building_def:
            return False

        cost = building_def.get('cost', {})

        # Bezahle normale Ressourcen (erschöpft dabei Arbeiter)
        for resource, amount in cost.items():
            if resource == 'exhausted_population':
                continue
            
            if not self.produce_resource(resource, amount):
                logger.warning(f"{self.name} kann {amount} {resource.value} nicht produzieren")
                return False

        # Erschöpfe zusätzliche benötigte Bevölkerung (für Gebäude die direkte Erschöpfung benötigen)
        exhausted_pop = cost.get('exhausted_population', {})
        for pop_type, amount in exhausted_pop.items():
            available = self.get_available_population(pop_type)
            if available < amount:
                logger.warning(f"{self.name} hat nicht genug {pop_type.value} verfügbar ({available}/{amount})")
                return False

            # Erschöpfe die Bevölkerung
            self.population[pop_type] -= amount
            self.exhausted_population[pop_type] += amount
            logger.debug(f"{self.name} erschöpft {amount} {pop_type.value} für Gebäude {building_type.value}")

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
            if pop_type in self.exhausted_population:
                exhausted_count = self.exhausted_population[pop_type]
                self.population[pop_type] += exhausted_count
                self.exhausted_population[pop_type] = 0
                if exhausted_count > 0:
                    logger.debug(f"{self.name} stellt {exhausted_count} {pop_type.value} wieder her")

        # Marine-Plättchen zurücksetzen
        trade_reset = self.erschöpfte_handels_plättchen
        exploration_reset = self.erschöpfte_erkundungs_plättchen
        self.erschöpfte_handels_plättchen = 0
        self.erschöpfte_erkundungs_plättchen = 0
    
        logger.info(f"{self.name} feiert Stadtfest - {trade_reset} Handels- und {exploration_reset} Erkundungsplättchen zurückgesetzt, alle Arbeiter wiederhergestellt")
    
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
       """Baut ein Gebäude mit Überbau-Logik und Platzprüfung"""
       building_def = BUILDING_DEFINITIONS.get(building_type)
       if not building_def:
           return False

       # Prüfe Bauplatz-Typ
       requires_coast = building_def.get('requires_coast', False)
       is_shipyard = building_def.get('type') == 'shipyard'
       is_ship = building_def.get('type') == 'ship'

       # Schiffe benötigen Küstenplätze (Werften)
       if is_ship:
           # Prüfe ob genug Werften-Plätze verfügbar
           num_shipyards = sum(self.shipyards.values())
           ships_built = sum(self.ships.values())
           if ships_built >= num_shipyards:
               logger.warning(f"Nicht genug Werften-Plätze für weitere Schiffe")
               return False

       # Gebäude-Platzprüfung
       elif requires_coast or is_shipyard:
           # Küstengebäude benötigen Küstenplatz
           if self.used_coast_tiles >= self.available_coast_tiles:
               logger.warning(f"Keine Küsten-Bauplätze mehr verfügbar")
               return False
       else:
           # Landgebäude benötigen Landplatz
           if self.used_land_tiles >= self.available_land_tiles:
               logger.warning(f"Keine Land-Bauplätze mehr verfügbar")
               return False

       # Überbau-Logik: Prüfe ob Industrie bereits vorhanden (max 1 pro Typ, außer Startgebäude)
       if building_def.get('produces') and building_type in self.buildings:
           # Erlaube Überbau von Startgebäuden
           if building_type in self.start_buildings:
               logger.info(f"{self.name} überbaut Startgebäude {building_type.value}")
               # Startgebäude wird entfernt
               self.start_buildings.remove(building_type)
           else:
               logger.warning(f"{self.name} hat {building_type.value} bereits gebaut")
               return False

       # Bezahle Kosten
       if not self.pay_building_cost(building_type):
           return False

       # Verbrauche Bauplatz
       if requires_coast or is_shipyard:
           self.used_coast_tiles += 1
       else:
           self.used_land_tiles += 1

       self.buildings.append(building_type)
       logger.info(f"{self.name} baut {building_type.value} (Land: {self.used_land_tiles}/{self.available_land_tiles}, Küste: {self.used_coast_tiles}/{self.available_coast_tiles})")

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
    
    def add_island_building_slots(self, island_type: str):
        """Fügt Bauplätze von einer neuen Insel hinzu"""
        if island_type == 'old_world':
            # Alte-Welt-Inseln bieten 4 neue Bauplätze: 2 Land, 2 Küste
            self.available_land_tiles += 2
            self.available_coast_tiles += 2
            logger.info(f"{self.name} erschließt Alte-Welt-Insel: +2 Land, +2 Küste Bauplätze")
        elif island_type == 'new_world':
            # Neue-Welt-Inseln bieten spezielle Ressourcen aber keine Bauplätze
            logger.info(f"{self.name} erkundet Neue-Welt-Insel für Ressourcen")
    
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
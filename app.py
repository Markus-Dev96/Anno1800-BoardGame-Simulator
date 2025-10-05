# app.py
from anno1800.utils.constants import BUILDING_DEFINITIONS
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime
import random
import numpy as np

# Füge das Projektverzeichnis zum Python-Path hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# app.py - Add this import
try:
    from anno1800.game.engine import GameEngine, GameAction, GamePhase
    from anno1800.game.player import PlayerState
    from anno1800.ai.strategy import AIStrategy
    from anno1800.ml.model import Anno1800MLModel
    from anno1800.ml.data_collector import OptimizedDataCollector  # Add this
    from anno1800.utils.constants import ActionType, PopulationType, BuildingType
except ImportError:
    # Fallback für Entwicklungsmodus
    print("Warning: Could not import game modules - running in fallback mode")
# Flask App erstellen
app = Flask(__name__, 
            static_folder='frontend/static',
            template_folder='frontend/templates')
CORS(app)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globale Spielinstanz
game_instance = {
    'engine': None,
    'ai_strategies': {},
    'ml_model': None,
    'data_collector': None,  
    'action_history': [],
}

# Route für die Hauptseite
@app.route('/')
def index():
    """Rendert die Hauptseite"""
    return send_from_directory('frontend/static', 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'running', 
        'timestamp': datetime.now().isoformat(),
        'game_active': game_instance['engine'] is not None
    })

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Startet ein neues Spiel"""
    try:
        data = request.json
        num_players = data.get('num_players', 4)
        strategies = data.get('strategies', ['human', 'balanced', 'economic', 'explorer'])
        player_names = data.get('player_names', [f"Spieler {i+1}" for i in range(num_players)])
        
        # Erstelle neue Game Engine
        game_instance['engine'] = GameEngine(num_players)
        game_instance['engine'].setup_game(player_names, strategies)
        
        # Erstelle KI-Strategien für nicht-menschliche Spieler
        game_instance['ai_strategies'] = {}
        for i, strategy in enumerate(strategies):
            if strategy != 'human':
                game_instance['ai_strategies'][i] = AIStrategy(strategy)
        
        # Reset action history
        game_instance['action_history'] = []
        
        # Initialisiere Data Collector
        if game_instance['data_collector'] is None:
            game_instance['data_collector'] = OptimizedDataCollector()
        
        logger.info(f"Neues Spiel gestartet mit {num_players} Spielern")
        
        return jsonify({
            'success': True,
            'game_state': serialize_game_state()
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Starten eines neuen Spiels: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/execute_action', methods=['POST'])
def execute_action():
    """Führt eine Spielaktion aus"""
    try:
        if not game_instance['engine']:
            return jsonify({'success': False, 'error': 'Kein Spiel gestartet'}), 400
        
        data = request.json
        action_type = data.get('action_type')
        parameters = data.get('parameters', {})
        
        current_player = game_instance['engine'].get_current_player()
        
        # Für KI-Spieler: Lass KI entscheiden
        if current_player.strategy != 'human':
            if current_player.id in game_instance['ai_strategies']:
                ai_strategy = game_instance['ai_strategies'][current_player.id]
                action = ai_strategy.decide_action(game_instance['engine'], current_player)
                success = game_instance['engine'].execute_action(action)
                
                if success:
                    collect_training_data(action)
                
                return jsonify({
                    'success': success,
                    'game_state': serialize_game_state(),
                    'message': f"{current_player.name} (KI) führt {action.action_type.name} aus"
                })
        
        # Konvertiere Action-Type String zu Enum
        action_type_enum = get_action_type_enum(action_type)
        
        # Für Bau-Aktionen: Prüfe auf maximale Anzahl (1 Gebäude pro Runde)
        if action_type_enum == ActionType.AUSBAUEN:
            buildings_to_build = parameters.get('buildings', [])
            if len(buildings_to_build) > 1:
                return jsonify({
                    'success': False,
                    'error': 'Maximal 1 Gebäude pro Runde kann gebaut werden',
                    'game_state': serialize_game_state()
                }), 400
            
            # Detaillierte Prüfung für Bau-Aktionen
            if buildings_to_build:
                building_id = buildings_to_build[0]
                # Konvertiere String zu BuildingType Enum
                try:
                    building_type = BuildingType(building_id)
                    # Prüfe ob Gebäude verfügbar ist
                    if game_instance['engine'].board.available_buildings.get(building_type, 0) <= 0:
                        return jsonify({
                            'success': False,
                            'error': f'Gebäude {building_id} ist nicht mehr verfügbar',
                            'game_state': serialize_game_state()
                        }), 400
                    
                    # Detaillierte Prüfung ob Spieler sich Gebäude leisten kann
                    if not current_player.can_afford_building_cost(building_type):
                        # Erstelle detaillierte Fehlermeldung
                        building_def = BUILDING_DEFINITIONS.get(building_type)
                        if building_def:
                            cost = building_def.get('cost', {})
                            missing_resources = []
                            
                            for resource, amount in cost.items():
                                if resource == 'exhausted_population':
                                    continue
                                if not current_player.can_produce_resource(resource, amount):
                                    missing_resources.append(f"{amount} {resource.value}")
                            
                            exhausted_pop = cost.get('exhausted_population', {})
                            for pop_type, amount in exhausted_pop.items():
                                if current_player.get_available_population(pop_type) < amount:
                                    missing_resources.append(f"{amount} {pop_type.value}")
                            
                            error_msg = f"Nicht genug Ressourcen: {', '.join(missing_resources)}" if missing_resources else "Nicht genug Ressourcen oder Bevölkerung"
                            return jsonify({
                                'success': False,
                                'error': error_msg,
                                'game_state': serialize_game_state()
                            }), 400
                        
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': f'Ungültiges Gebäude: {building_id}',
                        'game_state': serialize_game_state()
                    }), 400
        
        # Für menschliche Spieler: Lass KI Parameter generieren wenn leer
        if not parameters or parameters == {}:
            if current_player.id not in game_instance['ai_strategies']:
                game_instance['ai_strategies'][current_player.id] = AIStrategy('balanced')
            
            ai = game_instance['ai_strategies'][current_player.id]
            ai_action = ai._create_action(game_instance['engine'], current_player, action_type_enum)
            parameters = ai_action.parameters
        
        # Erstelle GameAction
        action = GameAction(
            player_id=current_player.id,
            action_type=action_type_enum,
            parameters=parameters
        )
        
        # Führe Aktion aus
        success = game_instance['engine'].execute_action(action)
        
        # Log action
        game_instance['action_history'].append({
            'player': current_player.name,
            'action': action_type,
            'success': success,
            'round': game_instance['engine'].round_number,
            'timestamp': datetime.now().isoformat()
        })
        
        # Sammle Trainingsdaten wenn erfolgreich
        if success:
            collect_training_data(action)
        
        # Spezifische Fehlermeldungen für Bau-Aktionen
        if not success and action_type_enum == ActionType.AUSBAUEN:
            buildings_to_build = parameters.get('buildings', [])
            if buildings_to_build:
                building_id = buildings_to_build[0]
                building_type = BuildingType(building_id)
                building_def = BUILDING_DEFINITIONS.get(building_type)
                
                if building_def:
                    # Erstelle detaillierte Fehleranalyse
                    cost = building_def.get('cost', {})
                    missing_details = []
                    
                    # Prüfe normale Ressourcen
                    for resource, amount in cost.items():
                        if resource == 'exhausted_population':
                            continue
                        if not current_player.can_produce_resource(resource, amount):
                            missing_details.append(f"{amount} {resource.value}")
                    
                    # Prüfe erschöpfte Bevölkerung
                    exhausted_pop = cost.get('exhausted_population', {})
                    for pop_type, amount in exhausted_pop.items():
                        if current_player.get_available_population(pop_type) < amount:
                            missing_details.append(f"{amount} {pop_type.value}")
                    
                    # Prüfe Bauplätze
                    requires_coast = building_def.get('requires_coast', False)
                    is_shipyard = building_def.get('type') == 'shipyard'
                    
                    if requires_coast or is_shipyard:
                        if current_player.used_coast_tiles >= current_player.available_coast_tiles:
                            missing_details.append("Kein Küsten-Bauplatz")
                    else:
                        if current_player.used_land_tiles >= current_player.available_land_tiles:
                            missing_details.append("Kein Land-Bauplatz")
                    
                    error_msg = "FEHLER: " + (", ".join(missing_details) if missing_details else "Unbekannter Fehler beim Bauen")
                    
                    return jsonify({
                        'success': False,
                        'error': error_msg,
                        'game_state': serialize_game_state(),
                        'message': error_msg
                    })
        
        return jsonify({
            'success': success,
            'game_state': serialize_game_state(),
            'message': f"{current_player.name} führt {action_type_enum.name} aus" if success else "Aktion fehlgeschlagen"
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Ausführen der Aktion: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f"Fehler: {str(e)}"}), 500
    
@app.route('/api/game_state', methods=['GET'])
def get_game_state():
    """Gibt den aktuellen Spielzustand zurück"""
    try:
        if not game_instance['engine']:
            return jsonify({'success': False, 'error': 'Kein Spiel gestartet'}), 400
        
        return jsonify({
            'success': True,
            'game_state': serialize_game_state()
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Spielzustands: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ml_suggestion', methods=['GET'])
def get_ml_suggestion():
    """Gibt einen ML-basierten Vorschlag zurück"""
    try:
        if not game_instance['engine']:
            return jsonify({'success': False, 'error': 'Kein Spiel gestartet'}), 400
        
        # Initialisiere ML-Modell falls nötig
        if game_instance['ml_model'] is None:
            game_instance['ml_model'] = Anno1800MLModel()
        
        if not game_instance['ml_model'].is_trained:
            return get_rule_based_suggestion()
        
        current_player = game_instance['engine'].get_current_player()
        action, confidence = game_instance['ml_model'].predict(
            game_instance['engine'], 
            current_player
        )
        
        if action:
            reasoning = generate_reasoning(action, current_player, game_instance['engine'])
            return jsonify({
                'success': True,
                'action': action.value,
                'confidence': round(confidence * 100, 1),
                'reasoning': reasoning
            })
        else:
            return get_rule_based_suggestion()
    
    except Exception as e:
        logger.error(f"Fehler beim ML-Vorschlag: {e}")
        return get_rule_based_suggestion()

@app.route('/api/run_simulation', methods=['POST'])
def run_simulation():
    """Führt eine Batch-Simulation aus"""
    try:
        data = request.json
        num_games = data.get('num_games', 10)  # Reduziert für Testzwecke
        
        results = {
            'games_played': 0,
            'data_points': 0,
            'strategy_wins': {}
        }
        
        for i in range(num_games):
            sim_result = simulate_single_game()
            results['games_played'] += 1
            results['data_points'] += len(sim_result['actions'])
            
            winner_strategy = sim_result['winner_strategy']
            if winner_strategy not in results['strategy_wins']:
                results['strategy_wins'][winner_strategy] = 0
            results['strategy_wins'][winner_strategy] += 1
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Fehler bei Simulation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/train_model', methods=['POST'])
def train_model():
    """Trainiert das ML-Modell mit gesammelten Daten"""
    try:
        # Initialisiere ML-Modell falls nötig
        if game_instance['ml_model'] is None:
            game_instance['ml_model'] = Anno1800MLModel()
        
        # Verwende den Data Collector für Trainingsdaten
        data_collector = get_data_collector()
        
        # Prüfe ob genug Daten vorhanden sind
        if not data_collector.has_sufficient_data(min_games=2):  # Noch niedrigere Schwelle für Entwicklung
            stats = data_collector.get_statistics()
            return jsonify({
                'success': False, 
                'error': f'Nicht genug Trainingsdaten: {stats.get("total_moves", 0)} Züge, benötigt mindestens 20'
            }), 400
        
        # Lade Trainingsdaten
        X, y = data_collector.get_normalized_training_data()
        
        if len(X) == 0:
            return jsonify({
                'success': False,
                'error': 'Keine gültigen Trainingsdaten gefunden'
            }), 400
        
        # Trainiere das Modell
        training_data = []
        for features, action in zip(X, y):
            training_data.append({
                'features': features.tolist() if hasattr(features, 'tolist') else features,
                'action': action
            })
        
        # Führe Training durch
        result = game_instance['ml_model'].train(training_data)
        
        logger.info(f"ML-Modell trainiert mit {len(X)} Beispielen, Genauigkeit: {result['accuracy']:.3f}")
        
        return jsonify({
            'success': True,
            'accuracy': result['accuracy'],
            'training_samples': len(X),
            'feature_dimension': result['feature_dimension'],
            'message': f'Modell mit {len(X)} Beispielen trainiert (Genauigkeit: {result["accuracy"]:.1%})'
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Training des ML-Modells: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# Hilfsfunktionen
def serialize_game_state():
    """Serialisiert den Spielzustand"""
    if not game_instance['engine']:
        return None
    
    engine = game_instance['engine']
    current_player = engine.get_current_player()
    
    players = []
    for player in engine.players:
        # Berechne verfügbare Bevölkerung
        available_population = {}
        for pop_type in PopulationType:
            total = player.population.get(pop_type, 0)
            exhausted = player.exhausted_population.get(pop_type, 0)
            workers_on_buildings = sum(1 for worker in player.workers_on_buildings.values() if worker == pop_type)
            available_population[pop_type.value] = max(0, total - exhausted - workers_on_buildings)
        
        # Erweiterte Basis-Ressourcen
        base_resources = [
            'grain',      # GETREIDE
            'potatoes',   # KARTOFFELN  
            'pig',        # SCHWEIN
            'wood',       # BRETTER (Sägewerk)
            'yarn',       # GARN (Spinnerei)
            'coal',       # KOHLE (Kohlemine)
            'bricks',     # ZIEGELSTEINE (Ziegelei)
            'goods',      # WAREN (Lagerhaus)
            'steel',      # STAHLTRÄGER (Stahlwerk)
            'sails'       # SEGEL (Segelmacher)
        ]
        
        # Bauplätze-Information
        building_slots = {
            'land': {
                'available': getattr(player, 'available_land_tiles', 4),
                'used': getattr(player, 'used_land_tiles', 0),
                'remaining': getattr(player, 'available_land_tiles', 4) - getattr(player, 'used_land_tiles', 0)
            },
            'coast': {
                'available': getattr(player, 'available_coast_tiles', 4),
                'used': getattr(player, 'used_coast_tiles', 1),  # Start-Werft belegt 1
                'remaining': getattr(player, 'available_coast_tiles', 4) - getattr(player, 'used_coast_tiles', 1)
            }
        }
        
        # Konvertiere Gebäude zu Strings für JSON
        buildings_list = [b.value for b in player.buildings]
        start_buildings_list = [b.value for b in getattr(player, 'start_buildings', [])]
        
        players.append({
            'id': player.id,
            'name': player.name,
            'strategy': player.strategy,
            'gold': player.gold,
            'handCards': len(player.hand_cards),
            'playedCards': len(player.played_cards),
            'buildings': buildings_list,
            'startBuildings': start_buildings_list,  # Neue: Startgebäude die überbaut werden können
            'population': {k.value: v for k, v in player.population.items()},
            'exhaustedPopulation': {k.value: v for k, v in player.exhausted_population.items()},
            'availablePopulation': available_population,
            'workersOnBuildings': {k: v.value for k, v in player.workers_on_buildings.items()},
            'tradeTokens': player.handels_plättchen,
            'explorationTokens': player.erkundungs_plättchen,
            'exhaustedTrade': player.erschöpfte_handels_plättchen,
            'exhaustedExploration': player.erschöpfte_erkundungs_plättchen,
            'availableTrade': player.handels_plättchen - player.erschöpfte_handels_plättchen,
            'availableExploration': player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen,
            'oldWorldIslands': len(player.old_world_islands),
            'newWorldIslands': len(player.new_world_islands),
            'expeditionCards': len(player.expedition_cards),
            'baseResources': base_resources,
            'buildingSlots': building_slots,  # Neue: Bauplätze-Information
            'score': player.calculate_score(),
            'canBuild': _can_build_anything(player),
            'canExplore': any([
                _can_explore_old_world(player),
                _can_explore_new_world(player),
                _can_expedition(player)
            ])
        })

    # Korrigierte verfügbare Gebäude - verwende die tatsächlichen BuildingType Enums
    available_buildings = {}
    affordable_buildings = {}  # Neue: Gebäude die sich der aktuelle Spieler leisten kann
    
    for building_type, count in engine.board.available_buildings.items():
        if count > 0:  # Nur Gebäude mit verfügbarer Anzahl > 0 anzeigen
            building_key = building_type.value
            available_buildings[building_key] = count
            
            # Prüfe ob der aktuelle Spieler sich das Gebäude leisten kann
            if current_player and current_player.can_afford_building_cost(building_type):
                affordable_buildings[building_key] = True
            else:
                affordable_buildings[building_key] = False
    
    # Korrigierte Gebäude-Informationen für das Frontend
    building_details = {}
    for building_type in BuildingType:
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if building_def:
            # Serialisiere die Gebäude-Definition für JSON
            serialized_def = {
                'name': building_def.get('name', building_type.value),
                'type': building_def.get('type', 'industry')
            }
            
            # Serialisiere Kosten - vermeide Enum-Sortierung
            cost = building_def.get('cost', {})
            serialized_cost = {}
            for cost_key, cost_value in cost.items():
                if cost_key == 'exhausted_population':
                    # Serialisiere erschöpfte Bevölkerung
                    serialized_exhausted = {}
                    for pop_type, amount in cost_value.items():
                        pop_key = pop_type.value  # Konvertiere Enum zu String
                        serialized_exhausted[pop_key] = amount
                    serialized_cost[cost_key] = serialized_exhausted
                else:
                    # Normale Ressourcen-Kosten - konvertiere ResourceType zu String
                    cost_key_str = cost_key.value if hasattr(cost_key, 'value') else str(cost_key)
                    serialized_cost[cost_key_str] = cost_value
            
            serialized_def['cost'] = serialized_cost
            
            # Serialisiere andere Attribute
            if 'produces' in building_def:
                produces = building_def['produces']
                serialized_def['produces'] = produces.value if hasattr(produces, 'value') else str(produces)
            
            if 'worker' in building_def:
                worker = building_def['worker']
                serialized_def['worker'] = worker.value if hasattr(worker, 'value') else str(worker)
            
            building_details[building_type.value] = serialized_def
    
    return {
        'currentPlayer': engine.current_player_idx,
        'round': engine.round_number,
        'phase': engine.phase.value,
        'players': players,
        'availableBuildings': available_buildings,
        'affordableBuildings': affordable_buildings,  # Neue: Information über leistbare Gebäude
        'buildingDetails': building_details
    }
def debug_building_costs(player, building_type):
    """Gibt detaillierte Debug-Informationen zu Gebäude-Kosten aus"""
    building_def = BUILDING_DEFINITIONS.get(building_type)
    if not building_def:
        return "Unbekanntes Gebäude"
    
    cost = building_def.get('cost', {})
    debug_info = []
    
    debug_info.append(f"Gebäude: {building_def.get('name', building_type.value)}")
    debug_info.append(f"Kosten: {cost}")
    
    # Prüfe normale Ressourcen
    for resource, amount in cost.items():
        if resource == 'exhausted_population':
            continue
        
        can_produce = player.can_produce_resource(resource, amount)
        debug_info.append(f"  {amount} {resource.value}: {'✓' if can_produce else '✗'}")

def _can_build_anything(player):
    """Prüft ob Spieler etwas bauen kann"""
    try:
        from anno1800.utils.constants import BuildingType, BUILDING_DEFINITIONS
        
        for building_type in BuildingType:
            building_def = BUILDING_DEFINITIONS.get(building_type)
            if building_def and player.can_afford_building_cost(building_type):
                return True
        return False
    except Exception as e:
        logger.error(f"Fehler in _can_build_anything: {e}")
        return False

def _can_explore_old_world(player):
    """Prüft ob Alte Welt erkundet werden kann"""
    try:
        from anno1800.utils.constants import EXPLORATION_COSTS
        
        if len(player.old_world_islands) >= 4:
            return False
        needed = EXPLORATION_COSTS['old_world'][min(len(player.old_world_islands), 3)]
        return (player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen) >= needed
    except Exception as e:
        logger.error(f"Fehler in _can_explore_old_world: {e}")
        return False

def _can_explore_new_world(player):
    """Prüft ob Neue Welt erkundet werden kann"""
    try:
        from anno1800.utils.constants import EXPLORATION_COSTS
        
        if len(player.new_world_islands) >= 4:
            return False
        needed = EXPLORATION_COSTS['new_world'][min(len(player.new_world_islands), 3)]
        return (player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen) >= needed
    except Exception as e:
        logger.error(f"Fehler in _can_explore_new_world: {e}")
        return False

def _can_expedition(player):
    """Prüft ob Expedition durchgeführt werden kann"""
    try:
        return (player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen) >= 2
    except Exception as e:
        logger.error(f"Fehler in _can_expedition: {e}")
        return False

def get_data_collector():
    if game_instance['data_collector'] is None:
        game_instance['data_collector'] = OptimizedDataCollector()
    return game_instance['data_collector']

def get_action_type_enum(action_string):
    """Konvertiert Action-String zu ActionType Enum"""
    action_map = {
        'build': ActionType.AUSBAUEN,
        'playCard': ActionType.BEVÖLKERUNG_AUSSPIELEN,
        'exchange': ActionType.KARTEN_AUSTAUSCHEN,
        'workforce': ActionType.ARBEITSKRAFT_ERHÖHEN,
        'upgrade': ActionType.AUFSTEIGEN,
        'oldWorld': ActionType.ALTE_WELT_ERSCHLIESSEN,
        'newWorld': ActionType.NEUE_WELT_ERKUNDEN,
        'expedition': ActionType.EXPEDITION,
        'festival': ActionType.STADTFEST
    }
    return action_map.get(action_string, ActionType.STADTFEST)

def get_rule_based_suggestion():
    """Gibt einen regelbasierten Vorschlag zurück"""
    if not game_instance['engine']:
        return jsonify({'success': False})
    
    current_player = game_instance['engine'].get_current_player()
    round_num = game_instance['engine'].round_number
    
    if round_num <= 5:
        return jsonify({
            'success': True,
            'action': 'build',
            'confidence': 75,
            'reasoning': 'Frühe Expansion schafft Produktionsvorteile'
        })
    elif len(current_player.hand_cards) > 12:
        return jsonify({
            'success': True,
            'action': 'playCard',
            'confidence': 80,
            'reasoning': 'Viele Handkarten sollten ausgespielt werden'
        })
    else:
        return jsonify({
            'success': True,
            'action': 'workforce',
            'confidence': 70,
            'reasoning': 'Mehr Arbeiter ermöglichen bessere Produktion'
        })
    
def get_building_affordability(player, building_type):
    """Prüft detailliert ob Spieler sich ein Gebäude leisten kann"""
    try:
        building_def = BUILDING_DEFINITIONS.get(building_type)
        if not building_def:
            return False, "Unbekanntes Gebäude"
        
        cost = building_def.get('cost', {})
        missing_resources = []
        
        # Prüfe normale Ressourcenkosten
        for resource, amount in cost.items():
            if resource == 'exhausted_population':
                continue  # Separat prüfen
            
            if not player.can_produce_resource(resource, amount):
                missing_resources.append(f"{amount} {resource.value}")
        
        # Prüfe erschöpfte Bevölkerung
        exhausted_pop = cost.get('exhausted_population', {})
        for pop_type, amount in exhausted_pop.items():
            if player.get_available_population(pop_type) < amount:
                missing_resources.append(f"{amount} {pop_type.value}")
        
        if missing_resources:
            return False, f"Fehlend: {', '.join(missing_resources)}"
        else:
            return True, "Kann gebaut werden"
            
    except Exception as e:
        logger.error(f"Fehler bei Gebäude-Prüfung: {e}")
        return False, f"Fehler bei Prüfung: {str(e)}"

def generate_reasoning(action, player, engine):
    """Generiert Begründung für Aktion"""
    reasons = {
        ActionType.AUSBAUEN: "Neue Gebäude erweitern die Produktionskapazität",
        ActionType.BEVÖLKERUNG_AUSSPIELEN: f"Mit {len(player.hand_cards)} Handkarten Punkte sammeln",
        ActionType.ARBEITSKRAFT_ERHÖHEN: "Mehr Bevölkerung für bessere Produktion",
        ActionType.AUFSTEIGEN: "Bevölkerungs-Upgrade für höhere Effizienz",
        ActionType.ALTE_WELT_ERSCHLIESSEN: "Neue Inseln für zusätzliche Ressourcen",
        ActionType.NEUE_WELT_ERKUNDEN: "Zugang zu exklusiven Neue-Welt-Ressourcen",
        ActionType.EXPEDITION: "Expeditionskarten für zusätzliche Punkte",
        ActionType.STADTFEST: "Zurücksetzen erschöpfter Arbeiter und Plättchen"
    }
    return reasons.get(action, "Strategisch sinnvolle Aktion")

def collect_training_data(action):
    """Sammelt Trainingsdaten für ML-Modell mit dem Data Collector"""
    try:
        if not game_instance['engine']:
            return
        
        current_player = game_instance['engine'].get_current_player()
        data_collector = get_data_collector()
        
        # Extrahiere Features
        features = extract_features_for_ml(game_instance['engine'], current_player)
        
        # Sammle Daten mit dem Data Collector
        success = data_collector.collect_move(
            game_state=game_instance['engine'],
            player=current_player,
            action=action.action_type.name,
            features=features
        )
        
        if success:
            logger.debug(f"Training data collected: {action.action_type.name}")
        else:
            logger.warning("Failed to collect training data")
            
    except Exception as e:
        logger.error(f"Error collecting training data: {e}")

def extract_features_for_ml(game: GameEngine, player: PlayerState) -> np.ndarray:
    """Extrahiert Features für ML-Training"""
    try:
        features = []
        
        # Spieler-Features
        features.extend([
            player.gold,
            player.handels_plättchen - player.erschöpfte_handels_plättchen,  # verfügbare Handelsplättchen
            player.erkundungs_plättchen - player.erschöpfte_erkundungs_plättchen,  # verfügbare Erkundungsplättchen
            len(player.hand_cards),
            len(player.played_cards),
            len(player.buildings),
            sum(player.population.values()),  # Gesamtbevölkerung
            len(player.old_world_islands) + len(player.new_world_islands),  # Gesamtinseln
            game.round_number,
            len([p for p in game.players if p.final_score > player.final_score])  # Rang
        ])
        
        # Bevölkerungsverteilung
        for pop_type in [PopulationType.BAUER, PopulationType.ARBEITER, 
                         PopulationType.HANDWERKER, PopulationType.INGENIEUR, PopulationType.INVESTOR]:
            features.append(player.population.get(pop_type, 0))
        
        return np.array(features, dtype=np.float32)
        
    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        return np.array([])

def simulate_single_game():
    """Simuliert ein einzelnes Spiel und sammelt Trainingsdaten"""
    try:
        # Erstelle eine temporäre Game Engine für Simulation
        sim_engine = GameEngine(4)
        strategies = ['aggressive', 'balanced', 'economic', 'explorer']
        player_names = [f"Sim_{s}" for s in strategies]
        sim_engine.setup_game(player_names, strategies)
        
        # Starte Datensammlung für dieses Spiel
        data_collector = get_data_collector()
        data_collector.start_game_collection()
        
        # Simuliere das Spiel (vereinfacht)
        actions_taken = []
        max_rounds = random.randint(10, 25)
        
        for round_num in range(1, max_rounds + 1):
            sim_engine.round_number = round_num
            
            for player_idx in range(4):
                player = sim_engine.players[player_idx]
                sim_engine.current_player_idx = player_idx
                
                # KI entscheidet Aktion
                if player.strategy != 'human':
                    ai_strategy = AIStrategy(player.strategy)
                    action = ai_strategy.decide_action(sim_engine, player)
                    
                    # Extrahiere Features und sammle Daten
                    features = extract_features_for_ml(sim_engine, player)
                    data_collector.collect_move(sim_engine, player, action.action_type.name, features)
                    
                    actions_taken.append({
                        'player': player.name,
                        'action': action.action_type.name,
                        'round': round_num
                    })
        
        # Bestimme Gewinner (vereinfacht)
        winner_idx = random.randint(0, 3)
        winner = sim_engine.players[winner_idx]
        
        # Beende Datensammlung für dieses Spiel
        result = {
            'winner': winner.name,
            'winner_strategy': winner.strategy,
            'players': [
                {
                    'name': p.name,
                    'strategy': p.strategy,
                    'score': random.randint(10, 50),
                    'rank': random.randint(1, 4)
                } for p in sim_engine.players
            ],
            'rounds_played': max_rounds
        }
        
        data_collector.collect_game_data(sim_engine, result)
        
        return {
            'winner': winner.name,
            'winner_strategy': winner.strategy,
            'actions': actions_taken,
            'final_scores': {p.name: random.randint(10, 50) for p in sim_engine.players},
            'rounds_played': max_rounds
        }
        
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        return {
            'winner': 'Sim_balanced',
            'winner_strategy': 'balanced',
            'actions': [],
            'final_scores': {},
            'rounds_played': 0
        }
    
@app.route('/api/debug/data_stats', methods=['GET'])
def debug_data_stats():
    """Zeigt Statistiken des Data Collectors"""
    try:
        data_collector = get_data_collector()
        stats = data_collector.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'has_sufficient_data': data_collector.has_sufficient_data(min_games=2),
            'data_directory': str(data_collector.data_dir)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/generate_training_data', methods=['POST'])
def generate_training_data():
    """Generiert Test-Trainingsdaten"""
    try:
        data = request.json
        num_samples = data.get('samples', 20)  # Reduziert für Testzwecke
        
        data_collector = get_data_collector()
        
        # Generiere Testdaten
        actions = ['AUSBAUEN', 'BEVÖLKERUNG_AUSSPIELEN', 'ARBEITSKRAFT_ERHÖHEN', 
                  'AUFSTEIGEN', 'ALTE_WELT_ERSCHLIESSEN', 'EXPEDITION']
        
        for i in range(num_samples):
            features = np.random.rand(15) * 10  # 15 Features mit zufälligen Werten
            action = random.choice(actions)
            
            # Simuliere einen Spielzug
            data_collector.collect_move(
                game_state=None,  # Für Testdaten nicht benötigt
                player=None,
                action=action,
                features=features
            )
        
        stats = data_collector.get_statistics()
        
        return jsonify({
            'success': True,
            'message': f'{num_samples} Testdaten generiert',
            'total_moves': stats['total_moves'],
            'has_sufficient_data': data_collector.has_sufficient_data(min_games=2)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
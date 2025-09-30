# backend_server.py
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime

# Füge das Projektverzeichnis zum Python-Path hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anno1800.game.engine import GameEngine, GameAction, GamePhase
from anno1800.game.player import PlayerState
from anno1800.ai.strategy import AIStrategy
from anno1800.ml.model import Anno1800MLModel
from anno1800.utils.constants import ActionType, PopulationType, BuildingType

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globale Spielinstanz
game_instance = {
    'engine': None,
    'ai_strategies': {},
    'ml_model': Anno1800MLModel(),
    'action_history': [],
    'training_data': []
}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'running', 'timestamp': datetime.now().isoformat()})

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
        
        logger.info(f"Neues Spiel gestartet mit {num_players} Spielern")
        
        return jsonify({
            'success': True,
            'game_state': serialize_game_state()
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Starten eines neuen Spiels: {e}")
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
        
        # Konvertiere Action-Type String zu Enum
        action_type_enum = get_action_type_enum(action_type)
        
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
        if success and game_instance['ml_model']:
            collect_training_data(action)
        
        return jsonify({
            'success': success,
            'game_state': serialize_game_state(),
            'message': f"{current_player.name} führt {action_type} aus"
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Ausführen der Aktion: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai_turn', methods=['POST'])
def ai_turn():
    """Führt einen KI-Zug aus"""
    try:
        if not game_instance['engine']:
            return jsonify({'success': False, 'error': 'Kein Spiel gestartet'}), 400
        
        current_player = game_instance['engine'].get_current_player()
        
        if current_player.id not in game_instance['ai_strategies']:
            return jsonify({'success': False, 'error': 'Kein KI-Spieler am Zug'}), 400
        
        ai_strategy = game_instance['ai_strategies'][current_player.id]
        action = ai_strategy.decide_action(game_instance['engine'], current_player)
        
        success = game_instance['engine'].execute_action(action)
        
        return jsonify({
            'success': success,
            'game_state': serialize_game_state(),
            'action_taken': action.action_type.value,
            'message': f"{current_player.name} (KI) führt {action.action_type.value} aus"
        })
    
    except Exception as e:
        logger.error(f"Fehler beim KI-Zug: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ml_suggestion', methods=['GET'])
def get_ml_suggestion():
    """Gibt einen ML-basierten Vorschlag für die beste Aktion zurück"""
    try:
        if not game_instance['engine']:
            return jsonify({'success': False, 'error': 'Kein Spiel gestartet'}), 400
        
        if not game_instance['ml_model'].is_trained:
            # Fallback auf regelbasierte Vorschläge
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

@app.route('/api/run_simulation', methods=['POST'])
def run_simulation():
    """Führt eine Batch-Simulation aus"""
    try:
        data = request.json
        num_games = data.get('num_games', 100)
        
        results = {
            'games_played': 0,
            'data_points': 0,
            'strategy_wins': {}
        }
        
        for i in range(num_games):
            # Simuliere ein Spiel
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
        if len(game_instance['training_data']) < 100:
            return jsonify({
                'success': False, 
                'error': f"Nicht genug Trainingsdaten: {len(game_instance['training_data'])}/100"
            }), 400
        
        # Trainiere Modell
        result = game_instance['ml_model'].train(game_instance['training_data'])
        
        # Speichere Modell
        os.makedirs('data/models', exist_ok=True)
        game_instance['ml_model'].save('data/models/latest_model.pkl')
        
        return jsonify({
            'success': True,
            'accuracy': result['accuracy'],
            'training_samples': result['training_samples'],
            'test_samples': result['test_samples']
        })
    
    except Exception as e:
        logger.error(f"Fehler beim Training: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/action_history', methods=['GET'])
def get_action_history():
    """Gibt die Aktionshistorie zurück"""
    return jsonify({
        'success': True,
        'history': game_instance['action_history'][-10:]  # Letzte 10 Aktionen
    })

# Hilfsfunktionen
def serialize_game_state():
    """Serialisiert den Spielzustand für die API"""
    if not game_instance['engine']:
        return None
    
    engine = game_instance['engine']
    current_player = engine.get_current_player()
    
    players = []
    for player in engine.players:
        players.append({
            'id': player.id,
            'name': player.name,
            'strategy': player.strategy,
            'gold': player.gold,
            'handCards': len(player.hand_cards),
            'playedCards': len(player.played_cards),
            'buildings': [b.value for b in player.buildings],
            'population': {k.value: v for k, v in player.population.items()},
            'exhaustedPopulation': {k.value: v for k, v in player.exhausted_population.items()},
            'tradeTokens': player.handels_plättchen,
            'explorationTokens': player.erkundungs_plättchen,
            'exhaustedTrade': player.erschöpfte_handels_plättchen,
            'exhaustedExploration': player.erschöpfte_erkundungs_plättchen,
            'oldWorldIslands': len(player.old_world_islands),
            'newWorldIslands': len(player.new_world_islands),
            'expeditionCards': len(player.expedition_cards),
            'score': player.calculate_score()
        })
    
    available_actions = []
    if current_player:
        for action in engine.get_available_actions(current_player):
            available_actions.append(action.value)
    
    return {
        'currentPlayer': engine.current_player_idx,
        'round': engine.round_number,
        'phase': engine.phase.value,
        'gameEndTriggered': engine.game_end_triggered,
        'players': players,
        'availableActions': available_actions
    }

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
    """Gibt einen regelbasierten Vorschlag zurück wenn ML nicht verfügbar"""
    if not game_instance['engine']:
        return jsonify({'success': False})
    
    current_player = game_instance['engine'].get_current_player()
    round_num = game_instance['engine'].round_number
    
    # Einfache Heuristiken
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
            'reasoning': 'Viele Handkarten sollten ausgespielt werden für Punkte'
        })
    else:
        return jsonify({
            'success': True,
            'action': 'workforce',
            'confidence': 70,
            'reasoning': 'Mehr Arbeiter ermöglichen bessere Produktion'
        })

def generate_reasoning(action, player, engine):
    """Generiert eine Begründung für die vorgeschlagene Aktion"""
    reasons = {
        ActionType.AUSBAUEN: "Neue Gebäude erweitern die Produktionskapazität",
        ActionType.BEVÖLKERUNG_AUSSPIELEN: f"Mit {len(player.hand_cards)} Handkarten sollten Karten für Punkte gespielt werden",
        ActionType.ARBEITSKRAFT_ERHÖHEN: "Mehr Bevölkerung ermöglicht bessere Ressourcenproduktion",
        ActionType.AUFSTEIGEN: "Höhere Bevölkerungsstufen produzieren wertvollere Güter",
        ActionType.ALTE_WELT_ERSCHLIESSEN: "Neue Inseln bieten zusätzlichen Bauplatz",
        ActionType.NEUE_WELT_ERKUNDEN: "Die Neue Welt bietet exklusive Ressourcen",
        ActionType.EXPEDITION: "Expeditionen bringen wertvolle Punkte",
        ActionType.STADTFEST: "Arbeiter zurücksetzen für neue Produktionsrunde"
    }
    
    # Füge Kontext hinzu
    if engine.round_number > 15:
        return reasons.get(action, "") + " - Im Endspiel besonders wichtig"
    elif engine.round_number < 5:
        return reasons.get(action, "") + " - Gute Basis für weiteren Spielverlauf"
    
    return reasons.get(action, "Strategisch sinnvolle Aktion")

def collect_training_data(action):
    """Sammelt Trainingsdaten aus erfolgreichen Aktionen"""
    if not game_instance['engine']:
        return
    
    try:
        player = game_instance['engine'].players[action.player_id]
        
        # Vereinfachte Features für Training
        training_example = {
            'features': [
                player.gold,
                len(player.hand_cards),
                len(player.buildings),
                len(player.old_world_islands) + len(player.new_world_islands),
                game_instance['engine'].round_number,
                sum(game_instance['engine'].board.available_buildings.values()),
                len(game_instance['engine'].board.old_world_islands) + 
                len(game_instance['engine'].board.new_world_islands),
                player.calculate_score()
            ],
            'action': action.action_type.name,
            'strategy': player.strategy,
            'round': game_instance['engine'].round_number
        }
        
        game_instance['training_data'].append(training_example)
        
    except Exception as e:
        logger.error(f"Fehler beim Sammeln von Trainingsdaten: {e}")

def simulate_single_game():
    """Simuliert ein einzelnes Spiel für Training"""
    # Erstelle temporäre Game Engine
    sim_engine = GameEngine(4)
    strategies = ['aggressive', 'balanced', 'economic', 'explorer']
    player_names = [f"Sim_{s}" for s in strategies]
    sim_engine.setup_game(player_names, strategies)
    
    # Erstelle KI-Strategien
    ai_strategies = {}
    for i, strategy in enumerate(strategies):
        ai_strategies[i] = AIStrategy(strategy)
    
    actions_taken = []
    max_rounds = 50
    
    # Spiel-Loop
    while sim_engine.phase != GamePhase.ENDED and sim_engine.round_number < max_rounds:
        current_player = sim_engine.get_current_player()
        ai = ai_strategies[current_player.id]
        action = ai.decide_action(sim_engine, current_player)
        
        success = sim_engine.execute_action(action)
        if success:
            actions_taken.append({
                'player': current_player.name,
                'action': action.action_type.value,
                'round': sim_engine.round_number
            })
    
    # Bestimme Gewinner
    scores = {p.name: p.calculate_score() for p in sim_engine.players}
    winner = max(scores, key=scores.get)
    winner_strategy = next(p.strategy for p in sim_engine.players if p.name == winner)
    
    return {
        'winner': winner,
        'winner_strategy': winner_strategy,
        'actions': actions_taken,
        'final_scores': scores
    }

# Lade ML-Modell beim Start
def load_ml_model():
    """Lädt ein gespeichertes ML-Modell falls vorhanden"""
    model_path = 'data/models/latest_model.pkl'
    if os.path.exists(model_path):
        try:
            game_instance['ml_model'].load(model_path)
            logger.info("ML-Modell erfolgreich geladen")
        except Exception as e:
            logger.error(f"Fehler beim Laden des ML-Modells: {e}")

# Static file serving für React Frontend (wenn gebaut)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    load_ml_model()
    app.run(debug=True, host='0.0.0.0', port=5000)
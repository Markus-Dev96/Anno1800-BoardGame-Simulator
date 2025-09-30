# anno1800/ml/model.py
"""
Machine Learning Modell für Zugvorhersagen
Angepasst an die korrekten Brettspiel-Attributnamen
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import pickle
import os
from datetime import datetime
import logging

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score

try:
    import tensorflow as tf
    from tensorflow import keras
    from keras import models
    from keras import layers
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logging.warning("TensorFlow nicht verfügbar - nutze sklearn")

from anno1800.utils.constants import ActionType, PopulationType, BuildingType
from anno1800.game.engine import GameEngine
from anno1800.game.player import PlayerState

logger = logging.getLogger(__name__)

class FeatureExtractor:
    """Extrahiert Features aus Spielzustand"""
    
    @staticmethod
    def extract_features(game: GameEngine, player: PlayerState) -> np.ndarray:
        """Extrahiert Feature-Vektor aus aktuellem Spielzustand"""
        features = []
        
        # Spieler-Features (14)
        features.extend([
            player.gold,
            player.handels_plättchen,
            player.erkundungs_plättchen,
            player.erschöpfte_handels_plättchen,
            player.erschöpfte_erkundungs_plättchen,
            len(player.hand_cards),
            len(player.played_cards),
            len(player.buildings),
            len(player.old_world_islands),
            len(player.new_world_islands),
            len(player.expedition_cards),
            sum(player.ships.values()),
            player.final_score,
            int(player.has_fireworks),
        ])
        
        # Bevölkerung (10) - 5 Typen * 2 (verfügbar + erschöpft)
        for pop_type in PopulationType:
            features.append(player.population.get(pop_type, 0))
            features.append(player.exhausted_population.get(pop_type, 0))
        
        # Spielzustand (10)
        features.extend([
            game.round_number,
            game.num_players,
            game.current_player_idx,
            int(game.game_end_triggered),
            int(game.phase.value == 'main_game'),
            int(game.phase.value == 'final_round'),
            len(game.board.old_world_islands),
            len(game.board.new_world_islands),
            len(game.board.expedition_cards),
            len(game.action_history)
        ])
        
        # Relative Position (5)
        player_scores = [p.final_score for p in game.players]
        features.extend([
            player.final_score - np.mean(player_scores) if player_scores else 0,
            player.final_score - max(player_scores) if player_scores else 0,
            player.final_score - min(player_scores) if player_scores else 0,
            game.players.index(player) + 1,  # Position
            len([p for p in game.players if p.final_score > player.final_score]) + 1  # Rang
        ])
        
        # Verfügbare Aktionen (9) - Anzahl der deutschen ActionTypes
        available_actions = game.get_available_actions(player)
        action_types = [
            ActionType.AUSBAUEN,
            ActionType.BEVÖLKERUNG_AUSSPIELEN,
            ActionType.KARTEN_AUSTAUSCHEN,
            ActionType.ARBEITSKRAFT_ERHÖHEN,
            ActionType.AUFSTEIGEN,
            ActionType.ALTE_WELT_ERSCHLIESSEN,
            ActionType.NEUE_WELT_ERKUNDEN,
            ActionType.EXPEDITION,
            ActionType.STADTFEST
        ]
        for action_type in action_types:
            features.append(1 if action_type in available_actions else 0)
        
        # Gebäude-Besitz (wichtigste 10) - mit korrekten deutschen BuildingTypes
        important_buildings = [
            BuildingType.LAGERHAUS,
            BuildingType.STAHLWERK,
            BuildingType.BRAUEREI,
            BuildingType.KANONENGIESEREI,
            BuildingType.WERFT_1,
            BuildingType.WERFT_2,
            BuildingType.SEGELMACHEREI,
            BuildingType.ZIEGELEI,
            BuildingType.SÄGEWERK,
            BuildingType.GLASHÜTTE
        ]
        for building in important_buildings:
            features.append(1 if building in player.buildings else 0)
        
        return np.array(features)

class Anno1800MLModel:
    """Machine Learning Modell für Anno 1800"""
    
    def __init__(self, model_type: str = 'random_forest'):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_extractor = FeatureExtractor()
        self.is_trained = False
        self.expected_feature_dim = 8  # Wird beim Training gesetzt
        
        # Trainingshistorie
        self.training_history = []
        self.feature_importance = None
        
    def create_model(self, input_dim: int, output_dim: int):
        """Erstellt das ML-Modell"""
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=20,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boost':
            self.model = GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=10,
                random_state=42
            )
        elif self.model_type == 'neural_network':
            self.model = MLPClassifier(
                hidden_layer_sizes=(128, 256, 256, 128),
                activation='relu',
                solver='adam',
                learning_rate='adaptive',
                max_iter=500,
                random_state=42
            )
        elif self.model_type == 'deep_learning' and TF_AVAILABLE:
            self.model = self._create_deep_model(input_dim, output_dim)
        else:
            raise ValueError(f"Unbekannter Modelltyp: {self.model_type}")
    
    def _create_deep_model(self, input_dim: int, output_dim: int):
        """Erstellt Deep Learning Modell mit TensorFlow"""
        model = models.Sequential([
            layers.Dense(128, activation='relu', input_shape=(input_dim,)),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            layers.Dense(output_dim, activation='softmax')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train(self, training_data: List[Dict]) -> Dict:
        """Trainiert das Modell"""
        if not training_data:
            raise ValueError("Keine Trainingsdaten vorhanden")
        
        # Convert training data to the expected format
        X, y = self._prepare_training_data(training_data)
        
        if len(X) == 0 or len(y) == 0:
            raise ValueError("Keine gültigen Trainingsdaten nach der Vorverarbeitung")
        
        # Speichere die erwartete Feature-Dimension
        self.expected_feature_dim = X.shape[1]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        if len(X_train) == 0:
            raise ValueError("Keine Trainingsdaten nach dem Split")
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Encode labels mit den korrekten deutschen ActionType-Namen
        # Stelle sicher, dass alle möglichen Labels bekannt sind
        all_actions = [
            'AUSBAUEN', 'BEVÖLKERUNG_AUSSPIELEN', 'KARTEN_AUSTAUSCHEN',
            'ARBEITSKRAFT_ERHÖHEN', 'AUFSTEIGEN', 'ALTE_WELT_ERSCHLIESSEN',
            'NEUE_WELT_ERKUNDEN', 'EXPEDITION', 'STADTFEST'
        ]
        
        # Füge alle möglichen Actions zum Label Encoder hinzu
        unique_labels = list(set(y))
        for action in all_actions:
            if action not in unique_labels:
                unique_labels.append(action)
        
        self.label_encoder.fit(unique_labels)
        y_train_encoded = self.label_encoder.transform(y_train)
        y_test_encoded = self.label_encoder.transform(y_test)
        
        # Create model
        self.create_model(X_train_scaled.shape[1], len(unique_labels))
        
        # Train model
        if self.model_type == 'deep_learning' and TF_AVAILABLE:
            history = self.model.fit(
                X_train_scaled, y_train_encoded,
                epochs=50,
                batch_size=32,
                validation_split=0.2,
                verbose=0
            )
            accuracy = self.model.evaluate(X_test_scaled, y_test_encoded, verbose=0)[1]
        else:
            self.model.fit(X_train_scaled, y_train_encoded)
            accuracy = self.model.score(X_test_scaled, y_test_encoded)
        
        self.is_trained = True
        
        logger.info(f"Modell trainiert: {self.model_type}, Genauigkeit: {accuracy:.3f}, Features: {self.expected_feature_dim}")
        
        return {
            'accuracy': accuracy,
            'model_type': self.model_type,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'feature_dimension': self.expected_feature_dim
        }
    
    def _adjust_feature_dimension(self, features: np.ndarray) -> np.ndarray:
        """Passt Feature-Dimension an erwartete Größe an"""
        current_dim = len(features)
        expected_dim = self.expected_feature_dim

        if current_dim < expected_dim:
            # Füge Nullen hinzu
            adjusted = np.zeros(expected_dim)
            adjusted[:current_dim] = features
            return adjusted
        elif current_dim > expected_dim:
            # Schneide ab
            return features[:expected_dim]
        else:
            return features

    def _prepare_training_data(self, training_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Bereitet Trainingsdaten vor"""
        X = []
        y = []
        
        for example in training_data:
            try:
                features = example.get('features')
                action = example.get('action')
                
                if not features or not action:
                    continue
                
                # Stelle sicher, dass Features die richtige Länge haben
                if isinstance(features, list) and len(features) >= 5:
                    # Verwende die Features wie sie sind (sollten 7-8 Basis-Features sein)
                    X.append(features[:8] if len(features) > 8 else features + [0] * (8 - len(features)))
                    
                    # Konvertiere alte englische Action-Namen zu deutschen wenn nötig
                    action_mapping = {
                        'BUILD': 'AUSBAUEN',
                        'PLAY_CARD': 'BEVÖLKERUNG_AUSSPIELEN',
                        'EXCHANGE_CARDS': 'KARTEN_AUSTAUSCHEN',
                        'INCREASE_WORKFORCE': 'ARBEITSKRAFT_ERHÖHEN',
                        'UPGRADE_POPULATION': 'AUFSTEIGEN',
                        'EXPLORE_OLD_WORLD': 'ALTE_WELT_ERSCHLIESSEN',
                        'EXPLORE_NEW_WORLD': 'NEUE_WELT_ERKUNDEN',
                        'EXPEDITION': 'EXPEDITION',
                        'CITY_FESTIVAL': 'STADTFEST'
                    }
                    
                    # Mappe Action-Namen wenn nötig
                    if action in action_mapping:
                        action = action_mapping[action]
                    
                    y.append(action)
                    
            except Exception as e:
                logger.warning(f"Konnte Trainingsbeispiel nicht verarbeiten: {e}")
                continue
        
        if len(X) == 0:
            logger.error("Keine gültigen Trainingsdaten gefunden")
            return np.array([]), np.array([])
        
        return np.array(X), np.array(y)

    def predict(self, game: GameEngine, player: PlayerState) -> Tuple[Optional[ActionType], float]:
        """Sagt beste Aktion voraus"""
        if not self.is_trained:
            logger.warning("Modell ist nicht trainiert")
            return None, 0.0
        
        try:
            # Extract features
            features = self.feature_extractor.extract_features(game, player)
            
            # Stelle sicher, dass Features die richtige Dimension haben
            if len(features) != self.expected_feature_dim:
                features = self._adjust_feature_dimension(features)
            
            features_scaled = self.scaler.transform([features])
            
            # Predict
            if self.model_type == 'deep_learning' and TF_AVAILABLE:
                probabilities = self.model.predict(features_scaled, verbose=0)[0]
            else:
                probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Get available actions
            available_actions = game.get_available_actions(player)
            
            # Find best available action
            best_action = None
            best_prob = 0
            
            for i, prob in enumerate(probabilities):
                if i < len(self.label_encoder.classes_):
                    action_name = self.label_encoder.classes_[i]
                    
                    # Versuche ActionType zu finden
                    try:
                        # Direkt über den Namen
                        action_type = ActionType[action_name]
                    except KeyError:
                        # Versuche über den value
                        action_type = None
                        for at in ActionType:
                            if at.name == action_name:
                                action_type = at
                                break
                    
                    if action_type and action_type in available_actions and prob > best_prob:
                        best_action = action_type
                        best_prob = prob
            
            return best_action, best_prob
            
        except Exception as e:
            logger.error(f"Fehler bei Vorhersage: {e}")
            return None, 0.0
    
    def save(self, filepath: str):
        """Speichert das Modell"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            model_data = {
                'model_type': self.model_type,
                'scaler': self.scaler,
                'label_encoder': self.label_encoder,
                'is_trained': self.is_trained,
                'feature_importance': self.feature_importance,
                'expected_feature_dim': self.expected_feature_dim
            }
            
            if self.model_type == 'deep_learning' and TF_AVAILABLE:
                # Save TF model separately
                tf_path = filepath.replace('.pkl', '_tf_model')
                self.model.save(tf_path)
                model_data['tf_model_path'] = tf_path
            else:
                model_data['model'] = self.model
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Modell gespeichert: {filepath}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Modells: {e}")
    
    def load(self, filepath: str):
        """Lädt ein gespeichertes Modell"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model_type = model_data['model_type']
            self.scaler = model_data['scaler']
            self.label_encoder = model_data['label_encoder']
            self.is_trained = model_data['is_trained']
            self.feature_importance = model_data.get('feature_importance')
            self.expected_feature_dim = model_data.get('expected_feature_dim', 8)
            
            if self.model_type == 'deep_learning' and TF_AVAILABLE:
                tf_path = model_data.get('tf_model_path')
                if tf_path and os.path.exists(tf_path):
                    self.model = keras.models.load_model(tf_path)
            else:
                self.model = model_data.get('model')
            
            logger.info(f"Modell geladen: {filepath}")
        except Exception as e:
            logger.error(f"Fehler beim Laden des Modells: {e}")
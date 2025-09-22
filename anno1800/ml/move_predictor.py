# ml/move_predictor.py
import numpy as np
import pandas as pd
import pickle
import os
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
import logging

logger = logging.getLogger(__name__)

class MovePredictor:
    """Deep Learning basierter Zugvorhersager für Anno 1800"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.action_encoder = {}
        self.feature_names = []
        self.model_type = 'neural_network'  # 'random_forest', 'neural_network', 'deep_learning'
        self.is_trained = False
        
        # Deep Learning Model
        self.dl_model = None
        self.training_history = None
        
    def extract_features(self, game_state, player) -> np.ndarray:
        """Extrahiert Features aus dem aktuellen Spielzustand"""
        features = []
        
        # Spieler-Features
        features.extend([
            player.gold,
            player.trade_tokens,
            player.exploration_tokens,
            len(player.hand),
            len(player.played_cards),
            len(player.buildings),
            len(player.old_world_islands),
            len(player.new_world_islands),
            player.ships.get('trade', 0),
            player.ships.get('exploration', 0),
        ])
        
        # Bevölkerung
        for pop_type in ['farmer', 'worker', 'craftsman', 'engineer', 'investor']:
            features.append(player.population.get(pop_type, 0))
            features.append(player.exhausted_population.get(pop_type, 0))
        
        # Spiel-Features
        features.extend([
            game_state.round_number,
            game_state.num_players,
            1 if game_state.game_end_triggered else 0,
            self._get_player_position(game_state, player),
            self._calculate_point_difference(game_state, player),
        ])
        
        # Verfügbare Aktionen (One-Hot Encoding)
        available_actions = player.get_available_actions()
        action_types = ['build', 'play_card', 'exchange_cards', 'increase_workforce', 
                       'upgrade', 'explore_old_world', 'explore_new_world', 
                       'expedition', 'city_festival']
        
        for action in action_types:
            features.append(1 if action in available_actions else 0)
        
        # Ressourcen-Produktionsfähigkeit
        resources = ['wood', 'bricks', 'steel', 'goods', 'sails', 'weapons']
        for resource in resources:
            features.append(1 if player.can_produce_resource(resource, 1) else 0)
        
        # Kartentypen in Hand
        card_types = {'farmer_worker': 0, 'craftsman_engineer_investor': 0, 'new_world': 0}
        for card in player.hand:
            card_type = card.get('type', '')
            if card_type in card_types:
                card_types[card_type] += 1
        
        for count in card_types.values():
            features.append(count)
        
        return np.array(features)
    
    def _get_player_position(self, game_state, player) -> int:
        """Berechnet die aktuelle Position des Spielers (1-4)"""
        scores = [(p.final_score if hasattr(p, 'final_score') else 0, i) 
                  for i, p in enumerate(game_state.players)]
        scores.sort(reverse=True)
        
        player_idx = game_state.players.index(player)
        for pos, (_, idx) in enumerate(scores):
            if idx == player_idx:
                return pos + 1
        return 4
    
    def _calculate_point_difference(self, game_state, player) -> int:
        """Berechnet Punktedifferenz zum führenden Spieler"""
        max_score = max(getattr(p, 'final_score', 0) for p in game_state.players)
        player_score = getattr(player, 'final_score', 0)
        return max_score - player_score
    
    def prepare_training_data(self, game_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Bereitet Trainingsdaten aus Spielverläufen auf"""
        X = []
        y = []
        
        for game in game_data:
            for move in game['moves']:
                features = move['features']
                action = move['action']
                
                X.append(features)
                y.append(self._encode_action(action))
        
        return np.array(X), np.array(y)
    
    def _encode_action(self, action: str) -> int:
        """Kodiert eine Aktion zu einer Zahl"""
        if action not in self.action_encoder:
            self.action_encoder[action] = len(self.action_encoder)
        return self.action_encoder[action]
    
    def _decode_action(self, encoded: int) -> str:
        """Dekodiert eine Zahl zu einer Aktion"""
        for action, code in self.action_encoder.items():
            if code == encoded:
                return action
        return 'city_festival'  # Fallback
    
    def build_deep_learning_model(self, input_shape: int, num_classes: int):
        """Erstellt ein Deep Learning Modell mit TensorFlow/Keras"""
        model = models.Sequential([
            # Input Layer
            layers.Dense(256, activation='relu', input_shape=(input_shape,)),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            # Hidden Layers
            layers.Dense(512, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(512, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            # Output Layer
            layers.Dense(num_classes, activation='softmax')
        ])
        
        # Custom Learning Rate Schedule
        initial_learning_rate = 0.001
        lr_schedule = keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate,
            decay_steps=1000,
            decay_rate=0.96,
            staircase=True
        )
        
        # Compile Model
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=lr_schedule),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy', keras.metrics.TopKCategoricalAccuracy(k=3)]
        )
        
        return model
    
    def train(self, training_data: List[Dict], model_type: str = 'deep_learning') -> float:
        """Trainiert das Vorhersagemodell"""
        self.model_type = model_type
        
        # Prepare data
        X, y = self.prepare_training_data(training_data)
        
        if len(X) == 0:
            raise ValueError("Keine Trainingsdaten verfügbar")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info(f"Training mit {len(X_train)} Samples, {X.shape[1]} Features")
        
        if model_type == 'random_forest':
            return self._train_random_forest(X_train_scaled, y_train, X_test_scaled, y_test)
        elif model_type == 'neural_network':
            return self._train_sklearn_nn(X_train_scaled, y_train, X_test_scaled, y_test)
        else:  # deep_learning
            return self._train_deep_learning(X_train_scaled, y_train, X_test_scaled, y_test)
    
    def _train_random_forest(self, X_train, y_train, X_test, y_test) -> float:
        """Trainiert ein Random Forest Modell"""
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        accuracy = accuracy_score(y_test, self.model.predict(X_test))
        
        logger.info(f"Random Forest Accuracy: {accuracy:.3f}")
        self.is_trained = True
        return accuracy
    
    def _train_sklearn_nn(self, X_train, y_train, X_test, y_test) -> float:
        """Trainiert ein sklearn Neural Network"""
        self.model = MLPClassifier(
            hidden_layer_sizes=(256, 512, 512, 256, 128),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=32,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        accuracy = accuracy_score(y_test, self.model.predict(X_test))
        
        logger.info(f"Neural Network Accuracy: {accuracy:.3f}")
        self.is_trained = True
        return accuracy
    
    def _train_deep_learning(self, X_train, y_train, X_test, y_test) -> float:
        """Trainiert ein Deep Learning Modell mit TensorFlow"""
        num_classes = len(np.unique(y_train))
        input_shape = X_train.shape[1]
        
        # Build model
        self.dl_model = self.build_deep_learning_model(input_shape, num_classes)
        
        # Callbacks
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=20,
            restore_best_weights=True
        )
        
        reduce_lr = keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
            min_lr=0.00001
        )
        
        # Train
        self.training_history = self.dl_model.fit(
            X_train, y_train,
            epochs=100,
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stopping, reduce_lr],
            verbose=0
        )
        
        # Evaluate
        test_loss, test_acc, test_top3_acc = self.dl_model.evaluate(X_test, y_test, verbose=0)
        
        logger.info(f"Deep Learning Accuracy: {test_acc:.3f}, Top-3 Accuracy: {test_top3_acc:.3f}")
        self.is_trained = True
        self.model = self.dl_model  # Für predict Funktion
        
        return test_acc
    
    def predict_best_move(self, game_state, player) -> Optional[Dict]:
        """Sagt den besten Zug voraus"""
        if not self.is_trained:
            return None
        
        try:
            # Extract features
            features = self.extract_features(game_state, player)
            features_scaled = self.scaler.transform([features])
            
            # Get prediction probabilities
            if self.model_type == 'deep_learning' and self.dl_model:
                probs = self.dl_model.predict(features_scaled, verbose=0)[0]
            else:
                probs = self.model.predict_proba(features_scaled)[0]
            
            # Get available actions
            available_actions = player.get_available_actions()
            
            # Find best available action
            action_probs = []
            for action in available_actions:
                if action in self.action_encoder:
                    action_code = self.action_encoder[action]
                    if action_code < len(probs):
                        action_probs.append((action, probs[action_code]))
                    else:
                        action_probs.append((action, 0.0))
                else:
                    action_probs.append((action, 0.1))  # Default probability
            
            # Sort by probability
            action_probs.sort(key=lambda x: x[1], reverse=True)
            
            if action_probs:
                best_action = action_probs[0][0]
                confidence = action_probs[0][1]
                
                # Generate reasoning
                reasoning = self._generate_reasoning(
                    game_state, player, best_action, action_probs
                )
                
                return {
                    'action': best_action,
                    'confidence': confidence,
                    'alternatives': action_probs[:3],
                    'reasoning': reasoning
                }
                
        except Exception as e:
            logger.error(f"Fehler bei Zugvorhersage: {e}")
            return None
    
    def _generate_reasoning(self, game_state, player, action, action_probs) -> str:
        """Generiert eine Begründung für die Vorhersage"""
        reasoning = []
        
        # Hauptgrund
        if action == 'play_card':
            reasoning.append(f"Kartenaktion wird empfohlen, da {len(player.hand)} Karten auf der Hand sind.")
        elif action == 'build':
            reasoning.append("Bauaktion verstärkt die Produktionskapazität.")
        elif action == 'explore_old_world':
            reasoning.append("Alte-Welt-Erkundung erweitert den verfügbaren Bauplatz.")
        elif action == 'upgrade':
            reasoning.append("Arbeiter-Upgrade verbessert die Effizienz.")
        
        # Spielsituation
        if game_state.round_number > 15:
            reasoning.append("Im späten Spiel sollten Punkte maximiert werden.")
        elif game_state.round_number < 5:
            reasoning.append("Frühe Expansion schafft Vorteile.")
        
        # Konfidenz
        confidence = action_probs[0][1] * 100
        if confidence > 80:
            reasoning.append(f"Das Modell ist sehr sicher ({confidence:.0f}%).")
        elif confidence > 60:
            reasoning.append(f"Das Modell ist zuversichtlich ({confidence:.0f}%).")
        else:
            reasoning.append(f"Alternative Züge könnten ebenfalls gut sein ({confidence:.0f}%).")
        
        # Alternativen
        if len(action_probs) > 1:
            alt = action_probs[1][0]
            reasoning.append(f"Alternative: {alt} ({action_probs[1][1]*100:.0f}%)")
        
        return "\n".join(reasoning)
    
    def save_model(self, filename: str):
        """Speichert das trainierte Modell"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        model_data = {
            'model_type': self.model_type,
            'model': self.model if self.model_type != 'deep_learning' else None,
            'scaler': self.scaler,
            'action_encoder': self.action_encoder,
            'is_trained': self.is_trained
        }
        
        # Save sklearn models
        with open(filename, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Save deep learning model separately if exists
        if self.model_type == 'deep_learning' and self.dl_model:
            dl_filename = filename.replace('.pkl', '_dl.h5')
            self.dl_model.save(dl_filename)
            logger.info(f"Deep Learning Modell gespeichert: {dl_filename}")
    
    def load_model(self, filename: str) -> bool:
        """Lädt ein gespeichertes Modell"""
        try:
            with open(filename, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model_type = model_data['model_type']
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.action_encoder = model_data['action_encoder']
            self.is_trained = model_data['is_trained']
            
            # Load deep learning model if exists
            if self.model_type == 'deep_learning':
                dl_filename = filename.replace('.pkl', '_dl.h5')
                if os.path.exists(dl_filename):
                    self.dl_model = keras.models.load_model(dl_filename)
                    self.model = self.dl_model
                    logger.info(f"Deep Learning Modell geladen: {dl_filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Modells: {e}")
            return False
    
    def load_latest_model(self) -> bool:
        """Lädt das neueste gespeicherte Modell"""
        model_dir = 'models'
        if not os.path.exists(model_dir):
            return False
        
        # Find latest model file
        model_files = [f for f in os.listdir(model_dir) if f.endswith('.pkl')]
        if not model_files:
            return False
        
        latest_file = max(model_files, key=lambda f: os.path.getmtime(os.path.join(model_dir, f)))
        return self.load_model(os.path.join(model_dir, latest_file))
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { AlertCircle, Users, Anchor, Factory, Globe, Ship, Coins, Brain, Play, RotateCcw, ChevronRight, Home, Map, Package, TrendingUp, Award, Settings } from 'lucide-react';

const Anno1800BoardGame = () => {
  const [gameState, setGameState] = useState({
    currentPlayer: 0,
    round: 1,
    phase: 'main',
    players: [
      { 
        name: 'Spieler 1', 
        strategy: 'human',
        gold: 0,
        handCards: 9,
        playedCards: 0,
        buildings: [],
        population: { farmer: 4, worker: 3, craftsman: 2, engineer: 0, investor: 0 },
        exhaustedPopulation: { farmer: 0, worker: 0, craftsman: 0, engineer: 0, investor: 0 },
        tradeTokens: 2,
        explorationTokens: 1,
        exhaustedTrade: 0,
        exhaustedExploration: 0,
        oldWorldIslands: 0,
        newWorldIslands: 0,
        expeditionCards: 0
      },
      { 
        name: 'KI - Balanced', 
        strategy: 'balanced',
        gold: 1,
        handCards: 9,
        playedCards: 0,
        buildings: [],
        population: { farmer: 4, worker: 3, craftsman: 2, engineer: 0, investor: 0 },
        exhaustedPopulation: { farmer: 0, worker: 0, craftsman: 0, engineer: 0, investor: 0 },
        tradeTokens: 2,
        explorationTokens: 1,
        exhaustedTrade: 0,
        exhaustedExploration: 0,
        oldWorldIslands: 0,
        newWorldIslands: 0,
        expeditionCards: 0
      },
      { 
        name: 'KI - Economic', 
        strategy: 'economic',
        gold: 2,
        handCards: 9,
        playedCards: 0,
        buildings: [],
        population: { farmer: 4, worker: 3, craftsman: 2, engineer: 0, investor: 0 },
        exhaustedPopulation: { farmer: 0, worker: 0, craftsman: 0, engineer: 0, investor: 0 },
        tradeTokens: 2,
        explorationTokens: 1,
        exhaustedTrade: 0,
        exhaustedExploration: 0,
        oldWorldIslands: 0,
        newWorldIslands: 0,
        expeditionCards: 0
      },
      { 
        name: 'KI - Explorer', 
        strategy: 'explorer',
        gold: 3,
        handCards: 9,
        playedCards: 0,
        buildings: [],
        population: { farmer: 4, worker: 3, craftsman: 2, engineer: 0, investor: 0 },
        exhaustedPopulation: { farmer: 0, worker: 0, craftsman: 0, engineer: 0, investor: 0 },
        tradeTokens: 2,
        explorationTokens: 1,
        exhaustedTrade: 0,
        exhaustedExploration: 0,
        oldWorldIslands: 0,
        newWorldIslands: 0,
        expeditionCards: 0
      }
    ]
  });

  const [selectedAction, setSelectedAction] = useState(null);
  const [gameLog, setGameLog] = useState([]);
  const [mlSuggestion, setMlSuggestion] = useState(null);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [trainingStats, setTrainingStats] = useState({
    gamesPlayed: 0,
    dataPoints: 0,
    modelAccuracy: 0,
    lastTraining: null
  });

  const actions = [
    { id: 'build', name: 'Ausbauen', icon: Factory, description: 'Industrie, Werft oder Schiff bauen' },
    { id: 'playCard', name: 'Karte ausspielen', icon: Package, description: 'Bevölkerungskarte ausspielen' },
    { id: 'exchange', name: 'Karten tauschen', icon: RotateCcw, description: 'Bis zu 3 Karten austauschen' },
    { id: 'workforce', name: 'Arbeitskraft erhöhen', icon: Users, description: 'Neue Bevölkerung hinzufügen' },
    { id: 'upgrade', name: 'Aufsteigen', icon: TrendingUp, description: 'Bevölkerung verbessern' },
    { id: 'oldWorld', name: 'Alte Welt', icon: Map, description: 'Alte-Welt-Insel erschließen' },
    { id: 'newWorld', name: 'Neue Welt', icon: Globe, description: 'Neue-Welt-Insel erkunden' },
    { id: 'expedition', name: 'Expedition', icon: Ship, description: 'Expeditions-Karten nehmen' },
    { id: 'festival', name: 'Stadtfest', icon: Award, description: 'Arbeiter zurücksetzen' }
  ];

  const populationColors = {
    farmer: 'bg-green-500',
    worker: 'bg-blue-500',
    craftsman: 'bg-red-500',
    engineer: 'bg-purple-500',
    investor: 'bg-cyan-500'
  };

  const executeAction = (actionId) => {
    const currentPlayer = gameState.players[gameState.currentPlayer];
    
    // Hier würde die Aktionslogik implementiert
    const logEntry = `${currentPlayer.name} führt Aktion aus: ${actions.find(a => a.id === actionId).name}`;
    setGameLog(prev => [...prev.slice(-4), logEntry]);
    
    // Nächster Spieler
    setGameState(prev => ({
      ...prev,
      currentPlayer: (prev.currentPlayer + 1) % 4,
      round: prev.currentPlayer === 3 ? prev.round + 1 : prev.round
    }));
    
    setSelectedAction(null);
  };

  const getMLSuggestion = () => {
    // Simulierte ML-Vorschlag
    const suggestions = [
      { action: 'build', confidence: 85, reasoning: 'Frühe Expansion schafft Produktionsvorteile' },
      { action: 'workforce', confidence: 72, reasoning: 'Mehr Arbeiter ermöglichen bessere Ressourcenproduktion' },
      { action: 'oldWorld', confidence: 68, reasoning: 'Neue Inseln bieten zusätzliche Bauplätze' }
    ];
    setMlSuggestion(suggestions[0]);
  };

  const runSimulation = () => {
    setSimulationRunning(true);
    // Simulierte Batch-Simulation
    setTimeout(() => {
      setTrainingStats(prev => ({
        ...prev,
        gamesPlayed: prev.gamesPlayed + 100,
        dataPoints: prev.dataPoints + 2500,
        modelAccuracy: Math.min(prev.modelAccuracy + 5, 92),
        lastTraining: new Date().toLocaleString()
      }));
      setSimulationRunning(false);
    }, 3000);
  };

  const currentPlayer = gameState.players[gameState.currentPlayer];
  const isHumanTurn = currentPlayer.strategy === 'human';

  return (
    <div className="w-full max-w-7xl mx-auto p-4 bg-amber-50">
      {/* Header */}
      <div className="mb-6 bg-gradient-to-r from-blue-800 to-blue-900 text-white p-4 rounded-lg shadow-lg">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold mb-2">Anno 1800 - Das Brettspiel</h1>
            <div className="flex gap-4 text-sm">
              <span>Runde: {gameState.round}</span>
              <span>|</span>
              <span>Aktueller Spieler: <strong>{currentPlayer.name}</strong></span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Neues Spiel
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Linke Seite - Spielbrett & Aktionen */}
        <div className="col-span-8 space-y-4">
          {/* Spielertableau */}
          <Card className="border-2 border-amber-700">
            <CardHeader className="bg-amber-100">
              <CardTitle>Spielertableau</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <div className="grid grid-cols-4 gap-3">
                {gameState.players.map((player, idx) => (
                  <div 
                    key={idx} 
                    className={`p-3 rounded-lg border-2 ${
                      idx === gameState.currentPlayer 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-300 bg-white'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold text-sm">{player.name}</span>
                      <Badge variant={player.strategy === 'human' ? 'default' : 'secondary'}>
                        {player.strategy}
                      </Badge>
                    </div>
                    
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span>Gold:</span>
                        <span className="font-bold">{player.gold}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Handkarten:</span>
                        <span className="font-bold">{player.handCards}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Inseln:</span>
                        <span className="font-bold">{player.oldWorldIslands + player.newWorldIslands}</span>
                      </div>
                    </div>
                    
                    {/* Bevölkerung */}
                    <div className="mt-2 flex gap-1">
                      {Object.entries(player.population).map(([type, count]) => (
                        count > 0 && (
                          <div key={type} className={`w-6 h-6 ${populationColors[type]} rounded-sm flex items-center justify-center text-white text-xs font-bold`}>
                            {count}
                          </div>
                        )
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Heimat-Insel & Aktionen */}
          <Card className="border-2 border-amber-700">
            <CardHeader className="bg-amber-100">
              <CardTitle>Heimat-Insel - {currentPlayer.name}</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              <div className="grid grid-cols-2 gap-4">
                {/* Wohnviertel */}
                <div className="space-y-2">
                  <h3 className="font-bold text-sm mb-2">Wohnviertel</h3>
                  {Object.entries(currentPlayer.population).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 ${populationColors[type]} rounded flex items-center justify-center text-white font-bold`}>
                          {count}
                        </div>
                        <span className="capitalize">{type}</span>
                      </div>
                      {currentPlayer.exhaustedPopulation[type] > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          -{currentPlayer.exhaustedPopulation[type]} erschöpft
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>

                {/* Marine-Plättchen */}
                <div className="space-y-2">
                  <h3 className="font-bold text-sm mb-2">Marine-Plättchen</h3>
                  <div className="p-3 bg-gray-50 rounded">
                    <div className="flex justify-between items-center mb-2">
                      <span>Handel:</span>
                      <div className="flex items-center gap-2">
                        <span className="font-bold">{currentPlayer.tradeTokens - currentPlayer.exhaustedTrade}</span>
                        <span className="text-gray-400">/ {currentPlayer.tradeTokens}</span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span>Erkundung:</span>
                      <div className="flex items-center gap-2">
                        <span className="font-bold">{currentPlayer.explorationTokens - currentPlayer.exhaustedExploration}</span>
                        <span className="text-gray-400">/ {currentPlayer.explorationTokens}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Aktionsauswahl */}
              {isHumanTurn && (
                <div className="mt-4 pt-4 border-t">
                  <h3 className="font-bold text-sm mb-3">Verfügbare Aktionen:</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {actions.map(action => {
                      const Icon = action.icon;
                      return (
                        <Button
                          key={action.id}
                          variant={selectedAction === action.id ? "default" : "outline"}
                          className="h-auto flex-col py-3"
                          onClick={() => setSelectedAction(action.id)}
                        >
                          <Icon className="w-5 h-5 mb-1" />
                          <span className="text-xs">{action.name}</span>
                        </Button>
                      );
                    })}
                  </div>
                  
                  {selectedAction && (
                    <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                      <p className="text-sm mb-2">
                        {actions.find(a => a.id === selectedAction).description}
                      </p>
                      <Button 
                        onClick={() => executeAction(selectedAction)}
                        className="w-full"
                        variant="default"
                      >
                        Aktion ausführen
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Spielverlauf */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Spielverlauf</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {gameLog.length === 0 ? (
                  <p className="text-gray-400 text-sm">Noch keine Aktionen durchgeführt</p>
                ) : (
                  gameLog.map((log, idx) => (
                    <div key={idx} className="text-sm py-1 px-2 bg-gray-50 rounded">
                      {log}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Rechte Seite - KI & Training */}
        <div className="col-span-4 space-y-4">
          <Tabs defaultValue="suggestion" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="suggestion">KI-Hilfe</TabsTrigger>
              <TabsTrigger value="simulation">Simulation</TabsTrigger>
              <TabsTrigger value="training">Training</TabsTrigger>
            </TabsList>

            <TabsContent value="suggestion" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="w-5 h-5" />
                    KI-Vorschlag
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {!mlSuggestion ? (
                    <div>
                      <p className="text-sm text-gray-600 mb-3">
                        Lass dir von der KI helfen, die beste Aktion zu finden.
                      </p>
                      <Button onClick={getMLSuggestion} className="w-full">
                        Vorschlag anzeigen
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold">
                            {actions.find(a => a.id === mlSuggestion.action).name}
                          </span>
                          <Badge variant="default">
                            {mlSuggestion.confidence}% Konfidenz
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600">
                          {mlSuggestion.reasoning}
                        </p>
                      </div>
                      
                      <div className="flex gap-2">
                        <Button 
                          variant="default" 
                          className="flex-1"
                          onClick={() => {
                            setSelectedAction(mlSuggestion.action);
                            executeAction(mlSuggestion.action);
                          }}
                        >
                          Annehmen
                        </Button>
                        <Button 
                          variant="outline" 
                          className="flex-1"
                          onClick={getMLSuggestion}
                        >
                          Neu berechnen
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="simulation" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Automatische Simulation</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 mb-4">
                    Simuliere Spiele zwischen KI-Gegnern, um Trainingsdaten zu sammeln.
                  </p>
                  
                  {simulationRunning ? (
                    <div className="space-y-3">
                      <Progress value={66} className="w-full" />
                      <p className="text-sm text-center">Simulation läuft...</p>
                    </div>
                  ) : (
                    <Button onClick={runSimulation} className="w-full">
                      <Play className="w-4 h-4 mr-2" />
                      100 Spiele simulieren
                    </Button>
                  )}
                  
                  <div className="mt-4 pt-3 border-t space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Gespielte Spiele:</span>
                      <strong>{trainingStats.gamesPlayed}</strong>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Gesammelte Daten:</span>
                      <strong>{trainingStats.dataPoints}</strong>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="training" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>ML-Modell Training</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="p-3 bg-gray-50 rounded">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm">Modell-Genauigkeit:</span>
                        <Badge variant={trainingStats.modelAccuracy > 80 ? "default" : "secondary"}>
                          {trainingStats.modelAccuracy}%
                        </Badge>
                      </div>
                      <Progress value={trainingStats.modelAccuracy} className="w-full" />
                    </div>
                    
                    {trainingStats.dataPoints < 1000 ? (
                      <div className="p-3 bg-yellow-50 rounded-lg flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5" />
                        <p className="text-sm text-yellow-800">
                          Sammle mehr Daten durch Simulationen für bessere Ergebnisse.
                        </p>
                      </div>
                    ) : (
                      <Button className="w-full">
                        Modell trainieren
                      </Button>
                    )}
                    
                    {trainingStats.lastTraining && (
                      <p className="text-xs text-gray-500 text-center">
                        Letztes Training: {trainingStats.lastTraining}
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Spielstand */}
          <Card>
            <CardHeader>
              <CardTitle>Spielstand</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {gameState.players.map((player, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm">{player.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">
                        {player.playedCards * 3 + Math.floor(player.gold / 3)} EP
                      </span>
                      <div className={`w-2 h-2 rounded-full ${
                        idx === gameState.currentPlayer ? 'bg-blue-500' : 'bg-gray-300'
                      }`} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Anno1800BoardGame;
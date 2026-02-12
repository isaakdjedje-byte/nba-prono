"""
Modele de prediction du vainqueur (winner signal)
Heuristique basee sur forme recente et statistiques equipes
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class WinnerPrediction:
    """Resultat de prediction winner"""
    winner: str  # "home" ou "away"
    confidence: float  # 0.0 - 1.0
    method: str = "heuristic"
    factors: Optional[Dict[str, Any]] = None


class WinnerModel:
    """
    Modele heuristique de prediction winner MVP
    Base sur: forme recente, home/away advantage, stats offensives/defensives
    """

    def __init__(self):
        self.home_advantage = 3.0  # Points d'avantage domicile

    def predict(
        self,
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any]
    ) -> WinnerPrediction:
        """
        Preduit le vainqueur d'un match

        Args:
            home_stats: Stats equipe a domicile
            away_stats: Stats equipe visiteuse

        Returns:
            WinnerPrediction avec winner et confiance
        """
        # Score forme recente (wins last 5)
        home_form = home_stats.get("wins_last_5", 0)
        away_form = away_stats.get("wins_last_5", 0)

        # Score offensif moyen
        home_offense = home_stats.get("avg_points", 100)
        away_offense = away_stats.get("avg_points", 100)

        # Score defensif (points encaisses)
        home_defense = home_stats.get("avg_allowed", 100)
        away_defense = away_stats.get("avg_allowed", 100)

        # Calcul des forces
        home_strength = (
            home_form * 5 +  # Forme recente (0-25 points)
            (home_offense - 100) * 0.5 +  # Bonus offense
            (100 - home_defense) * 0.5 +  # Bonus defense
            self.home_advantage  # Avantage domicile
        )

        away_strength = (
            away_form * 5 +  # Forme recente
            (away_offense - 100) * 0.5 +  # Bonus offense
            (100 - away_defense) * 0.5    # Bonus defense
        )

        # Determination winner
        if home_strength > away_strength:
            winner = "home"
            confidence = min(0.5 + (home_strength - away_strength) / 20, 0.95)
        else:
            winner = "away"
            confidence = min(0.5 + (away_strength - home_strength) / 20, 0.95)

        return WinnerPrediction(
            winner=winner,
            confidence=round(confidence, 2),
            method="heuristic",
            factors={
                "home_strength": round(home_strength, 2),
                "away_strength": round(away_strength, 2),
                "home_form": home_form,
                "away_form": away_form,
                "home_advantage_applied": self.home_advantage
            }
        )
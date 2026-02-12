"""
Projecteur de score total (score projete)
Estimation basee sur moyennes offensives/defensives
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ScoreProjection:
    """Resultat de projection de score"""
    total_score: float
    home_projected: float
    away_projected: float
    method: str = "statistical_average"


class ScoreProjector:
    """
    Projecteur de score MVP
    Calcule le score total estime base sur les moyennes des equipes
    """

    def __init__(self):
        self.league_avg_score = 110.0  # Moyenne NBA

    def project(
        self,
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any]
    ) -> ScoreProjection:
        """
        Projete le score d'un match

        Args:
            home_stats: Stats equipe a domicile
            away_stats: Stats equipe visiteuse

        Returns:
            ScoreProjection avec scores projetes
        """
        # Moyennes offensives
        home_avg_points = home_stats.get("avg_points", self.league_avg_score)
        away_avg_points = away_stats.get("avg_points", self.league_avg_score)

        # Moyennes defensives (points encaisses)
        home_avg_allowed = home_stats.get("avg_allowed", self.league_avg_score)
        away_avg_allowed = away_stats.get("avg_allowed", self.league_avg_score)

        # Calcul des scores projetes
        # Formule: moyenne entre ce qu'une equipe marque et ce que l'adversaire encaisse
        home_projected = (home_avg_points + away_avg_allowed) / 2
        away_projected = (away_avg_points + home_avg_allowed) / 2

        # Ajustement home advantage (+3 points pour home)
        home_projected += 1.5
        away_projected -= 1.5

        # Plages realistes (180-280 points total)
        total_score = home_projected + away_projected

        return ScoreProjection(
            total_score=round(total_score, 1),
            home_projected=round(home_projected, 1),
            away_projected=round(away_projected, 1),
            method="statistical_average"
        )
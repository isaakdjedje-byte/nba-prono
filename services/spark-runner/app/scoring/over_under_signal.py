"""
Generateur de signal Over/Under
Compare le score projete a la ligne standard
"""
from dataclasses import dataclass
from typing import Optional
from .score_projector import ScoreProjection


@dataclass
class OverUnderSignal:
    """Signal over/under avec confiance"""
    signal: str  # "over", "under", "no_signal"
    line: float
    projected_score: float
    confidence: float
    edge: float  # Difference projete vs ligne


class OverUnderGenerator:
    """
    Generateur de signal over/under MVP
    """

    def __init__(self, default_line: float = 220.5):
        self.default_line = default_line
        self.edge_threshold = 5.0  # Seuil pour generer un signal (points)

    def generate(
        self,
        score_projection: ScoreProjection,
        line: Optional[float] = None
    ) -> OverUnderSignal:
        """
        Genere le signal over/under

        Args:
            score_projection: Projection de score
            line: Ligne over/under (defaut: 220.5)

        Returns:
            OverUnderSignal avec signal et confiance
        """
        ou_line = line or self.default_line
        projected = score_projection.total_score
        edge = projected - ou_line

        # Determiner le signal
        if abs(edge) < self.edge_threshold:
            signal = "no_signal"
            confidence = 0.5
        elif edge > 0:
            signal = "over"
            # Confiance basee sur l'ecart (max 0.9)
            confidence = min(0.5 + abs(edge) / 20, 0.9)
        else:
            signal = "under"
            confidence = min(0.5 + abs(edge) / 20, 0.9)

        return OverUnderSignal(
            signal=signal,
            line=ou_line,
            projected_score=projected,
            confidence=round(confidence, 2),
            edge=round(edge, 1)
        )
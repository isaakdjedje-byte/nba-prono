"""
Gestion des exclusions de matchs
Detection et categorisation des matchs non eligibles au scoring
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List


class ExclusionReason(str, Enum):
    """Raisons d'exclusion d'un match"""
    MISSING_DATA = "missing_data"
    INSUFFICIENT_HISTORY = "insufficient_history"
    INSUFFICIENT_QUALITY = "insufficient_quality"
    INVALID_STATUS = "invalid_status"


@dataclass
class MatchExclusion:
    """Exclusion d'un match avec raison"""
    match_id: str
    reason: ExclusionReason
    details: Dict[str, Any]
    excluded_at: datetime

    @property
    def excluded(self) -> bool:
        """Toujours True pour une exclusion"""
        return True


class ExclusionChecker:
    """
    Verificateur d'exclusion de matchs
    Determine si un match est eligible au scoring
    """

    def __init__(
        self,
        min_history_games: int = 5,
        min_quality_score: float = 80.0
    ):
        self.min_history_games = min_history_games
        self.min_quality_score = min_quality_score

    def check(self, match_data: Dict[str, Any]) -> Optional[MatchExclusion]:
        """
        Verifie si un match doit etre exclu

        Args:
            match_data: Donnees du match

        Returns:
            MatchExclusion avec raison si exclu, sinon None
        """
        match_id = match_data.get("external_id", "unknown")

        # 1. Verifier statut match
        status = match_data.get("status", "scheduled")
        if status not in ["scheduled", "upcoming"]:
            return MatchExclusion(
                match_id=match_id,
                reason=ExclusionReason.INVALID_STATUS,
                details={"status": status, "required": "scheduled"},
                excluded_at=datetime.now(timezone.utc)
            )

        # 2. Verifier presence donnees requises
        home_stats = match_data.get("home_stats")
        away_stats = match_data.get("away_stats")

        if not home_stats or not away_stats:
            missing = []
            if not home_stats:
                missing.append("home_stats")
            if not away_stats:
                missing.append("away_stats")
            return MatchExclusion(
                match_id=match_id,
                reason=ExclusionReason.MISSING_DATA,
                details={"missing_fields": missing},
                excluded_at=datetime.now(timezone.utc)
            )

        # 3. Verifier qualite des donnees (avant historique)
        quality_score = match_data.get("quality_score", 0)
        if quality_score < self.min_quality_score:
            return MatchExclusion(
                match_id=match_id,
                reason=ExclusionReason.INSUFFICIENT_QUALITY,
                details={
                    "quality_score": quality_score,
                    "required": self.min_quality_score
                },
                excluded_at=datetime.now(timezone.utc)
            )

        # 4. Verifier historique suffisant
        home_games = home_stats.get("games_played", 0)
        away_games = away_stats.get("games_played", 0)

        if home_games < self.min_history_games or away_games < self.min_history_games:
            return MatchExclusion(
                match_id=match_id,
                reason=ExclusionReason.INSUFFICIENT_HISTORY,
                details={
                    "home_games": home_games,
                    "away_games": away_games,
                    "required": self.min_history_games
                },
                excluded_at=datetime.now(timezone.utc)
            )

        # Match eligible
        return None

    def check_batch(
        self,
        matches: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[MatchExclusion]]:
        """
        Verifie un batch de matchs

        Returns:
            Tuple (matches_eligibles, exclusions)
        """
        eligible: List[Dict[str, Any]] = []
        exclusions: List[MatchExclusion] = []

        for match in matches:
            exclusion = self.check(match)
            if exclusion is not None:
                exclusions.append(exclusion)
            else:
                eligible.append(match)

        return eligible, exclusions
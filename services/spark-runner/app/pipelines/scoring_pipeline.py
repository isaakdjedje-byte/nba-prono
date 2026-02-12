"""
Pipeline de scoring predictif
Orchestre la generation des signaux winner, score projete, over/under
"""
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from app.scoring.winner_model import WinnerModel
from app.scoring.score_projector import ScoreProjector
from app.scoring.over_under_signal import OverUnderGenerator
from app.scoring.exclusions import ExclusionChecker, MatchExclusion, ExclusionReason
from app.storage.postgres_writer import PostgresWriter

logger = logging.getLogger(__name__)


class ScoringStatus(str, Enum):
    """Statuts possibles du scoring"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringPipeline:
    """
    Pipeline de scoring predictif MVP
    Genere les signaux: winner, score projete, over/under
    """

    def __init__(
        self,
        min_quality_score: float = 80.0,
        default_ou_line: float = 220.5,
        max_retries: int = 3
    ):
        self.min_quality_score = min_quality_score
        self.default_ou_line = default_ou_line
        self.max_retries = max_retries

        # Sous-composants
        self.winner_model = WinnerModel()
        self.score_projector = ScoreProjector()
        self.ou_generator = OverUnderGenerator(default_line=default_ou_line)
        self.exclusion_checker = ExclusionChecker(min_quality_score=min_quality_score)

    def score_matches(
        self,
        run_id: str,
        trace_id: str,
        matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute le scoring sur un batch de matchs

        Args:
            run_id: Identifiant du run
            trace_id: ID de tracabilite
            matches: Liste des matchs a scorer

        Returns:
            Dict avec statut, signaux, exclusions
        """
        logger.info(f"[trace:{trace_id}] Starting scoring for run {run_id} with {len(matches)} matches")

        result = {
            "status": "success",
            "run_id": run_id,
            "trace_id": trace_id,
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "signals": [],
            "exclusions": [],
            "stats": {
                "total": len(matches),
                "eligible": 0,
                "excluded": 0,
                "signals_generated": 0
            }
        }

        try:
            # 1. Filtrer les matchs eligibles
            eligible_matches, exclusions = self.exclusion_checker.check_batch(matches)

            result["exclusions"] = [
                {
                    "match_id": ex.match_id,
                    "reason": ex.reason.value,
                    "details": ex.details,
                    "excluded_at": ex.excluded_at.isoformat()
                }
                for ex in exclusions
            ]

            result["stats"]["eligible"] = len(eligible_matches)
            result["stats"]["excluded"] = len(exclusions)

            logger.info(f"[trace:{trace_id}] {len(eligible_matches)}/{len(matches)} matches eligible for scoring")

            # 2. Generer les signaux pour les matchs eligibles
            signals = []
            for match in eligible_matches:
                signal = self._generate_signal_for_match(match, trace_id)
                if signal:
                    signals.append(signal)

            result["signals"] = signals
            result["stats"]["signals_generated"] = len(signals)

            # 3. Persister les signaux (avec atomicite et retry)
            if signals:
                success = self._persist_signals_with_retry(run_id, signals, trace_id)
                if not success:
                    # Echec persistance = rollback, aucun signal publie
                    raise Exception("Failed to persist signals after all retries")

            logger.info(f"[trace:{trace_id}] Scoring completed: {len(signals)} signals generated")

        except Exception as e:
            logger.error(f"[trace:{trace_id}] Scoring failed: {e}")
            result["status"] = "failed"
            result["error_cause"] = str(e)
            # En cas d'echec: aucun signal ne doit etre publie (atomicite)
            result["signals"] = []

        return result

    def _generate_signal_for_match(
        self,
        match: Dict[str, Any],
        trace_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Genere tous les signaux pour un match

        Args:
            match: Donnees du match
            trace_id: ID de tracabilite

        Returns:
            Dict avec signaux ou None si erreur
        """
        try:
            match_id = match.get("external_id")
            home_stats = match.get("home_stats", {})
            away_stats = match.get("away_stats", {})

            # 1. Prediction winner
            winner_pred = self.winner_model.predict(home_stats, away_stats)

            # 2. Projection score
            score_proj = self.score_projector.project(home_stats, away_stats)

            # 3. Signal over/under
            ou_signal = self.ou_generator.generate(score_proj)

            signal = {
                "match_id": match_id,
                "run_id": match.get("run_id"),
                "home_team": match.get("home_team", {}),
                "away_team": match.get("away_team", {}),
                "scheduled_at": match.get("scheduled_at"),
                "winner": {
                    "prediction": winner_pred.winner,
                    "confidence": winner_pred.confidence,
                    "method": winner_pred.method,
                    "factors": winner_pred.factors
                },
                "score_projection": {
                    "total": score_proj.total_score,
                    "home": score_proj.home_projected,
                    "away": score_proj.away_projected,
                    "method": score_proj.method
                },
                "over_under": {
                    "signal": ou_signal.signal,
                    "line": ou_signal.line,
                    "projected_score": ou_signal.projected_score,
                    "confidence": ou_signal.confidence,
                    "edge": ou_signal.edge
                },
                "quality_score": match.get("quality_score"),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

            logger.debug(f"[trace:{trace_id}] Signal generated for match {match_id}")
            return signal

        except Exception as e:
            logger.error(f"[trace:{trace_id}] Error generating signal for match: {e}")
            return None

    def _persist_signals_with_retry(
        self,
        run_id: str,
        signals: List[Dict[str, Any]],
        trace_id: str
    ) -> bool:
        """
        Persiste les signaux avec mecanisme de retry

        Args:
            run_id: ID du run
            signals: Liste des signaux a persister
            trace_id: ID de tracabilite

        Returns:
            True si succes, False si tous les retries ont echoue
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                writer = PostgresWriter()
                writer.save_signals(run_id, signals)
                logger.info(f"[trace:{trace_id}] Signals persisted successfully (attempt {attempt})")
                return True

            except Exception as e:
                last_error = e
                logger.warning(f"[trace:{trace_id}] Persistence attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    import time
                    time.sleep(0.5 * attempt)  # Backoff exponentiel

        # Tous les retries ont echoue
        return False
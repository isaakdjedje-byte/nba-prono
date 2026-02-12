"""
Tests pour le pipeline de scoring predictif
Red-Green-Refactor: Tests rouges d'abord
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from app.pipelines.scoring_pipeline import ScoringPipeline, ScoringStatus
from app.scoring.winner_model import WinnerPrediction
from app.scoring.score_projector import ScoreProjection
from app.scoring.over_under_signal import OverUnderSignal
from app.scoring.exclusions import ExclusionReason, MatchExclusion


class TestScoringPipeline:
    """Tests du pipeline de scoring complet"""

    def test_pipeline_initialization(self):
        """Test initialisation du pipeline avec configuration"""
        pipeline = ScoringPipeline(min_quality_score=80.0)
        assert pipeline.min_quality_score == 80.0
        assert pipeline.default_ou_line == 220.5

    def test_scoring_status_enum(self):
        """Test les statuts de scoring"""
        assert ScoringStatus.PENDING == "pending"
        assert ScoringStatus.RUNNING == "running"
        assert ScoringStatus.COMPLETED == "completed"
        assert ScoringStatus.FAILED == "failed"

    @patch('app.pipelines.scoring_pipeline.PostgresWriter')
    def test_score_matches_with_valid_data(self, mock_writer_class):
        """Test scoring avec donnees valides - AC1"""
        # Arrange
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        pipeline = ScoringPipeline()

        matches = [
            {
                "external_id": "match_001",
                "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
                "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
                "home_stats": {"wins_last_5": 4, "avg_points": 115.5, "avg_allowed": 108.2, "games_played": 10},
                "away_stats": {"wins_last_5": 3, "avg_points": 112.3, "avg_allowed": 110.5, "games_played": 10},
                "quality_score": 85.0,
                "scheduled_at": "2026-02-11T20:00:00Z",
                "status": "scheduled"
            }
        ]

        # Act
        result = pipeline.score_matches(
            run_id="run_001",
            trace_id="trace_001",
            matches=matches
        )

        # Assert
        assert result["status"] == "success"
        assert result["run_id"] == "run_001"
        assert result["trace_id"] == "trace_001"
        assert len(result["signals"]) == 1

        signal = result["signals"][0]
        assert "winner" in signal
        assert "score_projection" in signal
        assert "over_under" in signal
        assert signal["match_id"] == "match_001"

    @patch('app.pipelines.scoring_pipeline.PostgresWriter')
    def test_exclusion_insufficient_data(self, mock_writer_class):
        """Test exclusion match avec donnees insuffisantes - AC2"""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        pipeline = ScoringPipeline()

        matches = [
            {
                "external_id": "match_002",
                "home_team": {"id": "lal", "name": "Lakers"},
                "away_team": {"id": "gsw", "name": "Warriors"},
                # Donnees stats manquantes
                "quality_score": 85.0
            }
        ]

        result = pipeline.score_matches(
            run_id="run_002",
            trace_id="trace_002",
            matches=matches
        )

        assert result["status"] == "success"
        assert len(result["signals"]) == 0
        assert len(result["exclusions"]) == 1

        exclusion = result["exclusions"][0]
        assert exclusion["match_id"] == "match_002"
        assert "reason" in exclusion
        assert exclusion["reason"] == ExclusionReason.MISSING_DATA.value

    @patch('app.pipelines.scoring_pipeline.PostgresWriter')
    def test_exclusion_low_quality_score(self, mock_writer_class):
        """Test exclusion match avec qualite insuffisante"""
        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        pipeline = ScoringPipeline(min_quality_score=80.0)

        matches = [
            {
                "external_id": "match_003",
                "home_team": {"id": "lal", "name": "Lakers"},
                "away_team": {"id": "gsw", "name": "Warriors"},
                "home_stats": {"wins_last_5": 4, "avg_points": 115.5},
                "away_stats": {"wins_last_5": 3, "avg_points": 112.3},
                "quality_score": 70.0  # En dessous du seuil
            }
        ]

        result = pipeline.score_matches(
            run_id="run_003",
            trace_id="trace_003",
            matches=matches
        )

        assert len(result["exclusions"]) == 1
        assert result["exclusions"][0]["reason"] == ExclusionReason.INSUFFICIENT_QUALITY.value

    @patch('app.pipelines.scoring_pipeline.PostgresWriter')
    def test_atomicity_no_partial_publish(self, mock_writer_class):
        """Test atomicite: pas de publication partielle - AC3"""
        mock_writer = MagicMock()
        mock_writer.save_signals.side_effect = Exception("DB Error")
        mock_writer_class.return_value = mock_writer

        pipeline = ScoringPipeline()

        matches = [
            {
                "external_id": "match_004",
                "home_team": {"id": "lal", "name": "Lakers"},
                "away_team": {"id": "gsw", "name": "Warriors"},
                "home_stats": {"wins_last_5": 4, "avg_points": 115.5, "avg_allowed": 108.2, "games_played": 10},
                "away_stats": {"wins_last_5": 3, "avg_points": 112.3, "avg_allowed": 110.5, "games_played": 10},
                "quality_score": 85.0,
                "status": "scheduled",
                "scheduled_at": "2026-02-11T20:00:00Z"
            }
        ]

        result = pipeline.score_matches(
            run_id="run_004",
            trace_id="trace_004",
            matches=matches
        )

        # En cas d'echec DB, aucun signal ne doit etre persiste
        assert result["status"] == "failed"
        assert "Failed to persist" in result["error_cause"]
        assert len(result["signals"]) == 0

    def test_winner_prediction_calculation(self):
        """Test calcul prediction winner"""
        from app.scoring.winner_model import WinnerModel

        model = WinnerModel()

        # Cas: Home team favorite
        home_stats = {"wins_last_5": 4, "avg_points": 115.5, "avg_allowed": 108.2}
        away_stats = {"wins_last_5": 2, "avg_points": 105.3, "avg_allowed": 112.5}

        prediction = model.predict(home_stats, away_stats)

        assert prediction.winner in ["home", "away"]
        assert 0.0 <= prediction.confidence <= 1.0
        assert prediction.method == "heuristic"

    def test_score_projection_calculation(self):
        """Test calcul score projete"""
        from app.scoring.score_projector import ScoreProjector

        projector = ScoreProjector()

        home_stats = {"avg_points": 115.5, "avg_allowed": 108.2}
        away_stats = {"avg_points": 112.3, "avg_allowed": 110.5}

        projection = projector.project(home_stats, away_stats)

        assert 180 <= projection.total_score <= 280
        assert projection.home_projected > 0
        assert projection.away_projected > 0
        assert projection.method == "statistical_average"

    def test_over_under_signal_generation(self):
        """Test generation signal over/under"""
        from app.scoring.over_under_signal import OverUnderGenerator

        generator = OverUnderGenerator(default_line=220.5)

        score_projection = ScoreProjection(
            total_score=225.5,
            home_projected=115.0,
            away_projected=110.5,
            method="statistical_average"
        )

        signal = generator.generate(score_projection)

        assert signal.signal in ["over", "under", "no_signal"]
        assert signal.line == 220.5
        assert signal.projected_score == 225.5
        assert signal.confidence >= 0.0

    def test_exclusion_categorization(self):
        """Test categorisation des raisons d'exclusion"""
        from app.scoring.exclusions import ExclusionChecker

        checker = ExclusionChecker(min_history_games=5, min_quality_score=80.0)

        # Test missing data
        match_missing = {"external_id": "m1", "home_stats": None}
        result = checker.check(match_missing)
        assert result is not None
        assert result.excluded
        assert result.reason == ExclusionReason.MISSING_DATA

        # Test insufficient quality (checked before history)
        match_low_quality = {
            "external_id": "m2",
            "home_stats": {"games_played": 10},
            "away_stats": {"games_played": 10},
            "quality_score": 70.0
        }
        result = checker.check(match_low_quality)
        assert result is not None
        assert result.reason == ExclusionReason.INSUFFICIENT_QUALITY

        # Test insufficient history (need good quality first)
        match_low_hist = {
            "external_id": "m3",
            "home_stats": {"games_played": 3},
            "away_stats": {"games_played": 3},
            "quality_score": 85.0
        }
        result = checker.check(match_low_hist)
        assert result is not None
        assert result.reason == ExclusionReason.INSUFFICIENT_HISTORY

        # Test invalid status
        match_invalid = {
            "external_id": "m4",
            "home_stats": {"games_played": 10},
            "away_stats": {"games_played": 10},
            "status": "finished",
            "quality_score": 85.0
        }
        result = checker.check(match_invalid)
        assert result is not None
        assert result.reason == ExclusionReason.INVALID_STATUS

    @patch('app.pipelines.scoring_pipeline.PostgresWriter')
    def test_retry_mechanism(self, mock_writer_class):
        """Test mecanisme de retry pour erreurs transitoires"""
        mock_writer = MagicMock()
        # Echoue 2 fois, reussit la 3eme
        mock_writer.save_signals.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            None  # Success
        ]
        mock_writer_class.return_value = mock_writer

        pipeline = ScoringPipeline(max_retries=3)

        matches = [
            {
                "external_id": "match_005",
                "home_team": {"id": "lal", "name": "Lakers"},
                "away_team": {"id": "gsw", "name": "Warriors"},
                "home_stats": {"wins_last_5": 4, "avg_points": 115.5, "avg_allowed": 108.2, "games_played": 10},
                "away_stats": {"wins_last_5": 3, "avg_points": 112.3, "avg_allowed": 110.5, "games_played": 10},
                "quality_score": 85.0,
                "status": "scheduled",
                "scheduled_at": "2026-02-11T20:00:00Z"
            }
        ]

        result = pipeline.score_matches(
            run_id="run_005",
            trace_id="trace_005",
            matches=matches
        )

        assert result["status"] == "success"
        assert mock_writer.save_signals.call_count == 3


class TestScoringModels:
    """Tests des modeles de donnees scoring"""

    def test_winner_prediction_model(self):
        """Test modele WinnerPrediction"""
        prediction = WinnerPrediction(
            winner="home",
            confidence=0.75,
            method="heuristic"
        )

        assert prediction.winner == "home"
        assert prediction.confidence == 0.75
        assert prediction.method == "heuristic"

    def test_score_projection_model(self):
        """Test modele ScoreProjection"""
        projection = ScoreProjection(
            total_score=225.5,
            home_projected=115.0,
            away_projected=110.5,
            method="statistical_average"
        )

        assert projection.total_score == 225.5
        assert projection.home_projected == 115.0
        assert projection.away_projected == 110.5

    def test_over_under_signal_model(self):
        """Test modele OverUnderSignal"""
        signal = OverUnderSignal(
            signal="over",
            line=220.5,
            projected_score=225.5,
            confidence=0.65,
            edge=5.0
        )

        assert signal.signal == "over"
        assert signal.line == 220.5
        assert signal.projected_score == 225.5

    def test_match_exclusion_model(self):
        """Test modele MatchExclusion"""
        exclusion = MatchExclusion(
            match_id="match_001",
            reason=ExclusionReason.MISSING_DATA,
            details={"missing_fields": ["home_stats", "away_stats"]},
            excluded_at=datetime.now(timezone.utc)
        )

        assert exclusion.match_id == "match_001"
        assert exclusion.reason == ExclusionReason.MISSING_DATA

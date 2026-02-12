"""
Tests unitaires pour la validation qualite data
Pattern TDD : tests rouges avant implementation
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le chemin pour imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from quality.quality_checks import QualityChecker, QualityRule, QualityStatus
from quality.scoring import QualityScorer


class TestQualityRule:
    """Tests pour les regles de qualite individuelles"""

    def test_rule_completeness_check_missing_field(self):
        """Test: Detection champ manquant"""
        rule = QualityRule.completeness_check(required_fields=["external_id", "home_team", "away_team"])
        
        incomplete_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"}
            # Missing away_team
        }
        
        result = rule.check(incomplete_match)
        assert result.passed is False
        assert "away_team" in result.details["missing_fields"]

    def test_rule_completeness_check_all_fields_present(self):
        """Test: Completeness passe si tous champs presents"""
        rule = QualityRule.completeness_check(required_fields=["external_id", "home_team", "away_team"])
        
        complete_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"}
        }
        
        result = rule.check(complete_match)
        assert result.passed is True

    def test_rule_validity_check_negative_score(self):
        """Test: Detection valeur invalide (score negatif)"""
        rule = QualityRule.validity_check()
        
        invalid_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "home_score": -10,  # Invalid negative
            "away_score": 95
        }
        
        result = rule.check(invalid_match)
        assert result.passed is False
        assert "home_score" in str(result.details)

    def test_rule_validity_check_valid_scores(self):
        """Test: Validity passe avec scores valides"""
        rule = QualityRule.validity_check()
        
        valid_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "home_score": 102,
            "away_score": 98
        }
        
        result = rule.check(valid_match)
        assert result.passed is True

    def test_rule_consistency_check_same_team(self):
        """Test: Detection incoherence (meme equipe)"""
        rule = QualityRule.consistency_check()
        
        inconsistent_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"}  # Same team
        }
        
        result = rule.check(inconsistent_match)
        assert result.passed is False
        assert "same_team" in str(result.details).lower()

    def test_rule_timeliness_check_old_match(self):
        """Test: Detection match trop ancien"""
        rule = QualityRule.timeliness_check(max_age_hours=24)
        
        old_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "scheduled_at": "2023-01-01T20:00:00Z"  # Too old
        }
        
        result = rule.check(old_match)
        assert result.passed is False


class TestQualityChecker:
    """Tests pour le validateur qualite"""

    def test_checker_initialization(self):
        """Test: Initialisation avec trace_id"""
        checker = QualityChecker(trace_id="test-trace-123")
        assert checker.trace_id == "test-trace-123"
        assert len(checker.rules) > 0

    def test_validate_match_all_rules_pass(self):
        """Test: Match passe toutes les regles de qualite"""
        checker = QualityChecker(trace_id="test-trace-123")
        
        valid_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "scheduled_at": (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2)).isoformat() + "Z",
            "season": "2023-24",
            "game_type": "regular",
            "home_score": 102,
            "away_score": 98
        }
        
        result = checker.validate_match(valid_match)
        assert result.status == QualityStatus.PASS
        assert result.errors == []

    def test_validate_match_missing_fields(self):
        """Test: Detection champs manquants"""
        checker = QualityChecker(trace_id="test-trace-123")
        
        incomplete_match = {
            "external_id": "nba-2024-001"
            # Missing teams and other fields
        }
        
        result = checker.validate_match(incomplete_match)
        assert result.status == QualityStatus.FAIL
        assert len(result.errors) > 0

    def test_validate_match_invalid_values(self):
        """Test: Detection valeurs invalides"""
        checker = QualityChecker(trace_id="test-trace-123")
        
        invalid_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "scheduled_at": (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2)).isoformat() + "Z",
            "home_score": -5,  # Invalid
            "away_score": 100
        }
        
        result = checker.validate_match(invalid_match)
        assert result.status == QualityStatus.FAIL
        assert any("score" in str(e).lower() for e in result.errors)

    def test_validate_batch_mixed_quality(self):
        """Test: Validation lot avec qualite mixte"""
        checker = QualityChecker(trace_id="test-trace-123")
        
        tomorrow = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)).isoformat() + "Z"
        
        matches = [
            {  # Valid
                "external_id": "nba-001",
                "home_team": {"id": "lal", "name": "Lakers", "city": "LA"},
                "away_team": {"id": "gsw", "name": "Warriors", "city": "GS"},
                "scheduled_at": tomorrow,
                "season": "2023-24"
            },
            {  # Invalid - missing fields
                "external_id": "nba-002"
            },
            {  # Valid
                "external_id": "nba-003",
                "home_team": {"id": "bos", "name": "Celtics", "city": "Boston"},
                "away_team": {"id": "mia", "name": "Heat", "city": "Miami"},
                "scheduled_at": tomorrow,
                "season": "2023-24"
            }
        ]
        
        results = checker.validate_batch(matches)
        
        assert len(results) == 3
        assert results[0].status == QualityStatus.PASS
        assert results[1].status == QualityStatus.FAIL
        assert results[2].status == QualityStatus.PASS

    def test_critical_threshold_detection(self):
        """Test: Detection seuil critique (>20% echecs)"""
        checker = QualityChecker(trace_id="test-trace-123")
        
        tomorrow = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)).isoformat() + "Z"
        
        # 5 matches, 2 invalid = 40% failure (above 20% threshold)
        matches = [
            {"external_id": "nba-001", "home_team": {"id": "lal", "name": "L", "city": "LA"}, "away_team": {"id": "gsw", "name": "W", "city": "GS"}, "scheduled_at": tomorrow, "season": "2023-24"},
            {"external_id": "nba-002"},  # Invalid
            {"external_id": "nba-003", "home_team": {"id": "bos", "name": "C", "city": "B"}, "away_team": {"id": "mia", "name": "H", "city": "M"}, "scheduled_at": tomorrow, "season": "2023-24"},
            {"external_id": "nba-004"},  # Invalid
            {"external_id": "nba-005", "home_team": {"id": "chi", "name": "B", "city": "C"}, "away_team": {"id": "nyk", "name": "K", "city": "NY"}, "scheduled_at": tomorrow, "season": "2023-24"}
        ]
        
        results = checker.validate_batch(matches)
        summary = checker.get_quality_summary(results)
        
        assert summary["critical_failure"] is True
        assert summary["pass_rate"] == 0.6  # 3/5 passed


class TestQualityScorer:
    """Tests pour le scoring qualite"""

    def test_score_calculation_per_match(self):
        """Test: Calcul score par match"""
        scorer = QualityScorer()
        
        # Match avec quelques erreurs mineures
        match_result = Mock()
        match_result.status = QualityStatus.FAIL
        match_result.errors = ["missing_field:optional_field"]
        match_result.warnings = []
        match_result.match_id = "nba-001"
        
        result = scorer.calculate_match_score(match_result)
        assert 0 <= result.score <= 100

    def test_aggregate_scores_per_run(self):
        """Test: Agregation scores par run"""
        scorer = QualityScorer()
        
        match_scores = [
            {"match_id": "nba-001", "score": 100, "status": "PASS"},
            {"match_id": "nba-002", "score": 0, "status": "FAIL"},
            {"match_id": "nba-003", "score": 100, "status": "PASS"}
        ]
        
        aggregate = scorer.aggregate_run_scores(match_scores)
        
        assert aggregate["total_matches"] == 3
        assert aggregate["passed_matches"] == 2
        assert aggregate["failed_matches"] == 1
        assert aggregate["average_score"] == 66.67
        assert aggregate["pass_rate"] == 0.67


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

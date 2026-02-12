"""
Tests unitaires pour le mecanisme de fallback source
Pattern TDD : tests rouges avant implementation
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Ajouter le chemin pour imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from pipelines.fallback_pipeline import FallbackPipeline, FallbackStatus
from quality.quality_checks import QualityChecker, QualityResult, QualityStatus


class TestFallbackPipeline:
    """Tests pour le pipeline de fallback"""

    def test_pipeline_initialization(self):
        """Test: Initialisation avec source secondaire"""
        pipeline = FallbackPipeline(
            trace_id="test-trace-123",
            fallback_url="https://api.backup-nba.com/games"
        )
        assert pipeline.trace_id == "test-trace-123"
        assert pipeline.fallback_url == "https://api.backup-nba.com/games"
        assert pipeline.status == FallbackStatus.PENDING

    def test_fallback_source_fetch_success(self):
        """Test: Recuperation depuis source fallback reussie"""
        pipeline = FallbackPipeline(trace_id="test-trace-123")
        
        with patch('pipelines.fallback_pipeline.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "games": [
                    {
                        "external_id": "nba-2024-001",
                        "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
                        "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
                        "scheduled_at": "2024-01-15T20:00:00Z",
                        "season": "2023-24",
                        "game_type": "regular"
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            result = pipeline.fetch_from_fallback()
            
            assert result is not None
            assert len(result) == 1
            assert pipeline.status == FallbackStatus.SUCCESS

    def test_fallback_source_failure(self):
        """Test: Echec source fallback"""
        pipeline = FallbackPipeline(trace_id="test-trace-123")
        
        with patch('pipelines.fallback_pipeline.requests.get') as mock_get:
            from requests.exceptions import Timeout
            mock_get.side_effect = Timeout("Fallback API timeout")
            
            result = pipeline.fetch_from_fallback()
            
            assert result is None
            assert pipeline.status == FallbackStatus.FAILED
            assert pipeline.error_cause is not None

    def test_trigger_fallback_on_quality_failure(self):
        """Test: Declenchement fallback sur echec qualite critique"""
        pipeline = FallbackPipeline(trace_id="test-trace-123")
        
        # Simuler resultats qualite avec echec critique
        quality_results = [
            Mock(spec=QualityResult, status=QualityStatus.FAIL, match_id="nba-001"),
            Mock(spec=QualityResult, status=QualityStatus.FAIL, match_id="nba-002"),
            Mock(spec=QualityResult, status=QualityStatus.PASS, match_id="nba-003"),
        ]
        
        # 2/3 echecs = 66% > 20% seuil critique
        with patch.object(pipeline, 'fetch_from_fallback') as mock_fetch:
            mock_fetch.return_value = [
                {"external_id": "fallback-001", "home_team": {"id": "lal"}, "away_team": {"id": "gsw"}}
            ]
            
            result = pipeline.trigger_fallback_if_needed(quality_results)
            
            assert result is not None
            assert pipeline.was_triggered is True
            mock_fetch.assert_called_once()

    def test_no_fallback_when_quality_pass(self):
        """Test: Pas de declenchement si qualite OK"""
        pipeline = FallbackPipeline(trace_id="test-trace-123")
        
        # Tous les matchs passent
        quality_results = [
            Mock(spec=QualityResult, status=QualityStatus.PASS, match_id="nba-001"),
            Mock(spec=QualityResult, status=QualityStatus.PASS, match_id="nba-002"),
            Mock(spec=QualityResult, status=QualityStatus.PASS, match_id="nba-003"),
        ]
        
        with patch.object(pipeline, 'fetch_from_fallback') as mock_fetch:
            result = pipeline.trigger_fallback_if_needed(quality_results)
            
            assert result is None
            assert pipeline.was_triggered is False
            mock_fetch.assert_not_called()

    def test_fallback_logging(self):
        """Test: Journalisation du trigger fallback"""
        pipeline = FallbackPipeline(trace_id="test-trace-123")
        
        # Simuler un declenchement
        quality_results = [Mock(spec=QualityResult, status=QualityStatus.FAIL)] * 5
        
        with patch.object(pipeline, 'fetch_from_fallback') as mock_fetch:
            mock_fetch.return_value = [{"external_id": "test"}]
            pipeline.trigger_fallback_if_needed(quality_results)
            
            # Verifier que les evenements ont ete loggues (trigger + success)
            assert len(pipeline.fallback_events) == 2
            trigger_event = pipeline.fallback_events[0]
            assert trigger_event["type"] == "FALLBACK_TRIGGERED"
            assert "timestamp" in trigger_event
            assert "reason" in trigger_event

    def test_fallback_cascading_failure(self):
        """Test: Echec fallback apres echec source primaire"""
        pipeline = FallbackPipeline(trace_id="test-trace-123")
        
        quality_results = [Mock(spec=QualityResult, status=QualityStatus.FAIL)] * 5
        
        # Le mock ne met pas a jour le status, donc on appelle directement pour tester le comportement
        with patch('pipelines.fallback_pipeline.requests.get') as mock_get:
            from requests.exceptions import Timeout
            mock_get.side_effect = Timeout("Fallback API timeout")
            
            result = pipeline.trigger_fallback_if_needed(quality_results)
            
            assert result is None
            assert pipeline.cascading_failure is True


class TestFallbackIntegration:
    """Tests d'integration fallback avec qualite"""

    def test_full_fallback_scenario(self):
        """Test: Scenario complet - echec qualite -> fallback"""
        from quality.quality_checks import QualityChecker
        
        checker = QualityChecker(trace_id="test-trace")
        pipeline = FallbackPipeline(trace_id="test-trace")
        
        # Donnees de mauvaise qualite
        bad_matches = [
            {"external_id": "nba-001"},  # Incomplet
            {"external_id": "nba-002"},  # Incomplet
            {"external_id": "nba-003"},  # Incomplet
            {"external_id": "nba-004"},  # Incomplet
            {"external_id": "nba-005"},  # Incomplet
        ]
        
        # Validation
        quality_results = checker.validate_batch(bad_matches)
        summary = checker.get_quality_summary(quality_results)
        
        # Doit detecter echec critique
        assert summary["critical_failure"] is True
        
        with patch.object(pipeline, 'fetch_from_fallback') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "external_id": "fallback-001",
                    "home_team": {"id": "lal", "name": "Lakers", "city": "LA"},
                    "away_team": {"id": "gsw", "name": "Warriors", "city": "GS"},
                    "scheduled_at": "2024-01-15T20:00:00Z",
                    "season": "2023-24"
                }
            ]
            
            result = pipeline.trigger_fallback_if_needed(quality_results)
            
            assert result is not None
            assert len(result) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests unitaires pour le pipeline d'ingestion NBA
Pattern TDD : tests rouges avant implementation
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le chemin pour imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from pipelines.ingest_pipeline import IngestPipeline, IngestionStatus
from contracts.input_models import MatchInput, TeamInput
from contracts.output_models import IngestionResult


class TestIngestPipeline:
    """Tests pour le pipeline d'ingestion"""

    def test_pipeline_initialization(self):
        """Test: Le pipeline doit s'initialiser avec un trace_id"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        assert pipeline.trace_id == "test-trace-123"
        assert pipeline.status == IngestionStatus.PENDING

    def test_validate_match_contract_valid(self):
        """Test: Validation contrat match valide doit passer"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        valid_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal", "name": "Lakers", "city": "Los Angeles"},
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "scheduled_at": "2024-01-15T20:00:00Z",
            "season": "2023-24",
            "game_type": "regular"
        }
        
        # Doit valider sans erreur
        result = pipeline.validate_match_contract(valid_match)
        assert result is True

    def test_validate_match_contract_invalid_missing_field(self):
        """Test: Validation contrat match invalide (champ manquant) doit echouer"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        invalid_match = {
            "external_id": "nba-2024-001",
            # Missing home_team
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "scheduled_at": "2024-01-15T20:00:00Z"
        }
        
        # Doit lever une exception de validation
        with pytest.raises(ValueError) as exc_info:
            pipeline.validate_match_contract(invalid_match)
        
        assert "home_team" in str(exc_info.value)

    def test_validate_match_contract_invalid_team_structure(self):
        """Test: Validation structure equipe invalide doit echouer"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        invalid_match = {
            "external_id": "nba-2024-001",
            "home_team": {"id": "lal"},  # Missing name and city
            "away_team": {"id": "gsw", "name": "Warriors", "city": "Golden State"},
            "scheduled_at": "2024-01-15T20:00:00Z",
            "season": "2023-24",
            "game_type": "regular"
        }
        
        with pytest.raises(ValueError) as exc_info:
            pipeline.validate_match_contract(invalid_match)
        
        assert "name" in str(exc_info.value) or "city" in str(exc_info.value)

    @patch('pipelines.ingest_pipeline.requests.get')
    def test_fetch_matches_success(self, mock_get):
        """Test: Recuperation matchs API NBA reussie"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        # Mock reponse API
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
        
        result = pipeline.fetch_matches_from_source()
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["external_id"] == "nba-2024-001"
        assert pipeline.status == IngestionStatus.COLLECTING

    @patch('pipelines.ingest_pipeline.requests.get')
    def test_fetch_matches_api_timeout(self, mock_get):
        """Test: Timeout API doit etre geree avec statut echec explicite"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        # Simuler timeout
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("API NBA timeout")
        
        result = pipeline.fetch_matches_from_source()
        
        assert result is None
        assert pipeline.status == IngestionStatus.SOURCE_ERROR
        assert pipeline.error_cause == "SOURCE_TIMEOUT"

    @patch('pipelines.ingest_pipeline.requests.get')
    def test_fetch_matches_api_http_error(self, mock_get):
        """Test: Erreur HTTP API doit etre journalisee avec cause explicite"""
        pipeline = IngestPipeline(trace_id="test-trace-123")

        # Simuler erreur HTTP - lever exception directement lors de l'appel API
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 503
        error = HTTPError("Service Unavailable")
        error.response = mock_response
        mock_get.side_effect = error

        result = pipeline.fetch_matches_from_source()

        assert result is None
        assert pipeline.status == IngestionStatus.SOURCE_ERROR
        assert pipeline.error_cause == "SOURCE_HTTP_ERROR"

    @patch('pipelines.ingest_pipeline.requests.get')
    def test_run_full_pipeline_success(self, mock_get):
        """Test: Pipeline complet reussi"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        # Mock reponse API
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
        
        result = pipeline.run()
        
        assert isinstance(result, IngestionResult)
        assert result.status == "success"
        assert result.trace_id == "test-trace-123"
        assert result.matches_count == 1
        assert result.error_cause is None

    @patch('pipelines.ingest_pipeline.requests.get')
    def test_run_pipeline_source_failure_no_success_state(self, mock_get):
        """Test: Echec source ne doit jamais publier etat succes"""
        pipeline = IngestPipeline(trace_id="test-trace-123")
        
        # Simuler timeout
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("API NBA timeout")
        
        result = pipeline.run()
        
        assert isinstance(result, IngestionResult)
        assert result.status == "error"
        assert result.matches_count == 0
        assert result.error_cause == "SOURCE_TIMEOUT"
        # CRITICAL: Ne jamais avoir statut success si collecte echoue
        assert result.status != "success"

    def test_ingestion_result_structure(self):
        """Test: Structure du resultat d'ingestion"""
        result = IngestionResult(
            status="success",
            trace_id="test-trace-123",
            run_id="run-456",
            matches_count=2,
            matches=[{"id": "1"}, {"id": "2"}],
            collected_at=datetime.utcnow(),
            error_cause=None
        )
        
        assert result.status == "success"
        assert result.trace_id == "test-trace-123"
        assert result.matches_count == 2


class TestInputModels:
    """Tests pour les modeles de validation input"""

    def test_team_input_valid(self):
        """Test: TeamInput valide"""
        team = TeamInput(id="lal", name="Lakers", city="Los Angeles")
        assert team.id == "lal"
        assert team.name == "Lakers"
        assert team.city == "Los Angeles"

    def test_team_input_invalid_missing_name(self):
        """Test: TeamInput invalide (nom manquant)"""
        with pytest.raises(ValueError):
            TeamInput(id="lal", city="Los Angeles")  # Missing name

    def test_match_input_valid(self):
        """Test: MatchInput valide"""
        match = MatchInput(
            external_id="nba-2024-001",
            home_team=TeamInput(id="lal", name="Lakers", city="Los Angeles"),
            away_team=TeamInput(id="gsw", name="Warriors", city="Golden State"),
            scheduled_at="2024-01-15T20:00:00Z",
            season="2023-24",
            game_type="regular"
        )
        assert match.external_id == "nba-2024-001"
        assert match.home_team.name == "Lakers"
        assert match.away_team.name == "Warriors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

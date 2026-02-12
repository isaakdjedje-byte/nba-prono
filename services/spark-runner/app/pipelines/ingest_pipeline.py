"""
Pipeline d'ingestion des matchs NBA
Implementation du service spark-runner
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import requests
from requests.exceptions import Timeout, HTTPError, RequestException

# Import des contrats
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.input_models import MatchInput, TeamInput
from contracts.output_models import IngestionResult, IngestionStatus

# Configuration logging structure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestPipeline:
    """
    Pipeline d'ingestion des matchs NBA depuis source primaire
    Responsabilites:
    - Collecte API externe
    - Validation contrat de donnees
    - Journalisation statut (succes/echec)
    """
    
    def __init__(self, trace_id: Optional[str] = None, source_url: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.source_url = source_url or "https://api.nba.com/v1/games/today"
        self.status = IngestionStatus.PENDING
        self.error_cause: Optional[str] = None
        self.error_details: Optional[str] = None
        self.collected_matches: List[Dict[str, Any]] = []
        self.run_id: str = str(uuid.uuid4())
        
        logger.info(f"[{self.trace_id}] Pipeline initialise - run_id: {self.run_id}")
    
    def validate_match_contract(self, match_data: Dict[str, Any]) -> bool:
        """
        Valide le contrat de donnees d'un match entrant
        
        Args:
            match_data: Donnees brute du match
            
        Returns:
            bool: True si valide
            
        Raises:
            ValueError: Si validation echoue avec details
        """
        try:
            # Validation Pydantic stricte
            match = MatchInput(**match_data)
            logger.debug(f"[{self.trace_id}] Match valide: {match.external_id}")
            return True
        except Exception as e:
            logger.error(f"[{self.trace_id}] Validation echouee: {e}")
            raise ValueError(f"Invalid match data: {e}")
    
    def fetch_matches_from_source(self) -> Optional[List[Dict[str, Any]]]:
        """
        Recupere les matchs depuis la source primaire (API NBA)
        
        Returns:
            List[Dict]: Liste des matchs ou None si echec
        """
        self.status = IngestionStatus.COLLECTING
        logger.info(f"[{self.trace_id}] Debut collecte depuis {self.source_url}")
        
        try:
            # Appel API avec timeout
            response = requests.get(
                self.source_url,
                timeout=30,  # 30 secondes timeout
                headers={
                    "Accept": "application/json",
                    "X-Trace-Id": self.trace_id
                }
            )
            response.raise_for_status()
            
            data = response.json()
            matches = data.get("games", [])
            
            logger.info(f"[{self.trace_id}] Collecte reussie: {len(matches)} matchs")
            return matches
            
        except Timeout as e:
            self.status = IngestionStatus.SOURCE_ERROR
            self.error_cause = "SOURCE_TIMEOUT"
            self.error_details = f"API timeout apres 30s: {e}"
            logger.error(f"[{self.trace_id}] Timeout source: {e}")
            return None
            
        except HTTPError as e:
            self.status = IngestionStatus.SOURCE_ERROR
            self.error_cause = "SOURCE_HTTP_ERROR"
            self.error_details = f"HTTP {e.response.status_code if hasattr(e, 'response') else 'unknown'}"
            logger.error(f"[{self.trace_id}] HTTP error: {e}")
            return None
            
        except RequestException as e:
            self.status = IngestionStatus.SOURCE_ERROR
            self.error_cause = "SOURCE_UNAVAILABLE"
            self.error_details = f"Request failed: {e}"
            logger.error(f"[{self.trace_id}] Source unavailable: {e}")
            return None
    
    def validate_matches_batch(self, matches: List[Dict[str, Any]]) -> List[MatchInput]:
        """
        Valide un lot de matchs
        
        Args:
            matches: Liste des matchs bruts
            
        Returns:
            List[MatchInput]: Matchs valides
        """
        self.status = IngestionStatus.VALIDATING
        valid_matches = []
        
        for match_data in matches:
            try:
                if self.validate_match_contract(match_data):
                    match = MatchInput(**match_data)
                    valid_matches.append(match)
            except ValueError as e:
                logger.warning(f"[{self.trace_id}] Match invalide ignore: {e}")
                continue
        
        logger.info(f"[{self.trace_id}] Validation: {len(valid_matches)}/{len(matches)} matchs valides")
        return valid_matches
    
    def run(self) -> IngestionResult:
        """
        Execute le pipeline complet d'ingestion
        
        Returns:
            IngestionResult: Resultat avec statut et metadonnees
        """
        started_at = datetime.utcnow()
        logger.info(f"[{self.trace_id}] === Demarrage pipeline ingestion ===")
        
        try:
            # 1. Collecte
            raw_matches = self.fetch_matches_from_source()
            
            if raw_matches is None:
                # Echec collecte - retourner erreur explicite
                # CRITICAL: Ne jamais publier etat succes si collecte echoue
                return IngestionResult(
                    status="error",
                    trace_id=self.trace_id,
                    run_id=self.run_id,
                    matches_count=0,
                    matches=[],
                    error_cause=self.error_cause,
                    error_details=self.error_details
                )
            
            # 2. Validation
            valid_matches = self.validate_matches_batch(raw_matches)
            
            # 3. Preparation resultat
            matches_data = [m.model_dump() for m in valid_matches]
            self.collected_matches = matches_data
            self.status = IngestionStatus.SUCCESS
            
            result = IngestionResult(
                status="success",
                trace_id=self.trace_id,
                run_id=self.run_id,
                matches_count=len(valid_matches),
                matches=matches_data,
                error_cause=None,
                error_details=None
            )
            
            logger.info(f"[{self.trace_id}] === Pipeline succes: {len(valid_matches)} matchs ===")
            return result
            
        except Exception as e:
            self.status = IngestionStatus.SOURCE_ERROR
            self.error_cause = "PIPELINE_ERROR"
            self.error_details = str(e)
            logger.error(f"[{self.trace_id}] Pipeline erreur: {e}")
            
            return IngestionResult(
                status="error",
                trace_id=self.trace_id,
                run_id=self.run_id,
                matches_count=0,
                matches=[],
                error_cause=self.error_cause,
                error_details=self.error_details
            )


if __name__ == "__main__":
    # Test manuel du pipeline
    pipeline = IngestPipeline(trace_id="manual-test-001")
    result = pipeline.run()
    print(f"Result: {result.model_dump_json_safe()}")

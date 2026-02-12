"""
Pipeline de fallback vers source secondaire
Basculement automatique sur echec qualite critique
"""
import logging
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import requests
from requests.exceptions import Timeout, HTTPError, RequestException

# Import qualite
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quality.quality_checks import QualityResult, QualityStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FallbackStatus(Enum):
    """Statuts du pipeline fallback"""
    PENDING = "pending"
    TRIGGERED = "triggered"
    SUCCESS = "success"
    FAILED = "failed"


class FallbackPipeline:
    """
    Pipeline de fallback vers source secondaire
    Se declenche automatiquement sur echec qualite critique
    """
    
    # Seuil pour declencher fallback ( utilise celui de QualityChecker)
    CRITICAL_FAILURE_THRESHOLD = 0.20
    
    def __init__(self, 
                 trace_id: Optional[str] = None, 
                 fallback_url: Optional[str] = None):
        """
        Initialise le pipeline fallback
        
        Args:
            trace_id: ID de tracabilite
            fallback_url: URL de la source secondaire
        """
        self.trace_id = trace_id or str(uuid.uuid4())
        self.fallback_url = fallback_url or "https://api.thesportsdb.com/v1/json/3/eventsnextleague.php?id=4387"
        self.status = FallbackStatus.PENDING
        self.error_cause: Optional[str] = None
        self.error_details: Optional[str] = None
        self.was_triggered: bool = False
        self.cascading_failure: bool = False
        self.fallback_events: List[Dict[str, Any]] = []
        self.triggered_at: Optional[datetime] = None
        
        logger.info(f"[{self.trace_id}] FallbackPipeline initialise - source: {self.fallback_url}")
    
    def fetch_from_fallback(self) -> Optional[List[Dict[str, Any]]]:
        """
        Recupere les donnees depuis la source secondaire
        
        Returns:
            Liste des matchs ou None si echec
        """
        self.status = FallbackStatus.TRIGGERED
        logger.info(f"[{self.trace_id}] Tentative fallback depuis {self.fallback_url}")
        
        try:
            response = requests.get(
                self.fallback_url,
                timeout=30,
                headers={
                    "Accept": "application/json",
                    "X-Trace-Id": self.trace_id
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Adapter selon format API (TheSportsDB ou autre)
            if "events" in data:
                matches = self._convert_thesportsdb_format(data.get("events", []))
            elif "games" in data:
                matches = data.get("games", [])
            else:
                matches = data if isinstance(data, list) else []
            
            if matches:
                self.status = FallbackStatus.SUCCESS
                logger.info(f"[{self.trace_id}] Fallback reussi: {len(matches)} matchs recuperes")
                return matches
            else:
                self.status = FallbackStatus.FAILED
                self.error_cause = "FALLBACK_EMPTY_RESPONSE"
                self.error_details = "Fallback API returned empty data"
                logger.warning(f"[{self.trace_id}] Fallback: reponse vide")
                return None
                
        except Timeout as e:
            self.status = FallbackStatus.FAILED
            self.error_cause = "FALLBACK_TIMEOUT"
            self.error_details = f"Fallback API timeout: {e}"
            logger.error(f"[{self.trace_id}] Fallback timeout: {e}")
            return None
            
        except HTTPError as e:
            self.status = FallbackStatus.FAILED
            self.error_cause = "FALLBACK_HTTP_ERROR"
            self.error_details = f"HTTP {getattr(e.response, 'status_code', 'unknown')}"
            logger.error(f"[{self.trace_id}] Fallback HTTP error: {e}")
            return None
            
        except RequestException as e:
            self.status = FallbackStatus.FAILED
            self.error_cause = "FALLBACK_UNAVAILABLE"
            self.error_details = str(e)
            logger.error(f"[{self.trace_id}] Fallback unavailable: {e}")
            return None
            
        except Exception as e:
            self.status = FallbackStatus.FAILED
            self.error_cause = "FALLBACK_ERROR"
            self.error_details = str(e)
            logger.error(f"[{self.trace_id}] Fallback error: {e}")
            return None
    
    def _convert_thesportsdb_format(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """
        Convertit format TheSportsDB vers notre format standard
        
        Args:
            events: Evenements TheSportsDB
            
        Returns:
            Liste matchs au format standard
        """
        matches = []
        
        for event in events:
            try:
                match = {
                    "external_id": f"tsdb-{event.get('idEvent', '')}",
                    "home_team": {
                        "id": event.get('idHomeTeam', 'home')[:10].lower(),
                        "name": event.get('strHomeTeam', 'Home Team'),
                        "city": event.get('strHomeTeam', 'Home').split()[-1]
                    },
                    "away_team": {
                        "id": event.get('idAwayTeam', 'away')[:10].lower(),
                        "name": event.get('strAwayTeam', 'Away Team'),
                        "city": event.get('strAwayTeam', 'Away').split()[-1]
                    },
                    "scheduled_at": self._parse_date(event.get('strTimestamp') or event.get('dateEvent')),
                    "season": self._derive_season(event.get('strSeason') or event.get('dateEvent')),
                    "game_type": "regular" if event.get('strStatus') != 'FINISHED' else "finished"
                }
                matches.append(match)
            except Exception as e:
                logger.warning(f"[{self.trace_id}] Erreur conversion event: {e}")
                continue
        
        return matches
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """Parse et formate la date"""
        if not date_str:
            return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        try:
            # Essayer ISO 8601
            if 'T' in date_str:
                return date_str
            # Essayer format date simple
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.isoformat() + "Z"
        except Exception:
            return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    
    def _derive_season(self, season_str: Optional[str]) -> str:
        """Derive la saison depuis string"""
        if season_str and "-" in season_str:
            return season_str
        
        # Deriver de l'annee courante
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        year = now.year
        if now.month < 7:
            return f"{year-1}-{str(year)[2:]}"
        else:
            return f"{year}-{str(year+1)[2:]}"
    
    def trigger_fallback_if_needed(self, quality_results: List[QualityResult]) -> Optional[List[Dict[str, Any]]]:
        """
        Declenche le fallback si necessaire base sur resultats qualite
        
        Args:
            quality_results: Resultats de validation qualite
            
        Returns:
            Donnees fallback ou None
        """
        # Calculer taux d'echec
        if not quality_results:
            logger.info(f"[{self.trace_id}] Aucun resultat qualite, pas de fallback necessaire")
            return None
        
        fail_count = sum(1 for r in quality_results if r.status == QualityStatus.FAIL)
        total_count = len(quality_results)
        fail_rate = fail_count / total_count
        
        logger.info(f"[{self.trace_id}] Qualite: {fail_count}/{total_count} echecs ({fail_rate:.1%})")
        
        # Verifier si seuil critique atteint
        if fail_rate < self.CRITICAL_FAILURE_THRESHOLD:
            logger.info(f"[{self.trace_id}] Qualite acceptable ({fail_rate:.1%} < {self.CRITICAL_FAILURE_THRESHOLD:.0%}), pas de fallback")
            self.was_triggered = False
            return None
        
        # Declencher fallback
        logger.warning(f"[{self.trace_id}] SEUIL CRITIQUE ATTEINT - Declenchement fallback!")
        self.was_triggered = True
        self.triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Logger l'evenement
        event = {
            "type": "FALLBACK_TRIGGERED",
            "timestamp": self.triggered_at.isoformat(),
            "reason": f"Quality failure rate {fail_rate:.1%} exceeds threshold {self.CRITICAL_FAILURE_THRESHOLD:.0%}",
            "quality_summary": {
                "total": total_count,
                "failed": fail_count,
                "fail_rate": round(fail_rate, 2)
            },
            "trace_id": self.trace_id
        }
        self.fallback_events.append(event)
        
        # Executer fallback
        fallback_data = self.fetch_from_fallback()
        
        if fallback_data is None:
            # Echec cascade: source primaire + fallback
            self.cascading_failure = True
            logger.error(f"[{self.trace_id}] ECHEC CASCADE: Source primaire et fallback ont echoue")
            
            # Logger l'echec cascade
            fail_event = {
                "type": "FALLBACK_FAILED",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "reason": self.error_cause or "Unknown",
                "details": self.error_details,
                "cascading_failure": True,
                "trace_id": self.trace_id
            }
            self.fallback_events.append(fail_event)
        else:
            # Succes fallback
            success_event = {
                "type": "FALLBACK_SUCCESS",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "matches_recovered": len(fallback_data),
                "trace_id": self.trace_id
            }
            self.fallback_events.append(success_event)
        
        return fallback_data
    
    def get_fallback_report(self) -> Dict[str, Any]:
        """
        Genere un rapport de fallback
        
        Returns:
            Dictionnaire avec details du fallback
        """
        return {
            "was_triggered": self.was_triggered,
            "status": self.status.value,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "cascading_failure": self.cascading_failure,
            "error_cause": self.error_cause,
            "error_details": self.error_details,
            "events": self.fallback_events,
            "trace_id": self.trace_id
        }

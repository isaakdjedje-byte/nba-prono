"""
No-Bet Guard - Gestion du mode degrade
Protection automatique quand qualite insuffisante ou fallback en echec
"""
import logging
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DegradedMode(Enum):
    """Modes de fonctionnement du systeme"""
    NORMAL = "normal"
    DEGRADED_FALLBACK = "degraded-fallback"
    DEGRADED_NO_BET = "degraded-no-bet"


@dataclass
class GuardDecision:
    """Decision du guard no-bet"""
    mode: DegradedMode
    allow_betting: bool
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "mode": self.mode.value,
            "allow_betting": self.allow_betting,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class NoBetGuard:
    """
    Guard de protection no-bet automatique
    Prend des decisions basees sur la qualite data et le statut fallback
    """
    
    def __init__(self, trace_id: Optional[str] = None):
        """
        Initialise le guard
        
        Args:
            trace_id: ID de tracabilite
        """
        self.trace_id = trace_id or str(uuid.uuid4())
        self.is_degraded: bool = False
        self.current_mode: DegradedMode = DegradedMode.NORMAL
        self.audit_trail: List[Dict[str, Any]] = []
        
        logger.info(f"[{self.trace_id}] NoBetGuard initialise")
    
    def evaluate_run_status(
        self, 
        quality_summary: Dict[str, Any],
        fallback_result: Optional[List[Dict[str, Any]]]
    ) -> GuardDecision:
        """
        Evalue le statut du run et prend une decision
        
        Args:
            quality_summary: Resume qualite du run
            fallback_result: Resultat du fallback (None si pas declenche ou echoue)
            
        Returns:
            GuardDecision avec mode et permissions
        """
        critical_failure = quality_summary.get("critical_failure", False)
        pass_rate = quality_summary.get("pass_rate", 1.0)
        
        logger.info(f"[{self.trace_id}] Evaluation - qualite: {pass_rate:.1%}, "
                   f"critique: {critical_failure}, fallback: {fallback_result is not None}")
        
        # Decision tree
        if not critical_failure:
            # Qualite acceptable - mode normal
            decision = GuardDecision(
                mode=DegradedMode.NORMAL,
                allow_betting=True,
                reason="Qualite des donnees acceptable",
                metadata={
                    "quality_pass_rate": pass_rate,
                    "critical_failure": False
                }
            )
            
        elif fallback_result is not None:
            # Qualite critique mais fallback reussi - mode degrade avec fallback
            decision = GuardDecision(
                mode=DegradedMode.DEGRADED_FALLBACK,
                allow_betting=True,  # On permet mais avec prudence
                reason=f"Qualite critique ({pass_rate:.0%} pass) mais fallback reussi - "
                       f"utilisation donnees secondaires avec vigilance",
                metadata={
                    "quality_pass_rate": pass_rate,
                    "critical_failure": True,
                    "fallback_used": True,
                    "fallback_matches": len(fallback_result)
                }
            )
            
        else:
            # Qualite critique ET fallback echoue - mode degrade no-bet
            decision = GuardDecision(
                mode=DegradedMode.DEGRADED_NO_BET,
                allow_betting=False,  # BLOCAGE
                reason=f"QUALITE INSUFFISANTE ({pass_rate:.0%} pass) ET FALLBACK EN ECHEC - "
                       f"Systeme en mode no-bet pour protection. "
                       f"Donnees corrompues ou incompletes detectees. "
                       f"Requiert investigation operateur.",
                metadata={
                    "quality_pass_rate": pass_rate,
                    "critical_failure": True,
                    "fallback_used": False,
                    "fallback_failed": True,
                    "blocking_reason": "cascading_failure"
                }
            )
        
        # Mise a jour etat interne
        self.current_mode = decision.mode
        self.is_degraded = decision.mode != DegradedMode.NORMAL
        
        # Audit
        self._log_decision(decision, quality_summary)
        
        logger.info(f"[{self.trace_id}] Decision: {decision.mode.value}, "
                   f"betting: {decision.allow_betting}")
        
        return decision
    
    def _log_decision(self, decision: GuardDecision, quality_summary: Dict[str, Any]):
        """Loggue la decision dans l'audit trail"""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "mode": decision.mode.value,
            "allow_betting": decision.allow_betting,
            "reason": decision.reason,
            "quality_summary": {
                "pass_rate": quality_summary.get("pass_rate"),
                "critical_failure": quality_summary.get("critical_failure"),
                "total_matches": quality_summary.get("total_matches"),
                "failed": quality_summary.get("failed")
            },
            "trace_id": self.trace_id
        }
        
        self.audit_trail.append(audit_entry)
        
        # Log niveau approprie
        if decision.mode == DegradedMode.DEGRADED_NO_BET:
            logger.error(f"[{self.trace_id}] MODE DEGRADE NO-BET ACTIVE - {decision.reason}")
        elif decision.mode == DegradedMode.DEGRADED_FALLBACK:
            logger.warning(f"[{self.trace_id}] Mode degrade fallback - {decision.reason}")
        else:
            logger.info(f"[{self.trace_id}] Mode normal - qualite OK")
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """
        Retourne l'historique des decisions
        
        Returns:
            Liste des entrees d'audit
        """
        return self.audit_trail.copy()
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        Retourne le statut courant du guard
        
        Returns:
            Dictionnaire avec statut complet
        """
        return {
            "is_degraded": self.is_degraded,
            "current_mode": self.current_mode.value,
            "audit_count": len(self.audit_trail),
            "trace_id": self.trace_id,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
    
    def force_degraded_mode(self, reason: str) -> GuardDecision:
        """
        Force le mode degrade (pour usage administratif)
        
        Args:
            reason: Raison du forçage
            
        Returns:
            GuardDecision forcee
        """
        decision = GuardDecision(
            mode=DegradedMode.DEGRADED_NO_BET,
            allow_betting=False,
            reason=f"FORCAGE MANUEL: {reason}",
            metadata={"forced": True}
        )
        
        self.current_mode = decision.mode
        self.is_degraded = True
        self._log_decision(decision, {"forced": True})
        
        logger.warning(f"[{self.trace_id}] MODE DEGRADE FORCE - {reason}")
        
        return decision
    
    def reset_to_normal(self, reason: str) -> GuardDecision:
        """
        Retour au mode normal (apres resolution)
        
        Args:
            reason: Raison du retour normal
            
        Returns:
            GuardDecision normale
        """
        decision = GuardDecision(
            mode=DegradedMode.NORMAL,
            allow_betting=True,
            reason=f"RETOUR NORMAL: {reason}",
            metadata={"reset": True}
        )
        
        self.current_mode = decision.mode
        self.is_degraded = False
        self._log_decision(decision, {"reset": True})
        
        logger.info(f"[{self.trace_id}] Retour mode normal - {reason}")
        
        return decision

"""
Regles de validation qualite data
Detection anomalies schema/contenu
"""
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QualityStatus(Enum):
    """Statuts de validation qualite"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class RuleResult:
    """Resultat d'une regle de validation"""
    rule_name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # error, warning


@dataclass
class QualityResult:
    """Resultat complet de validation qualite pour un match"""
    match_id: str
    status: QualityStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rule_results: List[RuleResult] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class QualityRule:
    """
    Regles de validation qualite predefinies
    """
    
    @staticmethod
    def completeness_check(required_fields: List[str]) -> 'QualityRule':
        """
        Cree une regle de verification de compleude
        
        Args:
            required_fields: Liste des champs requis
            
        Returns:
            QualityRule instance
        """
        rule = QualityRule()
        rule.name = "completeness"
        rule.required_fields = required_fields
        rule.check = lambda match_data: rule._check_completeness(match_data)
        return rule
    
    @staticmethod
    def validity_check() -> 'QualityRule':
        """
        Cree une regle de verification de validite
        
        Returns:
            QualityRule instance
        """
        rule = QualityRule()
        rule.name = "validity"
        rule.check = lambda match_data: rule._check_validity(match_data)
        return rule
    
    @staticmethod
    def consistency_check() -> 'QualityRule':
        """
        Cree une regle de verification de coherence
        
        Returns:
            QualityRule instance
        """
        rule = QualityRule()
        rule.name = "consistency"
        rule.check = lambda match_data: rule._check_consistency(match_data)
        return rule
    
    @staticmethod
    def timeliness_check(max_age_hours: int = 24) -> 'QualityRule':
        """
        Cree une regle de verification de fraicheur
        
        Args:
            max_age_hours: Age maximum acceptable en heures
            
        Returns:
            QualityRule instance
        """
        rule = QualityRule()
        rule.name = "timeliness"
        rule.max_age_hours = max_age_hours
        rule.check = lambda match_data: rule._check_timeliness(match_data)
        return rule
    
    def __init__(self):
        self.name = ""
        self.check = None
    
    def _check_completeness(self, match_data: Dict[str, Any]) -> RuleResult:
        """Verifie que tous les champs requis sont presents"""
        missing_fields = []
        
        for field in self.required_fields:
            if field not in match_data or match_data[field] is None:
                missing_fields.append(field)
        
        passed = len(missing_fields) == 0
        
        return RuleResult(
            rule_name="completeness",
            passed=passed,
            details={"missing_fields": missing_fields},
            severity="error" if not passed else "info"
        )
    
    def _check_validity(self, match_data: Dict[str, Any]) -> RuleResult:
        """Verifie la validite des valeurs"""
        invalid_fields = []
        
        # Check scores non negatifs
        for score_field in ["home_score", "away_score"]:
            if score_field in match_data:
                score = match_data[score_field]
                if score is not None and (not isinstance(score, (int, float)) or score < 0):
                    invalid_fields.append(f"{score_field}: negative or invalid value")
        
        # Check format date si present
        if "scheduled_at" in match_data and match_data["scheduled_at"]:
            try:
                scheduled = match_data["scheduled_at"]
                if isinstance(scheduled, str):
                    # Tenter de parser ISO 8601
                    scheduled.replace('Z', '+00:00')
            except Exception:
                invalid_fields.append("scheduled_at: invalid datetime format")
        
        passed = len(invalid_fields) == 0
        
        return RuleResult(
            rule_name="validity",
            passed=passed,
            details={"invalid_fields": invalid_fields},
            severity="error" if not passed else "info"
        )
    
    def _check_consistency(self, match_data: Dict[str, Any]) -> RuleResult:
        """Verifie la coherence interne des donnees"""
        errors = []
        
        # Check que home_team et away_team sont differents
        if "home_team" in match_data and "away_team" in match_data:
            home = match_data["home_team"]
            away = match_data["away_team"]
            
            if isinstance(home, dict) and isinstance(away, dict):
                home_id = home.get("id", "").lower()
                away_id = away.get("id", "").lower()
                
                if home_id and away_id and home_id == away_id:
                    errors.append("same_team: home and away teams are identical")
        
        # Check qu'il y a bien 2 equipes
        if "home_team" not in match_data or "away_team" not in match_data:
            errors.append("missing_team: need both home and away teams")
        
        passed = len(errors) == 0
        
        return RuleResult(
            rule_name="consistency",
            passed=passed,
            details={"errors": errors},
            severity="error" if not passed else "info"
        )
    
    def _check_timeliness(self, match_data: Dict[str, Any]) -> RuleResult:
        """Verifie la fraicheur des donnees"""
        errors = []
        
        if "scheduled_at" in match_data and match_data["scheduled_at"]:
            try:
                scheduled_str = match_data["scheduled_at"]
                # Parser ISO 8601
                if isinstance(scheduled_str, str):
                    scheduled_str = scheduled_str.replace('Z', '+00:00')
                    scheduled = datetime.fromisoformat(scheduled_str)
                else:
                    scheduled = scheduled_str
                
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                age = now - scheduled.replace(tzinfo=None)
                
                if age > timedelta(hours=self.max_age_hours):
                    errors.append(f"stale_data: match is {age.total_seconds() / 3600:.1f} hours old (max: {self.max_age_hours})")
                    
            except Exception as e:
                errors.append(f"timeliness_check_error: {e}")
        
        passed = len(errors) == 0
        
        return RuleResult(
            rule_name="timeliness",
            passed=passed,
            details={"errors": errors},
            severity="warning" if not passed else "info"
        )


class QualityChecker:
    """
    Validateur qualite pour les matchs NBA
    Orquestre l'execution de toutes les regles de qualite
    """
    
    # Seuil critique: >20% d'echecs declenche fallback
    CRITICAL_FAILURE_THRESHOLD = 0.20
    
    def __init__(self, trace_id: Optional[str] = None):
        """
        Initialise le checker avec les regles par defaut
        
        Args:
            trace_id: ID de tracabilite pour correlation logs
        """
        self.trace_id = trace_id or "quality-check"
        self.rules = self._setup_default_rules()
        logger.info(f"[{self.trace_id}] QualityChecker initialise avec {len(self.rules)} regles")
    
    def _setup_default_rules(self) -> List[QualityRule]:
        """Configure les regles de qualite par defaut"""
        return [
            QualityRule.completeness_check(required_fields=[
                "external_id", "home_team", "away_team", "scheduled_at", "season"
            ]),
            QualityRule.validity_check(),
            QualityRule.consistency_check(),
            QualityRule.timeliness_check(max_age_hours=24)
        ]
    
    def validate_match(self, match_data: Dict[str, Any]) -> QualityResult:
        """
        Valide un match contre toutes les regles
        
        Args:
            match_data: Donnees du match a valider
            
        Returns:
            QualityResult avec statut et erreurs
        """
        match_id = match_data.get("external_id", "unknown")
        errors = []
        warnings = []
        rule_results = []
        
        logger.debug(f"[{self.trace_id}] Validation qualite match: {match_id}")
        
        for rule in self.rules:
            try:
                result = rule.check(match_data)
                rule_results.append(result)
                
                if not result.passed:
                    if result.severity == "error":
                        errors.append(f"{result.rule_name}: {result.details}")
                    else:
                        warnings.append(f"{result.rule_name}: {result.details}")
                        
            except Exception as e:
                logger.error(f"[{self.trace_id}] Erreur regle {rule.name}: {e}")
                errors.append(f"{rule.name}_error: {str(e)}")
        
        # Determine status global
        if errors:
            status = QualityStatus.FAIL
        elif warnings:
            status = QualityStatus.WARNING
        else:
            status = QualityStatus.PASS
        
        result = QualityResult(
            match_id=match_id,
            status=status,
            errors=errors,
            warnings=warnings,
            rule_results=rule_results
        )
        
        logger.info(f"[{self.trace_id}] Match {match_id}: {status.value} ({len(errors)} erreurs, {len(warnings)} warnings)")
        return result
    
    def validate_batch(self, matches: List[Dict[str, Any]]) -> List[QualityResult]:
        """
        Valide un lot de matchs
        
        Args:
            matches: Liste des matchs a valider
            
        Returns:
            Liste des QualityResult
        """
        logger.info(f"[{self.trace_id}] Validation batch de {len(matches)} matchs")
        
        results = []
        for match in matches:
            result = self.validate_match(match)
            results.append(result)
        
        # Resume
        pass_count = sum(1 for r in results if r.status == QualityStatus.PASS)
        fail_count = sum(1 for r in results if r.status == QualityStatus.FAIL)
        
        logger.info(f"[{self.trace_id}] Batch complete: {pass_count} OK, {fail_count} FAIL")
        return results
    
    def get_quality_summary(self, results: List[QualityResult]) -> Dict[str, Any]:
        """
        Calcule un resume qualite pour le run
        
        Args:
            results: Liste des resultats de validation
            
        Returns:
            Dictionnaire avec metriques qualite
        """
        total = len(results)
        if total == 0:
            return {
                "total_matches": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "critical_failure": False
            }
        
        passed = sum(1 for r in results if r.status == QualityStatus.PASS)
        failed = total - passed
        pass_rate = passed / total
        
        # Critical si >20% d'echecs
        critical_failure = pass_rate < (1 - self.CRITICAL_FAILURE_THRESHOLD)
        
        summary = {
            "total_matches": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 2),
            "critical_failure": critical_failure,
            "threshold": self.CRITICAL_FAILURE_THRESHOLD
        }
        
        if critical_failure:
            logger.warning(f"[{self.trace_id}] SEUIL CRITIQUE ATTEINT: {pass_rate:.1%} pass rate (seuil: {1-self.CRITICAL_FAILURE_THRESHOLD:.0%})")
        
        return summary

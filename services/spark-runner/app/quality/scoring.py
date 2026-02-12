"""
Scoring qualite par match et aggregation par run
"""
import logging
from typing import Dict, Any, List
from dataclasses import dataclass

from .quality_checks import QualityResult, QualityStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MatchQualityScore:
    """Score qualite pour un match individuel"""
    match_id: str
    score: float  # 0-100
    status: str  # PASS, FAIL, WARNING
    details: Dict[str, Any]


class QualityScorer:
    """
    Calculateur de scores qualite
    """
    
    # Poids des differents types d'erreurs
    ERROR_WEIGHT = 50  # Points deduits par erreur
    WARNING_WEIGHT = 10  # Points deduits par warning
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_match_score(self, quality_result: QualityResult) -> MatchQualityScore:
        """
        Calcule un score qualite (0-100) pour un match
        
        Args:
            quality_result: Resultat de validation qualite
            
        Returns:
            MatchQualityScore avec score calcule
        """
        score = 100.0
        
        # Deductions pour erreurs
        score -= len(quality_result.errors) * self.ERROR_WEIGHT
        
        # Deductions pour warnings
        score -= len(quality_result.warnings) * self.WARNING_WEIGHT
        
        # Borner entre 0 et 100
        score = max(0.0, min(100.0, score))
        
        # Determine status base sur score
        if score >= 90:
            status = "PASS"
        elif score >= 70:
            status = "WARNING"
        else:
            status = "FAIL"
        
        details = {
            "error_count": len(quality_result.errors),
            "warning_count": len(quality_result.warnings),
            "errors": quality_result.errors[:5],  # Limit details
            "warnings": quality_result.warnings[:5]
        }
        
        return MatchQualityScore(
            match_id=quality_result.match_id,
            score=round(score, 2),
            status=status,
            details=details
        )
    
    def calculate_batch_scores(self, results: List[QualityResult]) -> List[MatchQualityScore]:
        """
        Calcule les scores pour un lot de matchs
        
        Args:
            results: Liste des resultats de validation
            
        Returns:
            Liste des scores
        """
        return [self.calculate_match_score(r) for r in results]
    
    def aggregate_run_scores(self, match_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Agrege les scores d'un run complet
        
        Args:
            match_scores: Liste des scores individuels (dictionnaires)
            
        Returns:
            Dictionnaire avec metriques agregees
        """
        if not match_scores:
            return {
                "total_matches": 0,
                "passed_matches": 0,
                "failed_matches": 0,
                "warning_matches": 0,
                "average_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
                "pass_rate": 0.0
            }
        
        total = len(match_scores)
        scores = [m.get("score", 0) for m in match_scores]
        
        passed = sum(1 for m in match_scores if m.get("status") == "PASS")
        failed = sum(1 for m in match_scores if m.get("status") == "FAIL")
        warnings = sum(1 for m in match_scores if m.get("status") == "WARNING")
        
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        pass_rate = passed / total
        
        aggregate = {
            "total_matches": total,
            "passed_matches": passed,
            "failed_matches": failed,
            "warning_matches": warnings,
            "average_score": round(avg_score, 2),
            "min_score": round(min_score, 2),
            "max_score": round(max_score, 2),
            "pass_rate": round(pass_rate, 2)
        }
        
        logger.info(f"Run quality aggregate: {passed}/{total} passed (rate: {pass_rate:.1%}, avg: {avg_score:.1f})")
        return aggregate
    
    def get_quality_grade(self, score: float) -> str:
        """
        Attribue une note qualite basee sur le score
        
        Args:
            score: Score 0-100
            
        Returns:
            Lettre grade (A, B, C, D, F)
        """
        if score >= 95:
            return "A"
        elif score >= 85:
            return "B"
        elif score >= 75:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

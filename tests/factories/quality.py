"""
Quality Factories

Factory functions for creating mock quality-related data.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def create_mock_quality_check(
    match_id: str = "match-001",
    run_id: str = "run-001",
    passed: bool = True,
    completeness_score: float = 1.0,
    validity_score: float = 1.0,
    consistency_score: float = 1.0,
    timeliness_score: float = 1.0,
    overall_score: float = 1.0,
    failures: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock quality check for testing.
    
    Args:
        match_id: Match identifier
        run_id: Run identifier
        passed: Whether quality check passed
        completeness_score: Completeness score (0-1)
        validity_score: Validity score (0-1)
        consistency_score: Consistency score (0-1)
        timeliness_score: Timeliness score (0-1)
        overall_score: Overall quality score (0-1)
        failures: List of failure reasons
        **kwargs: Additional fields to override
        
    Returns:
        Mock quality check dictionary
    """
    if failures is None and not passed:
        failures = ["missing_home_team_stats"]
    
    check = {
        "id": f"quality-{match_id}",
        "matchId": match_id,
        "runId": run_id,
        "passed": passed,
        "scores": {
            "completeness": completeness_score,
            "validity": validity_score,
            "consistency": consistency_score,
            "timeliness": timeliness_score,
            "overall": overall_score,
        },
        "failures": failures or [],
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
    check.update(kwargs)
    return check


def create_mock_quality_report(
    run_id: str = "run-001",
    total_matches: int = 10,
    passed_matches: int = 8,
    failed_matches: int = 2,
    fallback_triggered: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock quality report for testing.
    
    Args:
        run_id: Run identifier
        total_matches: Total number of matches checked
        passed_matches: Number of matches that passed quality check
        failed_matches: Number of matches that failed quality check
        fallback_triggered: Whether fallback was triggered
        **kwargs: Additional fields to override
        
    Returns:
        Mock quality report dictionary
    """
    pass_rate = passed_matches / total_matches if total_matches > 0 else 0
    
    report = {
        "id": f"report-{run_id}",
        "runId": run_id,
        "summary": {
            "totalMatches": total_matches,
            "passedMatches": passed_matches,
            "failedMatches": failed_matches,
            "passRate": pass_rate,
        },
        "fallbackTriggered": fallback_triggered,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    report.update(kwargs)
    return report


def create_mock_fallback_event(
    run_id: str = "run-001",
    reason: str = "quality_critical_failure",
    source_primary_failed: bool = True,
    source_fallback_used: bool = True,
    success: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock fallback event for testing.
    
    Args:
        run_id: Run identifier
        reason: Reason for fallback
        source_primary_failed: Whether primary source failed
        source_fallback_used: Whether fallback source was used
        success: Whether fallback was successful
        **kwargs: Additional fields to override
        
    Returns:
        Mock fallback event dictionary
    """
    event = {
        "id": f"fallback-{run_id}",
        "runId": run_id,
        "reason": reason,
        "sourcePrimaryFailed": source_primary_failed,
        "sourceFallbackUsed": source_fallback_used,
        "success": success,
        "triggeredAt": datetime.now(timezone.utc).isoformat(),
    }
    event.update(kwargs)
    return event

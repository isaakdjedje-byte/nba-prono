"""
Decision Factories

Factory functions for creating mock decision-related data.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def create_mock_signal(
    match_id: str = "match-001",
    run_id: str = "run-001",
    winner_prediction: Optional[str] = "home",
    winner_confidence: float = 0.72,
    projected_score_home: int = 112,
    projected_score_away: int = 108,
    over_under_line: float = 220.5,
    over_under_signal: Optional[str] = "under",
    edge_winner: float = 0.08,
    edge_over_under: float = 0.03,
    quality_score: float = 0.85,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock signal for testing.
    
    Args:
        match_id: Match identifier
        run_id: Run identifier
        winner_prediction: Predicted winner ('home', 'away', or None)
        winner_confidence: Confidence in winner prediction (0-1)
        projected_score_home: Projected score for home team
        projected_score_away: Projected score for away team
        over_under_line: Over/under line
        over_under_signal: Over/under signal ('over', 'under', or None)
        edge_winner: Edge for winner prediction
        edge_over_under: Edge for over/under prediction
        quality_score: Quality score (0-1)
        **kwargs: Additional fields to override
        
    Returns:
        Mock signal dictionary
    """
    signal = {
        "id": f"signal-{match_id}",
        "matchId": match_id,
        "runId": run_id,
        "winnerPrediction": winner_prediction,
        "winnerConfidence": winner_confidence,
        "projectedScoreHome": projected_score_home,
        "projectedScoreAway": projected_score_away,
        "overUnderLine": over_under_line,
        "overUnderSignal": over_under_signal,
        "edgeWinner": edge_winner,
        "edgeOverUnder": edge_over_under,
        "qualityScore": quality_score,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    signal.update(kwargs)
    return signal


def create_mock_gate_results(
    signal_id: str = "signal-001",
    match_id: str = "match-001",
    run_id: str = "run-001",
    edge_winner_passed: bool = True,
    edge_over_under_passed: bool = True,
    confidence_passed: bool = True,
    drift_passed: bool = True,
    overall_passed: bool = True,
    failure_reason: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create mock gate results for testing.
    
    Args:
        signal_id: Signal identifier
        match_id: Match identifier
        run_id: Run identifier
        edge_winner_passed: Whether edge winner gate passed
        edge_over_under_passed: Whether edge over/under gate passed
        confidence_passed: Whether confidence gate passed
        drift_passed: Whether drift gate passed
        overall_passed: Whether all gates passed
        failure_reason: Reason for failure (if any)
        **kwargs: Additional fields to override
        
    Returns:
        Mock gate results dictionary
    """
    gates = {
        "id": f"gates-{signal_id}",
        "signalId": signal_id,
        "matchId": match_id,
        "runId": run_id,
        "gates": {
            "edgeWinner": {
                "passed": edge_winner_passed,
                "value": 0.08 if edge_winner_passed else 0.02,
                "threshold": 0.05,
            },
            "edgeOverUnder": {
                "passed": edge_over_under_passed,
                "value": 0.04 if edge_over_under_passed else 0.01,
                "threshold": 0.03,
            },
            "confidence": {
                "passed": confidence_passed,
                "value": 0.75 if confidence_passed else 0.60,
                "threshold": 0.70,
            },
            "drift": {
                "passed": drift_passed,
                "value": 0.10 if drift_passed else 0.20,
                "threshold": 0.15,
            },
        },
        "overallPassed": overall_passed,
        "failureReason": failure_reason,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    gates.update(kwargs)
    return gates


def create_mock_decision(
    match_id: str = "match-001",
    run_id: str = "run-001",
    status: str = "pick",  # 'pick', 'no_bet', 'blocked'
    home_team: str = "Lakers",
    away_team: str = "Warriors",
    edge: float = 0.08,
    confidence: float = 0.75,
    rationale: Optional[str] = None,
    hard_stop_triggered: bool = False,
    hard_stop_reason: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock decision for testing.
    
    Args:
        match_id: Match identifier
        run_id: Run identifier
        status: Decision status ('pick', 'no_bet', 'blocked')
        home_team: Home team name
        away_team: Away team name
        edge: Edge value
        confidence: Confidence value
        rationale: Decision rationale
        hard_stop_triggered: Whether hard-stop was triggered
        hard_stop_reason: Hard-stop reason (if triggered)
        **kwargs: Additional fields to override
        
    Returns:
        Mock decision dictionary
    """
    if rationale is None:
        if status == "pick":
            rationale = f"Pick : edge positif de {edge:.1%} sur {home_team}"
        elif status == "no_bet":
            rationale = "No-Bet : confiance insuffisante (< 70%)"
        else:
            rationale = "Bloqué : protection hard-stop active"
    
    decision = {
        "id": f"decision-{match_id}",
        "matchId": match_id,
        "runId": run_id,
        "status": status,
        "match": {
            "id": match_id,
            "homeTeam": home_team,
            "awayTeam": away_team,
            "startTime": datetime.now(timezone.utc).isoformat(),
        },
        "signals": {
            "edge": edge,
            "confidence": confidence,
            "projectedScore": "112-108",
        },
        "rationale": {
            "summary": rationale,
            "primaryReason": "edge" if status == "pick" else "confidence",
        },
        "hardStop": {
            "triggered": hard_stop_triggered,
            "reason": hard_stop_reason,
        } if hard_stop_triggered else None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    decision.update(kwargs)
    return decision


def create_mock_decision_list(
    count: int = 5,
    status: str = "pick",
    run_id: str = "run-001",
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Create a list of mock decisions.
    
    Args:
        count: Number of decisions to create
        status: Status for all decisions
        run_id: Run identifier
        **kwargs: Additional fields to override
        
    Returns:
        List of mock decision dictionaries
    """
    teams = [
        ("Lakers", "Warriors"),
        ("Celtics", "Heat"),
        ("Bucks", "76ers"),
        ("Suns", "Nuggets"),
        ("Mavericks", "Grizzlies"),
    ]
    
    decisions = []
    for i in range(min(count, len(teams))):
        home, away = teams[i]
        decision = create_mock_decision(
            match_id=f"match-{i+1:03d}",
            run_id=run_id,
            status=status,
            home_team=home,
            away_team=away,
            edge=0.05 + (i * 0.01),  # Varying edge
            **kwargs
        )
        decisions.append(decision)
    
    return decisions

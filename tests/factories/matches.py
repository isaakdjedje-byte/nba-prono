"""
Match Factories

Factory functions for creating mock match data.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def create_mock_match(
    match_id: str = "match-001",
    home_team: str = "Lakers",
    away_team: str = "Warriors",
    start_time: Optional[datetime] = None,
    status: str = "scheduled",
    home_score: Optional[int] = None,
    away_score: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock match for testing.
    
    Args:
        match_id: Match identifier
        home_team: Home team name
        away_team: Away team name
        start_time: Match start time (defaults to now + 3 hours)
        status: Match status ('scheduled', 'live', 'finished')
        home_score: Home team score (if finished/live)
        away_score: Away team score (if finished/live)
        **kwargs: Additional fields to override
        
    Returns:
        Mock match dictionary
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc) + timedelta(hours=3)
    
    match = {
        "id": match_id,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "startTime": start_time.isoformat(),
        "status": status,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    
    if home_score is not None:
        match["homeScore"] = home_score
    if away_score is not None:
        match["awayScore"] = away_score
    
    match.update(kwargs)
    return match


def create_mock_match_list(
    count: int = 5,
    status: str = "scheduled",
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Create a list of mock matches for testing.
    
    Args:
        count: Number of matches to create
        status: Status for all matches
        **kwargs: Additional fields to override
        
    Returns:
        List of mock match dictionaries
    """
    teams = [
        ("Lakers", "Warriors"),
        ("Celtics", "Heat"),
        ("Bucks", "76ers"),
        ("Suns", "Nuggets"),
        ("Mavericks", "Grizzlies"),
        ("Knicks", "Nets"),
        ("Clippers", "Kings"),
    ]
    
    matches = []
    base_time = datetime.now(timezone.utc) + timedelta(hours=3)
    
    for i in range(min(count, len(teams))):
        home, away = teams[i]
        match = create_mock_match(
            match_id=f"match-{i+1:03d}",
            home_team=home,
            away_team=away,
            start_time=base_time + timedelta(hours=i),
            status=status,
            **kwargs
        )
        matches.append(match)
    
    return matches

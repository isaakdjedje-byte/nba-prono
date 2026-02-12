"""
Module de scoring predictif pour matchs NBA
Generation des signaux: winner, score projete, over/under
"""
from .winner_model import WinnerModel, WinnerPrediction
from .score_projector import ScoreProjector, ScoreProjection
from .over_under_signal import OverUnderGenerator, OverUnderSignal
from .exclusions import ExclusionChecker, MatchExclusion, ExclusionReason

__all__ = [
    'WinnerModel',
    'WinnerPrediction',
    'ScoreProjector',
    'ScoreProjection',
    'OverUnderGenerator',
    'OverUnderSignal',
    'ExclusionChecker',
    'MatchExclusion',
    'ExclusionReason',
]
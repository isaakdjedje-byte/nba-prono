"""
Test Data Factories

This module provides factory functions for creating test data.
All test data should be created through these factories to ensure consistency.

Usage:
    from tests.factories import create_mock_signal, create_mock_decision
    
    signal = create_mock_signal(edge=0.08, confidence=0.75)
    decision = create_mock_decision(status='pick')
"""

from .decisions import (
    create_mock_decision,
    create_mock_gate_results,
    create_mock_signal,
)
from .matches import create_mock_match
from .quality import create_mock_quality_check, create_mock_quality_report

__all__ = [
    'create_mock_signal',
    'create_mock_gate_results',
    'create_mock_decision',
    'create_mock_match',
    'create_mock_quality_check',
    'create_mock_quality_report',
]

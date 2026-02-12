"""
Tests unitaires pour le guard no-bet et mode degrade
Pattern TDD : tests rouges avant implementation
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le chemin pour imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from policy.no_bet_guard import NoBetGuard, DegradedMode, GuardDecision
from quality.quality_checks import QualityResult, QualityStatus


class TestNoBetGuard:
    """Tests pour le guard no-bet"""

    def test_guard_initialization(self):
        """Test: Initialisation du guard"""
        guard = NoBetGuard(trace_id="test-trace-123")
        assert guard.trace_id == "test-trace-123"
        assert guard.is_degraded is False

    def test_degraded_mode_triggered_when_fallback_fails(self):
        """Test: Mode degrade active quand fallback echoue"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        # Simuler echec qualite + echec fallback
        quality_summary = {
            "critical_failure": True,
            "pass_rate": 0.5,
            "total_matches": 10,
            "failed": 5
        }
        
        fallback_result = None  # Fallback a echoue
        
        decision = guard.evaluate_run_status(quality_summary, fallback_result)
        
        assert decision.mode == DegradedMode.DEGRADED_NO_BET
        assert decision.allow_betting is False
        assert decision.reason is not None
        assert "fallback" in decision.reason.lower() or "qualite" in decision.reason.lower()

    def test_normal_mode_when_quality_pass(self):
        """Test: Mode normal quand qualite OK"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        quality_summary = {
            "critical_failure": False,
            "pass_rate": 0.95,
            "total_matches": 10,
            "failed": 0
        }
        
        fallback_result = None  # Pas besoin de fallback
        
        decision = guard.evaluate_run_status(quality_summary, fallback_result)
        
        assert decision.mode == DegradedMode.NORMAL
        assert decision.allow_betting is True

    def test_degraded_mode_when_critical_quality(self):
        """Test: Mode degrade sur echec qualite critique"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        quality_summary = {
            "critical_failure": True,
            "pass_rate": 0.6,
            "total_matches": 10,
            "failed": 4
        }
        
        # Meme avec fallback reussi, on reste en mode degrade par precaution
        fallback_result = [{"external_id": "fb-001"}]
        
        decision = guard.evaluate_run_status(quality_summary, fallback_result)
        
        # Doit etre degrade car qualite critique
        assert decision.mode == DegradedMode.DEGRADED_FALLBACK
        assert "fallback" in decision.reason.lower()

    def test_audit_trail_creation(self):
        """Test: Creation audit trail"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        quality_summary = {
            "critical_failure": True,
            "pass_rate": 0.5,
            "total_matches": 10,
            "failed": 5
        }
        
        decision = guard.evaluate_run_status(quality_summary, None)
        
        audit = guard.get_audit_trail()
        
        assert len(audit) == 1
        assert audit[0]["mode"] == DegradedMode.DEGRADED_NO_BET.value
        assert "timestamp" in audit[0]
        assert "reason" in audit[0]

    def test_explicit_reason_for_no_bet(self):
        """Test: Raison explicite pour no-bet"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        # Cas 1: Qualite insuffisante + fallback echoue
        quality_summary = {"critical_failure": True, "pass_rate": 0.3}
        decision = guard.evaluate_run_status(quality_summary, None)
        
        assert decision.mode == DegradedMode.DEGRADED_NO_BET
        assert decision.reason is not None
        assert len(decision.reason) > 10  # Raison detaillee

    def test_multiple_runs_tracking(self):
        """Test: Suivi multi-runs"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        # Run 1: degrade
        guard.evaluate_run_status({"critical_failure": True, "pass_rate": 0.3}, None)
        
        # Run 2: normal
        guard.evaluate_run_status({"critical_failure": False, "pass_rate": 0.95}, None)
        
        audit = guard.get_audit_trail()
        
        assert len(audit) == 2
        assert audit[0]["mode"] == DegradedMode.DEGRADED_NO_BET.value
        assert audit[1]["mode"] == DegradedMode.NORMAL.value

    def test_degraded_flag_exposed(self):
        """Test: Flag degrade expose"""
        guard = NoBetGuard(trace_id="test-trace-123")
        
        # Initialement pas degrade
        assert guard.is_degraded is False
        
        # Apres echec
        guard.evaluate_run_status({"critical_failure": True, "pass_rate": 0.3}, None)
        assert guard.is_degraded is True
        
        # Apres retour normal
        guard.evaluate_run_status({"critical_failure": False, "pass_rate": 0.95}, None)
        assert guard.is_degraded is False


class TestGuardDecision:
    """Tests pour les decisions du guard"""

    def test_decision_serialization(self):
        """Test: Serialization decision"""
        decision = GuardDecision(
            mode=DegradedMode.DEGRADED_NO_BET,
            allow_betting=False,
            reason="Qualite insuffisante et fallback en echec"
        )
        
        data = decision.to_dict()
        
        assert data["mode"] == "degraded-no-bet"
        assert data["allow_betting"] is False
        assert data["reason"] == "Qualite insuffisante et fallback en echec"

    def test_decision_with_metadata(self):
        """Test: Decision avec metadata"""
        decision = GuardDecision(
            mode=DegradedMode.DEGRADED_FALLBACK,
            allow_betting=False,
            reason="Fallback active",
            metadata={
                "quality_pass_rate": 0.6,
                "fallback_used": True,
                "original_match_count": 10
            }
        )
        
        data = decision.to_dict()
        
        assert data["metadata"]["quality_pass_rate"] == 0.6
        assert data["metadata"]["fallback_used"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

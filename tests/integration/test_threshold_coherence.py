"""
Threshold Coherence Test

This test verifies that Python and TypeScript services use the same threshold values.
It reads the YAML configuration directly and compares with runtime values from both services.

Run with: pytest tests/integration/test_threshold_coherence.py -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "spark-runner"))


def load_yaml_config():
    """Load configuration from shared YAML file."""
    yaml_path = project_root / "shared-config" / "policy-thresholds.yaml"
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestPythonConfigLoading:
    """Test that Python correctly loads configuration from YAML."""
    
    def test_python_loads_critical_failure_threshold(self):
        """Verify Python loads quality.critical_failure_threshold correctly."""
        from app.config.policy_thresholds import POLICY_THRESHOLDS
        yaml_config = load_yaml_config()
        
        assert POLICY_THRESHOLDS.quality.critical_failure_threshold == yaml_config['quality']['critical_failure_threshold']
        assert POLICY_THRESHOLDS.quality.critical_failure_threshold == 0.20
    
    def test_python_loads_gate_thresholds(self):
        """Verify Python loads all gate thresholds correctly."""
        from app.config.policy_thresholds import POLICY_THRESHOLDS
        yaml_config = load_yaml_config()
        
        assert POLICY_THRESHOLDS.gates.edge_winner.threshold == yaml_config['gates']['edge_winner']['threshold']
        assert POLICY_THRESHOLDS.gates.edge_over_under.threshold == yaml_config['gates']['edge_over_under']['threshold']
        assert POLICY_THRESHOLDS.gates.confidence.threshold == yaml_config['gates']['confidence']['threshold']
        assert POLICY_THRESHOLDS.gates.drift.threshold == yaml_config['gates']['drift']['threshold']
    
    def test_python_loads_hard_stop_thresholds(self):
        """Verify Python loads hard-stop thresholds correctly."""
        from app.config.policy_thresholds import POLICY_THRESHOLDS
        yaml_config = load_yaml_config()
        
        assert POLICY_THRESHOLDS.hard_stops.daily_loss_cap.value == yaml_config['hard_stops']['daily_loss_cap']['value']
        assert POLICY_THRESHOLDS.hard_stops.max_consecutive_losses.count == yaml_config['hard_stops']['max_consecutive_losses']['count']
        assert POLICY_THRESHOLDS.hard_stops.max_drawdown.percent == yaml_config['hard_stops']['max_drawdown']['percent']


class TestTypeScriptConfigGeneration:
    """Test that TypeScript configuration is correctly generated."""
    
    def test_typescript_file_exists(self):
        """Verify TypeScript config file was generated."""
        ts_path = project_root / "nba-prono" / "src" / "lib" / "config" / "policy-thresholds.ts"
        assert ts_path.exists(), f"TypeScript config not found at {ts_path}"
    
    def test_typescript_contains_thresholds(self):
        """Verify TypeScript file contains expected thresholds."""
        ts_path = project_root / "nba-prono" / "src" / "lib" / "config" / "policy-thresholds.ts"
        content = ts_path.read_text()
        
        # Check for critical thresholds
        assert "criticalFailureThreshold: 0.20" in content
        assert "edgeWinner:" in content
        assert "threshold: 0.05" in content
        assert "dailyLossCap:" in content


class TestCrossLanguageCoherence:
    """Test that Python and TypeScript use identical values."""
    
    def test_quality_thresholds_match(self):
        """Verify quality thresholds are identical in Python and TypeScript."""
        from app.config.policy_thresholds import POLICY_THRESHOLDS
        
        # Read TypeScript file to extract values
        ts_path = project_root / "nba-prono" / "src" / "lib" / "config" / "policy-thresholds.ts"
        ts_content = ts_path.read_text()
        
        # Extract TypeScript values (simple parsing)
        ts_critical = self._extract_ts_value(ts_content, "criticalFailureThreshold")
        ts_minimum = self._extract_ts_value(ts_content, "minimumForScoring")
        
        assert POLICY_THRESHOLDS.quality.critical_failure_threshold == ts_critical, \
            f"critical_failure_threshold mismatch: Python={POLICY_THRESHOLDS.quality.critical_failure_threshold}, TS={ts_critical}"
        assert POLICY_THRESHOLDS.quality.minimum_for_scoring == ts_minimum, \
            f"minimum_for_scoring mismatch: Python={POLICY_THRESHOLDS.quality.minimum_for_scoring}, TS={ts_minimum}"
    
    def test_gate_thresholds_match(self):
        """Verify gate thresholds are identical in Python and TypeScript."""
        from app.config.policy_thresholds import POLICY_THRESHOLDS
        
        ts_path = project_root / "nba-prono" / "src" / "lib" / "config" / "policy-thresholds.ts"
        ts_content = ts_path.read_text()
        
        # Extract and compare each gate
        gates = ['edgeWinner', 'edgeOverUnder', 'confidence', 'drift']
        python_values = {
            'edgeWinner': POLICY_THRESHOLDS.gates.edge_winner.threshold,
            'edgeOverUnder': POLICY_THRESHOLDS.gates.edge_over_under.threshold,
            'confidence': POLICY_THRESHOLDS.gates.confidence.threshold,
            'drift': POLICY_THRESHOLDS.gates.drift.threshold,
        }
        
        for gate in gates:
            ts_value = self._extract_ts_gate_threshold(ts_content, gate)
            py_value = python_values[gate]
            assert py_value == ts_value, \
                f"{gate} threshold mismatch: Python={py_value}, TS={ts_value}"
    
    def _extract_ts_value(self, content: str, key: str) -> float:
        """Extract a numeric value from TypeScript content."""
        import re
        pattern = rf"{key}:\s*(\d+\.?\d*)"
        match = re.search(pattern, content)
        if match:
            value = match.group(1)
            return float(value) if '.' in value else int(value)
        raise ValueError(f"Could not find {key} in TypeScript content")
    
    def _extract_ts_gate_threshold(self, content: str, gate: str) -> float:
        """Extract a gate threshold from TypeScript content."""
        import re
        # Find the gate object and extract threshold
        pattern = rf"{gate}:\s*{{[^}}]*threshold:\s*(\d+\.?\d*)"
        match = re.search(pattern, content)
        if match:
            value = match.group(1)
            return float(value)
        raise ValueError(f"Could not find {gate} threshold in TypeScript content")


class TestYamlSourceOfTruth:
    """Test that YAML is the actual single source of truth."""
    
    def test_yaml_matches_python(self):
        """Verify YAML values match Python runtime values."""
        from app.config.policy_thresholds import POLICY_THRESHOLDS
        yaml_config = load_yaml_config()
        
        # Compare all major thresholds
        assert yaml_config['quality']['critical_failure_threshold'] == POLICY_THRESHOLDS.quality.critical_failure_threshold
        assert yaml_config['gates']['edge_winner']['threshold'] == POLICY_THRESHOLDS.gates.edge_winner.threshold
        assert yaml_config['hard_stops']['daily_loss_cap']['value'] == POLICY_THRESHOLDS.hard_stops.daily_loss_cap.value
    
    def test_yaml_matches_typescript(self):
        """Verify YAML values match TypeScript generated values."""
        yaml_config = load_yaml_config()
        ts_path = project_root / "nba-prono" / "src" / "lib" / "config" / "policy-thresholds.ts"
        ts_content = ts_path.read_text()
        
        # Check that YAML values appear in TypeScript
        assert str(yaml_config['quality']['critical_failure_threshold']) in ts_content
        assert str(yaml_config['gates']['edge_winner']['threshold']) in ts_content
        assert str(yaml_config['hard_stops']['daily_loss_cap']['value']) in ts_content


class TestConfigValidation:
    """Test that configuration validation works correctly."""
    
    def test_validation_passes_with_valid_config(self):
        """Verify validation passes with valid configuration."""
        from app.config.policy_thresholds import validate_config
        # Should not raise
        validate_config()
    
    def test_get_threshold_helper(self):
        """Test the get_threshold helper function."""
        from app.config.policy_thresholds import get_threshold
        
        assert get_threshold('quality.critical_failure_threshold') == 0.20
        assert get_threshold('gates.edge_winner.threshold') == 0.05
        assert get_threshold('hard_stops.daily_loss_cap.value') == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

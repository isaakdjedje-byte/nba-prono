"""
Policy Thresholds Configuration

This module loads configuration from the shared YAML file.
It serves as the SINGLE SOURCE OF TRUTH for all business constants in Python.

WARNING: DO NOT hardcode thresholds in other files. Always import from here.

Usage:
    from app.config.policy_thresholds import POLICY_THRESHOLDS
    
    if failure_rate > POLICY_THRESHOLDS.quality.critical_failure_threshold:
        trigger_fallback()
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Union

import yaml


def _load_yaml_config() -> Dict[str, Any]:
    """Load configuration from shared YAML file."""
    # Find project root (where shared-config/ is located)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent.parent
    yaml_path = project_root / "shared-config" / "policy-thresholds.yaml"
    
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {yaml_path}\n"
            "Make sure you're running from the project root."
        )
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class QualityThresholds:
    """Quality validation thresholds (Story 1.3)."""
    critical_failure_threshold: float  # 0.20
    minimum_for_scoring: float  # 0.80
    validation_rules: Dict[str, float]


@dataclass(frozen=True)
class GateThreshold:
    """Individual gate threshold with metadata."""
    threshold: float
    description: str


@dataclass(frozen=True)
class GatesThresholds:
    """Policy gates thresholds (Story 1.5)."""
    edge_winner: GateThreshold
    edge_over_under: GateThreshold
    confidence: GateThreshold
    drift: GateThreshold


@dataclass(frozen=True)
class DailyLossCap:
    value: float
    unit: str
    description: str


@dataclass(frozen=True)
class MaxConsecutiveLosses:
    count: int
    description: str


@dataclass(frozen=True)
class MaxDrawdown:
    percent: float
    window_days: int
    description: str


@dataclass(frozen=True)
class ManualHalt:
    enabled: bool
    description: str


@dataclass(frozen=True)
class HardStopsThresholds:
    """Hard-stop thresholds (Story 1.7)."""
    daily_loss_cap: DailyLossCap
    max_consecutive_losses: MaxConsecutiveLosses
    max_drawdown: MaxDrawdown
    manual_halt: ManualHalt


@dataclass(frozen=True)
class ScoringConfig:
    """Scoring parameters (Story 1.4)."""
    default_line_over_under: float
    min_historical_games: int
    max_retries: int
    retry_delay_ms: int


@dataclass(frozen=True)
class PerformanceConfig:
    """Performance limits (NFRs)."""
    api_response_timeout_ms: int
    ui_max_load_time_ms: int
    default_page_size: int
    max_page_size: int
    cache_ttl_seconds: int


@dataclass(frozen=True)
class PolicyThresholds:
    """Complete policy thresholds configuration."""
    version: str
    last_updated: str
    quality: QualityThresholds
    gates: GatesThresholds
    hard_stops: HardStopsThresholds
    scoring: ScoringConfig
    performance: PerformanceConfig


def _build_config(raw_config: Dict[str, Any]) -> PolicyThresholds:
    """Build typed configuration from raw YAML dict."""
    return PolicyThresholds(
        version=raw_config['version'],
        last_updated=raw_config['last_updated'],
        quality=QualityThresholds(
            critical_failure_threshold=raw_config['quality']['critical_failure_threshold'],
            minimum_for_scoring=raw_config['quality']['minimum_for_scoring'],
            validation_rules=raw_config['quality']['validation_rules']
        ),
        gates=GatesThresholds(
            edge_winner=GateThreshold(
                threshold=raw_config['gates']['edge_winner']['threshold'],
                description=raw_config['gates']['edge_winner']['description']
            ),
            edge_over_under=GateThreshold(
                threshold=raw_config['gates']['edge_over_under']['threshold'],
                description=raw_config['gates']['edge_over_under']['description']
            ),
            confidence=GateThreshold(
                threshold=raw_config['gates']['confidence']['threshold'],
                description=raw_config['gates']['confidence']['description']
            ),
            drift=GateThreshold(
                threshold=raw_config['gates']['drift']['threshold'],
                description=raw_config['gates']['drift']['description']
            )
        ),
        hard_stops=HardStopsThresholds(
            daily_loss_cap=DailyLossCap(
                value=raw_config['hard_stops']['daily_loss_cap']['value'],
                unit=raw_config['hard_stops']['daily_loss_cap']['unit'],
                description=raw_config['hard_stops']['daily_loss_cap']['description']
            ),
            max_consecutive_losses=MaxConsecutiveLosses(
                count=raw_config['hard_stops']['max_consecutive_losses']['count'],
                description=raw_config['hard_stops']['max_consecutive_losses']['description']
            ),
            max_drawdown=MaxDrawdown(
                percent=raw_config['hard_stops']['max_drawdown']['percent'],
                window_days=raw_config['hard_stops']['max_drawdown']['window_days'],
                description=raw_config['hard_stops']['max_drawdown']['description']
            ),
            manual_halt=ManualHalt(
                enabled=raw_config['hard_stops']['manual_halt']['enabled'],
                description=raw_config['hard_stops']['manual_halt']['description']
            )
        ),
        scoring=ScoringConfig(
            default_line_over_under=raw_config['scoring']['default_line_over_under'],
            min_historical_games=raw_config['scoring']['min_historical_games'],
            max_retries=raw_config['scoring']['max_retries'],
            retry_delay_ms=raw_config['scoring']['retry_delay_ms']
        ),
        performance=PerformanceConfig(
            api_response_timeout_ms=raw_config['performance']['api_response_timeout_ms'],
            ui_max_load_time_ms=raw_config['performance']['ui_max_load_time_ms'],
            default_page_size=raw_config['performance']['default_page_size'],
            max_page_size=raw_config['performance']['max_page_size'],
            cache_ttl_seconds=raw_config['performance']['cache_ttl_seconds']
        )
    )


# =============================================================================
# GLOBAL CONFIGURATION INSTANCE
# =============================================================================

# Load configuration at module import time
# This ensures any YAML syntax errors are caught immediately
_raw_config = _load_yaml_config()
POLICY_THRESHOLDS: PolicyThresholds = _build_config(_raw_config)


def get_threshold(path: str) -> Union[float, int, str, bool, Dict]:
    """
    Get a threshold value by dot-notation path.
    
    Args:
        path: Dot-notation path (e.g., 'quality.critical_failure_threshold')
        
    Returns:
        The threshold value
        
    Example:
        >>> get_threshold('gates.edge_winner.threshold')
        0.05
    """
    keys = path.split('.')
    value: Any = POLICY_THRESHOLDS
    
    for key in keys:
        if isinstance(value, dict):
            value = value[key]
        else:
            value = getattr(value, key)
    
    return value


def reload_config() -> PolicyThresholds:
    """
    Reload configuration from YAML file.
    
    Useful for testing or when configuration changes at runtime.
    
    Returns:
        Updated PolicyThresholds instance
    """
    global POLICY_THRESHOLDS
    raw = _load_yaml_config()
    POLICY_THRESHOLDS = _build_config(raw)
    return POLICY_THRESHOLDS


# =============================================================================
# VALIDATION
# =============================================================================

def validate_config() -> None:
    """
    Validate that all required thresholds are present and valid.
    
    Raises:
        ValueError: If any threshold is invalid
    """
    errors = []
    
    # Validate quality thresholds
    if not 0 <= POLICY_THRESHOLDS.quality.critical_failure_threshold <= 1:
        errors.append("quality.critical_failure_threshold must be between 0 and 1")
    
    if not 0 <= POLICY_THRESHOLDS.quality.minimum_for_scoring <= 1:
        errors.append("quality.minimum_for_scoring must be between 0 and 1")
    
    # Validate gate thresholds
    for gate_name in ['edge_winner', 'edge_over_under', 'confidence', 'drift']:
        gate = getattr(POLICY_THRESHOLDS.gates, gate_name)
        if not 0 <= gate.threshold <= 1:
            errors.append(f"gates.{gate_name}.threshold must be between 0 and 1")
    
    # Validate hard-stops
    if POLICY_THRESHOLDS.hard_stops.daily_loss_cap.value < 0:
        errors.append("hard_stops.daily_loss_cap.value must be non-negative")
    
    if POLICY_THRESHOLDS.hard_stops.max_consecutive_losses.count < 1:
        errors.append("hard_stops.max_consecutive_losses.count must be at least 1")
    
    if not 0 <= POLICY_THRESHOLDS.hard_stops.max_drawdown.percent <= 1:
        errors.append("hard_stops.max_drawdown.percent must be between 0 and 1")
    
    if errors:
        raise ValueError("Configuration validation failed:\n" + "\n".join(errors))


# Validate on import
validate_config()

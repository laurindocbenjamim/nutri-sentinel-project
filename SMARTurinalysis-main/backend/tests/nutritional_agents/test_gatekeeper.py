"""
Tests for Agent 1 — GatekeeperAgent.

Verifies hard clinical safety boundaries:
- Ketoacidosis detection (glucose ++ + ketone present)
- Acute renal overload (protein Large)
- Active UTI (leukocytes + nitrite both positive)
- Clear passage for healthy markers
"""

import pytest
from src.domains.nutritional_agents.gatekeeper import GatekeeperAgent
from src.domains.nutritional_agents.models import UrinalysisData, TriageStatus

agent = GatekeeperAgent()


def _make_data(**overrides) -> UrinalysisData:
    """Build a baseline healthy UrinalysisData with optional field overrides."""
    defaults = {
        "Glucose": "Negative", "Ketone": "Negative", "Protein": "Negative",
        "Leukocytes": "Negative", "Nitrite": "Negative",
        "pHValue": 7.0, "SpecificGravity": 1.015,
    }
    defaults.update(overrides)
    return UrinalysisData(**defaults)


class TestGatekeeperClearPath:
    def test_healthy_markers_returns_clear(self):
        """Baseline healthy data (like the user image) must always return CLEAR."""
        data = _make_data()
        assert agent.validate_thresholds(data) == TriageStatus.CLEAR

    def test_trace_glucose_no_ketone_is_clear(self):
        """Trace glucose without ketones should not trigger emergency."""
        data = _make_data(Glucose="Trace")
        assert agent.validate_thresholds(data) == TriageStatus.CLEAR


class TestGatekeeperKetoacidosis:
    def test_high_glucose_string_with_ketone_triggers_lock(self):
        """'+++' glucose AND ketone present → EMERGENCY_LOCK."""
        data = _make_data(Glucose="+++", Ketone="Large")
        assert agent.validate_thresholds(data) == TriageStatus.EMERGENCY_LOCK

    def test_double_plus_glucose_with_ketone_triggers_lock(self):
        data = _make_data(Glucose="++", Ketone="Moderate")
        assert agent.validate_thresholds(data) == TriageStatus.EMERGENCY_LOCK

    def test_numeric_300_glucose_with_ketone_triggers_lock(self):
        data = _make_data(Glucose="300", Ketone="+")
        assert agent.validate_thresholds(data) == TriageStatus.EMERGENCY_LOCK

    def test_high_glucose_alone_no_lock(self):
        """High glucose without ketones is not a ketoacidosis signal."""
        data = _make_data(Glucose="+++", Ketone="Negative")
        assert agent.validate_thresholds(data) == TriageStatus.CLEAR


class TestGatekeeperRenalOverload:
    def test_large_protein_triggers_lock(self):
        data = _make_data(Protein="Large")
        assert agent.validate_thresholds(data) == TriageStatus.EMERGENCY_LOCK

    def test_numeric_300_protein_triggers_lock(self):
        data = _make_data(Protein="300")
        assert agent.validate_thresholds(data) == TriageStatus.EMERGENCY_LOCK

    def test_trace_protein_is_clear(self):
        data = _make_data(Protein="Trace")
        assert agent.validate_thresholds(data) == TriageStatus.CLEAR


class TestGatekeeperUTI:
    def test_positive_leukocytes_and_nitrite_triggers_lock(self):
        data = _make_data(Leukocytes="Positive", Nitrite="Positive")
        assert agent.validate_thresholds(data) == TriageStatus.EMERGENCY_LOCK

    def test_only_leukocytes_positive_is_clear(self):
        data = _make_data(Leukocytes="Positive", Nitrite="Negative")
        assert agent.validate_thresholds(data) == TriageStatus.CLEAR


class TestGatekeeperEmergencyPayload:
    def test_emergency_payload_contains_helpline(self):
        result = agent.trigger_emergency_lock()
        assert result.triagem == TriageStatus.EMERGENCY_LOCK
        assert "808 24 24 24" in result.helpline
        assert result.action == "ABORT_DIET"

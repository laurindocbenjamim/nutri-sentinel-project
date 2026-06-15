"""
Integration tests for the NutritionalOrchestrator DAG pipeline.

Verifies:
- Full pipeline with healthy celiac + weight-gain data → APPROVED plan
- Emergency lock short-circuits all further processing
- Max loop exhaustion returns safe-failure message
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.domains.nutritional_agents.orchestrator import NutritionalOrchestrator
from src.domains.nutritional_agents.models import UrinalysisData, UserProfile, BudgetTier


def _healthy_data() -> UrinalysisData:
    return UrinalysisData(**{
        "Glucose": "Negative", "Ketone": "Negative", "Protein": "Negative",
        "Leukocytes": "Negative", "Nitrite": "Negative",
        "pHValue": 7.0, "SpecificGravity": 1.015,
    })


def _critical_data() -> UrinalysisData:
    return UrinalysisData(**{
        "Glucose": "+++", "Ketone": "Large", "Protein": "Negative",
        "Leukocytes": "Negative", "Nitrite": "Negative",
        "pHValue": 5.0, "SpecificGravity": 1.030,
    })


def _celiac_profile() -> UserProfile:
    return UserProfile(
        user_id="test_user",
        age=28,
        sex="F",
        pathologies=["Celíaca"],
        allergies=[],
        medications=[],
        pregnancy=False,
        goal="ganhar_peso",
        budget_tier=BudgetTier.STUDENT,
        activity_level="moderado",
    )


class TestOrchestratorEmergencyLock:
    @pytest.mark.asyncio
    async def test_critical_data_returns_emergency_response(self):
        """Ketoacidosis markers must abort the pipeline without generating a plan."""
        orchestrator = NutritionalOrchestrator()
        result = await orchestrator.run(_critical_data(), "test_user")
        assert result.success is False
        assert result.triage_alert is not None
        assert result.plan is None

    @pytest.mark.asyncio
    async def test_emergency_response_contains_helpline(self):
        orchestrator = NutritionalOrchestrator()
        result = await orchestrator.run(_critical_data(), "test_user")
        assert "808 24 24 24" in result.triage_alert.helpline


class TestOrchestratorCeliacWeightGain:
    @pytest.mark.asyncio
    async def test_healthy_celiac_returns_approved_plan(self):
        """Full pipeline with healthy celiac user must produce an approved plan."""
        orchestrator = NutritionalOrchestrator()

        with patch.object(
            orchestrator._router, "fetch_clinical_profile",
            new=AsyncMock(return_value=_celiac_profile())
        ):
            result = await orchestrator.run(_healthy_data(), "test_user")

        assert result.success is True
        assert result.plan is not None
        assert result.plan.auditor_evaluation.status.value == "APPROVED"

    @pytest.mark.asyncio
    async def test_approved_plan_contains_legal_disclaimer(self):
        """Every approved plan must carry the legal disclaimer in metadata."""
        orchestrator = NutritionalOrchestrator()

        with patch.object(
            orchestrator._router, "fetch_clinical_profile",
            new=AsyncMock(return_value=_celiac_profile())
        ):
            result = await orchestrator.run(_healthy_data(), "test_user")

        assert "legal_disclaimer" in result.plan.metadata


class TestOrchestratorMaxLoopExhaustion:
    @pytest.mark.asyncio
    async def test_always_rejecting_auditor_returns_safe_failure(self):
        """If the auditor always rejects, return the safe-failure message."""
        orchestrator = NutritionalOrchestrator()

        with patch.object(
            orchestrator._router, "fetch_clinical_profile",
            new=AsyncMock(return_value=_celiac_profile())
        ), patch.object(
            orchestrator._auditor, "audit",
            return_value={"status": "REJECTED", "rejection_reason": "Forced rejection for test"}
        ):
            result = await orchestrator.run(_healthy_data(), "test_user")

        assert result.success is False
        assert result.plan is None
        assert "nutricionista humano" in result.error

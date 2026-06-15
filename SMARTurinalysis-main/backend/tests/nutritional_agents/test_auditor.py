"""
Tests for Agent 4 — AuditorAgent.

Verifies independent safety inspection:
- Allergen detection
- Zero-tolerance gluten sweep for celiac users
- Budget ceiling enforcement
- Meal count validation
"""

import pytest
from decimal import Decimal
from src.domains.nutritional_agents.auditor import AuditorAgent
from src.domains.nutritional_agents.models import (
    UserProfile, WeeklyPlanPayload, DietSummary, MacroDistribution,
    FinancialMetrics, AuditorEvaluation, Meal, DailyPlan,
    BudgetTier, BudgetStatus, GlycemicLoad,
)

agent = AuditorAgent()

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _make_safe_meal(ingredients: list[str] | None = None) -> Meal:
    return Meal(
        description="Test meal",
        ingredients=ingredients or ["frango", "arroz", "azeite"],
        allergens_checked=["glúten"],
        glycemic_load=GlycemicLoad.LOW,
    )


def _make_daily(meal_ingredients: list[str] | None = None) -> DailyPlan:
    meal = _make_safe_meal(meal_ingredients)
    return DailyPlan(pequeno_almoco=meal, almoco=meal, lanche=meal, jantar=meal)


def _make_plan(
    ingredients: list[str] | None = None,
    cost: Decimal = Decimal("42.00"),
    budget_tier: BudgetTier = BudgetTier.STUDENT,
) -> WeeklyPlanPayload:
    daily = _make_daily(ingredients)
    return WeeklyPlanPayload(
        metadata={"user_id": "test", "loop_attempt": 1, "timestamp": "2026-06-15T00:00:00Z"},
        diet_summary=DietSummary(
            diet_type="Test",
            target_calories_kcal=2000,
            macro_distribution=MacroDistribution(carbohydrates_g=250, proteins_g=100, fats_g=67),
        ),
        financial_metrics=FinancialMetrics(
            user_budget_tier=budget_tier,
            estimated_weekly_cost_eur=cost,
            budget_status=BudgetStatus.COMPLIANT,
        ),
        weekly_plan={day: daily for day in DAYS},
        auditor_evaluation=AuditorEvaluation(),
    )


def _make_profile(**overrides) -> UserProfile:
    defaults = dict(user_id="u1", age=28, sex="F", pathologies=[], allergies=[], medications=[])
    defaults.update(overrides)
    return UserProfile(**defaults)


class TestAuditorAllergens:
    def test_detected_allergen_causes_rejection(self):
        plan = _make_plan(ingredients=["amendoins", "arroz"])
        profile = _make_profile(allergies=["amendoins"])
        result = agent.audit(plan, profile)
        assert result["status"] == "REJECTED"
        assert "amendoins" in result["rejection_reason"]

    def test_no_allergen_passes(self):
        plan = _make_plan()
        profile = _make_profile()
        result = agent.audit(plan, profile)
        assert result["status"] == "APPROVED"


class TestAuditorGluten:
    def test_wheat_ingredient_rejected_for_celiac(self):
        plan = _make_plan(ingredients=["pão de trigo", "manteiga"])
        profile = _make_profile()
        directives = {"autoimmune": {"zero_tolerance_gluten": True}}
        result = agent.audit(plan, profile, directives)
        assert result["status"] == "REJECTED"
        assert "trigo" in result["rejection_reason"]

    def test_certified_oat_approved_for_celiac(self):
        plan = _make_plan(ingredients=["aveia certificada sem glúten", "banana"])
        profile = _make_profile()
        directives = {"autoimmune": {"zero_tolerance_gluten": True}}
        result = agent.audit(plan, profile, directives)
        assert result["status"] == "APPROVED"

    def test_plain_oat_rejected_for_celiac(self):
        plan = _make_plan(ingredients=["aveia", "leite"])
        profile = _make_profile()
        directives = {"autoimmune": {"zero_tolerance_gluten": True}}
        result = agent.audit(plan, profile, directives)
        assert result["status"] == "REJECTED"


class TestAuditorBudget:
    def test_cost_exceeds_student_ceiling_rejected(self):
        plan = _make_plan(cost=Decimal("80.00"), budget_tier=BudgetTier.STUDENT)
        profile = _make_profile(budget_tier=BudgetTier.STUDENT)
        result = agent.audit(plan, profile)
        assert result["status"] == "REJECTED"
        assert "80" in result["rejection_reason"]

    def test_cost_within_student_ceiling_approved(self):
        plan = _make_plan(cost=Decimal("42.00"), budget_tier=BudgetTier.STUDENT)
        profile = _make_profile(budget_tier=BudgetTier.STUDENT)
        result = agent.audit(plan, profile)
        assert result["status"] == "APPROVED"

"""
Agent 4 — Auditor (Safety Inspector).

Independent safety reviewer that validates the generated meal plan
against allergens, nutritional targets, and budget ceiling.
Returns APPROVED or REJECTED with a detailed rejection reason.
"""

from __future__ import annotations
from src.domains.nutritional_agents.models import (
    UserProfile, WeeklyPlanPayload, AuditStatus, AuditorEvaluation, BudgetTier,
)
from src.domains.nutritional_agents.specialists.autoimmune import _contains_hidden_gluten

# Sodium limit (mg/day) per WHO guidelines for general population
_MAX_SODIUM_MG = 2000
# Minimum daily meals required
_MIN_MEALS_PER_DAY = 4
# Student weekly budget ceiling in EUR
_BUDGET_CEILING_EUR: dict[BudgetTier, float] = {
    BudgetTier.STUDENT: 55.0,
    BudgetTier.MEDIUM: 90.0,
    BudgetTier.PREMIUM: 999.0,
}


def _audit_meal_allergens(meal_ingredients: list[str], user_allergies: list[str]) -> list[str]:
    """
    Cross-reference meal ingredients against user's registered allergies.
    Returns a list of detected allergen violations.
    """
    violations = []
    allergies_lower = {a.lower() for a in user_allergies}
    for ingredient in meal_ingredients:
        if ingredient.lower() in allergies_lower:
            violations.append(ingredient)
    return violations


def _audit_gluten_zero_tolerance(weekly_plan: dict, active: bool) -> list[str]:
    """
    When autoimmune (gluten-free) directive is active, scan every ingredient
    across the entire week for any hidden gluten contamination.
    """
    if not active:
        return []

    flagged = []
    for day, daily_plan in weekly_plan.items():
        for meal_name in ("pequeno_almoco", "almoco", "lanche", "jantar"):
            meal = getattr(daily_plan, meal_name, None)
            if meal:
                for ingredient in meal.ingredients:
                    if _contains_hidden_gluten(ingredient):
                        flagged.append(f"{day}.{meal_name}: '{ingredient}'")
    return flagged


class AuditorAgent:
    """
    Agent 4 — Safety Inspector.
    Independently validates the plan before delivery to the user.
    """

    def audit_allergens(self, plan: WeeklyPlanPayload, profile: UserProfile) -> list[str]:
        """
        Scan all meal ingredients for user-registered allergens.
        Returns a list of flagged violations across the entire weekly plan.
        """
        violations = []
        for day, daily_plan in plan.weekly_plan.items():
            for meal_name in ("pequeno_almoco", "almoco", "lanche", "jantar"):
                meal = getattr(daily_plan, meal_name, None)
                if meal:
                    meal_violations = _audit_meal_allergens(meal.ingredients, profile.allergies)
                    for v in meal_violations:
                        violations.append(f"{day}.{meal_name}: allergen '{v}'")
        return violations

    def validate_nutritional_targets(
        self, plan: WeeklyPlanPayload, directives: dict
    ) -> list[str]:
        """
        Check that the plan meets the minimum required daily meal count,
        and flag potential nutritional compliance issues.
        """
        issues = []
        # Count distinct meal slots per day (each day has 4 meals)
        for day, daily_plan in plan.weekly_plan.items():
            meal_count = sum(
                1 for name in ("pequeno_almoco", "almoco", "lanche", "jantar")
                if getattr(daily_plan, name, None)
            )
            if meal_count < _MIN_MEALS_PER_DAY:
                issues.append(f"{day}: only {meal_count} meals (minimum {_MIN_MEALS_PER_DAY})")
        return issues

    def audit_budget_ceiling(
        self, plan: WeeklyPlanPayload, profile: UserProfile
    ) -> list[str]:
        """
        Verify the estimated weekly cost does not exceed the user's budget tier ceiling.
        """
        ceiling = _BUDGET_CEILING_EUR.get(profile.budget_tier, 999.0)
        cost = float(plan.financial_metrics.estimated_weekly_cost_eur)
        if cost > ceiling:
            return [
                f"Custo semanal estimado ({cost}€) excede o teto do perfil "
                f"'{profile.budget_tier}' ({ceiling}€)."
            ]
        return []

    def audit(self, plan: WeeklyPlanPayload, profile: UserProfile, directives: dict = None) -> dict:
        """
        Run all audit checks and return a consolidated result dict.
        Sets plan.auditor_evaluation.status to APPROVED or REJECTED.
        """
        directives = directives or {}
        all_issues: list[str] = []

        # 1. User allergen scan
        all_issues.extend(self.audit_allergens(plan, profile))

        # 2. Zero-tolerance gluten scan (only when autoimmune directive is active)
        gluten_active = directives.get("autoimmune", {}).get("zero_tolerance_gluten", False)
        all_issues.extend(_audit_gluten_zero_tolerance(plan.weekly_plan, gluten_active))

        # 3. Nutritional structure validation
        all_issues.extend(self.validate_nutritional_targets(plan, directives))

        # 4. Budget ceiling check
        all_issues.extend(self.audit_budget_ceiling(plan, profile))

        if all_issues:
            plan.auditor_evaluation = AuditorEvaluation(
                status=AuditStatus.REJECTED,
                rejected_meals=all_issues,
                rejection_reason="; ".join(all_issues),
            )
            return {"status": "REJECTED", "rejection_reason": "; ".join(all_issues)}

        plan.auditor_evaluation = AuditorEvaluation(status=AuditStatus.APPROVED)
        return {"status": "APPROVED"}

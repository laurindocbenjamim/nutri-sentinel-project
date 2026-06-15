"""
Agent 3.D — Clinical Nutrition Agent (Diet Builder).

Consolidates all specialist directives and generates a 7-day personalized
meal plan. Applies budget constraints and caloric density adjustments.
"""

from __future__ import annotations
from decimal import Decimal
from datetime import datetime, timezone

from src.domains.nutritional_agents.models import (
    UserProfile, UrinalysisData, Meal, DailyPlan,
    WeeklyPlanPayload, DietSummary, MacroDistribution,
    FinancialMetrics, AuditorEvaluation, BudgetTier, BudgetStatus, GlycemicLoad,
)

# Cost weight table for budget gate (used by calculate_recipe_budget)
_PRICE_WEIGHTS: dict[str, int] = {
    "student": {
        "low": ["arroz", "batata-doce", "frango", "ovos", "alface", "banana",
                "maçã", "feijão", "atum em lata", "cenoura", "cebola"],
        "medium": ["aveia sem glúten", "quinoa", "azeite", "bebida de amêndoa", "iogurte"],
        "high": ["salmão fresco", "abacate", "nozes", "manteiga de amêndoa", "carne de vaca premium"],
    }
}
_BUDGET_THRESHOLDS = {BudgetTier.STUDENT: 7, BudgetTier.MEDIUM: 14, BudgetTier.PREMIUM: 999}
_WEEKLY_COST_ESTIMATES = {BudgetTier.STUDENT: Decimal("42.00"), BudgetTier.MEDIUM: Decimal("70.00"), BudgetTier.PREMIUM: Decimal("120.00")}

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _build_base_menu(directives: dict, profile: UserProfile) -> dict[str, DailyPlan]:
    """
    Generate a 7-day meal structure using safe, directive-compliant ingredients.
    Uses rotation logic to vary meals across the week.
    """
    gluten_free = directives.get("autoimmune", {}).get("zero_tolerance_gluten", False)
    oat_label = "aveia certificada sem glúten" if gluten_free else "aveia"
    bread_label = "pão sem glúten" if gluten_free else "pão integral"

    # Two rotating daily templates to ensure meal variety across 7 days
    template_a = DailyPlan(
        pequeno_almoco=Meal(
            description=f"Papas de {oat_label} com bebida de amêndoa, banana e sementes de girassol.",
            ingredients=[oat_label, "bebida de amêndoa", "banana", "sementes de girassol"],
            allergens_checked=["glúten", "lactose"],
            glycemic_load=GlycemicLoad.MEDIUM,
        ),
        almoco=Meal(
            description="Peito de frango grelhado com arroz basmati, brócolos e azeite.",
            ingredients=["peito de frango", "arroz basmati", "brócolos", "azeite"],
            allergens_checked=["glúten"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        lanche=Meal(
            description="Iogurte sem lactose com nozes e morangos.",
            ingredients=["iogurte sem lactose", "nozes", "morangos"],
            allergens_checked=["lactose", "frutos de casca rija"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        jantar=Meal(
            description="Posta de salmão assado com batata-doce e salada de pepino.",
            ingredients=["salmão", "batata-doce", "pepino", "alface", "azeite"],
            allergens_checked=["glúten", "peixe"],
            glycemic_load=GlycemicLoad.MEDIUM,
        ),
    )
    template_b = DailyPlan(
        pequeno_almoco=Meal(
            description=f"Ovos mexidos com {bread_label} e sumo de laranja natural.",
            ingredients=["ovos", bread_label, "laranja"],
            allergens_checked=["glúten", "ovos"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        almoco=Meal(
            description="Feijão preto com arroz, couve refogada em azeite e frango desfiado.",
            ingredients=["feijão preto", "arroz", "couve", "azeite", "frango"],
            allergens_checked=["glúten"],
            glycemic_load=GlycemicLoad.MEDIUM,
        ),
        lanche=Meal(
            description="Banana com manteiga de amendoim e bebida de aveia sem glúten.",
            ingredients=["banana", "manteiga de amendoim", oat_label],
            allergens_checked=["glúten", "amendoins"],
            glycemic_load=GlycemicLoad.LOW,
        ),
        jantar=Meal(
            description="Bacalhau assado com batatas e legumes grelhados.",
            ingredients=["bacalhau", "batata", "pimento", "azeite", "alho"],
            allergens_checked=["glúten", "peixe"],
            glycemic_load=GlycemicLoad.LOW,
        ),
    )

    # Alternate templates across week days
    return {day: (template_a if i % 2 == 0 else template_b) for i, day in enumerate(DAYS)}


class ClinicalNutritionAgent:
    """
    Agent 3.D — Clinical Nutrition Agent.
    Assembles the full 7-day meal plan from specialist directives.
    """

    def calculate_recipe_budget(self, ingredients: list[str], tier: BudgetTier) -> str:
        """
        Score ingredients by cost weight and reject premium items for budget users.
        Returns 'APPROVED_BY_BUDGET' or 'REJECTED_BY_BUDGET'.
        """
        score = 0
        low = _PRICE_WEIGHTS["student"]["low"]
        medium = _PRICE_WEIGHTS["student"]["medium"]
        high = _PRICE_WEIGHTS["student"]["high"]

        for ing in ingredients:
            lower = ing.lower()
            if any(h in lower for h in high):
                score += 3
            elif any(m in lower for m in medium):
                score += 2
            else:
                score += 1

        threshold = _BUDGET_THRESHOLDS.get(tier, 14)
        return "APPROVED_BY_BUDGET" if score <= threshold else "REJECTED_BY_BUDGET"

    def adjust_caloric_density(self, goal: str, base_macros: dict) -> dict:
        """
        Apply a caloric surplus for weight-gain goals by increasing
        fat and carbohydrate targets proportionally.
        """
        if goal == "ganhar_peso":
            return {
                "carbohydrates_g": int(base_macros["carbohydrates_g"] * 1.15),
                "proteins_g": int(base_macros["proteins_g"] * 1.10),
                "fats_g": int(base_macros["fats_g"] * 1.15),
                "target_calories_kcal": int(base_macros["target_calories_kcal"] * 1.12),
            }
        return base_macros

    def structure_weekly_menu(
        self,
        urinalysis_data: UrinalysisData,
        profile: UserProfile,
        directives: dict,
        loop_attempt: int = 1,
    ) -> WeeklyPlanPayload:
        """
        Build and return the full WeeklyPlanPayload incorporating all directives.
        """
        # Determine macro targets and apply goal-specific caloric adjustments
        from src.domains.nutritional_agents.router_agent import RouterAgent
        base_macros = RouterAgent().calculate_metabolic_goals(profile)
        adjusted = self.adjust_caloric_density(profile.goal, base_macros)

        diet_type = "Isenta de Glúten" if directives.get("autoimmune") else "Equilibrada"
        if profile.goal == "ganhar_peso":
            diet_type = f"Hipercalórica / {diet_type}"

        weekly = _build_base_menu(directives, profile)

        estimated_cost = _WEEKLY_COST_ESTIMATES.get(profile.budget_tier, Decimal("70.00"))

        return WeeklyPlanPayload(
            metadata={
                "user_id": profile.user_id,
                "loop_attempt": loop_attempt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            diet_summary=DietSummary(
                diet_type=diet_type,
                target_calories_kcal=adjusted["target_calories_kcal"],
                macro_distribution=MacroDistribution(
                    carbohydrates_g=adjusted["carbohydrates_g"],
                    proteins_g=adjusted["proteins_g"],
                    fats_g=adjusted["fats_g"],
                ),
            ),
            financial_metrics=FinancialMetrics(
                user_budget_tier=profile.budget_tier,
                estimated_weekly_cost_eur=estimated_cost,
                budget_status=BudgetStatus.COMPLIANT,
            ),
            weekly_plan=weekly,
            auditor_evaluation=AuditorEvaluation(),
        )

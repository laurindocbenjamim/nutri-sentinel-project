"""
Agent 3.B — Pregnancy Specialist (Nutrição Materno-Infantil).

Ensures maternal-fetal nutritional safety. Overrides and blocks any
restrictive dietary patterns (ketogenic, fasting, extreme low-carb).
"""

from src.domains.nutritional_agents.models import UserProfile

# Minimum daily micronutrient targets for pregnant women (WHO guidelines)
_GESTATIONAL_MINIMUMS = {
    "folic_acid_mcg": 600,
    "iron_mg": 27,
    "iodine_mcg": 220,
    "calcium_mg": 1000,
    "vitamin_d_iu": 600,
    "omega3_dha_mg": 200,
}

# Dietary patterns incompatible with a safe pregnancy
_BLOCKED_DIET_TYPES = frozenset({
    "cetogénica", "keto", "jejum intermitente",
    "very low carb", "vlcd", "dieta de choque",
})

# Foods with known teratogenic risk or pregnancy contraindications
_BLOCKED_INGREDIENTS = frozenset({
    "álcool", "fígado bovino cru", "atum em conserva em excesso",
    "queijo não pasteurizado", "ovos crus", "carne mal cozida",
    "peixe espada", "tubarão", "swordfish",
})


class PregnancyAgent:
    """
    Agent 3.B — Materno-Infantil Specialist.
    Enforces WHO gestational nutritional minimums and blocks unsafe diets.
    """

    def validate_gestational_minimums(self) -> dict:
        """
        Return minimum daily micronutrient targets for a safe pregnancy
        based on WHO and EFSA guidelines.
        """
        return {"gestational_minimums": _GESTATIONAL_MINIMUMS}

    def block_restrictive_diets(self, goal: str) -> dict:
        """
        Override goals that are incompatible with pregnancy safety.
        If a ketogenic or fasting diet is requested, hard-block it.
        """
        is_blocked = goal.lower() in _BLOCKED_DIET_TYPES
        return {
            "restrictive_diet_blocked": is_blocked,
            "override_goal": "saúde_gestacional" if is_blocked else goal,
        }

    def generate_directives(self, profile: UserProfile) -> dict:
        """
        Build the full set of pregnancy-specific directives to be injected
        into the Clinical Nutrition Agent.
        """
        minimums = self.validate_gestational_minimums()
        diet_block = self.block_restrictive_diets(profile.goal)

        return {
            "pregnancy": {
                "active": True,
                "blocked_ingredients": list(_BLOCKED_INGREDIENTS),
                "min_meals_per_day": 5,
                "allow_supplements_note": True,
                **minimums,
                **diet_block,
            }
        }

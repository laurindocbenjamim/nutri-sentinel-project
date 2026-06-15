"""
Agent 3.A — Oncology Specialist.

Generates dietary directives to combat tumor cachexia and support
immune modulation. Blocks all pro-inflammatory food categories.
"""

from src.domains.nutritional_agents.models import UserProfile

# Foods and categories proven pro-inflammatory or harmful during cancer treatment
_BLOCKED_FOODS = frozenset({
    "gordura trans", "margarina", "álcool", "açúcar refinado",
    "refrigerantes", "embutidos", "enchidos", "fast food",
    "fritos", "óleos refinados", "carnes processadas",
})

# Target omega-3 to omega-6 ratio (1:4 is the therapeutic oncology target)
_OMEGA_TARGET_RATIO = (1, 4)


class OncologyAgent:
    """
    Agent 3.A — Oncology & Immunomodulation Specialist.
    Generates directives for users with active or historical cancer diagnoses.
    """

    def calculate_immunomodulation_ratio(self) -> dict:
        """
        Define omega-3 to omega-6 therapeutic ratio for immune support.
        Returns macro adjustment flags for the clinical diet builder.
        """
        return {
            "omega3_priority": True,
            "omega3_to_omega6_ratio": f"1:{_OMEGA_TARGET_RATIO[1]}",
            "preferred_fats": ["azeite", "salmão", "sardinha", "linhaça", "nozes"],
        }

    def filter_pro_inflammatory_foods(self) -> dict:
        """
        Return a set of blocked ingredients and food categories that are
        pro-inflammatory or contraindicated during cancer treatment.
        """
        return {"blocked_ingredients": list(_BLOCKED_FOODS)}

    def generate_directives(self, profile: UserProfile) -> dict:
        """
        Consolidate all oncology-specific dietary restrictions and preferences
        into a unified directives dict for the Clinical Nutrition Agent.
        """
        fat_directives = self.calculate_immunomodulation_ratio()
        inflammatory_blocks = self.filter_pro_inflammatory_foods()

        return {
            "oncology": {
                "active": True,
                "min_meals_per_day": 5,  # Frequent small meals to fight cachexia
                "caloric_density_priority": "alta",
                "antioxidant_priority": True,
                "preferred_foods": [
                    "brócolos", "espinafres", "curcuma", "gengibre",
                    "mirtilos", "romã", "tomate", "alho",
                ],
                **fat_directives,
                **inflammatory_blocks,
            }
        }

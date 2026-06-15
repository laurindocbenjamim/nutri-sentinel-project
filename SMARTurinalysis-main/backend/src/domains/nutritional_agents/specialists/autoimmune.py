"""
Agent 3.C — Autoimmune Specialist (Celíase / Doença de Crohn).

Enforces zero-tolerance gluten elimination. Detects hidden gluten sources
and cross-contamination risks in ingredient lists.
"""

from src.domains.nutritional_agents.models import UserProfile

# Primary forbidden gluten-containing grains and derivatives
_GLUTEN_KEYWORDS = frozenset({
    "trigo", "centeio", "cevada", "malte", "espelta",
    "kamut", "triticale", "farro",
})

# Processed food terms that may hide gluten (must be checked without "sem glúten" suffix)
_HIDDEN_GLUTEN_TERMS = frozenset({
    "farinha", "pão", "massa", "sêmola", "amido",
    "molho de soja", "aveia",  # aveia is safe only if certified
})

# Words that indicate a gluten-free certified variant — safe to use
_SAFE_SUFFIXES = frozenset({"sem glúten", "gluten free", "gluten-free", "certificada"})

# Foods that support intestinal barrier regeneration (Crohn / Celiac)
_GUT_HEALING_FOODS = [
    "caldo de ossos", "couve", "papaia", "aloe vera",
    "kefir sem lactose", "cúrcuma", "gengibre", "ghee",
]


def _contains_hidden_gluten(ingredient: str) -> bool:
    """
    Detect if an ingredient string contains a gluten risk keyword
    that is NOT qualified with a safe certified-gluten-free suffix.
    """
    lower = ingredient.lower()

    # Check primary forbidden grains — always unsafe
    for keyword in _GLUTEN_KEYWORDS:
        if keyword in lower:
            return True

    # Check hidden gluten terms — only unsafe without a certified suffix
    for term in _HIDDEN_GLUTEN_TERMS:
        if term in lower:
            has_safe_suffix = any(suffix in lower for suffix in _SAFE_SUFFIXES)
            if not has_safe_suffix:
                return True

    return False


class AutoimmuneAgent:
    """
    Agent 3.C — Autoimmune & Gluten-Intolerance Specialist.
    Generates zero-tolerance gluten directives for Celiac and Crohn profiles.
    """

    def strict_gluten_filter(self, ingredients: list[str]) -> list[str]:
        """
        Scan a list of ingredients and return only those that contain
        detected gluten risks. Returns empty list if all are safe.
        """
        return [ing for ing in ingredients if _contains_hidden_gluten(ing)]

    def map_cross_contamination_risk(self) -> dict:
        """
        Return guidance on cross-contamination risks and labeling requirements
        for certified gluten-free products.
        """
        return {
            "cross_contamination_warning": True,
            "label_requirement": "Produto deve ter certificação 'Sem Glúten' visível no rótulo.",
            "shared_facility_risk": "Verificar se o produto é processado em instalações com trigo.",
        }

    def generate_directives(self, profile: UserProfile) -> dict:
        """
        Produce all gluten-free and gut-healing directives for the Clinical Agent.
        """
        contamination = self.map_cross_contamination_risk()

        return {
            "autoimmune": {
                "active": True,
                "zero_tolerance_gluten": True,
                "gluten_keywords_blocked": list(_GLUTEN_KEYWORDS | _HIDDEN_GLUTEN_TERMS),
                "safe_suffixes_required": list(_SAFE_SUFFIXES),
                "gut_healing_foods": _GUT_HEALING_FOODS,
                **contamination,
            }
        }

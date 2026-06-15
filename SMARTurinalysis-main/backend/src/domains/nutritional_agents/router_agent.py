"""
Agent 2 — Router Agent (Context Engine).

Retrieves the user's clinical profile from the database and determines
which specialist agents must be activated for this pipeline run.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from src.domains.nutritional_agents.models import UserProfile, BudgetTier
from src.shared.database import get_collection

# Drugs known to mask or alter urinalysis readings (e.g., iSGLT2 causes glycosuria)
_MASKING_MEDICATIONS = {"empagliflozin", "dapagliflozin", "canagliflozin", "isglt2"}

# Pathology → specialist module mapping (populated lazily to avoid circular imports)
_PATHOLOGY_AGENT_MAP: dict[str, str] = {
    "Celíaca": "autoimmune",
    "Doença de Crohn": "autoimmune",
    "Cancro": "oncology",
    "Cancro de Mama": "oncology",
    "Cancro do Pulmão": "oncology",
}


def _load_specialist(key: str):
    """Lazy-load specialist agent class by key to avoid circular imports."""
    if key == "autoimmune":
        from src.domains.nutritional_agents.specialists.autoimmune import AutoimmuneAgent
        return AutoimmuneAgent()
    if key == "oncology":
        from src.domains.nutritional_agents.specialists.oncology import OncologyAgent
        return OncologyAgent()
    if key == "pregnancy":
        from src.domains.nutritional_agents.specialists.pregnancy import PregnancyAgent
        return PregnancyAgent()
    return None


class RouterAgent:
    """
    Agent 2 — Context Engine.
    Fetches and enriches the user's clinical profile, then selects
    which specialist agents must participate in the pipeline.
    """

    async def fetch_clinical_profile(self, user_id: str) -> UserProfile:
        """
        Retrieve the clinical profile for a given user from MongoDB.
        Queries the 'user_profiles' collection using the user_id field.
        Falls back to a safe default profile if the document is not found.
        """
        collection = get_collection("user_profiles")
        doc = await collection.find_one({"user_id": user_id}, {"_id": 0})

        if not doc:
            # Return a safe default profile when user is not yet in DB
            return UserProfile(
                user_id=user_id,
                age=30,
                sex="M",
                pathologies=[],
                allergies=[],
                medications=[],
                pregnancy=False,
                goal="manter_peso",
                budget_tier=BudgetTier.MEDIUM,
                activity_level="moderado",
            )

        return UserProfile(
            user_id=doc.get("user_id", user_id),
            age=doc.get("age", 30),
            sex=doc.get("sex", "M"),
            pathologies=doc.get("pathologies", []),
            allergies=doc.get("allergies", []),
            medications=doc.get("medications", []),
            pregnancy=doc.get("pregnancy", False),
            goal=doc.get("goal", "manter_peso"),
            budget_tier=BudgetTier(doc.get("budget_tier", BudgetTier.MEDIUM)),
            activity_level=doc.get("activity_level", "moderado"),
        )

    def check_active_medications(self, profile: UserProfile) -> list[str]:
        """
        Identify medications that may mask or alter biomarker readings.
        Returns list of known masking drug names found in the user's medications.
        """
        return [
            med for med in profile.medications
            if med.lower() in _MASKING_MEDICATIONS
        ]

    def calculate_metabolic_goals(self, profile: UserProfile) -> dict:
        """
        Derive daily TDEE and macro targets based on user profile and goal.
        Uses simplified Harris-Benedict multipliers.
        """
        activity_multipliers = {
            "sedentario": 1.2, "leve": 1.375,
            "moderado": 1.55, "alto": 1.725, "muito_alto": 1.9,
        }
        base_bmr = 1800 if profile.sex == "F" else 2000
        multiplier = activity_multipliers.get(profile.activity_level, 1.55)
        tdee = int(base_bmr * multiplier)

        surplus = 300 if profile.goal == "ganhar_peso" else 0
        target = tdee + surplus

        return {
            "tdee_kcal": tdee,
            "target_calories_kcal": target,
            "proteins_g": int(target * 0.25 / 4),
            "carbohydrates_g": int(target * 0.50 / 4),
            "fats_g": int(target * 0.25 / 9),
        }

    def define_pipeline(self, profile: UserProfile) -> list:
        """
        Determine and instantiate specialist agents required for this user.
        Returns an ordered list of specialist agent instances.
        """
        agents = []

        if profile.pregnancy:
            agent = _load_specialist("pregnancy")
            if agent:
                agents.append(agent)

        for pathology in profile.pathologies:
            key = _PATHOLOGY_AGENT_MAP.get(pathology)
            if key:
                # Avoid duplicates if multiple pathologies map to same agent
                existing_types = {type(a).__name__ for a in agents}
                candidate = _load_specialist(key)
                if candidate and type(candidate).__name__ not in existing_types:
                    agents.append(candidate)

        return agents

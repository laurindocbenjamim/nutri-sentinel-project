#!/usr/bin/env python3
"""
End-to-end integration test script for the Nutritional Agents pipeline.

Steps performed:
  1. Seed a default user profile in MongoDB (user_profiles collection)
  2. Submit the Unilabs PDF to the blood analysis agent → extract biomarkers
  3. Map blood biomarkers to UrinalysisData fields (urinalysis-style markers)
  4. Call POST /api/nutrition/plan with the mapped data
  5. Print the approved 7-day meal plan or the triage emergency alert

Usage:
    cd SMARTurinalysis-main/backend
    source .venv/bin/activate
    python3 integration_test.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from io import BytesIO

# ── Path bootstrap so we can import src.* without installing the package ──────
sys.path.insert(0, str(Path(__file__).parent))

from pypdf import PdfReader
from motor.motor_asyncio import AsyncIOMotorClient

from src.config.config import settings
from src.domains.blood_analysis.agents import (
    ExtractionAgent, StructuringAgent, ValidationAgent, EvaluationAgent, LoopAgent
)
from src.domains.nutritional_agents.gatekeeper import GatekeeperAgent
from src.domains.nutritional_agents.router_agent import RouterAgent
from src.domains.nutritional_agents.orchestrator import NutritionalOrchestrator
from src.domains.nutritional_agents.models import UrinalysisData

PDF_PATH = Path(__file__).parent.parent.parent / "unilabs results 3.pdf"
USER_ID = "test_user_laurindo"

# ─── Default user profile to seed ─────────────────────────────────────────────
DEFAULT_USER_PROFILE = {
    "user_id": USER_ID,
    "age": 32,
    "sex": "M",
    "pathologies": [],
    "allergies": [],
    "medications": [],
    "pregnancy": False,
    "goal": "manter_peso",
    "budget_tier": "Medio",
    "activity_level": "moderado",
}

# ─── Biomarker → UrinalysisData field mapping ──────────────────────────────────
# Blood panel biomarker names (Portuguese) → UrinalysisData field names
# We map what exists; fill safe defaults for absent fields.
BIOMARKER_MAP = {
    "Glicose": "Glucose",
    "Glucose": "Glucose",
    "Corpos Cetónicos": "Ketone",
    "Cetona": "Ketone",
    "Proteína": "Protein",
    "Proteínas": "Protein",
    "Leucócitos": "Leukocytes",
    "Nitritos": "Nitrite",
    "pH": "pHValue",
    "Densidade": "SpecificGravity",
}

SAFE_DEFAULTS = {
    "Glucose": "Negative",
    "Ketone": "Negative",
    "Protein": "Negative",
    "Leukocytes": "Negative",
    "Nitrite": "Negative",
    "pHValue": 7.0,
    "SpecificGravity": 1.015,
}


def _normalize_value(field: str, raw_value: str) -> str | float:
    """Normalize a raw biomarker string value to the UrinalysisData expected format."""
    val = raw_value.strip()

    if field in ("pHValue", "SpecificGravity"):
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return SAFE_DEFAULTS[field]

    # Leukocytes from a blood count (× 10^9/L) is NOT a urine dipstick reading.
    # Blood leukocytes 4–11 × 10^9/L is normal → map to Negative (no urine infection)
    if field == "Leukocytes":
        # Matches "4.48 x 10^9/L", "4.48", or plain numeric values from blood count
        is_blood_count = ("x 10" in val or "10^" in val or "/L" in val)
        try:
            numeric = float(val.split()[0].replace(",", "."))
            # Blood count range: 4–11 × 10^9/L = normal WBC, not a urine dipstick positive
            if is_blood_count or numeric < 50:  # urine dipstick values are per µL (hundreds+)
                return "Negative" if 4.0 <= numeric <= 11.0 else "Positive"
        except (ValueError, IndexError):
            pass
        return val


    # Serum glucose (mg/dL from blood panel) → urine dipstick equivalent
    if field == "Glucose":
        # If value already looks like a dipstick qualifier, return it as-is
        if any(q in val.lower() for q in ("negative", "+", "trace", "low", "high")):
            return val
        try:
            numeric = float(val.split()[0].replace(",", "."))
            # Normal serum glucose (60-110 mg/dL) → no glycosuria
            if numeric <= 110:
                return "Negative"
            if numeric <= 180:
                return "Trace"
            if numeric <= 250:
                return "+"
            if numeric <= 350:
                return "++"
            return "+++"
        except (ValueError, IndexError):
            return SAFE_DEFAULTS[field]

    return val if val else SAFE_DEFAULTS.get(field, "Negative")


def map_biomarkers_to_urinalysis(biomarkers: list[dict]) -> dict:
    """
    Convert blood analysis biomarker list to UrinalysisData-compatible dict.
    Uses SAFE_DEFAULTS for any field not present in the biomarker list.
    """
    result = dict(SAFE_DEFAULTS)
    for entry in biomarkers:
        name = entry.get("biomarker", "")
        value = entry.get("value", "")
        for pt_name, field in BIOMARKER_MAP.items():
            if pt_name.lower() in name.lower():
                result[field] = _normalize_value(field, value)
                break
    return result


def run_blood_analysis_pipeline(pdf_path: Path) -> dict:
    """Run the blood analysis multi-agent pipeline on a PDF file."""
    print(f"\n[1/4] 📄 Reading PDF: {pdf_path.name}")
    file_bytes = pdf_path.read_bytes()
    content_type = "application/pdf"

    service_state = {
        "file_bytes": file_bytes,
        "content_type": content_type,
        "validation_result": "",
        "validation_feedback": "",
    }

    extraction = ExtractionAgent()
    structuring_loop = LoopAgent(
        name="RobustStructuringPlanner",
        description="Structuring + Validation loop",
        sub_agents=[StructuringAgent(), ValidationAgent()],
        max_iterations=3,
    )
    evaluation = EvaluationAgent()

    service_state = extraction.execute(service_state)
    print(f"    ✓ Extraction complete ({len(service_state.get('raw_text', ''))} chars)")

    service_state = structuring_loop.execute(service_state)
    structured = service_state.get("structured_data", {})
    print(f"    ✓ Structuring complete: {len(structured.get('biomarkers', []))} biomarkers found")

    service_state = evaluation.execute(service_state)
    result = service_state.get("final_result", {})
    print(f"    ✓ Evaluation complete for patient: {result.get('patient_name', 'Unknown')}")
    return result


async def seed_user_profile():
    """Insert (upsert) the default user profile into MongoDB."""
    print(f"\n[2/4] 🍃 Seeding user profile in MongoDB (user_id={USER_ID})")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    collection = db["user_profiles"]
    await collection.update_one(
        {"user_id": USER_ID},
        {"$set": DEFAULT_USER_PROFILE},
        upsert=True,
    )
    doc = await collection.find_one({"user_id": USER_ID}, {"_id": 0})
    client.close()
    print(f"    ✓ Profile seeded: {json.dumps(doc, indent=2, ensure_ascii=False)}")


async def run_nutrition_pipeline(urinalysis_dict: dict) -> None:
    """Run the full nutritional agent pipeline with mapped data."""
    print(f"\n[4/4] 🤖 Running Nutritional Agents pipeline (user_id={USER_ID})")

    # Build UrinalysisData — map dict keys to aliased fields
    alias_map = {
        "Glucose": "Glucose",
        "Ketone": "Ketone",
        "Protein": "Protein",
        "Leukocytes": "Leukocytes",
        "Nitrite": "Nitrite",
        "pHValue": "pHValue",
        "SpecificGravity": "SpecificGravity",
    }
    urinalysis_data = UrinalysisData(**{
        alias_map[k]: v for k, v in urinalysis_dict.items() if k in alias_map
    })

    orchestrator = NutritionalOrchestrator()
    response = await orchestrator.run(urinalysis_data=urinalysis_data, user_id=USER_ID)

    print("\n" + "═" * 60)
    if response.triage_alert:
        print("⚠️  EMERGENCY LOCK TRIGGERED")
        print(f"   Alert: {response.triage_alert.alert_message}")
        print(f"   Helpline: {response.triage_alert.helpline}")
        return

    if not response.success:
        print(f"❌ Pipeline failed: {response.error}")
        return

    plan = response.plan
    print(f"✅ PLAN APPROVED after audit")
    print(f"   Diet type  : {plan.diet_summary.diet_type}")
    print(f"   Calories   : {plan.diet_summary.target_calories_kcal} kcal/day")
    print(f"   Macros     : Carbs={plan.diet_summary.macro_distribution.carbohydrates_g}g | "
          f"Protein={plan.diet_summary.macro_distribution.proteins_g}g | "
          f"Fat={plan.diet_summary.macro_distribution.fats_g}g")
    print(f"   Budget     : {plan.financial_metrics.user_budget_tier} — "
          f"~{plan.financial_metrics.estimated_weekly_cost_eur}€/week")
    print(f"\n📅 Weekly Plan (Monday sample):")

    monday = plan.weekly_plan.get("monday")
    if monday:
        for meal_name in ("pequeno_almoco", "almoco", "lanche", "jantar"):
            meal = getattr(monday, meal_name, None)
            if meal:
                print(f"  {meal_name.upper():16s}: {meal.description}")
                print(f"  {'':16s}  Ingredients: {', '.join(meal.ingredients)}")

    disclaimer = plan.metadata.get("legal_disclaimer", "")
    if disclaimer:
        print(f"\n{disclaimer}")
    print("═" * 60)


async def main():
    if not PDF_PATH.exists():
        print(f"❌ PDF not found at: {PDF_PATH}")
        sys.exit(1)

    # Step 1 + 2: Blood analysis
    blood_result = run_blood_analysis_pipeline(PDF_PATH)
    biomarkers = blood_result.get("biomarkers", [])

    # Step 2: Seed MongoDB
    await seed_user_profile()

    # Step 3: Map biomarkers to urinalysis format
    print(f"\n[3/4] 🔬 Mapping {len(biomarkers)} biomarkers to UrinalysisData fields")
    urinalysis_dict = map_biomarkers_to_urinalysis(biomarkers)
    print(f"    ✓ Mapped data: {json.dumps(urinalysis_dict, ensure_ascii=False)}")

    # Step 4: Run nutritional agents
    await run_nutrition_pipeline(urinalysis_dict)


if __name__ == "__main__":
    asyncio.run(main())

"""
FastAPI router for the Nutritional Agents domain.
Registers endpoints under /api/nutrition/.
"""

from fastapi import APIRouter, HTTPException, status
from src.domains.nutritional_agents.models import (
    NutritionPlanRequest, NutritionPlanResponse,
)
from src.domains.nutritional_agents.orchestrator import NutritionalOrchestrator
from src.domains.nutritional_agents.router_agent import RouterAgent
from src.domains.nutritional_agents.models import UserProfile

router = APIRouter(prefix="/api/nutrition", tags=["Nutritional Agents"])

_orchestrator = NutritionalOrchestrator()


@router.post(
    "/plan",
    response_model=NutritionPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a personalized weekly nutrition plan",
    description=(
        "Receives structured urinalysis data and a user ID, runs the full "
        "Nutritional Agent pipeline, and returns a safe, personalized 7-day meal plan. "
        "Returns an emergency alert if critical clinical thresholds are detected."
    ),
)
async def generate_nutrition_plan(request: NutritionPlanRequest) -> NutritionPlanResponse:
    """
    Trigger the full orchestrator pipeline (Gatekeeper → Router → Clinical ↔ Auditor).
    Returns either an approved weekly plan or a triage emergency alert.
    """
    result = await _orchestrator.run(
        urinalysis_data=request.urinalysis_data,
        user_id=request.user_id,
    )

    # Surface emergency lock as a 503 so the client can render the alert UI
    if result.triage_alert:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.triage_alert.model_dump(),
        )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error,
        )

    return result


@router.get(
    "/status",
    summary="Nutritional agents subsystem health check",
)
async def nutrition_status() -> dict:
    """Return the health status of the nutritional agents subsystem."""
    return {
        "status": "operational",
        "agents": ["gatekeeper", "router", "oncology", "pregnancy", "autoimmune", "clinical", "auditor"],
    }


@router.get(
    "/profile/{user_id}",
    response_model=UserProfile,
    summary="Get User Clinical Profile",
)
async def get_user_profile(user_id: str) -> UserProfile:
    """Fetch the user's clinical profile from the database."""
    router_agent = RouterAgent()
    profile = await router_agent.fetch_clinical_profile(user_id)
    return profile


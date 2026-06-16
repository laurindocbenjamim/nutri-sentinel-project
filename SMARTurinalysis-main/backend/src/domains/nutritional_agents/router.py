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
from src.domains.nutritional_agents.models import (
    UserProfile, ShoppingListItem, PriceComparisonMatrix, PriceComparisonItem,
    ShoppingCategory
)
from src.shared.database import get_collection

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

@router.get(
    "/shopping-list",
    summary="Visualize a sample shopping list",
    description="Returns a generated sample shopping list and price matrix for visualization.",
)
async def visualize_shopping_list():
    """
    Returns a sample shopping list and price comparison matrix.
    This is useful for frontend visualization of the background capabilities.
    """
    return {
        "shopping_list": [
            ShoppingListItem(item_name="Aveia Sem Glúten", quantity="500g", category=ShoppingCategory.GROCERY),
            ShoppingListItem(item_name="Bebida de Amêndoa", quantity="1L", category=ShoppingCategory.GROCERY),
            ShoppingListItem(item_name="Peito de Frango", quantity="1kg", category=ShoppingCategory.MEAT_FISH),
            ShoppingListItem(item_name="Ovos M/L", quantity="1 dúzia", category=ShoppingCategory.MEAT_FISH),
            ShoppingListItem(item_name="Batata-Doce", quantity="2kg", category=ShoppingCategory.PRODUCE),
            ShoppingListItem(item_name="Brócolos", quantity="500g", category=ShoppingCategory.PRODUCE),
        ],
        "price_comparison": PriceComparisonMatrix(
            items=[
                PriceComparisonItem(ingredient="Aveia Sem Glúten", continente_price="2.29€", lidl_price="-", mercadona_price="2.40€", celeiro_price="2.54€"),
                PriceComparisonItem(ingredient="Peito de Frango (1kg)", continente_price="6.49€", lidl_price="6.59€", mercadona_price="6.59€", celeiro_price="15.00€"),
                PriceComparisonItem(ingredient="Batata-Doce", continente_price="1.79€", lidl_price="1.59€", mercadona_price="1.69€", celeiro_price="2.99€"),
            ],
            total_continente="10.57€",
            total_lidl="8.18€",
            total_mercadona="10.68€",
            total_celeiro="20.53€",
            auditor_note="O Lidl apresenta o cabaz mais económico para frescos. Recomendamos comprar aveia sem glúten no Continente ou Mercadona."
        )
    }

@router.get(
    "/ingredients",
    summary="List all ingredients",
    description="Returns a list of all ingredients available in the database, including their current prices.",
)
async def list_ingredients(skip: int = 0, limit: int = 100):
    """
    Fetch the list of ingredients/foods from the MongoDB database.
    """
    collection = get_collection("ingredients")
    cursor = collection.find({}).skip(skip).limit(limit)
    ingredients = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to string for JSON serialization
        ingredients.append(doc)
    return {"ingredients": ingredients}

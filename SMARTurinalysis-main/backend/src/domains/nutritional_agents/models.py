"""
Pydantic schemas for all inter-agent payloads in the Nutritional Agents pipeline.
These models define the shared communication contract between all agents.
"""

from __future__ import annotations
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class ShoppingCategory(str, Enum):
    MEAT_FISH = "Talho, Peixaria e Ovos"
    GROCERY = "Mercearia (Secção Sem Glúten)"
    PRODUCE = "Frutaria e Legumes"

class TriageStatus(str, Enum):
    CLEAR = "CLEAR"
    EMERGENCY_LOCK = "EMERGENCY_LOCK"


class AuditStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BudgetTier(str, Enum):
    STUDENT = "Economia_Estudante"
    MEDIUM = "Medio"
    PREMIUM = "Premium"


class BudgetStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    EXCEEDED = "EXCEEDED"


class GlycemicLoad(str, Enum):
    LOW = "Baixa"
    MEDIUM = "Média"
    HIGH = "Alta"


class FastingProtocol(str, Enum):
    NONE = "none"
    INTERMITTENT_12_12 = "12/12"
    INTERMITTENT_16_8 = "16/8"
    PROLONGED_24_48 = "24/48"


# ─── Input Models ─────────────────────────────────────────────────────────────

class UrinalysisData(BaseModel):
    """Raw structured urinalysis markers from the analysis domain."""
    glucose: str = Field(..., alias="Glucose")
    ketone: str = Field(..., alias="Ketone")
    protein: str = Field(..., alias="Protein")
    leukocytes: str = Field(..., alias="Leukocytes")
    nitrite: str = Field(..., alias="Nitrite")
    ph_value: float = Field(..., alias="pHValue")
    specific_gravity: float = Field(..., alias="SpecificGravity")

    model_config = {"populate_by_name": True}


class UserProfile(BaseModel):
    """Clinical and demographic profile retrieved from DB for a given user."""
    user_id: str
    user_uuid: Optional[str] = None
    username: Optional[str] = None
    age: int
    sex: str
    pathologies: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    pregnancy: bool = False
    goal: str = "manter_peso"
    budget_tier: BudgetTier = BudgetTier.MEDIUM
    activity_level: str = "moderado"


# ─── Triage Models ────────────────────────────────────────────────────────────

class TriageResult(BaseModel):
    """Output payload from the Gatekeeper Agent."""
    triagem: TriageStatus
    action: str
    alert_message: Optional[str] = None
    helpline: Optional[str] = "SNS 24: 808 24 24 24"


# ─── Meal Models ──────────────────────────────────────────────────────────────

class Meal(BaseModel):
    """A single meal within a daily plan."""
    description: str
    ingredients: list[str]
    allergens_checked: list[str]
    glycemic_load: GlycemicLoad


class DailyPlan(BaseModel):
    """Complete meals for a single day."""
    pequeno_almoco: Meal
    almoco: Meal
    lanche: Meal
    jantar: Meal
    explanation: str = ""


# ─── Plan Models ──────────────────────────────────────────────────────────────

class MacroDistribution(BaseModel):
    carbohydrates_g: int
    proteins_g: int
    fats_g: int


class DietSummary(BaseModel):
    diet_type: str
    target_calories_kcal: int
    macro_distribution: MacroDistribution
    clinical_summary: str = ""
    notes_explanation: str = ""


class FinancialMetrics(BaseModel):
    user_budget_tier: BudgetTier
    estimated_weekly_cost_eur: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    currency: str = "EUR"
    budget_status: BudgetStatus = BudgetStatus.COMPLIANT


class AuditorEvaluation(BaseModel):
    status: AuditStatus = AuditStatus.PENDING
    rejected_meals: list[str] = Field(default_factory=list)
    rejection_reason: str = ""


class ShoppingListItem(BaseModel):
    item_name: str
    quantity: str
    category: ShoppingCategory


class PriceComparisonItem(BaseModel):
    ingredient: str
    continente_price: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    lidl_price: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    mercadona_price: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    celeiro_price: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]


class PriceComparisonMatrix(BaseModel):
    items: list[PriceComparisonItem]
    total_continente: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    total_lidl: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    total_mercadona: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    total_celeiro: Annotated[Decimal, Field(max_digits=7, decimal_places=2)]
    auditor_note: str


class WeeklyPlanPayload(BaseModel):
    """Full inter-agent payload shared between Agent 3.D and Agent 4."""
    metadata: dict
    diet_summary: DietSummary
    financial_metrics: FinancialMetrics
    weekly_plan: dict[str, DailyPlan]
    shopping_list: list[ShoppingListItem] = Field(default_factory=list)
    price_comparison: Optional[PriceComparisonMatrix] = None
    auditor_evaluation: AuditorEvaluation = Field(
        default_factory=AuditorEvaluation
    )


# ─── Request / Response ───────────────────────────────────────────────────────

class NutritionPlanRequest(BaseModel):
    """API request body for POST /api/nutrition/plan."""
    urinalysis_data: UrinalysisData
    user_id: str


class NutritionPlanResponse(BaseModel):
    """API response for a successful plan generation."""
    success: bool
    plan: Optional[WeeklyPlanPayload] = None
    error: Optional[str] = None
    triage_alert: Optional[TriageResult] = None

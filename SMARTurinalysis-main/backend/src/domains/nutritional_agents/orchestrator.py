"""
DAG Orchestrator — Nutritional Agent Loop Controller.

Manages the full Hub-and-Spoke pipeline: Gatekeeper → Router → Specialists
→ [Clinical ↔ Auditor loop] → Final output.
Maximum 3 correction iterations before returning a safe-failure response.
"""

from __future__ import annotations
from src.domains.nutritional_agents.models import (
    UrinalysisData, UserProfile, WeeklyPlanPayload,
    TriageStatus, NutritionPlanResponse,
)
from src.domains.nutritional_agents.gatekeeper import GatekeeperAgent
from src.domains.nutritional_agents.router_agent import RouterAgent
from src.domains.nutritional_agents.specialists.clinical import ClinicalNutritionAgent
from src.domains.nutritional_agents.auditor import AuditorAgent

_MAX_LOOP_ITERATIONS = 3

_SAFE_FAILURE_MESSAGE = (
    "O sistema não conseguiu gerar um plano 100% seguro em ambiente automatizado. "
    "Por favor, consulte um nutricionista humano credenciado."
)

_LEGAL_DISCLAIMER = (
    "AVISO LEGAL: Este plano alimentar é gerado por IA e tem caráter meramente "
    "informativo. Não substitui a consulta com um médico ou nutricionista. "
    "Verifique sempre os rótulos dos produtos no supermercado para confirmar a "
    "certificação 'Sem Glúten' e a ausência de alérgenos declarados."
)


class NutritionalOrchestrator:
    """
    DAG controller for the full Nutritional Agent pipeline.
    Coordinates all agents from triage to final plan delivery.
    """

    def __init__(self):
        self._gatekeeper = GatekeeperAgent()
        self._router = RouterAgent()
        self._clinical = ClinicalNutritionAgent()
        self._auditor = AuditorAgent()

    async def run(self, urinalysis_data: UrinalysisData, user_id: str) -> NutritionPlanResponse:
        """
        Execute the full DAG pipeline and return a NutritionPlanResponse.

        Stages:
        1. Gatekeeper — safety triage
        2. Router — clinical profile + specialist activation
        3. Clinical ↔ Auditor loop (max 3 iterations)
        4. Final output or safe-failure response
        """
        # ── Stage 1: Safety Triage ────────────────────────────────────────────
        triage_status = self._gatekeeper.validate_thresholds(urinalysis_data)
        if triage_status == TriageStatus.EMERGENCY_LOCK:
            alert = self._gatekeeper.trigger_emergency_lock()
            return NutritionPlanResponse(
                success=False,
                triage_alert=alert,
                error="Parâmetros críticos detetados. Geração de dieta bloqueada.",
            )

        # ── Stage 2: Context + Specialist Routing ─────────────────────────────
        profile: UserProfile = await self._router.fetch_clinical_profile(user_id)
        specialists = self._router.define_pipeline(profile)

        # Accumulate all specialist directives
        directives: dict = {}
        for specialist in specialists:
            directives.update(specialist.generate_directives(profile))

        # ── Stage 3+4: Agent Loop (Clinical ↔ Auditor) ───────────────────────
        approved_plan: WeeklyPlanPayload | None = None

        for attempt in range(1, _MAX_LOOP_ITERATIONS + 1):
            plan = await self._clinical.structure_weekly_menu(
                urinalysis_data, profile, directives, loop_attempt=attempt
            )
            audit_result = self._auditor.audit(plan, profile, directives)

            if audit_result["status"] == "APPROVED":
                approved_plan = plan
                break

            # Inject auditor feedback into directives for next generation attempt
            directives["feedback_correction"] = audit_result["rejection_reason"]

        # ── Stage 5: Final Output ─────────────────────────────────────────────
        if approved_plan:
            # Generate Shopping List & Price Matrix
            approved_plan = await self._clinical.generate_shopping_list_and_prices(approved_plan)
            
            # Append legal disclaimer to metadata before delivery
            approved_plan.metadata["legal_disclaimer"] = _LEGAL_DISCLAIMER
            return NutritionPlanResponse(success=True, plan=approved_plan)

        return NutritionPlanResponse(success=False, error=_SAFE_FAILURE_MESSAGE)

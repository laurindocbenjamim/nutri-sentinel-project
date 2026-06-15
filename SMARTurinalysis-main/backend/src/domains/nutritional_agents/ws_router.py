"""
WebSocket endpoint for the Nutritional Agents pipeline.

Streams real-time progress events to the frontend during the
DAG agent loop execution (Gatekeeper → Router → Specialists → Clinical → Auditor).
"""

from __future__ import annotations
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.domains.nutritional_agents.gatekeeper import GatekeeperAgent
from src.domains.nutritional_agents.router_agent import RouterAgent
from src.domains.nutritional_agents.specialists.clinical import ClinicalNutritionAgent
from src.domains.nutritional_agents.auditor import AuditorAgent
from src.domains.subscriptions.database import get_db_session
from src.domains.subscriptions.service import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from src.domains.nutritional_agents.models import (
    UrinalysisData, TriageStatus, NutritionPlanResponse, TriageResult, FastingProtocol
)

router = APIRouter(prefix="/api/nutrition", tags=["Nutritional Agents WS"])

_MAX_LOOPS = 3
_EMERGENCY_HELPLINE = "SNS 24: 808 24 24 24"


async def _send(ws: WebSocket, event: str, payload: dict) -> None:
    """Send a structured JSON event over the WebSocket."""
    await ws.send_text(json.dumps({"event": event, **payload}))


@router.websocket("/ws/generate")
async def nutrition_ws(
    ws: WebSocket,
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    WebSocket endpoint that streams agent pipeline progress.

    Expected client message (JSON):
        { "urinalysis": {...}, "user_id": "..." }

    Emitted events:
        progress  — { step, label, percent }
        approved  — { plan: WeeklyPlanPayload }
        emergency — { alert: TriageResult }
        error     — { message: str }
        done      — {}
    """
    await ws.accept()
    try:
        raw = await ws.receive_text()
        payload = json.loads(raw)

        urinalysis_dict = payload.get("urinalysis", {})
        user_id = payload.get("user_id", "test_user_laurindo")
        blood_data = payload.get("blood_data", [])
        notes = payload.get("notes", "")
        fasting_raw = payload.get("fasting_protocol", "none")
        language = payload.get("language", "English")

        # Quota check
        sub_service = SubscriptionService(db_session)
        has_quota = await sub_service.check_and_consume_quota(user_id)
        if not has_quota:
            await _send(ws, "error", {"message": "Quota Exceeded. Please upgrade your plan to generate more nutritional reports."})
            await _send(ws, "done", {})
            return
        
        try:
            fasting_protocol = FastingProtocol(fasting_raw)
        except ValueError:
            fasting_protocol = FastingProtocol.NONE

        # Build UrinalysisData from the incoming dict
        urinalysis_data = UrinalysisData(**urinalysis_dict)

        # ── Step 1: Router / DB (Fetch Profile First) ─────────────────────────
        await _send(ws, "progress", {
            "step": 1, "label": "🔍 Router: Fetching clinical profile from database...", "percent": 10
        })
        router_agent = RouterAgent()
        profile = await router_agent.fetch_clinical_profile(user_id)
        
        # ── Apply Clinical Overrides ──
        overrides = payload.get("clinical_overrides", {})
        if overrides.get("pregnancy"):
            profile.pregnancy = True
        if overrides.get("cancer"):
            profile.pathologies.append("Cancro (Oncologia)")
        if overrides.get("other_risk"):
            profile.pathologies.append("Doença de Alto Risco")

        await _send(ws, "progress", {
            "step": 1,
            "label": f"✅ Router: Profile loaded — {len(profile.pathologies)} pathologies, {len(profile.allergies)} allergies.",
            "percent": 20
        })

        # ── Step 2: Gatekeeper ────────────────────────────────────────────────
        await _send(ws, "progress", {
            "step": 2, "label": "🛡️ Gatekeeper: Analysing clinical markers & safety rules...", "percent": 30
        })
        await asyncio.sleep(0.3)

        gatekeeper = GatekeeperAgent()
        
        # 2a. Validate fasting protocol against profile
        fasting_alert = gatekeeper.validate_fasting(profile, fasting_protocol)
        if fasting_alert:
            await _send(ws, "emergency", {"alert": fasting_alert.model_dump()})
            await _send(ws, "done", {})
            return

        # 2b. Validate urinalysis thresholds
        triage = gatekeeper.validate_thresholds(urinalysis_data)
        if triage == TriageStatus.EMERGENCY_LOCK:
            alert = gatekeeper.trigger_emergency_lock()
            await _send(ws, "emergency", {"alert": alert.model_dump()})
            await _send(ws, "done", {})
            return

        await _send(ws, "progress", {
            "step": 2, "label": "✅ Gatekeeper: All markers within safe limits.", "percent": 40
        })

        # ── Step 3: Specialist agents ─────────────────────────────────────────
        await _send(ws, "progress", {
            "step": 3, "label": "🧬 Specialists: Building dietary directives...", "percent": 50
        })
        specialists = router_agent.define_pipeline(profile)
        directives: dict = {}
        for specialist in specialists:
            directives.update(specialist.generate_directives(profile))

        specialist_names = [type(s).__name__ for s in specialists] or ["General Protocol"]
        await _send(ws, "progress", {
            "step": 3,
            "label": f"✅ Specialists: Active — {', '.join(specialist_names)}",
            "percent": 60
        })

        # ── Step 4: Clinical + Auditor loop ───────────────────────────────────
        clinical = ClinicalNutritionAgent()
        auditor = AuditorAgent()
        approved_plan = None

        for attempt in range(1, _MAX_LOOPS + 1):
            await _send(ws, "progress", {
                "step": 4,
                "label": f"🍽️ Clinical Agent: Generating 7-day meal plan (attempt {attempt}/{_MAX_LOOPS})...",
                "percent": 65 + (attempt - 1) * 8
            })
            plan = clinical.structure_weekly_menu(
                urinalysis_data, profile, directives, attempt, blood_data, notes, fasting_protocol, language
            )

            await _send(ws, "progress", {
                "step": 5,
                "label": f"🔎 Auditor: Validating allergens, budget & nutritional targets...",
                "percent": 70 + (attempt - 1) * 8
            })
            audit = auditor.audit(plan, profile, directives)

            if audit["status"] == "APPROVED":
                approved_plan = plan
                break
            directives["feedback_correction"] = audit["rejection_reason"]

        # ── Step 5: Final output ──────────────────────────────────────────────
        if approved_plan:
            _LEGAL = (
                "⚠️ AVISO LEGAL: Este plano alimentar é gerado por IA e tem caráter meramente "
                "informativo. Não substitui a consulta com um médico ou nutricionista. "
                "Verifique sempre os rótulos dos produtos no supermercado."
            )
            approved_plan.metadata["legal_disclaimer"] = _LEGAL

            await _send(ws, "progress", {
                "step": 6, "label": "✅ Plan approved! Delivering your personalised diet.", "percent": 100
            })
            await _send(ws, "approved", {"plan": approved_plan.model_dump(mode="json")})
        else:
            await _send(ws, "error", {
                "message": (
                    "O sistema não conseguiu gerar um plano 100% seguro. "
                    "Por favor, consulte um nutricionista humano credenciado."
                )
            })

        await _send(ws, "done", {})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await _send(ws, "error", {"message": f"Pipeline error: {str(exc)}"})
            await _send(ws, "done", {})
        except Exception:
            pass

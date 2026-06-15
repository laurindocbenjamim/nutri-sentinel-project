"""
FastAPI router for blood report OCR and multi-agent clinical analysis.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from src.domains.blood_analysis.service import BloodAnalysisService
from src.domains.blood_analysis.schemas import BloodAnalysisResult
from src.domains.subscriptions.database import get_db_session
from src.domains.subscriptions.service import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/blood-analysis", tags=["blood_analysis"])
service = BloodAnalysisService()

@router.post("/upload", response_model=BloodAnalysisResult)
async def upload_blood_report(
    file: UploadFile = File(...),
    user_uuid: str = Form(default="test_user_laurindo"),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Accepts a blood report PDF/image and runs the multi-agent extraction/evaluation pipeline.
    """
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and PNG/JPEG images are accepted."
        )

    sub_service = SubscriptionService(db_session)
    has_quota = await sub_service.check_and_consume_quota(user_uuid)
    if not has_quota:
        raise HTTPException(
            status_code=402,
            detail="Quota Exceeded. Please upgrade your plan to process more blood reports."
        )

    try:
        content = await file.read()
        res = service.process_blood_report(content, file.content_type)
        if not res or not res.get("biomarkers"):
            raise HTTPException(
                status_code=422,
                detail="Could not extract or validate clinical biomarkers from the report."
            )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent analysis failure: {str(e)}"
        )

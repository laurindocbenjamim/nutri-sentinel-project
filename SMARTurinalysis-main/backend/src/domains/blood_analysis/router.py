"""
FastAPI router for blood report OCR and multi-agent clinical analysis.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from src.domains.blood_analysis.service import BloodAnalysisService
from src.domains.blood_analysis.schemas import BloodAnalysisResult

router = APIRouter(prefix="/api/blood-analysis", tags=["blood_analysis"])
service = BloodAnalysisService()

@router.post("/upload", response_model=BloodAnalysisResult)
async def upload_blood_report(file: UploadFile = File(...)):
    """
    Accepts a blood report PDF/image and runs the multi-agent extraction/evaluation pipeline.
    """
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and PNG/JPEG images are accepted."
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

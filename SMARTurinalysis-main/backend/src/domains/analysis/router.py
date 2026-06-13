"""
FastAPI router for handling image uploads and returning analysis results.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from src.domains.analysis.service import AnalysisService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
service = AnalysisService()

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Accepts an uploaded smartphone photo of a urine dipstick and reference card,
    performs alignment, color extraction, and returns the clinical results.
    """
    # Verify file is an image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")
        
    try:
        content = await file.read()
        res = service.process_image(content)
        
        if not res.get("success"):
            raise HTTPException(status_code=422, detail=res.get("error", "Analysis failed"))
            
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

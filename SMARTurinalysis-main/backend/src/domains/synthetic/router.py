"""
FastAPI router for synthetic image generation.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from src.domains.synthetic.schemas import GenerateMockRequest
from src.domains.synthetic.service import (
    generate_ref_card,
    generate_urine_stick,
    generate_mock_photo,
    ensure_templates_exist,
    REF_IMAGES_DIR
)
from src.config.config import settings
import cv2

router = APIRouter(prefix="/api/synthetic", tags=["synthetic"])

# Static directory for serving generated mock photos
STATIC_DIR = os.path.join(settings.BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

@router.post("/generate")
async def generate_images(request: GenerateMockRequest):
    """
    Ensure template images exist and generate a mock combined photo.
    Returns the path to the generated mock photo.
    """
    try:
        # 1. Ensure templates exist in referenceimages/
        ensure_templates_exist()
        
        # 2. Load templates to build mock photo
        card_path = os.path.join(REF_IMAGES_DIR, "RefCard.jpg")
        stick_path = os.path.join(REF_IMAGES_DIR, "UrineStick.jpg")
        
        card = cv2.imread(card_path)
        stick = cv2.imread(stick_path)
        
        if card is None or stick is None:
            raise HTTPException(status_code=500, detail="Failed to load template images")
            
        # 3. Validate selections and reaction times
        eval_time = request.eval_time
        if eval_time not in [30, 40, 45, 60, 120]:
            raise HTTPException(status_code=400, detail="Invalid evaluation time. Must be one of: 30, 40, 45, 60, 120")

        # Time-dependent reaction times for Siemens Multistix 10 SG (in seconds)
        analyte_reaction_times = {
            0: 30,  # Glucose
            1: 30,  # Bilirubin
            2: 40,  # Ketone
            3: 45,  # SpecificGravity
            4: 60,  # Hemoglobin
            5: 60,  # pHValue
            6: 60,  # Protein
            7: 60,  # Urobilinogen
            8: 60,  # Nitrite
            9: 120  # Leukocytes
        }

        selections = {}
        for k, v in request.selections.items():
            if not (0 <= k <= 9) or not (0 <= v <= 6):
                raise HTTPException(status_code=400, detail="Invalid analyte (0-9) or color index (0-6)")
            # Only apply color selection if the evaluation time is reached
            if analyte_reaction_times[k] <= eval_time:
                selections[k] = v
            else:
                selections[k] = 0

        # 4. Generate combined mock photo
        mock_photo = generate_mock_photo(card, stick, selections)
        mock_path = os.path.join(STATIC_DIR, "mock_photo.png")
        cv2.imwrite(mock_path, mock_photo)
        
        return {
            "success": True,
            "mock_image_url": "/static/mock_photo.png",
            "ref_card_url": "/static/RefCard.jpg",
            "message": "Templates and mock photo generated successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.get("/templates/card")
async def get_ref_card():
    """
    Serve the RefCard template image.
    """
    ensure_templates_exist()
    card_path = os.path.join(REF_IMAGES_DIR, "RefCard.jpg")
    if not os.path.exists(card_path):
        raise HTTPException(status_code=404, detail="RefCard template not found")
    return FileResponse(card_path, media_type="image/jpeg")

@router.get("/templates/stick")
async def get_urine_stick():
    """
    Serve the UrineStick template image.
    """
    ensure_templates_exist()
    stick_path = os.path.join(REF_IMAGES_DIR, "UrineStick.jpg")
    if not os.path.exists(stick_path):
        raise HTTPException(status_code=404, detail="UrineStick template not found")
    return FileResponse(stick_path, media_type="image/jpeg")

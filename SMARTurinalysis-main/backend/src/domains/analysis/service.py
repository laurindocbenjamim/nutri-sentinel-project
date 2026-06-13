"""
Service module for orchestrating the Urinalysis detection and color analysis pipeline.
"""

import os
import cv2
import numpy as np
from src.domains.analysis.detector import UrineDetector
from src.domains.analysis.analyzer import analyze_urine

from src.config.config import settings

# Static directory for saving aligned objects
STATIC_DIR = os.path.join(settings.BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

class AnalysisService:
    """
    Orchestrates the detector and analyzer for a stateless API pipeline.
    """
    def __init__(self):
        self.detector = UrineDetector()

    def process_image(self, file_bytes: bytes) -> dict:
        """
        Processes upload image bytes, detects card and stick, runs color analysis.
        Saves aligned outputs to the static folder.
        """
        # Decode image from bytes
        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            return {"success": False, "error": "Invalid image format"}

        # Sharpness check using Laplacian Variance to detect blur
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if lap_var < 80.0:
            return {
                "success": False,
                "error": f"Image is too blurry (Sharpness score: {lap_var:.1f}). Please hold the camera steady and recapture."
            }

        # 1. Detect RefCard
        res_card = self.detector.find_object(image, self.detector.ref_card, 0.1)
        if res_card is None or res_card[0] is None:
            return {"success": False, "error": "Could not align Reference Card in photo. Make sure it is clearly visible."}
        
        ref_card_aligned, card_corners = res_card

        # 2. Detect UrineStick (passing RefCard corners to black it out)
        stick_aligned = self.detector.detect_stick(image, card_corners)
        if stick_aligned is None:
            return {"success": False, "error": "Could not align Urine Stick in photo. Make sure it is clearly visible."}

        # 3. Save aligned images to static folder
        card_static_path = os.path.join(STATIC_DIR, "aligned_card.jpg")
        stick_static_path = os.path.join(STATIC_DIR, "aligned_stick.jpg")
        
        cv2.imwrite(card_static_path, ref_card_aligned)
        cv2.imwrite(stick_static_path, stick_aligned)

        # 4. Run colorimetric analysis
        try:
            analysis_results = analyze_urine(ref_card_aligned, stick_aligned)
        except Exception as e:
            return {"success": False, "error": f"Urinalysis analysis failed: {str(e)}"}

        return {
            "success": True,
            "results": analysis_results,
            "aligned_card_url": "/static/aligned_card.jpg",
            "aligned_stick_url": "/static/aligned_stick.jpg"
        }

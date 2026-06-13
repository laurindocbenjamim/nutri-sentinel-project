"""
Tests for the Urinalysis alignment and analysis services and endpoints.
"""

import io
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_full_analysis_pipeline():
    """
    Generates a mock synthetic photo, uploads it to /api/analysis/upload,
    and asserts that all 10 analytes are correctly identified and evaluated.
    """
    # 1. Generate the synthetic mock photo (using default healthy selections)
    gen_response = client.post("/api/synthetic/generate", json={"selections": {
        0: 0, # Glucose: Negative
        2: 5  # Ketone: Level 5 (Large after col 1 deletion)
    }})
    assert gen_response.status_code == 200
    mock_url = gen_response.json()["mock_image_url"]
    
    # 2. Retrieve the mock image file bytes
    mock_img_response = client.get(mock_url)
    assert mock_img_response.status_code == 200
    image_bytes = mock_img_response.content
    
    # 3. Upload the mock photo for analysis
    file_payload = {
        "file": ("mock_photo.png", io.BytesIO(image_bytes), "image/png")
    }
    upload_response = client.post("/api/analysis/upload", files=file_payload)
    assert upload_response.status_code == 200
    
    analysis_data = upload_response.json()
    assert analysis_data["success"] is True
    assert "results" in analysis_data
    assert "aligned_card_url" in analysis_data
    assert "aligned_stick_url" in analysis_data
    
    # Verify that all 10 analytes exist
    results = analysis_data["results"]
    assert len(results) == 10
    
    for analyte in ["Glucose", "Bilirubin", "Ketone", "SpecificGravity", "Hemoglobin", "pHValue", "Protein", "Urobilinogen", "Nitrite", "Leukocytes"]:
        assert analyte in results
        assert "value" in results[analyte]
        assert "confidence" in results[analyte]
        assert "stick_color_bgr" in results[analyte]
        
    # Check that selections match the clinical mappings
    # Glucose selection was index 0 (Negative)
    assert "Negative" in results["Glucose"]["value"]
    # Ketone selection was index 4 (Large)
    assert "Large" in results["Ketone"]["value"]

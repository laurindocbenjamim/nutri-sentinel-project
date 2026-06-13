"""
Tests for the synthetic image generation service and API endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.domains.synthetic.service import REF_IMAGES_DIR

client = TestClient(app)

def test_ensure_templates_exist():
    """
    Test that RefCard.jpg and UrineStick.jpg templates are generated correctly.
    """
    card_path = os.path.join(REF_IMAGES_DIR, "RefCard.jpg")
    stick_path = os.path.join(REF_IMAGES_DIR, "UrineStick.jpg")
    
    # Clean up first to verify generation works
    if os.path.exists(card_path):
        os.remove(card_path)
    if os.path.exists(stick_path):
        os.remove(stick_path)
        
    response = client.post("/api/synthetic/generate", json={"selections": {}})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "mock_image_url" in data
    
    assert os.path.exists(card_path)
    assert os.path.exists(stick_path)

def test_generate_endpoint_validation():
    """
    Test that the synthetic generation endpoint validates selections.
    """
    # Invalid analyte index (10 is out of bounds)
    response = client.post("/api/synthetic/generate", json={"selections": {10: 0}})
    assert response.status_code == 400
    
    # Invalid color index (7 is out of bounds, max is 6)
    response = client.post("/api/synthetic/generate", json={"selections": {0: 7}})
    assert response.status_code == 400

def test_templates_endpoints():
    """
    Test that the endpoints serving RefCard and UrineStick respond successfully.
    """
    response_card = client.get("/api/synthetic/templates/card")
    assert response_card.status_code == 200
    assert response_card.headers["content-type"] == "image/jpeg"
    
    response_stick = client.get("/api/synthetic/templates/stick")
    assert response_stick.status_code == 200
    assert response_stick.headers["content-type"] == "image/jpeg"

def test_generate_endpoint_eval_time_validation():
    """
    Test validation of the eval_time query/body parameter.
    """
    # Valid evaluation times
    for t in [30, 40, 45, 60, 120]:
        response = client.post("/api/synthetic/generate", json={"selections": {}, "eval_time": t})
        assert response.status_code == 200
        
    # Invalid evaluation times
    for t in [0, 15, 50, 100, 150]:
        response = client.post("/api/synthetic/generate", json={"selections": {}, "eval_time": t})
        assert response.status_code == 400


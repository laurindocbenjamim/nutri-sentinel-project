"""
Integration tests for the multi-agent Blood Analysis OCR service and endpoints.
"""

import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def create_dummy_pdf() -> bytes:
    """Creates a basic empty PDF for testing text extraction flows."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

def test_blood_analysis_endpoint_unauthorized():
    """
    Ensures the blood analysis route enforces JWT session token security.
    """
    unauth_client = TestClient(app)
    pdf_bytes = create_dummy_pdf()
    files = {"file": ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = unauth_client.post("/api/blood-analysis/upload", files=files)
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

@patch("src.domains.blood_analysis.agents.call_groq")
def test_blood_analysis_pipeline_pdf(mock_call_groq):
    """
    Verifies that PDF analysis successfully coordinates the agent extraction and structuring steps.
    """
    mock_call_groq.side_effect = [
        # StructuringAgent result
        '{"patient_name": "Laurindo Chiteculo", "report_date": "16-09-2025", "biomarkers": [{"biomarker": "Glicose", "value": "85", "unit": "mg/dL", "reference_range": "60-110", "flag": "Normal"}]}',
        # EvaluationAgent result
        "Biomarkers are normal."
    ]
    pdf_bytes = create_dummy_pdf()
    files = {"file": ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    
    response = client.post("/api/blood-analysis/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_name"] == "Laurindo Chiteculo"
    assert data["report_date"] == "16-09-2025"
    assert len(data["biomarkers"]) == 1
    assert data["biomarkers"][0]["biomarker"] == "Glicose"
    assert data["biomarkers"][0]["value"] == "85"
    assert "normal" in data["recommendations"]

@patch("src.domains.blood_analysis.agents.call_groq")
def test_blood_analysis_pipeline_image(mock_call_groq):
    """
    Verifies that image uploads successfully route through the vision extraction pipeline.
    """
    mock_call_groq.side_effect = [
        # ExtractionAgent Vision call (simulating image text read)
        "Glicose 85 mg/dL (60-110)",
        # StructuringAgent call
        '{"patient_name": "Laurindo Chiteculo", "report_date": "16-09-2025", "biomarkers": [{"biomarker": "Glicose", "value": "85", "unit": "mg/dL", "reference_range": "60-110", "flag": "Normal"}]}',
        # EvaluationAgent call
        "Everything normal."
    ]
    img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    files = {"file": ("report.png", io.BytesIO(img_bytes), "image/png")}
    
    response = client.post("/api/blood-analysis/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_name"] == "Laurindo Chiteculo"
    assert len(data["biomarkers"]) == 1

def test_evaluation_agent_formatting():
    """
    Verifies that the EvaluationAgent programmatically strips out markdown header (##) and bold (**) markers.
    """
    from src.domains.blood_analysis.agents import EvaluationAgent
    agent = EvaluationAgent()
    state = {
        "structured_data": {
            "patient_name": "Test Patient",
            "report_date": "2026-06-14",
            "biomarkers": []
        }
    }
    with patch("src.domains.blood_analysis.agents.call_groq") as mock_call:
        mock_call.return_value = "## Recommendations\nWe suggest eating more **leafy greens**."
        res_state = agent.execute(state)
        final_result = res_state["final_result"]
        assert "##" not in final_result["recommendations"]
        assert "**" not in final_result["recommendations"]
        assert "Recommendations" in final_result["recommendations"]
        assert "leafy greens" in final_result["recommendations"]

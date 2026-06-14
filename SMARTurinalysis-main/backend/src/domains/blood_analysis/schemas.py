"""
Pydantic schemas for structured blood analysis data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

class BloodBiomarkerEntry(BaseModel):
    """
    Structured entry representing a single blood biomarker/test result.
    """
    biomarker: str = Field(..., description="Name of the biomarker/test (e.g., Glicose, Hemoglobina)")
    value: str = Field(..., description="Extracted value (e.g., 85, 1.09, <0.5)")
    unit: str = Field(..., description="Measurement unit (e.g., mg/dL, g/dL)")
    reference_range: str = Field(..., description="Reference normal range (e.g., 60-110, 13.2-16.6)")
    flag: str = Field(..., description="Status flag: Normal, High, Low, or Abnormal")

class BloodAnalysisResult(BaseModel):
    """
    Comprehensive blood report extraction result including metadata and clinical evaluation.
    """
    patient_name: Optional[str] = Field(None, description="Patient's full name if identified")
    report_date: Optional[str] = Field(None, description="Extraction/collection date of the report")
    biomarkers: List[BloodBiomarkerEntry] = Field(default_factory=list, description="Extracted biomarker list")
    recommendations: Optional[str] = Field(None, description="Health & nutrition evaluation from the final agent")

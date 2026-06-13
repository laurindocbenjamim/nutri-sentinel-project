"""
Pydantic validation schemas for the synthetic image generation domain.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field

class GenerateMockRequest(BaseModel):
    """
    Input schema for generating a synthetic urinalysis photo.
    Maps analyte indices (0-9) to color indices (0-6).
    """
    selections: Dict[int, int] = Field(
        default_factory=dict,
        description="Dictionary mapping analyte indices (0-9) to color indices (0-6)"
    )
    eval_time: Optional[int] = Field(
        default=120,
        description="Evaluation time in seconds (30, 40, 45, 60, 120) based on time-dependent reaction constraints."
    )

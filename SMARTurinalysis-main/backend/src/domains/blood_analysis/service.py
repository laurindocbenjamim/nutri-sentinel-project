"""
Service layer to orchestrate the multi-agent pipeline for blood report extraction and analysis.
"""

import logging
from src.domains.blood_analysis.agents import (
    ExtractionAgent,
    StructuringAgent,
    ValidationAgent,
    EvaluationAgent,
    LoopAgent
)

logger = logging.getLogger("nutri-sentinel")

class BloodAnalysisService:
    """
    Orchestrates sequential multi-agent execution for blood analysis reports.
    """
    def __init__(self) -> None:
        self.extraction_agent = ExtractionAgent()
        self.structuring_loop = LoopAgent(
            name="RobustStructuringPlanner",
            description="Runs structuring and validation in a loop with retry feedback.",
            sub_agents=[StructuringAgent(), ValidationAgent()],
            max_iterations=3
        )
        self.evaluation_agent = EvaluationAgent()

    def process_blood_report(self, file_bytes: bytes, content_type: str) -> dict:
        """
        Coordinates the multi-agent extraction, structuring, validation, and evaluation.
        """
        logger.info(f"Starting multi-agent processing for report with content type {content_type}")
        state = {
            "file_bytes": file_bytes,
            "content_type": content_type,
            "validation_result": "",
            "validation_feedback": ""
        }
        # Step 1: Extraction
        state = self.extraction_agent.execute(state)
        # Step 2: Structuring & Validation Loop
        state = self.structuring_loop.execute(state)
        # Step 3: Evaluation
        state = self.evaluation_agent.execute(state)
        
        return state.get("final_result", {})

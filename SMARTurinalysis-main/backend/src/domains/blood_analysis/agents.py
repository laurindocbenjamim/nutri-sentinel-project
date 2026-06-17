"""
Multi-agent system for blood report OCR and clinical evaluation.
"""

import base64
import json
import logging
from pypdf import PdfReader
import httpx
from src.config.config import settings

logger = logging.getLogger("nutri-sentinel")

def call_groq(prompt: str, system_prompt: str, json_mode: bool = False, model: str = None, image_url: str = None, max_tokens: int = None) -> str:
    """Calls Groq's Chat Completions API with support for text and vision models."""
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set. Returning mock JSON response.")
        if json_mode:
            return json.dumps({
                "patient_name": "Laurindo Chiteculo Benjamim",
                "report_date": "16-09-2025",
                "biomarkers": [
                    {"biomarker": "Glicose", "value": "85", "unit": "mg/dL", "reference_range": "60-110", "flag": "Normal"},
                    {"biomarker": "Creatinina", "value": "1.09", "unit": "mg/dL", "reference_range": "0.60-1.20", "flag": "Normal"}
                ]
            })
        return "Mock evaluation: Biomarkers are within healthy ranges."

    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    selected_model = model or settings.LLM_MODEL or "llama-3.1-8b-instant"
    
    if image_url:
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    else:
        user_content = prompt

    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error calling Groq API: {str(e)}")
        raise

class Agent:
    def __init__(self, name: str, description: str, instruction: str, output_key: str):
        self.name = name
        self.description = description
        self.instruction = instruction
        self.output_key = output_key

    def execute(self, state: dict) -> dict:
        raise NotImplementedError

class LoopAgent:
    def __init__(self, name: str, description: str, sub_agents: list, max_iterations: int = 3):
        self.name = name
        self.description = description
        self.sub_agents = sub_agents
        self.max_iterations = max_iterations

    def execute(self, state: dict) -> dict:
        for i in range(self.max_iterations):
            logger.info(f"LoopAgent {self.name}: iteration {i+1}/{self.max_iterations}")
            for agent in self.sub_agents:
                state = agent.execute(state)
            if state.get("validation_result") == "ok":
                break
        return state

class ExtractionAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ExtractionAgent",
            description="Extracts raw text from PDF files or images.",
            instruction="Extract raw patient and biomarker data text.",
            output_key="raw_text"
        )

    def execute(self, state: dict) -> dict:
        file_bytes = state.get("file_bytes")
        content_type = state.get("content_type", "")
        if "pdf" in content_type:
            from io import BytesIO
            reader = PdfReader(BytesIO(file_bytes))
            text_runs = [page.extract_text() or "" for page in reader.pages]
            state[self.output_key] = "\n".join(text_runs)
        else:
            img_b64 = base64.b64encode(file_bytes).decode("utf-8")
            sys_prompt = "You are a specialized medical OCR assistant. Read the image and extract all readable text."
            prompt = "Extract and describe all text, patient details, and biomarker readings in this image report."
            image_url = f"data:{content_type};base64,{img_b64}"
            state[self.output_key] = call_groq(
                prompt,
                sys_prompt,
                json_mode=False,
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                image_url=image_url
            )
        return state

class StructuringAgent(Agent):
    def __init__(self):
        super().__init__(
            name="StructuringAgent",
            description="Transforms raw text into a structured JSON database model.",
            instruction="Parse raw report text into structured JSON fields.",
            output_key="structured_data"
        )

    def execute(self, state: dict) -> dict:
        raw_text = state.get("raw_text", "")
        feedback = state.get("validation_feedback", "")
        sys_prompt = (
            "You are a clinical data structuring agent. Parse the provided raw lab report text "
            "into a JSON object matching this schema:\n"
            "{\n"
            "  'patient_name': string,\n"
            "  'report_date': string,\n"
            "  'biomarkers': [\n"
            "    { 'biomarker': string, 'value': string, 'unit': string, 'reference_range': string, 'flag': string }\n"
            "  ]\n"
            "}\n"
            "CRITICAL: Be extremely careful to extract ONLY the actual patient/utente's name. "
            "In these reports, the recipient/doctor is often listed first under 'A/C Exmo Sr(a). Dr(a).' or 'Médico' (e.g. 'ANA RITA AGUIAR'). "
            "Do NOT extract this doctor/recipient name as the patient. "
            "The actual patient/utente's name is located below the 'Utente' or 'Paciente' label (e.g. 'Laurindo Chiteculo Benjamim'). "
            "Do not extract doctor names, clinic directors, or laboratory technicians. "
            "For 'flag', specify 'Normal', 'High', 'Low', or 'Abnormal' based on value compared to reference range."
        )
        prompt = f"Raw report text:\n{raw_text}\n"
        if feedback:
            prompt += f"\nPrevious validation feedback to address:\n{feedback}"
        res = call_groq(prompt, sys_prompt, json_mode=True)
        state[self.output_key] = json.loads(res)
        return state

class ValidationAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ValidationAgent",
            description="Validates structured data for completeness and formatting.",
            instruction="Verify structured JSON structure, check for empty fields, and ensure safety.",
            output_key="validation_result"
        )

    def execute(self, state: dict) -> dict:
        data = state.get("structured_data", {})
        biomarkers = data.get("biomarkers", [])
        if not biomarkers:
            state[self.output_key] = "retry"
            state["validation_feedback"] = "No biomarkers parsed. Ensure you extract every row from the report."
            return state
        for b in biomarkers:
            if not b.get("biomarker") or not b.get("value"):
                state[self.output_key] = "retry"
                state["validation_feedback"] = f"Biomarker '{b.get('biomarker')}' is missing name or value."
                return state
        state[self.output_key] = "ok"
        state["validation_feedback"] = ""
        return state

class EvaluationAgent(Agent):
    def __init__(self):
        super().__init__(
            name="EvaluationAgent",
            description="Evaluates values in context of health and nutrition.",
            instruction="Provide nutrition, lifestyle, and health context for each parameter.",
            output_key="final_result"
        )

    def execute(self, state: dict) -> dict:
        data = state.get("structured_data", {})
        sys_prompt = (
            "You are a clinical health and nutrition advisor. Evaluate the provided structured blood report biomarkers. "
            "Discuss abnormal findings (High or Low flags), and provide target nutritional and lifestyle recommendations. "
            "CRITICAL: Do not use markdown headers (##) or bold text (**) in your response. Keep the output clean and raw-text styled."
        )
        prompt = f"Structured biomarkers: {json.dumps(data)}"
        raw_rec = call_groq(prompt, sys_prompt, json_mode=False)
        cleaned_rec = raw_rec.replace("**", "").replace("##", "")
        data["recommendations"] = cleaned_rec
        state[self.output_key] = data
        return state

"""
Agent 1 — Gatekeeper (Triagem e Emergência Médica).

Hard safety boundary. Analyzes urinalysis markers and blocks the entire
pipeline if any critical threshold is exceeded. No diet is generated when
EMERGENCY_LOCK is triggered.
"""

from src.domains.nutritional_agents.models import (
    UrinalysisData,
    TriageResult,
    TriageStatus,
    UserProfile,
    FastingProtocol,
)

# Categorical severity map for string-based markers (e.g., dipstick readings)
_SEVERITY_MAP: dict[str, int] = {
    "negative": 0, "trace": 1, "+": 1, "small": 1,
    "moderate": 2, "++": 2, "medium": 2,
    "large": 3, "+++": 3, "++++": 3,
}

_EMERGENCY_HELPLINE = "SNS 24: 808 24 24 24"
_EMERGENCY_MESSAGE = (
    "⚠️ Parâmetros críticos detetados. "
    "Por favor, contacte o SNS 24 ou dirija-se ao hospital mais próximo imediatamente."
)


def _severity(value: str) -> int:
    """Convert a string dipstick reading to a numeric severity level (0–3)."""
    return _SEVERITY_MAP.get(value.strip().lower(), 0)


def _is_glucose_critical(glucose: str) -> bool:
    """Return True if glucose reading indicates a dangerous level (≥ '++')."""
    try:
        numeric = float(glucose)
        return numeric >= 300
    except ValueError:
        return _severity(glucose) >= 2


def _is_ketone_present(ketone: str) -> bool:
    """Return True if ketone is anything other than 'Negative'."""
    return ketone.strip().lower() != "negative"


def _is_protein_critical(protein: str) -> bool:
    """Return True if protein indicates acute renal overload ('Large'/≥300)."""
    try:
        return float(protein) >= 300
    except ValueError:
        return _severity(protein) >= 3


def _is_uti_active(leukocytes: str, nitrite: str) -> bool:
    """Return True if both leukocytes and nitrite are positive — active UTI."""
    leu_positive = leukocytes.strip().lower() not in ("negative", "0", "none")
    nit_positive = nitrite.strip().lower() not in ("negative", "0", "none")
    return leu_positive and nit_positive


class GatekeeperAgent:
    """
    Agent 1 — Triagem e Emergência Médica.
    Validates urinalysis markers against hard clinical thresholds.
    Also validates fasting protocols against clinical profiles.
    """

    def validate_fasting(self, profile: UserProfile, fasting_protocol: FastingProtocol) -> TriageResult | None:
        """
        Check if the requested fasting protocol is clinically safe for the user.
        Blocks if pregnant, diabetic, or has an eating disorder.
        Returns a TriageResult(EMERGENCY_LOCK) if blocked, otherwise None.
        """
        if fasting_protocol == FastingProtocol.NONE:
            return None

        # Check conditions
        pathologies_lower = [p.lower() for p in profile.pathologies]
        
        is_diabetic = any("diabet" in p for p in pathologies_lower)
        has_eating_disorder = any("distúrbio" in p or "anorexia" in p or "bulimia" in p for p in pathologies_lower)
        has_cancer_or_risk = any("cancro" in p or "oncologia" in p or "alto risco" in p for p in pathologies_lower)
        
        if profile.pregnancy or is_diabetic or has_eating_disorder or has_cancer_or_risk:
            reason = "gravidez" if profile.pregnancy else "diabetes" if is_diabetic else "condição oncológica/alto risco" if has_cancer_or_risk else "histórico de distúrbio alimentar"
            msg = (
                f"⚠️ BLOQUEIO CLÍNICO: Protocolos de jejum não são indicados para o seu perfil "
                f"devido a {reason}. Risco elevado de complicações. "
                f"Por favor, desative a opção de jejum ou consulte o seu médico."
            )
            return TriageResult(
                triagem=TriageStatus.EMERGENCY_LOCK,
                action="ABORT_DIET",
                alert_message=msg,
                helpline=_EMERGENCY_HELPLINE,
            )
            
        return None

    def validate_thresholds(self, data: UrinalysisData) -> TriageStatus:
        """
        Analyze urinalysis markers and return CLEAR or EMERGENCY_LOCK.

        Rules:
        - Ketoacidosis: Critical glucose AND ketone present
        - Renal overload: Protein at 'Large' level
        - Active UTI: Both leukocytes and nitrite positive
        """
        if _is_glucose_critical(data.glucose) and _is_ketone_present(data.ketone):
            return TriageStatus.EMERGENCY_LOCK

        if _is_protein_critical(data.protein):
            return TriageStatus.EMERGENCY_LOCK

        if _is_uti_active(data.leukocytes, data.nitrite):
            return TriageStatus.EMERGENCY_LOCK

        return TriageStatus.CLEAR

    def trigger_emergency_lock(self) -> TriageResult:
        """Build and return the emergency alert payload."""
        return TriageResult(
            triagem=TriageStatus.EMERGENCY_LOCK,
            action="ABORT_DIET",
            alert_message=_EMERGENCY_MESSAGE,
            helpline=_EMERGENCY_HELPLINE,
        )

from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    correlation_id: str
    turbine_id: str
    timestamp: str
    metrics: Dict[str, Any]
    health_score: float
    alerts: List[Dict[str, Any]]
    diagnosis: Optional[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    pdf_path: Optional[str]
    email_sent: bool
    logs: List[str]
    next_agent: str

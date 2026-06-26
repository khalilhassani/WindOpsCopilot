from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class TelemetryData(BaseModel):
    turbine_id: str = Field(..., example="WTG-001")
    wind_speed: float = Field(..., description="Wind speed in m/s", example=12.5)
    rotor_speed: float = Field(..., description="Rotor speed in RPM", example=18.0)
    blade_temp: float = Field(..., description="Blade temperature in Celsius", example=48.2)
    generator_temp: float = Field(..., description="Generator temperature in Celsius", example=72.5)
    vibration: float = Field(..., description="Vibration in mm/s", example=0.15)
    power_output: float = Field(..., description="Power output in MW", example=2.8)
    status: str = Field(default="active", description="Operational status: active, offline, maintenance, curtailed", example="active")

class Alert(BaseModel):
    parameter: str
    value: float
    threshold: float
    severity: str  # warning, critical
    message: str

class DiagnosisResult(BaseModel):
    cause: str
    confidence: float
    details: str

class DecisionScenario(BaseModel):
    action: str  # e.g., "Normal Operation", "Curtail Power", "Plan Maintenance", "Emergency Shutdown"
    description: str
    risk_level: str  # low, medium, high
    production_impact: str  # none, low, moderate, severe
    confidence: float

class AgentResult(BaseModel):
    correlation_id: str
    turbine_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metrics: TelemetryData
    health_score: float
    alerts: List[Alert] = []
    diagnosis: Optional[DiagnosisResult] = None
    decisions: List[DecisionScenario] = []
    pdf_path: Optional[str] = None
    email_sent: bool = False
    logs: List[str] = []

class TurbineState(BaseModel):
    turbine_id: str
    health_score: float
    status: str
    last_update: str
    active_alerts_count: int

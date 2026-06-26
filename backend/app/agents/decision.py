import logging
import json
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.config import settings
from backend.app.agents.state import AgentState

logger = logging.getLogger("agents.decision")

def get_llm():
    """Returns ChatOpenAI instance if API key is present."""
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(temperature=0.1, model="gpt-4o-mini")
        except ImportError:
            pass
    return None

def decision_agent(state: AgentState) -> dict:
    """
    Evaluates operational alternatives and provides ranked recommendation scenarios.
    Applies hardcoded safety overrides for critical faults (wind > 25m/s or vibration > 0.25).
    """
    correlation_id = state.get("correlation_id", "N/A")
    metrics = state.get("metrics", {})
    alerts = state.get("alerts", [])
    diagnosis = state.get("diagnosis", {})
    health_score = state.get("health_score", 100.0)
    turbine_id = state.get("turbine_id", "Unknown")
    
    logger.info(f"[{correlation_id}] Decision Agent evaluating options for Turbine {turbine_id}")

    # Determine if a hard safety override is needed
    wind_speed = metrics.get("wind_speed", 0.0)
    vibration = metrics.get("vibration", 0.0)
    
    critical_shutdown_trigger = (wind_speed > 25.0) or (vibration > 0.25)
    
    decisions = []
    
    # Check if we should run LLM or rule fallback
    llm = get_llm()
    if llm and not critical_shutdown_trigger:
        try:
            # LLM Decision Logic
            system_prompt = (
                "You are a Senior Wind Farm Asset Management & Operations Decision Agent. "
                "Analyze the telemetry, health score, alerts, and diagnosis, and propose a list of ranked action options. "
                "Each scenario must contain:\n"
                "- 'action': A short title of the action (e.g. 'Curtail Power Output', 'Plan Immediate Maintenance').\n"
                "- 'description': Technical description of the scenario.\n"
                "- 'risk_level': 'low', 'medium', or 'high'.\n"
                "- 'production_impact': 'none', 'low', 'moderate', or 'severe'.\n"
                "- 'confidence': Decimal value between 0.0 and 1.0 showing recommendation certainty.\n"
                "Return strictly in JSON format as a list of dictionaries, with no formatting wrappers."
            )
            
            user_prompt = f"""
Turbine: {turbine_id}
Health Score: {health_score:.1f}%
Diagnosis Cause: {diagnosis.get('cause', 'N/A')}
Diagnosis Technical Details: {diagnosis.get('details', 'N/A')}
Active Alerts: {json.dumps(alerts, indent=2)}
Telemetry Data: {json.dumps(metrics, indent=2)}
"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = llm.invoke(messages)
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                    
            decisions = json.loads(content)
            
        except Exception as e:
            logger.warning(f"LLM decision failed: {e}. Falling back to rule-based engine.")

    # Rule-Based / Hardcoded safety overrides
    if not decisions:
        # Rule-Based Scenario Engine
        if critical_shutdown_trigger:
            # Mandated Emergency Shutdown
            reason = "extreme storm conditions (>25 m/s)" if wind_speed > 25.0 else "critical vibration threshold breach (>0.25 mm/s)"
            decisions = [
                {
                    "action": "Emergency Controlled Shutdown",
                    "description": f"Trigger pitch feathers and rotor brake immediately due to {reason}. Protect structural integrity of the asset.",
                    "risk_level": "low",
                    "production_impact": "severe",
                    "confidence": 1.0
                },
                {
                    "action": "De-rate / Curtail Power Output",
                    "description": "Reduce generator speed. (NOT RECOMMENDED: safety thresholds are violated, structural damage is likely if kept spinning).",
                    "risk_level": "high",
                    "production_impact": "moderate",
                    "confidence": 0.1
                }
            ]
        elif alerts:
            # Active warnings exist
            alert_params = [a["parameter"] for a in alerts]
            
            if "generator_temp" in alert_params or "blade_temp" in alert_params:
                decisions = [
                    {
                        "action": "Curtail Power Output (50% Load)",
                        "description": "De-rate the turbine capacity to reduce thermal load and allow generator/pitch systems to cool down while continuing partial production.",
                        "risk_level": "low",
                        "production_impact": "moderate",
                        "confidence": 0.90
                    },
                    {
                        "action": "Schedule Urgent Maintenance",
                        "description": "Deploy technician team within 48 hours to clean cooling manifolds and verify pitching gear actuators.",
                        "risk_level": "medium",
                        "production_impact": "low",
                        "confidence": 0.80
                    },
                    {
                        "action": "Continue Normal Production",
                        "description": "Maintain status quo. (HIGH RISK: temperature levels may continue escalating, risking permanent stator windings insulation damage).",
                        "risk_level": "high",
                        "production_impact": "none",
                        "confidence": 0.20
                    }
                ]
            elif "vibration" in alert_params:
                decisions = [
                    {
                        "action": "Plan Preventive Maintenance Inspection",
                        "description": "Schedule physical inspection of mechanical couplings and gearbox bearings within the next scheduled service cycle (7 days).",
                        "risk_level": "low",
                        "production_impact": "low",
                        "confidence": 0.85
                    },
                    {
                        "action": "De-rate Turbine Speed",
                        "description": "Impose RPM ceiling to suppress resonant vibrations while planning mechanical inspection.",
                        "risk_level": "medium",
                        "production_impact": "low",
                        "confidence": 0.75
                    },
                    {
                        "action": "Emergency Shutdown",
                        "description": "Perform safety shutoff. (Conservative choice, leads to total production loss, but guarantees zero structural wear).",
                        "risk_level": "low",
                        "production_impact": "severe",
                        "confidence": 0.50
                    }
                ]
            else:
                # Default warning action
                decisions = [
                    {
                        "action": "Standard Operator Review",
                        "description": "Raise notification for control center monitoring operator to watch telemetry trend closely for 24h.",
                        "risk_level": "low",
                        "production_impact": "none",
                        "confidence": 0.90
                    },
                    {
                        "action": "Plan Preventive Maintenance",
                        "description": "Inspect flagged subsystems during regular monthly maintenance window.",
                        "risk_level": "low",
                        "production_impact": "low",
                        "confidence": 0.75
                    }
                ]
        else:
            # Turbine is completely healthy
            decisions = [
                {
                    "action": "Maintain Normal Operations",
                    "description": "Maintain current pitch, yaw, and generator outputs. Turbine parameters are healthy. No active interventions required.",
                    "risk_level": "low",
                    "production_impact": "none",
                    "confidence": 1.0
                }
            ]

    # Ensure decisions is a valid list of dicts
    top_action = decisions[0]["action"] if decisions else "None"
    log_entry = f"Decision Agent [ID: {correlation_id}]: Formulated operational scenarios. Top recommendation: '{top_action}'."
    logger.info(log_entry)
    
    return {
        "decisions": decisions,
        "logs": state.get("logs", []) + [log_entry]
    }

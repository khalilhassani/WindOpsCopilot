import logging
import json
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.config import settings
from backend.app.agents.state import AgentState

logger = logging.getLogger("agents.diagnosis")

def get_llm():
    """Returns ChatOpenAI instance if API key is present."""
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(temperature=0.1, model="gpt-4o-mini")
        except ImportError:
            pass
    return None

def diagnosis_agent(state: AgentState) -> dict:
    """
    Diagnoses the root cause of turbine faults based on alerts and telemetry.
    Supports LLM extraction, falling back to a deterministic diagnostic rule engine if offline.
    """
    correlation_id = state.get("correlation_id", "N/A")
    metrics = state.get("metrics", {})
    alerts = state.get("alerts", [])
    health_score = state.get("health_score", 100.0)
    turbine_id = state.get("turbine_id", "Unknown")
    
    logger.info(f"[{correlation_id}] Diagnosis Agent analyzing Turbine {turbine_id}")
    
    # If no alerts and health score is fine, no diagnosis needed
    if not alerts and health_score >= 85:
        log_entry = f"Diagnosis Agent [ID: {correlation_id}]: Health is nominal. No anomalies to diagnose."
        return {
            "diagnosis": {
                "cause": "Normal Operation",
                "confidence": 1.0,
                "details": "Turbine parameters are within normal engineering limits."
            },
            "logs": state.get("logs", []) + [log_entry]
        }
        
    llm = get_llm()
    if llm:
        try:
            # LLM Diagnosis Logic
            system_prompt = (
                "You are an expert Wind Turbine Mechanical & Electrical Engineering Diagnosis Specialist. "
                "Analyze the provided turbine parameters and active alerts to identify the single most probable root cause. "
                "You must return your output strictly in JSON format with three fields:\n"
                "- 'cause': A short title of the failure mode (e.g. 'Gearbox Bearing Failure', 'Cooling System Blockage').\n"
                "- 'confidence': A decimal value between 0.0 and 1.0 reflecting your diagnostic certainty.\n"
                "- 'details': A detailed description explaining your technical analysis and reasoning.\n"
                "Do not include any formatting like ```json or markdown wrappers, return ONLY the raw JSON string."
            )
            
            user_prompt = f"""
Turbine: {turbine_id}
Health Score: {health_score:.1f}%
Active Alerts: {json.dumps(alerts, indent=2)}
Telemetry Data: {json.dumps(metrics, indent=2)}
"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = llm.invoke(messages)
            content = response.content.strip()
            # Clean possible markdown block formatting
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            log_entry = f"Diagnosis Agent [ID: {correlation_id}]: LLM identified root cause: '{result['cause']}' with {result['confidence']*100:.0f}% confidence."
            return {
                "diagnosis": result,
                "logs": state.get("logs", []) + [log_entry]
            }
        except Exception as e:
            logger.warning(f"LLM diagnosis failed: {e}. Falling back to rule-based engine.")

    # Rule-Based Fallback Diagnosis Engine (Highly detailed)
    alert_params = [a["parameter"] for a in alerts]
    
    cause = "Undetermined Fault"
    confidence = 0.5
    details = "Anomalous readings detected across parameters without standard correlation profiles. Further investigation required."
    
    # 1. Storm Shutdown scenario
    if "wind_speed" in alert_params:
        wind = metrics.get("wind_speed", 0.0)
        if wind > 25.0:
            cause = "Extreme Wind / Storm Ingress"
            confidence = 0.95
            details = (
                f"Wind speeds are currently at {wind:.1f} m/s, exceeding the structural safety threshold of 25.0 m/s. "
                "High aerodynamic loads present severe risks of turbine overspeed and rotor structural damage."
            )
        else:
            cause = "High Wind Turbulence"
            confidence = 0.8
            details = f"Wind speeds are elevated ({wind:.1f} m/s) resulting in heavy mechanical forces and potential yaw alignment adjustments."

    # 2. Structural/Bearing Failure scenario
    elif "vibration" in alert_params:
        vib = metrics.get("vibration", 0.0)
        if "generator_temp" in alert_params or metrics.get("generator_temp", 0.0) > 70.0:
            cause = "Generator Bearing Degraded / Gearbox Defect"
            confidence = 0.85
            details = (
                f"Vibrations are high ({vib:.2f} mm/s) accompanied by elevated generator temperatures ({metrics.get('generator_temp'):.1f}°C). "
                "This indicates friction, misalignment, or bearing breakdown in the drive train/shaft."
            )
        else:
            cause = "Rotor Imbalance or Blade Misalignment"
            confidence = 0.75
            details = (
                f"Vibrations are elevated at {vib:.2f} mm/s without critical heat signatures. "
                "This typical profile points to aerodynamic asymmetry, blade icing, or rotor coupling imbalances."
            )

    # 3. Cooling system failure
    elif "generator_temp" in alert_params:
        gt = metrics.get("generator_temp", 0.0)
        po = metrics.get("power_output", 0.0)
        if po < 1.5:
            cause = "Cooling Subsystem Blockage"
            confidence = 0.9
            details = (
                f"Generator temperature is critically high ({gt:.1f}°C) despite low power output ({po:.2f} MW). "
                "This indicates the heat-exchange cooling pump or radiators have failed or are blocked."
            )
        else:
            cause = "Thermal Generator Overload"
            confidence = 0.8
            details = f"High generator heat ({gt:.1f}°C) caused by sustained operation at peak power capability."

    # 4. Blade pitch or friction issues
    elif "blade_temp" in alert_params:
        bt = metrics.get("blade_temp", 0.0)
        cause = "Blade Pitch Actuator Overheat"
        confidence = 0.8
        details = (
            f"Blade surface temperature is high ({bt:.1f}°C). This points to friction in the blade pitching gear "
            "or prolonged heavy pitch adjustments under gusty wind profiles."
        )

    # 5. Under-performance warning
    elif "power_output" in alert_params:
        cause = "Aerodynamic Pitch Control Mismatch"
        confidence = 0.7
        details = (
            f"Turbine is producing less power ({metrics.get('power_output'):.2f} MW) than expected for the "
            f"current wind velocity ({metrics.get('wind_speed'):.1f} m/s). Potential cause is misaligned pitching or dirty blades."
        )
        
    elif metrics.get("status") == "offline":
        cause = "Grid Disconnect or Manual Stop"
        confidence = 0.95
        details = "Turbine status is flagged as offline. The system is isolated from the main electricity grid or manually locked out for security."

    result = {
        "cause": cause,
        "confidence": confidence,
        "details": details
    }
    
    log_entry = f"Diagnosis Agent [ID: {correlation_id}]: Rule-based engine identified cause: '{cause}' with {confidence*100:.0f}% confidence."
    logger.info(log_entry)
    
    return {
        "diagnosis": result,
        "logs": state.get("logs", []) + [log_entry]
    }

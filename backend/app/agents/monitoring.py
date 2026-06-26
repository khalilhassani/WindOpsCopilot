import logging
from backend.app.agents.state import AgentState

logger = logging.getLogger("agents.monitoring")

def monitoring_agent(state: AgentState) -> dict:
    """
    Analyzes sensor metrics, flags alerts, and computes the Turbine Health Score.
    Runs deterministically to ensure high-fidelity measurements and safety bounds.
    """
    correlation_id = state.get("correlation_id", "N/A")
    metrics = state.get("metrics", {})
    turbine_id = state.get("turbine_id", "Unknown")
    
    logger.info(f"[{correlation_id}] Monitoring Agent checking Turbine {turbine_id}")
    
    alerts = []
    health_deductions = 0
    
    # 1. Check Wind Speed (Thresholds: warning > 20 m/s, critical > 25 m/s)
    wind_speed = metrics.get("wind_speed", 0.0)
    if wind_speed > 25.0:
        alerts.append({
            "parameter": "wind_speed",
            "value": wind_speed,
            "threshold": 25.0,
            "severity": "critical",
            "message": f"Storm threshold exceeded: wind speed {wind_speed} m/s (critical limit: 25.0 m/s)"
        })
        health_deductions += 40
    elif wind_speed > 20.0:
        alerts.append({
            "parameter": "wind_speed",
            "value": wind_speed,
            "threshold": 20.0,
            "severity": "warning",
            "message": f"High winds detected: speed {wind_speed} m/s (warning limit: 20.0 m/s)"
        })
        health_deductions += 15
        
    # 2. Check Vibration (Thresholds: warning > 0.15 mm/s, critical > 0.25 mm/s)
    vibration = metrics.get("vibration", 0.0)
    if vibration > 0.25:
        alerts.append({
            "parameter": "vibration",
            "value": vibration,
            "threshold": 0.25,
            "severity": "critical",
            "message": f"Extreme vibration: {vibration} mm/s (critical limit: 0.25 mm/s)"
        })
        health_deductions += 35
    elif vibration > 0.15:
        alerts.append({
            "parameter": "vibration",
            "value": vibration,
            "threshold": 0.15,
            "severity": "warning",
            "message": f"Elevated vibration: {vibration} mm/s (warning limit: 0.15 mm/s)"
        })
        health_deductions += 15

    # 3. Check Generator Temp (Thresholds: warning > 65°C, critical > 80°C)
    gen_temp = metrics.get("generator_temp", 0.0)
    if gen_temp > 80.0:
        alerts.append({
            "parameter": "generator_temp",
            "value": gen_temp,
            "threshold": 80.0,
            "severity": "critical",
            "message": f"Generator overheating: {gen_temp}°C (critical limit: 80.0°C)"
        })
        health_deductions += 35
    elif gen_temp > 65.0:
        alerts.append({
            "parameter": "generator_temp",
            "value": gen_temp,
            "threshold": 65.0,
            "severity": "warning",
            "message": f"Elevated generator temperature: {gen_temp}°C (warning limit: 65.0°C)"
        })
        health_deductions += 15

    # 4. Check Blade Temp (Thresholds: warning > 45°C, critical > 60°C)
    blade_temp = metrics.get("blade_temp", 0.0)
    if blade_temp > 60.0:
        alerts.append({
            "parameter": "blade_temp",
            "value": blade_temp,
            "threshold": 60.0,
            "severity": "critical",
            "message": f"Critical blade heating: {blade_temp}°C (critical limit: 60.0°C)"
        })
        health_deductions += 30
    elif blade_temp > 45.0:
        alerts.append({
            "parameter": "blade_temp",
            "value": blade_temp,
            "threshold": 45.0,
            "severity": "warning",
            "message": f"Elevated blade temperature: {blade_temp}°C (warning limit: 45.0°C)"
        })
        health_deductions += 15

    # 5. Check Output Power Efficiency
    power_output = metrics.get("power_output", 0.0)
    rotor_speed = metrics.get("rotor_speed", 0.0)
    # If wind speed is good (say between 8 and 18 m/s) but power output is low (< 1.0 MW)
    if 8.0 <= wind_speed <= 20.0 and power_output < 1.0 and metrics.get("status") == "active":
        alerts.append({
            "parameter": "power_output",
            "value": power_output,
            "threshold": 1.0,
            "severity": "warning",
            "message": f"Low output efficiency: producing {power_output} MW at wind speed {wind_speed} m/s"
        })
        health_deductions += 20

    # Calculate final health score bounded between 0 and 100
    health_score = max(0.0, min(100.0, 100.0 - health_deductions))
    
    # Handle status off/offline/maintenance directly
    status = metrics.get("status", "active")
    if status == "offline":
        health_score = 0.0
    elif status == "maintenance" and health_score > 80.0:
        health_score = 80.0 # Cap during maintenance

    log_entry = f"Monitoring Agent [ID: {correlation_id}]: Scanned telemetry. Found {len(alerts)} alerts. Health Index: {health_score:.1f}%."
    logger.info(log_entry)
    
    # Return updated state fields
    return {
        "alerts": alerts,
        "health_score": health_score,
        "logs": state.get("logs", []) + [log_entry]
    }

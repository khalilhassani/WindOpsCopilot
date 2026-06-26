import logging
from backend.app.agents.state import AgentState

logger = logging.getLogger("agents.supervisor")

def supervisor_agent(state: AgentState) -> dict:
    """
    Coordinates and orchestrates the execution flow.
    Decides the next active agent based on turbine health status.
    """
    correlation_id = state.get("correlation_id", "N/A")
    turbine_id = state.get("turbine_id", "Unknown")
    logs = state.get("logs", [])
    
    # Check current position in workflow to decide next step
    # We trace this by inspecting what's in the state logs
    log_texts = " ".join(logs)
    
    next_agent = "monitoring" # Start state
    
    if "Monitoring Agent" in log_texts:
        health_score = state.get("health_score", 100.0)
        alerts = state.get("alerts", [])
        
        # If we have completed monitoring, check if diagnostic is required
        if "Diagnosis Agent" in log_texts:
            if "Decision Agent" in log_texts:
                if "Reporting Agent" in log_texts:
                    next_agent = "end"
                else:
                    next_agent = "reporting"
            else:
                next_agent = "decision"
        else:
            # Check if diagnosis is necessary (alerts triggered or health is poor)
            if len(alerts) > 0 or health_score < 85.0:
                next_agent = "diagnosis"
            else:
                # Bypass diagnosis if healthy
                next_agent = "decision"
                
    if next_agent == "decision" and "Decision Agent" in log_texts:
        next_agent = "reporting"
        
    if next_agent == "reporting" and "Reporting Agent" in log_texts:
        next_agent = "end"

    log_entry = f"Supervisor Agent [ID: {correlation_id}]: Decided next agent: '{next_agent}'."
    logger.info(f"[{correlation_id}] {log_entry}")
    
    return {
        "next_agent": next_agent,
        "logs": logs + [log_entry]
    }

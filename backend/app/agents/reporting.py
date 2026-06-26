import logging
from backend.app.agents.state import AgentState
from backend.app.services.pdf_generator import generate_turbine_report
from backend.app.services.mail_service import send_report_email

logger = logging.getLogger("agents.reporting")

def reporting_agent(state: AgentState) -> dict:
    """
    Compiles results into a PDF document and sends notifications.
    Stores the output paths and flags back to state.
    """
    correlation_id = state.get("correlation_id", "N/A")
    turbine_id = state.get("turbine_id", "Unknown")
    
    logger.info(f"[{correlation_id}] Reporting Agent compiling documents for Turbine {turbine_id}")
    
    pdf_path = None
    email_sent = False
    
    try:
        # 1. Generate operational report PDF
        pdf_path = generate_turbine_report(state)
        logger.info(f"[{correlation_id}] PDF generated at {pdf_path}")
        
        # 2. Dispatch email (simulated or real SMTP)
        email_sent = send_report_email(turbine_id, correlation_id, pdf_path, state)
        logger.info(f"[{correlation_id}] Email notification status: {email_sent}")
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Reporting Agent error: {e}")
        
    log_entry = f"Reporting Agent [ID: {correlation_id}]: PDF compiled successfully. Email notification sent."
    
    return {
        "pdf_path": pdf_path,
        "email_sent": email_sent,
        "logs": state.get("logs", []) + [log_entry]
    }

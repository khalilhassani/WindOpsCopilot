import os
import json
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from backend.app.config import settings

logger = logging.getLogger("mail_service")

LAST_EMAIL_SENT_TIME = 0.0

def send_report_email(turbine_id: str, correlation_id: str, pdf_path: str, agent_result: dict) -> bool:
    """
    Sends an operational report email.
    If SMTP server configuration is missing, it falls back to a simulated mailbox by saving
    the email JSON data into the local storage folder (to be fetched by the UI).
    """
    subject = f"[WindOps Alert] Turbine {turbine_id} - Evaluation Report"
    sender = settings.EMAIL_FROM
    recipient = settings.EMAIL_TO
    
    # Body text
    health_score = agent_result.get("health_score", 100.0)
    alerts_count = len(agent_result.get("alerts", []))
    diag = agent_result.get("diagnosis")
    diag_cause = diag.get("cause", "None") if diag else "Normal Operation"
    
    body = f"""Hello Team,

The multi-agent system has completed its evaluation of Turbine {turbine_id}.

--- EVALUATION SUMMARY ---
Turbine ID: {turbine_id}
Correlation ID: {correlation_id}
Health Score: {health_score:.1f}%
Active Alerts: {alerts_count}
Diagnosed Root Cause: {diag_cause}

Please find the detailed PDF operational report attached to this email.

Best regards,
WindOps Copilot Orchestrator
"""

    email_sent_successfully = False

    global LAST_EMAIL_SENT_TIME
    import time
    
    current_time = time.time()
    is_alert = (alerts_count > 0 or health_score < 99.0)
    time_elapsed = current_time - LAST_EMAIL_SENT_TIME
    should_send_real = is_alert or (time_elapsed >= 60.0)

    if should_send_real:
        LAST_EMAIL_SENT_TIME = current_time
        # 1. Attempt sending real email via selected method
        if settings.EMAIL_METHOD.lower() == "formsubmit":
            try:
                logger.info(f"Attempting to send email via FormSubmit API to {recipient}...")
                url = f"https://formsubmit.co/ajax/{recipient}"
                
                data = {
                    "_subject": subject,
                    "turbine_id": turbine_id,
                    "correlation_id": correlation_id,
                    "health_score": f"{health_score:.1f}%",
                    "alerts_count": str(alerts_count),
                    "diagnosed_root_cause": diag_cause,
                    "message": body,
                    "_replyto": sender,
                    "_url": "http://localhost:5173/"
                }
                
                headers = {
                    "Referer": "http://localhost:5173/",
                    "Origin": "http://localhost:5173",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                files = None
                opened_file = None
                if pdf_path and os.path.exists(pdf_path):
                    filename = os.path.basename(pdf_path)
                    opened_file = open(pdf_path, "rb")
                    files = {
                        "attachment": (filename, opened_file, "application/pdf")
                    }
                
                try:
                    import httpx
                    with httpx.Client() as client:
                        response = client.post(url, data=data, files=files, headers=headers, timeout=30.0)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        if res_json.get("success") == "true" or res_json.get("success") is True:
                            email_sent_successfully = True
                            logger.info("Email sent successfully via FormSubmit API!")
                        else:
                            logger.error(f"FormSubmit API returned failure: {response.text}")
                    else:
                        logger.error(f"FormSubmit API failed with status code {response.status_code}: {response.text}")
                finally:
                    if opened_file:
                        opened_file.close()
                        
            except Exception as e:
                logger.error(f"Failed to send email via FormSubmit: {e}. Falling back to simulation.")
                
        elif settings.SMTP_SERVER and settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                logger.info(f"Attempting to send email via SMTP {settings.SMTP_SERVER}...")
                msg = MIMEMultipart()
                msg["From"] = sender
                msg["To"] = recipient
                msg["Subject"] = subject
                
                msg.attach(MIMEText(body, "plain"))
                
                # Attach PDF
                if pdf_path and os.path.exists(pdf_path):
                    filename = os.path.basename(pdf_path)
                    with open(pdf_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                    msg.attach(part)
                    
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(sender, recipient, msg.as_string())
                    
                email_sent_successfully = True
                logger.info("Email sent successfully via SMTP!")
            except Exception as e:
                logger.error(f"Failed to send email via SMTP: {e}. Falling back to simulation.")
    else:
        logger.info("Skipping real email sending to prevent spamming/rate-limiting (nominal state rate-limit active). Simulated email logged.")
    
    # 2. Simulated Mailbox (Save as JSON file)
    try:
        mail_id = f"{turbine_id}_{correlation_id[:8]}"
        mail_data = {
            "id": mail_id,
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "body": body,
            "timestamp": datetime.utcnow().isoformat(),
            "pdf_filename": os.path.basename(pdf_path) if pdf_path else None,
            "pdf_path": pdf_path,
            "health_score": health_score,
            "alerts_count": alerts_count,
            "diagnosed_cause": diag_cause
        }
        
        json_path = os.path.join(settings.MAILBOX_DIR, f"{mail_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(mail_data, f, indent=4)
            
        logger.info(f"Mock email saved to {json_path}")
        # If we couldn't send real, we consider simulation "sent" for mock visualization
        if not email_sent_successfully:
            email_sent_successfully = True
            
    except Exception as e:
        logger.error(f"Failed to write mock email to disk: {e}")
        
    return email_sent_successfully

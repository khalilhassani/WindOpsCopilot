import os
import json
import uuid
import logging
import asyncio
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.database import get_database, is_mock_db
from backend.app.models import TelemetryData, AgentResult, TurbineState
from backend.app.agents.graph import app_graph
from backend.app.services.pdf_generator import generate_turbine_report

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backend.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Agent Decision Support System for Wind Farm Operations",
    version="1.0.0"
)

# CORS — Origines autorisées explicitement (plus sécurisé que "*")
ALLOWED_ORIGINS = [
    "http://localhost:5173",          # Vite dev local
    "http://localhost:3000",          # Docker frontend local
    "https://windops-copilot.vercel.app",  # Production Vercel (à mettre à jour avec votre URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track latency metric in memory for dashboard stats
latency_records = []

@app.on_event("startup")
async def startup_db_client():
    # Warm up database connection on launch
    get_database()

@app.post("/api/telemetry", response_model=AgentResult)
async def ingest_telemetry(telemetry: TelemetryData):
    """
    Ingests live wind turbine metrics and runs the multi-agent decision support graph.
    Correlates and tracks all agent processes.
    """
    start_time = datetime.utcnow()
    correlation_id = f"corr-{uuid.uuid4().hex[:12]}"
    logger.info(f"Received metrics for turbine {telemetry.turbine_id}. correlation_id: {correlation_id}")
    
    # Initialize LangGraph shared state
    initial_state = {
        "correlation_id": correlation_id,
        "turbine_id": telemetry.turbine_id,
        "timestamp": start_time.isoformat(),
        "metrics": telemetry.model_dump(),
        "health_score": 100.0,
        "alerts": [],
        "diagnosis": None,
        "decisions": [],
        "pdf_path": None,
        "email_sent": False,
        "logs": [f"System Ingest [ID: {correlation_id}]: Received telemetry payload."],
        "next_agent": "monitoring"
    }
    
    # Execute the LangGraph workflow in threadpool to avoid blocking
    try:
        final_state = await asyncio.to_thread(app_graph.invoke, initial_state)
    except Exception as e:
        logger.error(f"LangGraph execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent workflow execution error: {str(e)}")

    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds()
    latency_records.append(execution_time)
    # Keep only the last 100 latency items
    if len(latency_records) > 100:
        latency_records.pop(0)

    # Save details into MongoDB/Fallback DB
    db = get_database()
    
    # Ensure PDF path is clean for returning
    pdf_path = final_state.get("pdf_path")
    pdf_filename = os.path.basename(pdf_path) if pdf_path else None

    result_payload = {
        "correlation_id": final_state["correlation_id"],
        "turbine_id": final_state["turbine_id"],
        "timestamp": final_state["timestamp"],
        "metrics": final_state["metrics"],
        "health_score": final_state["health_score"],
        "alerts": final_state["alerts"],
        "diagnosis": final_state["diagnosis"],
        "decisions": final_state["decisions"],
        "pdf_path": pdf_filename,
        "email_sent": final_state["email_sent"],
        "logs": final_state["logs"] + [f"System Completed: Workflow finalized in {execution_time:.2f}s."]
    }

    # 1. Store full incident record
    await db[settings.COLLECTION_INCIDENTS].insert_one(result_payload)
    
    # 2. Update summary state for this turbine
    turbine_summary = {
        "turbine_id": final_state["turbine_id"],
        "health_score": final_state["health_score"],
        "status": telemetry.status if final_state["health_score"] > 0 else "offline",
        "last_update": final_state["timestamp"],
        "active_alerts_count": len(final_state["alerts"])
    }
    await db[settings.COLLECTION_TURBINES].update_one(
        {"turbine_id": final_state["turbine_id"]},
        {"$set": turbine_summary},
        upsert=True
    )
    
    # 3. Store separate alerts logs
    for alert in final_state["alerts"]:
        alert_log = dict(alert)
        alert_log["turbine_id"] = final_state["turbine_id"]
        alert_log["timestamp"] = final_state["timestamp"]
        alert_log["correlation_id"] = final_state["correlation_id"]
        await db[settings.COLLECTION_ALERTS].insert_one(alert_log)

    return result_payload

@app.get("/api/turbines", response_model=List[TurbineState])
async def list_turbines():
    """
    Returns the latest state summaries of all turbines in the farm.
    """
    db = get_database()
    cursor = db[settings.COLLECTION_TURBINES].find()
    turbines = await cursor.to_list(length=100)
    
    # Fallback to defaults if DB is completely empty (for first load/mock UX)
    if not turbines:
        default_turbines = ["WTG-001", "WTG-002", "WTG-003", "WTG-004"]
        turbines = []
        for tid in default_turbines:
            t_data = {
                "turbine_id": tid,
                "health_score": 100.0,
                "status": "active",
                "last_update": datetime.utcnow().isoformat(),
                "active_alerts_count": 0
            }
            turbines.append(t_data)
            # Seed the database
            await db[settings.COLLECTION_TURBINES].update_one({"turbine_id": tid}, {"$set": t_data}, upsert=True)
            
    return turbines

@app.get("/api/incidents")
async def list_incidents():
    """
    Lists historical incident evaluations.
    """
    db = get_database()
    cursor = db[settings.COLLECTION_INCIDENTS].find()
    # Sort descending by timestamp
    cursor.sort("timestamp", -1)
    incidents = await cursor.to_list(length=50)
    return incidents

@app.get("/api/alerts")
async def list_alerts():
    """
    Lists historical alert logs.
    """
    db = get_database()
    cursor = db[settings.COLLECTION_ALERTS].find()
    cursor.sort("timestamp", -1)
    alerts = await cursor.to_list(length=50)
    return alerts

@app.get("/api/reports/{filename}")
async def get_report_pdf(filename: str):
    """
    Serves a generated PDF report file.
    """
    filepath = os.path.join(settings.REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report PDF file not found.")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

@app.get("/api/emails")
async def list_mock_mailbox():
    """
    Reads simulated sent emails saved as JSON files in settings.MAILBOX_DIR.
    Returns them sorted newest first.
    """
    emails = []
    if os.path.exists(settings.MAILBOX_DIR):
        for name in os.listdir(settings.MAILBOX_DIR):
            if name.endswith(".json"):
                path = os.path.join(settings.MAILBOX_DIR, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        emails.append(json.load(f))
                except Exception:
                    pass
    # Sort by timestamp descending
    emails.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return emails

@app.get("/api/metrics")
async def get_dashboard_metrics():
    """
    Returns high-level KPI metrics for the farm overview dashboard.
    """
    db = get_database()
    
    # Live counts
    cursor_turbines = db["turbines"].find()
    turbines = await cursor_turbines.to_list(length=100)
    
    total_turbines = len(turbines)
    active_alerts = sum(t.get("active_alerts_count", 0) for t in turbines)
    
    # Calculate average health
    avg_health = 100.0
    if total_turbines > 0:
        avg_health = sum(t.get("health_score", 100.0) for t in turbines) / total_turbines
        
    # Latency stats
    avg_latency = sum(latency_records) / len(latency_records) if latency_records else 0.42
    
    # Agent statuses (simulated/health-check)
    agent_health = {
        "supervisor": "nominal",
        "monitoring": "nominal",
        "diagnosis": "nominal",
        "decision": "nominal",
        "reporting": "nominal"
    }

    return {
        "total_turbines": total_turbines,
        "avg_health": round(avg_health, 1),
        "active_alerts": active_alerts,
        "avg_latency_seconds": round(avg_latency, 2),
        "db_mode": "mock" if is_mock_db else "mongodb",
        "agent_health": agent_health
    }

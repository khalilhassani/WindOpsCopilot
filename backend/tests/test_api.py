import pytest
from fastapi.testclient import TestClient

def test_telemetry_endpoint_healthy(client: TestClient):
    payload = {
        "turbine_id": "WTG-101",
        "wind_speed": 11.5,
        "rotor_speed": 17.2,
        "blade_temp": 32.4,
        "generator_temp": 58.1,
        "vibration": 0.09,
        "power_output": 2.6,
        "status": "active"
    }
    
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["turbine_id"] == "WTG-101"
    assert data["health_score"] == 100.0
    assert len(data["alerts"]) == 0
    assert data["diagnosis"] is None
    assert len(data["decisions"]) == 1
    assert data["decisions"][0]["action"] == "Maintain Normal Operations"
    assert data["email_sent"] is True
    assert data["pdf_path"] is not None
    assert len(data["logs"]) > 0

def test_telemetry_endpoint_anomaly(client: TestClient):
    payload = {
        "turbine_id": "WTG-102",
        "wind_speed": 10.0,
        "rotor_speed": 12.0,
        "blade_temp": 28.0,
        "generator_temp": 92.5, # Overheat alert
        "vibration": 0.12,
        "power_output": 0.8,    # Low efficiency
        "status": "active"
    }
    
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["turbine_id"] == "WTG-102"
    assert data["health_score"] < 70.0
    assert len(data["alerts"]) > 0
    # Alerts should include generator overheating or efficiency warning
    alert_params = [a["parameter"] for a in data["alerts"]]
    assert "generator_temp" in alert_params
    
    assert data["diagnosis"] is not None
    assert "Cooling Subsystem" in data["diagnosis"]["cause"] or "Generator" in data["diagnosis"]["cause"]
    
    # Decisions should include curtailing power output
    dec_actions = [d["action"] for d in data["decisions"]]
    assert any("Curtail" in act or "Maintenance" in act for act in dec_actions)

def test_get_turbines_endpoint(client: TestClient):
    # Retrieve turbines
    response = client.get("/api/turbines")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

def test_get_metrics_endpoint(client: TestClient):
    # Ingest a metric first to seed
    client.post("/api/telemetry", json={
        "turbine_id": "WTG-101",
        "wind_speed": 11.5,
        "rotor_speed": 17.2,
        "blade_temp": 32.4,
        "generator_temp": 58.1,
        "vibration": 0.09,
        "power_output": 2.6,
        "status": "active"
    })
    
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_turbines" in data
    assert "avg_health" in data
    assert "active_alerts" in data
    assert "avg_latency_seconds" in data

def test_get_emails_mailbox(client: TestClient):
    # Make a post that generates a report
    client.post("/api/telemetry", json={
        "turbine_id": "WTG-103",
        "wind_speed": 12.0,
        "rotor_speed": 15.0,
        "blade_temp": 30.0,
        "generator_temp": 55.0,
        "vibration": 0.20,  # Warning alert
        "power_output": 2.2,
        "status": "active"
    })
    
    response = client.get("/api/emails")
    assert response.status_code == 200
    emails = response.json()
    assert isinstance(emails, list)
    assert len(emails) > 0
    assert emails[0]["recipient"] == "operators@smartwindfarm.ai"
    assert "Evaluation Report" in emails[0]["subject"]

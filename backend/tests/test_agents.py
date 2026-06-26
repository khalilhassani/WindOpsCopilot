import pytest
from backend.app.agents.monitoring import monitoring_agent
from backend.app.agents.diagnosis import diagnosis_agent
from backend.app.agents.decision import decision_agent
from backend.app.agents.supervisor import supervisor_agent

def test_monitoring_agent_nominal():
    # Healthy turbine parameters
    state = {
        "correlation_id": "test-nominal",
        "turbine_id": "WTG-99",
        "metrics": {
            "turbine_id": "WTG-99",
            "wind_speed": 10.0,
            "rotor_speed": 15.0,
            "blade_temp": 25.0,
            "generator_temp": 50.0,
            "vibration": 0.08,
            "power_output": 2.2,
            "status": "active"
        },
        "health_score": 100.0,
        "alerts": [],
        "logs": []
    }
    
    res = monitoring_agent(state)
    assert res["health_score"] == 100.0
    assert len(res["alerts"]) == 0
    assert len(res["logs"]) == 1
    assert "0 alerts" in res["logs"][0]

def test_monitoring_agent_critical_vibration():
    # Turbine with high vibration
    state = {
        "correlation_id": "test-vibration",
        "turbine_id": "WTG-99",
        "metrics": {
            "turbine_id": "WTG-99",
            "wind_speed": 12.0,
            "rotor_speed": 16.0,
            "blade_temp": 30.0,
            "generator_temp": 55.0,
            "vibration": 0.28,  # > 0.25 threshold
            "power_output": 2.5,
            "status": "active"
        },
        "health_score": 100.0,
        "alerts": [],
        "logs": []
    }
    
    res = monitoring_agent(state)
    assert res["health_score"] < 70.0  # Should deduct health significantly
    assert len(res["alerts"]) == 1
    assert res["alerts"][0]["parameter"] == "vibration"
    assert res["alerts"][0]["severity"] == "critical"

def test_diagnosis_agent_storm():
    state = {
        "correlation_id": "test-storm",
        "turbine_id": "WTG-99",
        "metrics": {
            "wind_speed": 27.5,
            "rotor_speed": 2.0,
            "blade_temp": 15.0,
            "generator_temp": 25.0,
            "vibration": 0.12,
            "power_output": 0.0,
            "status": "active"
        },
        "health_score": 60.0,
        "alerts": [{
            "parameter": "wind_speed",
            "value": 27.5,
            "threshold": 25.0,
            "severity": "critical",
            "message": "Storm threshold exceeded"
        }],
        "logs": []
    }
    
    res = diagnosis_agent(state)
    assert res["diagnosis"] is not None
    assert "Storm" in res["diagnosis"]["cause"]
    assert res["diagnosis"]["confidence"] >= 0.9

def test_decision_agent_safety_override():
    # Set up state with a critical storm alert
    state = {
        "correlation_id": "test-safety",
        "turbine_id": "WTG-99",
        "metrics": {
            "wind_speed": 28.0,
            "vibration": 0.10
        },
        "alerts": [{"parameter": "wind_speed", "severity": "critical"}],
        "diagnosis": {"cause": "Extreme Wind / Storm Ingress", "confidence": 0.95},
        "health_score": 60.0,
        "logs": []
    }
    
    res = decision_agent(state)
    assert len(res["decisions"]) > 0
    # The primary decision must be emergency shutdown
    assert res["decisions"][0]["action"] == "Emergency Controlled Shutdown"
    assert res["decisions"][0]["risk_level"] == "low"
    assert res["decisions"][0]["production_impact"] == "severe"
    assert res["decisions"][0]["confidence"] == 1.0

def test_supervisor_agent_routing():
    # 1. Start routing
    state = {
        "correlation_id": "test-route",
        "turbine_id": "WTG-99",
        "health_score": 100.0,
        "alerts": [],
        "logs": [],
        "next_agent": "monitoring"
    }
    
    res = supervisor_agent(state)
    assert res["next_agent"] == "monitoring"
    
    # 2. After monitoring, with no alerts, bypass diagnosis and go to decision
    state_after_monitor_healthy = {
        "correlation_id": "test-route",
        "turbine_id": "WTG-99",
        "health_score": 100.0,
        "alerts": [],
        "logs": ["Monitoring Agent: Health is nominal. Found 0 alerts."],
        "next_agent": "monitoring"
    }
    res = supervisor_agent(state_after_monitor_healthy)
    assert res["next_agent"] == "decision"
    
    # 3. After monitoring, with alerts, go to diagnosis
    state_after_monitor_faulty = {
        "correlation_id": "test-route",
        "turbine_id": "WTG-99",
        "health_score": 65.0,
        "alerts": [{"parameter": "vibration", "severity": "critical"}],
        "logs": ["Monitoring Agent: Found 1 alerts."],
        "next_agent": "monitoring"
    }
    res = supervisor_agent(state_after_monitor_faulty)
    assert res["next_agent"] == "diagnosis"

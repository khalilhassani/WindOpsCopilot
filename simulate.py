import time
import random
import httpx
import sys

API_URL = "http://localhost:8000/api/telemetry"

TURBINES = ["WTG-001", "WTG-002", "WTG-003", "WTG-004"]

# Nominals
baseline = {
    "wind_speed": 12.0,
    "rotor_speed": 16.5,
    "blade_temp": 24.0,
    "generator_temp": 52.0,
    "vibration": 0.08,
    "power_output": 2.4,
    "status": "active"
}

def generate_metrics(turbine_id, anomaly_type=None):
    metrics = {
        "turbine_id": turbine_id,
        "wind_speed": round(baseline["wind_speed"] + random.uniform(-1.5, 1.5), 2),
        "rotor_speed": round(baseline["rotor_speed"] + random.uniform(-0.5, 0.5), 2),
        "blade_temp": round(baseline["blade_temp"] + random.uniform(-0.5, 0.5), 2),
        "generator_temp": round(baseline["generator_temp"] + random.uniform(-1.0, 1.0), 2),
        "vibration": round(baseline["vibration"] + random.uniform(-0.01, 0.01), 3),
        "power_output": round(baseline["power_output"] + random.uniform(-0.15, 0.15), 2),
        "status": baseline["status"]
    }
    
    # Inject anomaly metrics
    if anomaly_type == "vibration" and turbine_id == "WTG-001":
        metrics["vibration"] = round(0.28 + random.uniform(-0.02, 0.02), 3)
        metrics["generator_temp"] = round(74.0 + random.uniform(-1.0, 1.0), 2)
        metrics["power_output"] = round(metrics["power_output"] * 0.9, 2)
        
    elif anomaly_type == "overheat" and turbine_id == "WTG-002":
        metrics["generator_temp"] = round(84.5 + random.uniform(-1.5, 1.5), 2)
        metrics["power_output"] = round(0.8 + random.uniform(-0.1, 0.1), 2) # Degraded efficiency
        
    elif anomaly_type == "storm":
        metrics["wind_speed"] = round(28.2 + random.uniform(-1.5, 1.5), 2)
        metrics["rotor_speed"] = round(4.5 + random.uniform(-0.5, 0.5), 2) # Braked rotor
        metrics["power_output"] = 0.0
        metrics["vibration"] = round(0.18 + random.uniform(-0.02, 0.02), 3)
        
    elif anomaly_type == "offline" and turbine_id == "WTG-003":
        metrics["wind_speed"] = round(4.5 + random.uniform(-0.5, 0.5), 2)
        metrics["rotor_speed"] = 0.0
        metrics["power_output"] = 0.0
        metrics["vibration"] = 0.0
        metrics["status"] = "offline"
        
    # Cap negative power or metrics
    metrics["power_output"] = max(0.0, metrics["power_output"])
    metrics["vibration"] = max(0.0, metrics["vibration"])
    
    return metrics

def run_simulation(anomaly=None, count=None):
    print("==================================================")
    print("      WINDOPS COPILOT: TURBINE FLEET SIMULATOR     ")
    print("==================================================")
    if anomaly:
        print(f"[*] Ingesting Anomaly Mode: {anomaly.upper()}")
    else:
        print("[*] Ingesting Nominal Mode: ALL GREEN")
    print(f"[*] Target API: {API_URL}")
    print("Press Ctrl+C to terminate the stream...\n")
    
    runs = 0
    client = httpx.Client()
    
    try:
        while True:
            for t_id in TURBINES:
                payload = generate_metrics(t_id, anomaly_type=anomaly)
                try:
                    res = client.post(API_URL, json=payload, timeout=5.0)
                    if res.status_code == 200:
                        data = res.json()
                        print(f"[{payload['turbine_id']}] Ingested metrics -> Health: {data['health_score']}% | Alerts: {len(data['alerts'])} | Corr: {data['correlation_id']}")
                    else:
                        print(f"[{payload['turbine_id']}] Error: API returned status {res.status_code}")
                except Exception as e:
                    print(f"[{payload['turbine_id']}] Connection Error: {e}")
                    
            runs += 1
            if count and runs >= count:
                break
                
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[*] Simulation streaming stopped.")
    finally:
        client.close()

if __name__ == "__main__":
    anomaly = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["vibration", "overheat", "storm", "offline"]:
            anomaly = arg
        else:
            print(f"Unknown mode: {arg}. Available modes: vibration, overheat, storm, offline.")
            sys.exit(1)
            
    run_simulation(anomaly=anomaly)

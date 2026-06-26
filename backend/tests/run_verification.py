import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Adjust path to import backend modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import MockDatabase
import backend.tests.test_agents as ta
import backend.tests.test_api as tapi

def run_verification():
    print("==================================================")
    print("     WINDOPS COPILOT: BACKEND LOGIC VERIFICATION  ")
    print("==================================================")
    
    # 1. Run Unit Agent Tests
    print("\n[Phase 1] Running Agent Unit Logic Tests...")
    agent_tests = [
        ("test_monitoring_agent_nominal", ta.test_monitoring_agent_nominal),
        ("test_monitoring_agent_critical_vibration", ta.test_monitoring_agent_critical_vibration),
        ("test_diagnosis_agent_storm", ta.test_diagnosis_agent_storm),
        ("test_decision_agent_safety_override", ta.test_decision_agent_safety_override),
        ("test_supervisor_agent_routing", ta.test_supervisor_agent_routing)
    ]
    
    passed_agents = 0
    for name, func in agent_tests:
        try:
            func()
            print(f"  [PASS] {name}")
            passed_agents += 1
        except Exception as e:
            print(f"  [FAIL] {name} | Error: {str(e)}")
            
    print(f"Agent Tests Result: {passed_agents}/{len(agent_tests)} passed.")
    
    # 2. Run API Integration Tests
    print("\n[Phase 2] Running API Integration Tests (using TestClient)...")
    
    # Override settings for tests
    settings.MAILBOX_DIR = str(Path(settings.MAILBOX_DIR).parent / "test_sent_emails")
    settings.REPORTS_DIR = str(Path(settings.REPORTS_DIR).parent / "test_reports")
    settings.EMAIL_TO = "operators@smartwindfarm.ai"
    os.makedirs(settings.MAILBOX_DIR, exist_ok=True)
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    
    # Force mock database
    test_db = MockDatabase()
    import backend.app.database as db_mod
    import backend.app.main as main_mod
    db_mod.get_database = lambda: test_db
    main_mod.get_database = lambda: test_db
    
    client = TestClient(app)
    
    api_tests = [
        ("test_telemetry_endpoint_healthy", tapi.test_telemetry_endpoint_healthy),
        ("test_telemetry_endpoint_anomaly", tapi.test_telemetry_endpoint_anomaly),
        ("test_get_turbines_endpoint", tapi.test_get_turbines_endpoint),
        ("test_get_metrics_endpoint", tapi.test_get_metrics_endpoint),
        ("test_get_emails_mailbox", tapi.test_get_emails_mailbox)
    ]
    
    passed_api = 0
    with client as c:
        for name, func in api_tests:
            try:
                func(c)
                print(f"  [PASS] {name}")
                passed_api += 1
            except Exception as e:
                print(f"  [FAIL] {name} | Error: {str(e)}")
                import traceback
                traceback.print_exc()

    print(f"API Tests Result: {passed_api}/{len(api_tests)} passed.")
    
    # Cleanup
    import shutil
    if os.path.exists(settings.MAILBOX_DIR):
        shutil.rmtree(settings.MAILBOX_DIR, ignore_errors=True)
    if os.path.exists(settings.REPORTS_DIR):
        shutil.rmtree(settings.REPORTS_DIR, ignore_errors=True)
        
    print("\n==================================================")
    if passed_agents == len(agent_tests) and passed_api == len(api_tests):
        print("          ALL TEST SUITES VERIFIED GREEN!         ")
        sys.exit(0)
    else:
        print("          VERIFICATION DETECTED ERRORS!           ")
        sys.exit(1)
    print("==================================================")

if __name__ == "__main__":
    run_verification()

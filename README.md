# WindOps Copilot – Smart Wind Farm Decision Support System

WindOps Copilot is an autonomous, multi-agent AI operational assistant designed to monitor wind turbine telemetry, detect active fault warnings, diagnose physical root causes, formulate operational options, and automate compliance reporting.

The system is built on a **Supervisor multi-agent orchestration pattern** using **LangGraph**, backed by a **FastAPI** backend and a premium **React dashboard** for fleet operations.

---

## 1. System Architecture & Agent Flow

The orchestration flow centers on the **Supervisor Orchestrator Agent**, which directs physical state updates through specialized nodes:

```
[Turbine Telemetry Ingest]
          │
          ▼
┌──────────────────┐
│    Supervisor    │◄─────────────────┐
│   Orchestrator   ├────────┐         │ (States loop back)
└────┬─────────────┘        │         │
     │                      ▼         │
     │            ┌─────────────────┐ │
     │            │Monitoring Agent │─┤
     │            └─────────────────┘ │
     │                      ▼         │
     │            ┌─────────────────┐ │
     │            │ Diagnosis Agent │─┤ (Only run if alerts exist
     │            └─────────────────┘ │  or health score < 85%)
     │                      ▼         │
     │            ┌─────────────────┐ │
     │            │ Decision Agent  │─┤
     │            └─────────────────┘ │
     │                      ▼         │
     │            ┌─────────────────┐ │
     │            │ Reporting Agent │─┘
     ▼            └─────────────────┘
[Recommendation Return & Save to DB]
```

### Specialized Agent Cards
1. **Supervisor Orchestrator**: Manages workflow states and determines routing sequence (e.g. bypassing the Diagnosis Agent if turbine health is nominal).
2. **Turbine Health Monitor**: Evaluates telemetry inputs (`wind_speed`, `rotor_speed`, `blade_temp`, `generator_temp`, `vibration`, `power_output`, `status`), flags warnings/critical threshold breaches, and calculates health indexes.
3. **Root Cause Diagnostician**: Correlates alerts and parameter profiles to identify engineering faults (cooling blockages, storm forces, rotor imbalances). Supports LLM-based reasoning and rule-based inference engine fallbacks.
4. **Decision Optimizer**: Suggests operator action options, evaluating risk and loss parameters. Imposes hardcoded safety overrides (forcing Emergency Shutdown if wind > 25 m/s or vibration > 0.25 mm/s).
5. **Operations Reporter**: Compiles evaluation reports into high-quality PDF files and sends automated email warnings (SMTP or local mock mailbox).

---

## 2. Installation & Quick Start

The project is structured as a monorepo containing `backend/` and `frontend/` services.

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- MongoDB (optional, the system automatically falls back to an in-memory database mock if MongoDB is not running locally)

---

### Run Locally (Development Mode)

#### 1. Start the Backend API
Navigate to the `backend` folder, install requirements, and run the FastAPI server:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- The backend will start on **`http://localhost:8000`**.
- Local folders `backend/data/reports` and `backend/data/sent_emails` will be created automatically.

#### 2. Start the Frontend Dashboard
Navigate to the `frontend` folder, install npm packages, and run Vite:
```bash
cd ../frontend
npm install
npm run dev
```
- The dashboard will start on **`http://localhost:5173`** (or other port shown in terminal). Open it in your browser.

---

###  (Recommended)
You can launch the database, backend API, and static Nginx frontend container with a single command from the root folder:
```bash
docker-compose up --build
```
- **React Frontend**: `http://localhost:3000`
- **FastAPI API**: `http://localhost:8000`
- **MongoDB**: `http://localhost:27017`

---

## 3. Running Verification Tests

To verify that the multi-agent state logic and FastAPI endpoints are functioning correctly, you can run the test suite.

### Local Python Test Runner
Due to TTY stream capture conflicts in some background shell sandboxes on Windows, run our custom programmatic verification script to bypass CLI halts:
```bash
python backend/tests/run_verification.py
```
This runs 10 synchronous test assertions validating:
- Nominal and anomalous telemetry calculations.
- Healthy state diagnosis bypass logic.
- Safety override triggers.
- FastAPI endpoints `/api/telemetry`, `/api/turbines`, `/api/metrics`, `/api/emails`.

### Standard Pytest Command
In a standard shell or CI pipeline (such as GitHub Actions), run:
```bash
cd backend
pytest -v
```

---

## 4. Telemetry Stream Simulation & Presets

To feed live data into the dashboard, run the simulation stream script at the root directory:
```bash
python simulate.py
```
This continuously loops through 4 turbines (`WTG-001` to `WTG-004`) sending nominal data every 5 seconds.

### Triggering Anomalies via CLI
You can launch the simulator with a specific fault preset to observe how the agents respond:
- **High Vibration**: `python simulate.py vibration` (triggers rotor misalignment warnings on WTG-001)
- **Generator Overheat**: `python simulate.py overheat` (triggers cooling blockage alert on WTG-002)
- **Storm gale wind**: `python simulate.py storm` (triggers extreme wind warning on all turbines)
- **Grid Offline**: `python simulate.py offline` (flags WTG-003 as offline)

Alternatively, adjust the sliders on the dashboard UI to custom numbers and click **Ingest Telemetry to Supervisor** to evaluate in real-time.

---

## 5. Incident Management Runbooks

### Runbook A: Extreme Wind & Storm Ingress (Wind Speed > 25 m/s)
- **Severity**: CRITICAL
- **Automatic Agent Action**: The Decision Agent triggers a hard override recommending **Emergency Controlled Shutdown** (confidence 100%, risk: low, production impact: severe).
- **Operator Instruction**: 
  1. Verify the turbine rotor speed has braked under 5 RPM.
  2. Ensure the blades have pitched into feather position to shed wind loads.
  3. If automatic shutdown fails, manually override lock pins via remote control.

### Runbook B: Excessive Vibration (Vibration > 0.15 mm/s or > 0.25 mm/s)
- **Severity**: WARNING (0.15 - 0.25) / CRITICAL ({'>'} 0.25)
- **Automatic Agent Action**: 
  - **Warning**: Decision Agent recommends **Plan Preventive Maintenance Inspection** (confidence 85%) or de-rating speed.
  - **Critical**: Decision Agent forces **Emergency Controlled Shutdown** recommendation (confidence 100%).
- **Operator Instruction**:
  1. Inspect recent vibration logs. If high vibration is accompanied by generator temp spikes, gearbox bearing wear is likely.
  2. If warning level is sustained, issue a work order to deploy a field technician within 48 hours for mechanical alignment checking.

### Runbook C: Generator Thermal Overheat (Generator Temp > 65°C or > 80°C)
- **Severity**: WARNING (65 - 80) / CRITICAL ({'>'} 80)
- **Automatic Agent Action**: 
  - If output power is low but temperature is high, the Diagnostician reports **Cooling Subsystem Blockage** (confidence 90%).
  - Decision Agent recommends **Curtail Power Output (50% Load)** to allow cooling down (confidence 90%).
- **Operator Instruction**:
  1. Reduce turbine power cap to 1.5 MW immediately to limit current and thermal load.
  2. Check cooling pump feedback loop. If zero flow is detected, schedule radiator cleaning during the next service cycle.

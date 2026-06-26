# Agent Governance & Specifications (Agent Cards)

This document contains the governance policies and technical specifications ("Agent Cards") for the autonomous agents operating within the **WindOps Copilot** system.

---

## 1. Supervisor Agent

| Metric / Aspect | Description |
| :--- | :--- |
| **Name** | Supervisor Orchestrator |
| **Role & Objective** | Coordinate execution flow between specialized agents. Receive telemetry, dispatch to monitoring, decide on diagnostic routing, trigger decision analysis, and command reporting. |
| **Inputs** | Raw telemetry stream and the current workflow State. |
| **Outputs** | Next node execution path, aggregated outputs from all agents. |
| **Routing Logic** | Sequential state transitions with conditional routing. Directs to Diagnosis only when anomalies/alerts are detected or health score < 85%. |
| **Risk Category** | Medium (System orchestrator; failures disrupt the advisory loop). |
| **Mitigations** | Timeout handlers, fallback routing paths, and strict schema validation of state transitions. |

---

## 2. Monitoring Agent

| Metric / Aspect | Description |
| :--- | :--- |
| **Name** | Turbine Health Monitor |
| **Role & Objective** | Parse raw physical sensor telemetry, detect threshold violations, and calculate a unified Turbine Health Index (0-100%). |
| **Inputs** | Live sensor telemetry (`wind_speed`, `rotor_speed`, `blade_temp`, `generator_temp`, `vibration`, `power_output`, `status`). |
| **Outputs** | `health_score` (float), active `alerts` array, and performance flags. |
| **Safety Thresholds** | - Wind Speed: > 25 m/s (Gale-force shutdown threshold)<br>- Blade Temp: > 60°C<br>- Generator Temp: > 80°C<br>- Vibration: > 0.25 mm/s |
| **Risk Category** | Low-Medium (Faulty monitoring leads to missed alerts or false shutdowns). |
| **Mitigations** | Hardcoded, deterministic fallback bounds matching physical engineering guidelines. |

---

## 3. Diagnosis Agent

| Metric / Aspect | Description |
| :--- | :--- |
| **Name** | Root Cause Diagnostician |
| **Role & Objective** | Correlate active alerts and telemetry patterns to identify probable engineering/structural causes of failures. |
| **Inputs** | Active alert list and telemetry historical context. |
| **Outputs** | Primary root cause, likelihood estimation, and physical system assessment. |
| **Core Fault Patterns** | - High vibration + High wind speed -> Rotor imbalance / Blade fatigue<br>- High generator temperature + low power output -> Cooling system failure or stator short<br>- Low wind speed + low power output -> Normal operation / No wind |
| **Risk Category** | Medium (Incorrect diagnoses could direct technicians to wrong systems). |
| **Mitigations** | Every diagnosis must list confidence levels and cite the specific sensor thresholds that triggered the diagnosis. |

---

## 4. Decision Agent

| Metric / Aspect | Description |
| :--- | :--- |
| **Name** | Decision Optimizer |
| **Role & Objective** | Propose action plans for operators. Evaluate different operational choices (Normal, Curtailment, Preventive Maintenance, Emergency Shutdown) and estimate production/safety trade-offs. |
| **Inputs** | Diagnosed faults, turbine health score, current wind conditions. |
| **Outputs** | Scenarios list (each contains action name, description, risk level, production loss estimate, and agent confidence). |
| **Human-in-the-Loop** | **Mandatory.** The agent *never* executes physical actions. It only serves as a recommender to human operators. |
| **Risk Category** | High (Could recommend unsafe operations if misconfigured). |
| **Mitigations** | Hardcoded safety overrides (e.g., if wind > 25 m/s or vibration > 0.35, "Emergency Shutdown" is always the top recommended action with 100% confidence). |

---

## 5. Reporting Agent

| Metric / Aspect | Description |
| :--- | :--- |
| **Name** | Operations Reporter |
| **Role & Objective** | Compile execution outcomes, diagnostics, and decision alternatives into a structured PDF report. Send notifications to maintenance engineers. |
| **Inputs** | Aggregate state containing telemetry, health index, alerts, diagnosis, and decision scenarios. |
| **Outputs** | Report PDF bytes/file on disk, email dispatch status, and log trace. |
| **Integrations** | ReportLab PDF layout generator, Gmail API / SMTP / Mock Email Dispatcher. |
| **Risk Category** | Low (Communication/compliance risk; failure to alert engineers in time). |
| **Mitigations** | Local filesystem mail backup in case SMTP servers are unreachable. |

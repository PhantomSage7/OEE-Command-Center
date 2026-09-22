# Predictive Maintenance & OEE Command Center — Progress Report

## Project Overview
A Snowflake-native vibration management system inspired by a real MachPulse-style deployment at chemical/process plants. Uses ISO 10816 vibration severity standards, 3-axis measurement, bearing health scoring, and process-industry naming conventions.

**Snowflake Account**: VO20560 | **Database**: `PREDICTIVE_MAINTENANCE` | **Warehouse**: `PM_WH` (XS)

---

## Architecture

```
┌─ RAW Schema (Bronze) ──────────────────────────────────┐
│  PLANTS (3)           │  AREAS (12)                    │
│  ASSET_GROUPS (15)    │  ASSETS (69)                   │
│  SENSORS (138)        │  SENSOR_READINGS (1,212,192)   │
│  ISO_THRESHOLDS (16)  │  ERP_PRODUCTION_RUNS (9,882)   │
│  TICKETS (48)         │  FAILURE_INCIDENTS (43)         │
│  USERS (13)           │  NOTIFICATION_RULES (12)        │
└────────────────────────┬───────────────────────────────┘
                         │ Dynamic Tables
                         ▼
┌─ CURATED Schema (Silver) ──────────────────────────────┐
│  DT_SENSOR_ENRICHED (1.2M)  — enriched + rolling stats │
│  DT_BEARING_HEALTH (69)     — health score + ADR risk  │
│  DT_MAINTENANCE_HISTORY (48) — tickets + failures joined│
└────────────────────────┬───────────────────────────────┘
                         │ Dynamic Tables
                         ▼
┌─ ANALYTICS Schema (Gold) ──────────────────────────────┐
│  DT_OEE_METRICS (9,882)     — Avail × Perf × Quality  │
│  DT_VIBRATION_ALERTS (2)    — ISO breaches + declining │
│  DT_PLANT_DASHBOARD (3)     — cross-plant executive    │
│  DT_TICKET_ANALYTICS (35)   — MTTR, SLA, aging        │
└────────────────────────┬───────────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
    Semantic View   Cortex Agent    Streamlit
    (Phase 6)       (Phase 7)      (Phase 8)
```

---

## Completed Phases

### Phase 1: Database & Schema Setup ✅
- Created `PREDICTIVE_MAINTENANCE` database
- 4 schemas: `RAW`, `CURATED`, `ANALYTICS`, `ML`
- Dedicated warehouse `PM_WH` (XS, auto-suspend 120s)

### Phase 2: Synthetic Data Generation ✅
12 tables, all populated with domain-authentic data:

| Table | Rows | Description |
|---|---|---|
| `PLANTS` | 3 | Atul Chemicals (Valsad), Vapi Polymers, Ankleshwar Pharma |
| `AREAS` | 12 | Functional areas: Utility, Refrigeration, Cooling, Process, etc. |
| `ASSET_GROUPS` | 15 | Equipment trains with criticality (A/B/C) |
| `ASSETS` | 69 | Motors, Compressors, Blowers, Pumps, Fans — process-industry naming (MTR 510 A, COMP 520 C, etc.) |
| `SENSORS` | 138 | 2 per asset (DE + NDE), BLE MAC IDs, 3-axis orientation mapping |
| `SENSOR_READINGS` | 1,212,192 | 12 months hourly, 3-axis velocity (mm/s) + acceleration (m/s²) + temperature (°C) |
| `ISO_THRESHOLDS` | 16 | ISO 10816 severity bands for machine classes I–IV |
| `USERS` | 13 | Plant managers, engineers, analysts, operators + system account |
| `NOTIFICATION_RULES` | 12 | Severity-based notification routing per plant |
| `FAILURE_INCIDENTS` | 43 | 6 failure modes across 12 months, correlated with sensor degradation |
| `TICKETS` | 48 | 43 closed (from resolved failures) + 5 open/in-progress |
| `ERP_PRODUCTION_RUNS` | 9,882 | 9 production lines × 3 shifts × 366 days for OEE |

**Failure modes modeled** (each with distinct vibration signature):
- **Bearing defects** — acceleration-dominant, gradual ramp
- **Misalignment** — 2× RPM, axial-dominant
- **Unbalance** — 1× RPM, radial-dominant
- **Looseness** — multiple harmonics
- **Electrical faults** — 2× line frequency
- **Lubrication issues** — temperature rise + broadband acceleration

**Active degradation** injected for 5 assets with open tickets to provide current demo data.

### Phase 3: Dynamic Tables — Silver Layer ✅

| Dynamic Table | Rows | Key Features |
|---|---|---|
| `DT_SENSOR_ENRICHED` | 1,212,192 | Joins readings with full asset hierarchy, adds 24h rolling avg/stddev, 7-day z-scores, ISO zone classification, temperature status |
| `DT_BEARING_HEALTH` | 69 | Composite health score (0–100) from velocity (40%), acceleration (35%), temperature (25%); ADR risk classification (Low/Medium/High/Critical) |
| `DT_MAINTENANCE_HISTORY` | 48 | Tickets joined with failure incidents + user names; computes MTTR, time-to-acknowledge, ticket age |

### Phase 4: Dynamic Tables — Gold Layer ✅

| Dynamic Table | Rows | Key Features |
|---|---|---|
| `DT_OEE_METRICS` | 9,882 | OEE = Availability × Performance × Quality per run; categorized as World Class / Good / Needs Improvement / Poor |
| `DT_VIBRATION_ALERTS` | 2 | Assets with health < 92 or anomalies; alert severity factoring in asset criticality; recommended actions |
| `DT_PLANT_DASHBOARD` | 3 | Cross-plant executive view: asset risk distribution, avg health, OEE, open tickets, active alerts |
| `DT_TICKET_ANALYTICS` | 35 | Monthly aggregates: ticket counts by severity/failure mode, MTTR stats, total downtime, health improvement |

**Current plant dashboard snapshot:**

| Plant | Assets | Avg Health | Min Health | OEE % | Open Tickets | Alerts |
|---|---|---|---|---|---|---|
| Atul Chemicals - Valsad | 26 | 94.9 | 86 | 90.7% | 1 | 1 |
| Vapi Polymers Unit | 22 | 95.7 | 94 | 89.7% | 2 | 0 |
| Ankleshwar Pharma Complex | 21 | 95.0 | 85 | 89.8% | 2 | 1 |

---

## Completed Phases (continued)

### Phase 5: ML — Bearing Degradation Prediction ✅
- Feature engineering table: 25,614 rows with 23 features (daily aggregates + 7-day trends + labels)
- Snowflake ML Classification model: **F1 = 88%** on failure class (precision 92%, recall 85%)
- Top features: VEL_STDDEV, ACCEL_STDDEV, PEAK_RSS_ACCEL, MAX_ABS_ZSCORE
- Predictions view `ML.BEARING_PREDICTIONS_V` with risk tiers (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
- Correctly identifies MTR 330 A and COMP 520 B as highest-risk assets

### Phase 6: Semantic View ✅
- `ANALYTICS.VIBRATION_MANAGEMENT` — 6 logical tables, relationships, 7 verified queries
- Tables: DT_BEARING_HEALTH, DT_OEE_METRICS, DT_MAINTENANCE_HISTORY, DT_VIBRATION_ALERTS, DT_PLANT_DASHBOARD, DT_TICKET_ANALYTICS
- Verified queries: plant overview, at-risk assets, active alerts, OEE by plant, open tickets, worst health, failure modes, ticket trends
- Deployed via `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML` — tested and working in Snowsight Cortex Analyst

### Phase 7: Cortex Agent ✅
- `ANALYTICS.PM_COMMAND_CENTER_AGENT` — 1 orchestrator with Cortex Analyst tool
- Instructions: vibration specialist persona, ISO 10816 references, process-industry terminology
- Deployed via `cortex agent-studio agent-deploy`
- Accessible via Snowsight AI & ML → Agents playground
- Note: `DATA_AGENT_RUN` SQL function has warehouse resolution issue; works via REST API/Snowsight

### Phase 8: Streamlit Command Center ✅
- `ANALYTICS.PM_COMMAND_CENTER` — 5-page app, 732 lines, deployed to Snowflake
- **Page 1 - Plant Overview**: KPI metrics, 3-column plant comparison cards, risk distribution chart, OEE trend
- **Page 2 - Vibration Monitor**: Cascading filters, health score/ADR/ISO metrics, 3-axis vibration time-series, temperature trend, sensor table
- **Page 3 - Alert Triage**: Actionable alert count, color-coded expandable alert cards with recommended actions
- **Page 4 - Ticket Management**: Summary metrics, filterable ticket table, failure mode pie chart, monthly trend
- **Page 5 - Root Cause Chat**: Cortex Agent integration, persistent conversation history, sample question buttons

### Phase 9: Automation & Notifications ✅
- **Email notification integration**: `PM_EMAIL_NOTIFICATIONS` (EMAIL type)
- **Daily Health Report task**: 7 AM IST, sends plant health summary via email
- **Weekly OEE Summary task**: Monday 8 AM IST, OEE by plant/line
- **Auto-Ticket task**: 6 AM IST, creates tickets from ML predictions with probability > 10%
- All tasks created in suspended state — resume with `ALTER TASK ... RESUME` when ready
- Demo queries: 6 scenarios covering cross-plant overview, bearing degradation, OEE deep dive, failure modes, ML model, and system stats

---

## Demo Narrative (Full Story)
The planned demo weaves three scenarios into a 10-minute narrative:

1. **Bearing degradation story** — Show COMP 520 B bearing degrading over 2–3 weeks, system catches it via declining health score, auto-creates ticket, analyst agent explains root cause
2. **Cross-plant OEE drill-down** — Compare 3 plants side-by-side, drill into worst performer, investigate why OEE dropped, trace back to vibration-induced downtime
3. **Alert-to-resolution workflow** — Start from alert triage, investigate MTR 330 A high-severity alert, create work order, show expected pre/post repair health improvement

---

## File Structure
```
D:\projects\pms\project\predictive-maintenance\
├── 01_setup.sql                    — DB, schemas, warehouse (executed)
├── 02_synthetic_data.sql           — All 12 raw tables (executed)
├── 03_dynamic_tables_silver.sql    — Silver-layer DTs (to be saved)
├── 04_dynamic_tables_gold.sql      — Gold-layer DTs (to be saved)
├── 05_ml_pipeline.sql              — Feature engineering + model (pending)
├── 06_semantic_view.yaml           — Semantic model (pending)
├── 07_cortex_agent.sql             — Agent creation (pending)
├── 08_streamlit_app.py             — Command center (pending)
├── 09_automation.sql               — Streams, tasks, alerts (pending)
├── 10_mcp_connector.py             — Email integration (pending)
├── 11_coco_skill/                  — Reusable skill package (pending)
│   └── SKILL.md
├── 12_demo_queries.sql             — Demo script (pending)
└── PROGRESS.md                     — This file
```

---

## Key Design Decisions
- **ISO 10816** for vibration severity — adds real-world credibility
- **Process-industry naming** (MTR 510 A, COMP 520 C) — matches actual plant conventions
- **3-axis vibration** (velocity + acceleration) — not a simplified single value
- **Bearing Health Score** = weighted composite (40% velocity zone, 35% acceleration, 25% temperature)
- **ADR Risk** classification derived from health score thresholds
- **Failure-mode-specific degradation** injected into sensor data with realistic signatures
- **Multi-plant from day one** — customer/plant isolation built into every table
- **Dynamic Tables** for the entire medallion pipeline — auto-refreshing, no manual orchestration

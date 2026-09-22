# Predictive Maintenance & OEE Command Center — Technical Walkthrough

---

## 1. Executive Summary

### What Was Built

A complete, Snowflake-native **Predictive Maintenance and OEE (Overall Equipment Effectiveness) Command Center** that converges IT (ERP production data, maintenance records) and OT (vibration sensors, temperature sensors) data streams for three chemical/polymer/pharmaceutical manufacturing plants in Gujarat, India.

The system monitors 69 industrial rotating assets (motors, compressors, blowers, pumps, fans) across 138 vibration sensors, predicts bearing failures 7 days in advance using machine learning, automates work order creation, and provides a natural-language chat interface for root cause investigation — all running entirely within Snowflake's platform with zero external infrastructure.

### The Problem Statement

> *Manufacturers lose value to unplanned downtime because OT sensor data sits apart from ERP and maintenance context. Build a solution that converges IT and OT data to predict failures, automate work orders, and lift Overall Equipment Effectiveness.*

Specifically, the hackathon required:
1. Correlate real-time sensor streams (vibration, temperature, RPM) with ERP and maintenance records
2. Predict failures in advance and support root cause investigation in natural language
3. Deliver a command center experience for alert triage and action

### How This Solution Addresses Each Judging Criterion

**Real World Relevance:** The system is grounded in actual vibration management practice from a real MachPulse-style deployment at ATUL APL chemical plants. It uses ISO 10816 vibration severity standards, 3-axis vibration measurement (velocity + acceleration), drive-end/non-drive-end sensor positioning, process-industry naming conventions (MTR 510 A, COMP 520 C), and realistic failure-mode-specific degradation signatures. The reference data files (`asset_details.csv`, `device_details.csv`) from a real deployment were used as templates for the synthetic data design.

**Technical Execution:** The solution uses a full medallion architecture (Bronze/Silver/Gold) implemented entirely with Snowflake Dynamic Tables, an ML classification model with 88% F1 score on failure prediction, a Semantic View with 7 verified queries, a Cortex Agent for natural language querying, and a 709-line Streamlit-in-Snowflake application with 5 interactive pages — all orchestrated by automated tasks with email notifications.

**Solution Completeness:** Every layer of the stack is implemented end-to-end: data fabrication (12 tables, 1.2M sensor readings), pipeline automation (7 Dynamic Tables), ML prediction (feature engineering through deployment), semantic modeling (6 logical tables with relationships), agent orchestration, visualization (5 pages with interactive charts), and operational automation (4 scheduled tasks with email integration).

**CoCo Usage:** The entire solution was built using Cortex Code (CoCo) across all phases: planning (exploring data models, drafting architecture), development (generating SQL, Python, YAML), execution (running SQL against Snowflake, deploying objects), and testing (validating outputs, debugging issues).

---

## 2. Tech Stack & Platform Decisions

### Why Snowflake-Native

A standalone web application would require managing separate infrastructure for:
- A database server (Postgres/MySQL) for structured data
- A time-series database (InfluxDB/TimescaleDB) for sensor readings
- An ETL orchestrator (Airflow/Dagster) for data pipelines
- A model serving layer (MLflow/SageMaker) for predictions
- A web server (Flask/FastAPI) for the API
- A frontend framework (React/Next.js) for the UI
- A notification service (SendGrid/SES) for alerts

By building Snowflake-native, all of these collapse into a single platform: Snowflake handles storage, compute, ETL (Dynamic Tables), ML (Snowflake ML Classification), semantic modeling (Semantic Views), AI orchestration (Cortex Agent), visualization (Streamlit-in-Snowflake), and notifications (SYSTEM$SEND_EMAIL). There is zero infrastructure to manage, zero network hops between components, and the entire system can be reproduced by running SQL files in sequence.

### What Is Snowflake (for Someone Coming from Postgres/MySQL)

Snowflake is a cloud data platform that separates storage from compute. If you are familiar with Postgres:

- **Storage** is managed automatically — you do not create tablespaces, manage WAL, or worry about disk. Data is stored in a columnar format in cloud object storage (S3/Azure Blob/GCS).
- **Compute** is provided by "virtual warehouses" — ephemeral clusters of compute nodes that you spin up, use, and suspend. Think of it as a Postgres connection pool that auto-scales and auto-suspends when idle. You pay per-second of compute.
- **Databases and Schemas** work like Postgres — `DATABASE.SCHEMA.TABLE` three-part naming. Unlike Postgres, you can have multiple databases in one account and query across them without foreign data wrappers.
- **There is no index management.** Snowflake uses micro-partitions (compressed columnar segments of 50-500 MB) and automatic clustering. Query pruning replaces B-tree indexes.
- **SQL is ANSI-compatible** with extensions. Most Postgres SQL works with minor syntax adjustments.

### Key Snowflake Concepts Used in This Project

**Warehouse (Compute):** A named cluster of compute resources. This project uses `PM_WH`, an extra-small (XS) warehouse that auto-suspends after 120 seconds of inactivity and auto-resumes on query. Cost: ~1 credit/hour (~$3/hour) when active.

```sql
CREATE WAREHOUSE IF NOT EXISTS PM_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 120
    AUTO_RESUME = TRUE;
```

**Database and Schema (Storage Organization):** Logical containers. This project uses one database (`PREDICTIVE_MAINTENANCE`) with four schemas (`RAW`, `CURATED`, `ANALYTICS`, `ML`) implementing a medallion architecture. Every table is referenced as `PREDICTIVE_MAINTENANCE.RAW.PLANTS` etc.

**Stage (File Storage):** An internal or external location for storing files. Snowflake stages are used to upload the Streamlit application code (`PUT` command uploads `.py` files to a stage, and `CREATE STREAMLIT` references them).

**Dynamic Tables:** Snowflake's declarative, auto-refreshing materialized views. You write a `SELECT` statement and Snowflake automatically keeps the result up to date when source data changes. This replaces traditional ETL pipelines built with streams + tasks. Explained in detail in Section 6.

**Cortex AI:** Snowflake's suite of AI/ML services, including:
- **Snowflake ML Classification** — AutoML for classification problems (used for bearing failure prediction)
- **Cortex Complete** — LLM inference (used in the Streamlit chat page)
- **Cortex Analyst** — NL-to-SQL engine powered by Semantic Views
- **Cortex Agent** — Agentic AI framework that orchestrates tools

**Streamlit-in-Snowflake (SiS):** Snowflake hosts Streamlit applications natively — the Python code runs inside Snowflake's infrastructure, not on an external server. Data never leaves Snowflake's security perimeter. The Streamlit version in SiS is typically behind the latest open-source release (currently ~1.26.x vs. open-source 1.39+), which affects available API features.

### The Role of CoCo (Cortex Code)

CoCo is Snowflake's AI-powered coding assistant (CLI and Desktop app) used throughout this project for:

- **Planning:** Exploring the data domain, drafting the architecture, designing the data model
- **Development:** Writing all SQL (860 lines of synthetic data generation, Dynamic Table definitions, ML pipeline), Python (709-line Streamlit app), and YAML (503-line semantic view, 25-line agent spec)
- **Execution:** Running SQL against the Snowflake account, deploying objects, validating results
- **Testing:** Querying tables to verify row counts, testing semantic view accuracy, debugging agent behavior

---

## 3. Domain Grounding — Real Vibration Management Systems

### What the Reference Data Showed

The project was inspired by a real **MachPulse-style** vibration monitoring deployment at ATUL APL chemical/process plants. Two reference CSV files provided the grounding:

**`asset_details.csv`** — A list of assets at a real plant with their ADR (Alarm, Danger, Risk) status:
```
Name;ADR Status
MTR 510 A;Low Risk
MTR 510 B;Low Risk
COMP 510 C;Low Risk
COMP 520 B;Low Risk
BLOWER 731 A;Medium Risk
MTR 731 A;No FFT Found
```

**`device_details.csv`** — Real BLE wireless vibration sensors with 3-axis measurements:
```
Device Name;Label;Sensor Location;xAxisType;yAxisType;zAxisType;X RMS Velocity (mm/sec);Y RMS Velocity...
10255bb0;MTR 510 C | MTR NDE;Motor Non-Drive end;Vertical;Horizontal;Axial;0.14;0.17;0.14;27.96;...
d475e271;COMP 510 A | COMP NDE;Comp Bearing B2_Compressor side;Vertical;Horizontal;Axial;1.01;1.24;2.5;42.92;...
```

### How We Used It as Inspiration vs. Directly Copying

The reference data provided:
1. **Naming conventions** — Asset names like `MTR 510 A`, `COMP 520 B`, `BLOWER 731 A` follow a pattern: `TYPE GROUP_NUMBER LETTER`. We adopted this exactly.
2. **Sensor labeling** — Labels like `MTR 510 C | MTR NDE` encode asset name, type abbreviation, and mount position. We replicated this format.
3. **Mount locations** — "Motor Drive End", "Comp Bearing B1_Coupling Side", "B2-Blower Side" are real positions. We used these exact strings.
4. **Axis orientation** — Each sensor has X/Y/Z mapped to Vertical/Horizontal/Axial differently depending on mounting. We modeled this variation.
5. **Measurement types** — 3-axis RMS velocity (mm/s), 3-axis RMS acceleration (m/s^2), and temperature (C). We used the same measurement schema.
6. **Vibration levels** — Real readings showed healthy machines at 0.1-0.2 mm/s velocity and degraded machines at 1-3 mm/s. Our synthetic baselines and degradation ramps match these ranges.

What we did NOT copy: the actual sensor readings, timestamps, or failure history. All data is synthetic, fabricated to match the statistical properties and domain patterns of real vibration management.

### Key Domain Concepts

**3-Axis Vibration (Velocity + Acceleration):** Industrial vibration sensors measure in three orthogonal axes. **Velocity** (mm/s RMS) captures low-frequency vibration energy (imbalance, misalignment, looseness) and is the primary ISO 10816 parameter. **Acceleration** (m/s^2 RMS) captures high-frequency energy (bearing defects, gear mesh, electrical faults). Temperature complements vibration for lubrication and friction problems.

**DE/NDE Sensor Positions:** Rotating machines have two bearing positions:
- **DE (Drive End)** — the coupling side where the shaft connects to the driven equipment
- **NDE (Non-Drive End)** — the opposite end, typically a free bearing

Each position gets its own sensor because vibration patterns differ. A coupling misalignment shows strongest at DE; a bearing defect on the NDE bearing shows strongest at NDE.

**ISO 10816 Severity Bands:** The international standard for evaluating machine vibration severity. It classifies vibration into four zones:
- **Zone A (Good):** Newly commissioned or excellent condition
- **Zone B (Satisfactory):** Acceptable for long-term operation
- **Zone C (Unsatisfactory):** Not suitable for long-term, remedial action needed
- **Zone D (Unacceptable):** Damage risk, immediate action required

The thresholds depend on **Machine Class** (I through IV), which is based on machine size and mounting:
- Class I: Small machines up to 15 kW
- Class II: Medium machines 15-75 kW, or rigidly mounted up to 300 kW
- Class III: Large machines on rigid foundations (>300 kW)
- Class IV: Large machines on soft/flexible foundations

**Bearing Health Scoring:** A composite score (0-100) that combines velocity zone compliance, acceleration levels, and temperature into a single number for each asset. Higher is healthier.

**ADR Risk Classification:** Derived from the bearing health score:
- Low Risk: score >= 75
- Medium Risk: score >= 50
- High Risk: score >= 25
- Critical Risk: score < 25

**Process-Industry Naming Conventions:** Equipment in chemical/pharma plants follows a pattern:
- `MTR 510 A` = Motor, Group 510, Train A
- `COMP 520 C` = Compressor, Group 520, Train C
- `BLWR 731 B` = Blower, Group 731, Train B
- `PUMP 310 A` = Pump, Group 310, Train A

The group number identifies the functional grouping (e.g., "Freon Compressor Group 510"), and the letter identifies redundant units within that group.

### Why This Grounding Matters

The hackathon judging criterion "Real World Relevance" rewards solutions that could be deployed in actual industrial settings. By grounding the data model, naming conventions, measurement schema, and severity standards in real practice, the solution demonstrates domain expertise rather than a generic "sensor readings" approach.

---

## 4. Architecture Overview

### Data Flow Diagram

```
                        ┌──────────────────────────────────────────────────┐
                        │              DATA FABRICATION                     │
                        │  02_synthetic_data.sql (860 lines)               │
                        │  12 tables, 1.2M+ rows total                     │
                        └────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
┌─ RAW Schema (Bronze) ─────────────────────────────────────────────────────┐
│                                                                           │
│  PLANTS (3)              AREAS (12)              ASSET_GROUPS (15)        │
│  ASSETS (69)             SENSORS (138)           ISO_THRESHOLDS (16)      │
│  SENSOR_READINGS (1.2M)  FAILURE_INCIDENTS (43)  TICKETS (48)            │
│  ERP_PRODUCTION_RUNS (9,882)   USERS (13)        NOTIFICATION_RULES (12) │
│                                                                           │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 │ Dynamic Tables (auto-refresh)
                                 ▼
┌─ CURATED Schema (Silver) ─────────────────────────────────────────────────┐
│                                                                           │
│  DT_SENSOR_ENRICHED (1,212,192)                                          │
│    └─ Joins: readings + sensors + assets + groups + areas + plants + ISO  │
│    └─ Adds: 24h rolling stats, z-scores, ISO zone, temp status           │
│                                                                           │
│  DT_BEARING_HEALTH (69)                                                  │
│    └─ Latest reading per sensor, composite health score, ADR risk        │
│                                                                           │
│  DT_MAINTENANCE_HISTORY (48)                                             │
│    └─ Tickets + failure incidents + user names, MTTR, ticket age         │
│                                                                           │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
                                 │ Dynamic Tables (auto-refresh)
                                 ▼
┌─ ANALYTICS Schema (Gold) ─────────────────────────────────────────────────┐
│                                                                           │
│  DT_OEE_METRICS (9,882)         — Availability x Performance x Quality   │
│  DT_VIBRATION_ALERTS (2)        — ISO breaches + declining health        │
│  DT_PLANT_DASHBOARD (3)         — Cross-plant executive view             │
│  DT_TICKET_ANALYTICS (35)       — Monthly MTTR, SLA, failure modes       │
│                                                                           │
└───────────┬───────────────────────┬───────────────────────┬───────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
┌───────────────────┐  ┌────────────────────┐  ┌───────────────────────────┐
│   Semantic View   │  │   Cortex Agent     │  │   Streamlit App           │
│   (06_semantic    │  │   (07_agent_spec   │  │   (08_streamlit_app.py)   │
│    _view.yaml)    │  │    .yaml)          │  │   5 pages, 709 lines     │
│                   │  │                    │  │                           │
│  6 logical tables │  │  1 orchestrator +  │  │  Plant Overview           │
│  7 verified       │  │  Cortex Analyst    │  │  Vibration Monitor        │
│    queries        │  │  tool              │  │  Alert Triage             │
│                   │  │                    │  │  Ticket Management        │
│                   │  │                    │  │  Root Cause Chat          │
└───────────────────┘  └────────────────────┘  └───────────────────────────┘
            │                       │                       │
            └───────────┬───────────┘                       │
                        ▼                                   │
               ┌─────────────────┐                          │
               │  ML Schema      │                          │
               │  BEARING_FAILURE│                          │
               │  _FEATURES      │                          │
               │  BEARING_FAILURE│                          │
               │  _MODEL         │                          │
               │  BEARING_       │                          │
               │  PREDICTIONS_V  │◄─────────────────────────┘
               └─────────────────┘         (used by automation tasks)
```

### The Medallion Architecture

The **Medallion Architecture** (also called Bronze/Silver/Gold or Multi-Hop) is a data engineering pattern that organizes data processing into layers of increasing quality and business value:

**Bronze (RAW Schema):** Raw data as-ingested. In a production system, this would be direct sensor streams via Snowpipe, ERP extracts, and maintenance system exports. In this project, it is synthetic data that simulates what raw ingestion would look like. No transformations, no joins, no computed columns. The "source of truth" layer.

**Silver (CURATED Schema):** Cleaned, enriched, joined data. Sensor readings are joined with their full asset hierarchy (sensor -> asset -> group -> area -> plant), rolling statistics are computed, ISO severity zones are classified, and anomaly z-scores are calculated. This is the "analyst-ready" layer.

**Gold (ANALYTICS Schema):** Business-level aggregations and metrics. OEE is computed from production runs, vibration alerts are generated from health scores, plant dashboards aggregate across all dimensions, and ticket analytics provide monthly trends. This is the "executive-ready" layer.

**ML Schema:** A parallel layer for machine learning artifacts — feature engineering tables, trained models, and prediction outputs.

### Why Dynamic Tables for the Pipeline

In traditional Snowflake ETL, you would use **streams** (change data capture on a table) and **tasks** (scheduled SQL execution) to propagate data changes through the pipeline. This requires writing imperative logic: "when new data arrives in table A, run this INSERT/MERGE into table B."

**Dynamic Tables** (introduced in 2023) flip this to declarative: you write the SELECT statement that defines what the table should look like, specify a target lag (how fresh the data should be), and Snowflake handles the rest — it monitors upstream tables, detects changes, and automatically refreshes the Dynamic Table.

```sql
-- Traditional approach: write a task + stream
CREATE STREAM sensor_stream ON TABLE RAW.SENSOR_READINGS;
CREATE TASK refresh_enriched WAREHOUSE = PM_WH SCHEDULE = '5 MINUTES' AS
    MERGE INTO CURATED.DT_SENSOR_ENRICHED t USING (SELECT ... FROM sensor_stream) s ON ...;

-- Dynamic Table approach: declare the result
CREATE DYNAMIC TABLE CURATED.DT_SENSOR_ENRICHED
    TARGET_LAG = '1 hour' WAREHOUSE = PM_WH AS
    SELECT ... FROM RAW.SENSOR_READINGS r JOIN RAW.SENSORS s ON ... ;
```

The Dynamic Table approach eliminates: task scheduling logic, merge/upsert complexity, dependency ordering between tasks, and manual error recovery. Snowflake manages it all.

### Every Snowflake Object Created

| Schema | Object | Type | Purpose |
|--------|--------|------|---------|
| — | `PREDICTIVE_MAINTENANCE` | Database | Project database |
| — | `PM_WH` | Warehouse | All compute |
| `RAW` | `PLANTS` | Table | 3 manufacturing plants |
| `RAW` | `AREAS` | Table | 12 functional areas |
| `RAW` | `ASSET_GROUPS` | Table | 15 equipment groups |
| `RAW` | `ASSETS` | Table | 69 rotating assets |
| `RAW` | `SENSORS` | Table | 138 vibration sensors |
| `RAW` | `SENSOR_READINGS` | Table | 1,212,192 hourly readings |
| `RAW` | `ISO_THRESHOLDS` | Table | 16 ISO 10816 severity bands |
| `RAW` | `FAILURE_INCIDENTS` | Table | 43 failure events |
| `RAW` | `TICKETS` | Table | 48 maintenance tickets |
| `RAW` | `ERP_PRODUCTION_RUNS` | Table | 9,882 production runs |
| `RAW` | `USERS` | Table | 13 plant personnel |
| `RAW` | `NOTIFICATION_RULES` | Table | 12 notification routing rules |
| `CURATED` | `DT_SENSOR_ENRICHED` | Dynamic Table | Enriched sensor readings |
| `CURATED` | `DT_BEARING_HEALTH` | Dynamic Table | Per-asset health scores |
| `CURATED` | `DT_MAINTENANCE_HISTORY` | Dynamic Table | Enriched ticket data |
| `ANALYTICS` | `DT_OEE_METRICS` | Dynamic Table | OEE calculations |
| `ANALYTICS` | `DT_VIBRATION_ALERTS` | Dynamic Table | Active vibration alerts |
| `ANALYTICS` | `DT_PLANT_DASHBOARD` | Dynamic Table | Executive plant summaries |
| `ANALYTICS` | `DT_TICKET_ANALYTICS` | Dynamic Table | Monthly ticket aggregations |
| `ANALYTICS` | `VIBRATION_MANAGEMENT` | Semantic View | NL-to-SQL interface |
| `ANALYTICS` | `PM_COMMAND_CENTER_AGENT` | Cortex Agent | NL orchestrator |
| `ANALYTICS` | `PM_COMMAND_CENTER` | Streamlit | 5-page command center |
| `ANALYTICS` | `DAILY_HEALTH_REPORT` | Task | Daily email report |
| `ANALYTICS` | `CRITICAL_ALERT_MONITOR` | Task | 30-min alert check |
| `ANALYTICS` | `WEEKLY_OEE_SUMMARY` | Task | Monday OEE email |
| `ANALYTICS` | `AUTO_TICKET_FROM_PREDICTIONS` | Task | Daily auto-ticket from ML |
| `ANALYTICS` | `PM_EMAIL_NOTIFICATIONS` | Notification Integration | Email delivery |
| `ML` | `BEARING_FAILURE_FEATURES` | Table | 25,614 feature rows |
| `ML` | `BEARING_FAILURE_FEATURES_V` | View | Cleaned feature view |
| `ML` | `BEARING_FAILURE_MODEL` | ML Model | Classification model |
| `ML` | `BEARING_PREDICTIONS` | Table | Raw prediction output |
| `ML` | `BEARING_PREDICTIONS_V` | View | Flattened predictions with risk tiers |

---

## 5. Data Fabrication — The Bronze Layer (RAW Schema)

The `02_synthetic_data.sql` file (860 lines) generates all 12 raw tables with domain-authentic data. This section explains the design decisions and SQL techniques behind each table.

### 5.1 Plant Hierarchy Design

The hierarchy mirrors a real multi-plant industrial operation:

```
PLANTS (3)
  └─ AREAS (12)           — 4 per plant: functional zones
       └─ ASSET_GROUPS (15) — 5 per plant: equipment trains
            └─ ASSETS (69)   — motors, compressors, blowers, pumps, fans
                 └─ SENSORS (138) — 2 per asset: DE + NDE
```

**PLANTS (3 rows):** Three chemical/polymer/pharma plants in Gujarat, India:

```sql
INSERT INTO PLANTS VALUES
    ('PLT-001', 'Atul Chemicals - Valsad',     'Valsad, Gujarat',      'West', 'Chemical Processing', '2008-03-15', 'Asia/Kolkata'),
    ('PLT-002', 'Vapi Polymers Unit',           'Vapi, Gujarat',        'West', 'Polymer Manufacturing','2012-07-22', 'Asia/Kolkata'),
    ('PLT-003', 'Ankleshwar Pharma Complex',    'Ankleshwar, Gujarat',  'West', 'Pharmaceutical',      '2015-11-10', 'Asia/Kolkata');
```

**AREAS (12 rows):** Each plant has 4 functional areas matching real plant layouts:
- PLT-001: Utility Block, Refrigeration Section, Cooling Water System, Process Block A
- PLT-002: Compressor House, Extrusion Line, Cooling Tower, Raw Material Handling
- PLT-003: HVAC Section, Solvent Recovery, Reactor Utilities, Water Treatment

**ASSET_GROUPS (15 rows):** Equipment trains with criticality ratings (A/B/C):
- **A (Critical):** Compressor groups, pump sets — production stops if they fail
- **B (Essential):** Blower groups, fan groups — degraded operation possible
- **C (General Purpose):** Conveyor drives — backup available

Each group has a numeric code (510, 520, 731, etc.) that forms the middle part of asset names.

**ASSETS (69 rows):** Process-industry naming convention applied:

```sql
('A-001', 'GRP-001', 'MTR 510 A',   'MOTOR',      'III', 1480, 110, '2010-05-12', 'Siemens',    '1LE1501-2AB53'),
('A-002', 'GRP-001', 'COMP 510 A',  'COMPRESSOR', 'III', 1480, NULL, '2010-05-12', 'Bitzer',     '6HE-28Y'),
```

Each asset has:
- `MACHINE_CLASS`: ISO 10816 class (I-IV) based on size and mounting
- `RATED_RPM`: Nominal speed (960, 1480, 2960 RPM — standard induction motor speeds)
- `RATED_POWER_KW`: Motor power (22-250 kW range)
- `MANUFACTURER`: Real manufacturers (Siemens, ABB, Crompton, Bitzer, Atlas Copco, KSB, etc.)
- `MODEL_NUMBER`: Realistic model numbers matching manufacturer catalogs

The 69 assets include:
- 30 motors (MTR) — drive units for all equipment
- 12 compressors (COMP) — freon and air compression
- 8 blowers (BLWR) — air handling and water treatment
- 10 pumps (PUMP) — cooling water, process, vacuum
- 8 fans (FAN) — cooling tower induced draft
- 1 additional motor type variant

**SENSORS (138 rows):** Auto-generated with a CTE — 2 sensors per asset (DE + NDE):

```sql
INSERT INTO SENSORS
WITH asset_sensor_gen AS (
    SELECT
        A.ASSET_ID, A.ASSET_NAME, A.ASSET_TYPE, A.INSTALL_DATE,
        pos.POSITION,
        ROW_NUMBER() OVER (ORDER BY A.ASSET_ID, pos.POSITION) AS rn
    FROM ASSETS A,
    (SELECT 'DE' AS POSITION UNION ALL SELECT 'NDE') pos
)
SELECT
    'SNS-' || LPAD(rn::VARCHAR, 4, '0') AS SENSOR_ID,
    ASSET_ID,
    SUBSTR(MD5(ASSET_ID || POSITION), 1, 8) AS BLE_MAC,
    ASSET_NAME || ' | ' ||
        CASE ASSET_TYPE
            WHEN 'MOTOR' THEN 'MTR'
            WHEN 'COMPRESSOR' THEN 'COMP'
            ...
        END || ' ' || POSITION AS SENSOR_LABEL,
    ...
```

The `BLE_MAC` is generated from an MD5 hash of asset+position, simulating the 8-character BLE MAC addresses of real wireless sensors. Axis orientation (X=Vertical/Horizontal/Axial, Y=..., Z=...) varies by sensor position, matching the real reference data where different sensors have different mounting orientations.

### 5.2 Failure Incident Design

**FAILURE_INCIDENTS (43 rows):** 43 failure events across 12 months, distributed across 6 failure modes.

Each failure mode has a distinct vibration signature grounded in rotating machinery physics:

**Bearing Defects (most common, 14 incidents):**
- **Physics:** Inner race, outer race, ball, or cage defects create impact pulses at characteristic bearing defect frequencies (BPFI, BPFO, BSF, FTF).
- **Vibration signature:** Dominant in **high-frequency acceleration** (8x multiplier on acceleration, only 1.5x on velocity). This is because bearing defect impacts are brief, high-energy events that show in the acceleration (derivative of velocity) spectrum.
- **Temperature:** +15C rise from friction heating.

**Misalignment (7 incidents):**
- **Physics:** Angular or parallel offset between coupled shafts creates a forcing function at 2x running speed.
- **Vibration signature:** Strong in the **axial direction** (5x multiplier on Z-axis velocity for axial, 3.5x on Y-axis). Misalignment generates axial thrust forces.
- **Temperature:** +8C moderate rise.

**Unbalance (6 incidents):**
- **Physics:** Uneven mass distribution creates a once-per-revolution (1x RPM) centrifugal force.
- **Vibration signature:** Strong in **radial velocity** (4x on X, 3.5x on Y) but weak axially (1.5x on Z). Minimal acceleration impact (1x) because the force is sinusoidal, not impulsive.
- **Temperature:** +3C minimal rise.

**Looseness (5 incidents):**
- **Physics:** Structural looseness (bolts, bearing housing, foundation) creates impacts and truncated waveforms that generate multiple harmonics (0.5x, 1x, 2x, 3x, ...).
- **Vibration signature:** Moderate across all axes (3x X-vel, 2.5x Y-vel, 2x Z-vel) with moderate acceleration impact (3x).
- **Temperature:** +5C mild rise.

**Electrical Faults (5 incidents):**
- **Physics:** Rotor bar cracks, stator winding faults, or air-gap eccentricity create vibration at 2x line frequency (100 Hz in India's 50 Hz grid) and its harmonics.
- **Vibration signature:** Moderate velocity (1.2x) but noticeable in acceleration (2x). The signature is distinctive because it is locked to electrical frequency, not shaft speed.
- **Temperature:** +12C winding heat.

**Lubrication Issues (6 incidents):**
- **Physics:** Grease degradation, oil contamination, or lubricant starvation increases friction, raising bearing temperature and broadband high-frequency vibration.
- **Vibration signature:** Mild velocity increase (0.8x) but noticeable acceleration (4x) and significant **temperature rise** (+20C). Temperature is the primary early indicator.

**Degradation Windows:**

Each failure incident has a severity-dependent lead time for the degradation ramp:

```sql
DATEADD('day',
    CASE fi.SEVERITY
        WHEN 'LOW'      THEN -7     -- 7 days of gradual degradation
        WHEN 'MEDIUM'   THEN -14    -- 14 days
        WHEN 'HIGH'     THEN -21    -- 21 days
        WHEN 'CRITICAL' THEN -28    -- 28 days (longest warning window)
    END,
    fi.FAILURE_TIMESTAMP) AS DEGRAD_START
```

This reflects reality: severe failures (HIGH/CRITICAL) typically show earlier warning signs because the defect is more aggressive and grows faster, giving vibration analysts more lead time. LOW severity issues (like lubrication) may not be detectable until close to the event.

### 5.3 Sensor Readings Generation (1,212,192 rows)

The largest and most complex table. The generation strategy uses five SQL CTEs chained together:

**Step 1: Time Spine**

```sql
time_spine AS (
    SELECT DATEADD('hour', SEQ4(), '2025-09-18 00:00:00'::TIMESTAMP_NTZ) AS ts
    FROM TABLE(GENERATOR(ROWCOUNT => 8784))  -- 366 days x 24 hours
    WHERE DATEADD('hour', SEQ4(), ....) <= '2026-09-18 23:00:00'
)
```

`TABLE(GENERATOR(ROWCOUNT => N))` is a Snowflake-specific function that generates N rows with a sequence column `SEQ4()`. This creates 8,784 hourly timestamps spanning 12 months. There is no equivalent in Postgres — the closest is `generate_series()`.

**Step 2: Sensor x Time Cross Join with Baselines**

```sql
sensor_time AS (
    SELECT
        s.SENSOR_ID, s.ASSET_ID, s.MOUNT_POSITION, t.ts,
        a.ASSET_TYPE, a.MACHINE_CLASS, a.RATED_RPM,
        -- Baseline vibration by asset type (healthy machine)
        CASE a.ASSET_TYPE
            WHEN 'MOTOR'      THEN 0.5   -- mm/s RMS velocity baseline
            WHEN 'COMPRESSOR' THEN 0.8
            WHEN 'BLOWER'     THEN 0.6
            WHEN 'PUMP'       THEN 0.7
            WHEN 'FAN'        THEN 0.4
        END AS BASE_VEL,
        CASE a.ASSET_TYPE
            WHEN 'MOTOR'      THEN 1.0   -- m/s^2 RMS acceleration baseline
            WHEN 'COMPRESSOR' THEN 1.5
            ...
        END AS BASE_ACCEL,
        CASE a.ASSET_TYPE
            WHEN 'MOTOR'      THEN 38    -- degrees C baseline
            WHEN 'COMPRESSOR' THEN 42
            ...
        END AS BASE_TEMP
    FROM SENSORS s
    JOIN ASSETS a ON a.ASSET_ID = s.ASSET_ID
    CROSS JOIN time_spine t
)
```

The 138 sensors x 8,784 hours = 1,212,192 rows. Baselines vary by asset type: compressors are naturally noisier than fans, and run hotter.

**Step 3: Degradation Factor Calculation**

```sql
degradation AS (
    SELECT st.*,
        COALESCE(MAX(
            CASE
                WHEN st.READING_TS BETWEEN fsm.DEGRAD_START AND fsm.DEGRAD_END THEN
                    -- Progressive ramp: 0.0 at start -> 1.0 at failure time
                    TIMESTAMPDIFF('hour', fsm.DEGRAD_START, st.READING_TS)::FLOAT /
                    NULLIF(TIMESTAMPDIFF('hour', fsm.DEGRAD_START, fsm.DEGRAD_END), 0)::FLOAT
                WHEN st.READING_TS > fsm.DEGRAD_END
                     AND st.READING_TS < DATEADD('day', 2, fsm.DEGRAD_END) THEN
                    -- Post-failure recovery: 1.0 -> 0.0 over 2 days
                    1.0 - (TIMESTAMPDIFF('hour', fsm.DEGRAD_END, st.READING_TS)::FLOAT / 48.0)
                ELSE 0
            END
        ), 0) AS DEGRAD_FACTOR,
        MAX(CASE
            WHEN st.READING_TS BETWEEN fsm.DEGRAD_START AND fsm.DEGRAD_END
            THEN fsm.FAILURE_MODE ELSE NULL
        END) AS ACTIVE_FAILURE_MODE
    FROM sensor_time st
    LEFT JOIN FAILURE_SENSOR_MAP fsm ON st.SENSOR_ID = fsm.SENSOR_ID
    GROUP BY ...
)
```

The `DEGRAD_FACTOR` is a linear ramp from 0.0 (start of degradation window) to 1.0 (failure moment). After failure, it recovers linearly to 0.0 over 2 days (simulating repair). The `MAX()` aggregation handles the case where an asset might have overlapping failure windows.

**Step 4: Applying Failure-Mode-Specific Multipliers**

Each axis and measurement type gets a different multiplier per failure mode:

```sql
-- X-axis velocity
GREATEST(0.01, ROUND(
    BASE_VEL * (1 + DEGRAD_FACTOR *
        CASE ACTIVE_FAILURE_MODE
            WHEN 'UNBALANCE'       THEN 4.0   -- strong radial
            WHEN 'MISALIGNMENT'    THEN 2.5   -- 2x RPM
            WHEN 'BEARING_DEFECT'  THEN 1.5   -- moderate velocity
            WHEN 'LOOSENESS'       THEN 3.0   -- multiple harmonics
            WHEN 'ELECTRICAL'      THEN 1.2   -- electrical frequencies
            WHEN 'LUBRICATION'     THEN 0.8   -- mild velocity
            ELSE 0
        END)
    + (RANDOM() / 9223372036854775807::FLOAT) * BASE_VEL * 0.15  -- 15% random noise
    + SIN(EXTRACT(HOUR FROM READING_TS)::FLOAT * 0.26) * BASE_VEL * 0.05  -- diurnal
, 2)) AS X_VEL_RMS,
```

The formula for each reading is:

```
reading = BASE * (1 + DEGRAD_FACTOR * FAILURE_MODE_MULTIPLIER)
        + random_noise (15% of base)
        + diurnal_pattern (5% sinusoidal on hour)
        + seasonal_temperature (for temp readings, 0-8C by month)
```

The `GREATEST(0.01, ...)` ensures readings never go negative. `RANDOM() / 9223372036854775807::FLOAT` normalizes Snowflake's `RANDOM()` (which returns a 64-bit integer) to a [0, 1] float.

**Temperature** additionally includes seasonal variation:

```sql
+ CASE EXTRACT(MONTH FROM READING_TS)
    WHEN 4 THEN 3 WHEN 5 THEN 5 WHEN 6 THEN 7
    WHEN 7 THEN 8 WHEN 8 THEN 6 WHEN 9 THEN 4
    ELSE 0
  END  -- Gujarat summer peak in July
```

### 5.4 Supporting Tables

**ISO_THRESHOLDS (16 rows):** Four zones per four machine classes:

```sql
INSERT INTO ISO_THRESHOLDS VALUES
    ('I',   'A_GOOD',           0,    0.71,  0,    2.5,   55, 65, 'Good...'),
    ('I',   'B_SATISFACTORY',   0.71, 1.8,   2.5,  6.3,   55, 65, 'Satisfactory...'),
    ('I',   'C_UNSATISFACTORY', 1.8,  4.5,   6.3,  16.0,  55, 65, 'Unsatisfactory...'),
    ('I',   'D_UNACCEPTABLE',   4.5,  999,   16.0, 999,   55, 65, 'Unacceptable...'),
    -- Class II thresholds are higher (larger machines tolerate more vibration)
    ('II',  'A_GOOD',           0,    1.12,  0,    4.0,   60, 70, ...),
    ...
```

The thresholds increase with machine class because larger machines naturally vibrate more. Class I (small machines) considers 0.71 mm/s as the boundary of "Good," while Class III (large machines) allows up to 1.8 mm/s.

**ERP_PRODUCTION_RUNS (9,882 rows):** 9 production lines x 3 shifts x 366 days. Generated with cross-joins and correlated with failure incidents for realistic unplanned downtime:

```sql
CASE
    WHEN EXISTS (
        SELECT 1 FROM FAILURE_INCIDENTS fi
        JOIN ASSETS a ON fi.ASSET_ID = a.ASSET_ID
        JOIN ASSET_GROUPS ag ON a.GROUP_ID = ag.GROUP_ID
        JOIN AREAS ar ON ag.AREA_ID = ar.AREA_ID
        WHERE ar.PLANT_ID = p.plant_id
        AND d.run_date BETWEEN fi.FAILURE_TIMESTAMP::DATE
            AND DATEADD('day', CEIL(fi.DOWNTIME_HOURS/24), fi.FAILURE_TIMESTAMP)::DATE
    ) THEN UNIFORM(30, 180, RANDOM())::FLOAT  -- 30-180 min unplanned downtime
    ELSE UNIFORM(0, 15, RANDOM())::FLOAT      -- 0-15 min normal stoppages
END AS unplanned_dt
```

This ensures OEE drops correlate with equipment failures — when a compressor fails at PLT-001, the production lines at PLT-001 show increased unplanned downtime during the failure window.

**TICKETS (48 rows):** 43 closed tickets generated from failure incidents + 5 hand-crafted open tickets for demo purposes:

```sql
-- Open tickets for current demo data
INSERT INTO TICKETS VALUES
    ('TK-0044', 'A-010', NULL, '2026-09-12 08:30:00', 'MEDIUM', 'OPEN', NULL, NULL, NULL,
     'Vibration trending up on COMP 520 B, monitor closely', NULL, NULL, 48, NULL, 'USR-013', NULL,
     'Velocity trending from 1.2 to 1.8 mm/s over 2 weeks'),
    ('TK-0046', 'A-059', NULL, '2026-09-15 14:45:00', 'HIGH', 'IN_PROGRESS', 'USR-011',
     '2026-09-15 15:30:00', 'USR-010',
     'Bearing Replacement, Alignment Check on MTR 330 A', ...),
    ...
```

These 5 open tickets are linked to the "active degradation" data — the same 5 assets have current degradation injected into their sensor readings, so the Streamlit dashboard shows live alerts.

**USERS (13 rows):** Each plant has 4 roles: Plant Manager, Maintenance Engineer, Vibration Analyst, Operator. Plus one system account (`USR-013`, "MachPulse System") for automated actions.

**NOTIFICATION_RULES (12 rows):** Severity-based routing per plant. LOW alerts go to the vibration analyst only; CRITICAL alerts escalate to analyst + engineer + plant manager + system admin.

---

## 6. The Silver Layer (CURATED Schema) — Dynamic Tables

### What Are Dynamic Tables

Dynamic Tables are a Snowflake feature (GA since 2023) that lets you define a table as a SQL `SELECT` statement. Snowflake automatically materializes the result and keeps it up-to-date as upstream data changes.

Key properties:
- **Declarative:** You write the query; Snowflake handles the refresh scheduling.
- **TARGET_LAG:** How stale the data is allowed to be (e.g., `'1 hour'` means the table will be refreshed within 1 hour of upstream changes). In this project, `DOWNSTREAM` is used, meaning the Dynamic Table refreshes to satisfy the lag requirements of whatever depends on it.
- **REFRESH_MODE:** `FULL` (recompute everything) or `INCREMENTAL` (only process changes). The complex joins and window functions in this project require FULL mode.
- **Warehouse:** Each Dynamic Table uses `PM_WH` for its refresh compute.

For someone coming from Postgres: think of it as a materialized view that auto-refreshes, with built-in dependency tracking across a chain of materialized views.

### 6.1 DT_SENSOR_ENRICHED

The core Silver table — joins every sensor reading with its full hierarchy and computes analytics.

**What it joins:** `SENSOR_READINGS` + `SENSORS` + `ASSETS` + `ASSET_GROUPS` + `AREAS` + `PLANTS` + `ISO_THRESHOLDS`. This denormalizes the 7-table hierarchy into a single wide table with 1,212,192 rows.

**Rolling statistics (24-hour window):**
```sql
AVG(MAX_VEL_RMS) OVER (
    PARTITION BY SENSOR_ID ORDER BY READING_TS
    ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
) AS VEL_24H_AVG,
STDDEV(MAX_VEL_RMS) OVER (
    PARTITION BY SENSOR_ID ORDER BY READING_TS
    ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
) AS VEL_24H_STDDEV
```

The 24-hour window (23 preceding hourly rows + current) smooths out random noise and diurnal patterns.

**Z-score for anomaly detection (7-day window):**
```sql
(MAX_VEL_RMS - AVG(MAX_VEL_RMS) OVER (
    PARTITION BY SENSOR_ID ORDER BY READING_TS
    ROWS BETWEEN 167 PRECEDING AND CURRENT ROW
)) / NULLIF(STDDEV(MAX_VEL_RMS) OVER (
    PARTITION BY SENSOR_ID ORDER BY READING_TS
    ROWS BETWEEN 167 PRECEDING AND CURRENT ROW
), 0) AS VEL_ZSCORE
```

A z-score measures how many standard deviations a reading is from its 7-day (168 hour) rolling mean. A z-score > 3 means the reading is statistically unusual. `NULLIF(..., 0)` prevents division-by-zero for sensors with constant readings.

**ISO zone classification:**
```sql
CASE
    WHEN MAX_VEL_RMS <= it.VEL_UPPER_MM_S AND 'A_GOOD' = it.ZONE THEN 'A_GOOD'
    WHEN MAX_VEL_RMS <= it.VEL_UPPER_MM_S AND 'B_SATISFACTORY' = it.ZONE THEN 'B_SATISFACTORY'
    WHEN MAX_VEL_RMS <= it.VEL_UPPER_MM_S AND 'C_UNSATISFACTORY' = it.ZONE THEN 'C_UNSATISFACTORY'
    ELSE 'D_UNACCEPTABLE'
END AS ISO_VEL_ZONE
```

This classifies each reading into its ISO 10816 zone based on the asset's machine class thresholds.

**Temperature status:**
```sql
CASE
    WHEN TEMPERATURE_C >= it.TEMP_ALARM_C THEN 'ALARM'
    WHEN TEMPERATURE_C >= it.TEMP_WARNING_C THEN 'WARNING'
    ELSE 'NORMAL'
END AS TEMP_STATUS
```

**Computed fields:**
- `MAX_VEL_RMS`: `GREATEST(X_VEL_RMS, Y_VEL_RMS, Z_VEL_RMS)` — worst-axis velocity
- `RSS_ACCEL`: `SQRT(X_ACCEL_RMS^2 + Y_ACCEL_RMS^2 + Z_ACCEL_RMS^2)` — root-sum-square acceleration magnitude

### 6.2 DT_BEARING_HEALTH

Reduces 1.2M enriched readings to 69 rows — one per asset — showing current health status.

**Latest-reading-per-sensor approach:**
```sql
WITH latest AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY SENSOR_ID ORDER BY READING_TS DESC) AS rn
    FROM CURATED.DT_SENSOR_ENRICHED
)
SELECT ... FROM latest WHERE rn = 1
```

This is a standard "latest record per group" pattern using `ROW_NUMBER()` window function. It picks the most recent reading for each sensor.

**Composite health score formula:**

```
BEARING_HEALTH_SCORE = 100 - (
    40% * velocity_penalty +
    35% * acceleration_penalty +
    25% * temperature_penalty
)
```

Where:
- **Velocity penalty (40%):** Maps ISO zone to a penalty: A_GOOD=0, B_SATISFACTORY=25, C_UNSATISFACTORY=50, D_UNACCEPTABLE=100. Uses the worst zone across both DE/NDE sensors.
- **Acceleration penalty (35%):** Normalizes RSS acceleration against the ISO acceleration thresholds. `(RSS_ACCEL / ACCEL_UPPER_C) * 100`, capped at 100.
- **Temperature penalty (25%):** `ALARM` = 100, `WARNING` = 50, `NORMAL` = 0.

The weights reflect vibration analyst practice: velocity is the primary indicator (40%), acceleration catches bearing defects early (35%), and temperature is a secondary confirmer (25%).

**ADR Risk classification:**
```sql
CASE
    WHEN BEARING_HEALTH_SCORE >= 75 THEN 'Low'
    WHEN BEARING_HEALTH_SCORE >= 50 THEN 'Medium'
    WHEN BEARING_HEALTH_SCORE >= 25 THEN 'High'
    ELSE 'Critical'
END AS ADR_RISK
```

**Anomaly flag:**
```sql
CASE WHEN MAX(ABS(VEL_ZSCORE)) > 3.0 THEN TRUE ELSE FALSE END AS ANOMALY_FLAG
```

### 6.3 DT_MAINTENANCE_HISTORY

Joins tickets with failure incidents and user names for a complete maintenance record.

```sql
SELECT
    t.TICKET_ID, t.SEVERITY, t.STATUS,
    a.ASSET_NAME, a.ASSET_TYPE,
    p.PLANT_NAME,
    fi.FAILURE_MODE, fi.ROOT_CAUSE, fi.DOWNTIME_HOURS,
    u_assigned.USER_NAME AS ASSIGNED_TO_NAME,
    -- Computed fields
    DATEDIFF('hour', t.ISSUE_OPEN_DATE, t.ISSUE_CLOSURE_DATE) AS MTTR_HOURS,
    DATEDIFF('hour', t.ISSUE_OPEN_DATE, t.ACKNOWLEDGE_DATE) AS TIME_TO_ACK_HOURS,
    DATEDIFF('day', t.ISSUE_OPEN_DATE, CURRENT_TIMESTAMP()) AS TICKET_AGE_DAYS,
    t.POST_REPAIR_HEALTH_SCORE - t.PRE_REPAIR_HEALTH_SCORE AS HEALTH_IMPROVEMENT
FROM RAW.TICKETS t
JOIN RAW.ASSETS a ON t.ASSET_ID = a.ASSET_ID
JOIN RAW.ASSET_GROUPS ag ON a.GROUP_ID = ag.GROUP_ID
JOIN RAW.AREAS ar ON ag.AREA_ID = ar.AREA_ID
JOIN RAW.PLANTS p ON ar.PLANT_ID = p.PLANT_ID
LEFT JOIN RAW.FAILURE_INCIDENTS fi ON t.INCIDENT_ID = fi.INCIDENT_ID
LEFT JOIN RAW.USERS u_assigned ON t.ASSIGNED_TO = u_assigned.USER_ID
```

Key computed fields:
- **MTTR (Mean Time To Repair):** Hours between ticket open and closure
- **Time-to-acknowledge:** Hours between ticket open and acknowledgment
- **Ticket age:** Days since ticket was opened (relevant for open tickets)
- **Health improvement:** Post-repair minus pre-repair health score

---

## 7. The Gold Layer (ANALYTICS Schema) — Dynamic Tables

### 7.1 DT_OEE_METRICS

OEE (Overall Equipment Effectiveness) is the gold standard KPI in manufacturing. It measures how effectively a manufacturing operation is utilized.

**OEE Formula:** `OEE = Availability x Performance x Quality`

Each component is computed from ERP production run data:

```sql
-- Availability: actual running time / planned production time
(ACTUAL_RUNTIME_MIN / (PLANNED_RUNTIME_MIN - PLANNED_DOWNTIME_MIN)) AS AVAILABILITY,

-- Performance: actual throughput / theoretical maximum throughput
(ACTUAL_QUANTITY * IDEAL_CYCLE_TIME_SEC / 60.0) / ACTUAL_RUNTIME_MIN AS PERFORMANCE,

-- Quality: good units / total units produced
(GOOD_QUANTITY::FLOAT / NULLIF(ACTUAL_QUANTITY, 0)) AS QUALITY,

-- OEE
AVAILABILITY * PERFORMANCE * QUALITY AS OEE
```

**OEE categorization:**
```sql
CASE
    WHEN OEE >= 0.85 THEN 'World Class'   -- Top-tier manufacturing
    WHEN OEE >= 0.65 THEN 'Good'          -- Typical for process industry
    WHEN OEE >= 0.50 THEN 'Needs Improvement'
    ELSE 'Poor'
END AS OEE_CATEGORY
```

World Class OEE (>=85%) is the benchmark for best-in-class manufacturing. Most process-industry plants operate at 65-75%.

The table also joins plant names for easy querying:

```sql
FROM RAW.ERP_PRODUCTION_RUNS e
JOIN RAW.PLANTS p ON e.PLANT_ID = p.PLANT_ID
```

### 7.2 DT_VIBRATION_ALERTS

Generates actionable alerts from bearing health data. An alert is raised when any of these conditions are true:

```sql
WHERE BEARING_HEALTH_SCORE < 92
   OR ADR_RISK != 'Low'
   OR ANOMALY_FLAG = TRUE
   OR WORST_TEMP_STATUS = 'ALARM'
```

The threshold of 92 (rather than, say, 75) is intentionally sensitive — it catches assets that are beginning to degrade before they reach medium risk.

**Alert severity derivation** factors in asset criticality:
```sql
CASE
    WHEN BEARING_HEALTH_SCORE < 25 THEN 'CRITICAL'
    WHEN BEARING_HEALTH_SCORE < 50 OR (BEARING_HEALTH_SCORE < 75 AND CRITICALITY = 'A') THEN 'HIGH'
    WHEN BEARING_HEALTH_SCORE < 75 THEN 'MEDIUM'
    ELSE 'LOW'
END AS ALERT_SEVERITY
```

A critical-classification (A) asset with a health score of 60 is classified as HIGH rather than MEDIUM, because failure of a critical asset has higher business impact.

**Recommended action generation:**
```sql
CASE
    WHEN ADR_RISK = 'Critical' THEN 'IMMEDIATE: Stop equipment, emergency bearing inspection'
    WHEN ADR_RISK = 'High'     THEN 'URGENT: Schedule bearing replacement within 48 hours'
    WHEN WORST_TEMP_STATUS = 'ALARM' THEN 'Check lubrication, inspect bearing seals'
    WHEN ANOMALY_FLAG          THEN 'Investigate anomaly: collect FFT spectrum, check for new defects'
    ELSE 'Monitor: review trend at next scheduled round'
END AS RECOMMENDED_ACTION
```

An `IS_ACTIONABLE` boolean flags alerts that require human intervention (non-LOW severity).

### 7.3 DT_PLANT_DASHBOARD

An executive summary — 3 rows (one per plant) — aggregating data from health, OEE, tickets, and alerts:

```sql
SELECT
    p.PLANT_NAME,
    COUNT(DISTINCT bh.ASSET_ID) AS TOTAL_ASSETS,
    ROUND(AVG(bh.BEARING_HEALTH_SCORE), 1) AS AVG_HEALTH_SCORE,
    MIN(bh.BEARING_HEALTH_SCORE) AS MIN_HEALTH_SCORE,
    -- OEE average over last 30 days
    (SELECT AVG(oee.OEE) FROM ANALYTICS.DT_OEE_METRICS oee
     WHERE oee.PLANT_NAME = p.PLANT_NAME
     AND oee.RUN_DATE >= DATEADD('day', -30, CURRENT_DATE())) AS AVG_OEE_30D,
    -- Risk distribution counts
    SUM(CASE WHEN bh.ADR_RISK = 'Low' THEN 1 ELSE 0 END) AS ASSETS_LOW_RISK,
    SUM(CASE WHEN bh.ADR_RISK = 'Medium' THEN 1 ELSE 0 END) AS ASSETS_MEDIUM_RISK,
    SUM(CASE WHEN bh.ADR_RISK = 'High' THEN 1 ELSE 0 END) AS ASSETS_HIGH_RISK,
    SUM(CASE WHEN bh.ADR_RISK = 'Critical' THEN 1 ELSE 0 END) AS ASSETS_CRITICAL_RISK,
    -- Ticket and alert counts
    (SELECT COUNT(*) FROM CURATED.DT_MAINTENANCE_HISTORY mh
     WHERE mh.PLANT_NAME = p.PLANT_NAME AND mh.STATUS != 'CLOSED') AS OPEN_TICKETS,
    (SELECT COUNT(*) FROM ANALYTICS.DT_VIBRATION_ALERTS va
     WHERE va.PLANT_NAME = p.PLANT_NAME) AS ACTIVE_ALERTS,
    ...
```

This is the primary data source for the Streamlit Plant Overview page's KPI metrics and plant comparison cards.

### 7.4 DT_TICKET_ANALYTICS

Monthly aggregation of maintenance ticket data for trend analysis:

```sql
SELECT
    PLANT_NAME,
    DATE_TRUNC('month', ISSUE_OPEN_DATE) AS MONTH,
    COUNT(*) AS TOTAL_TICKETS,
    SUM(CASE WHEN STATUS = 'CLOSED' THEN 1 ELSE 0 END) AS CLOSED_TICKETS,
    SUM(CASE WHEN STATUS != 'CLOSED' THEN 1 ELSE 0 END) AS OPEN_TICKETS,
    ROUND(AVG(MTTR_HOURS), 1) AS AVG_MTTR_HOURS,
    SUM(DOWNTIME_HOURS) AS TOTAL_DOWNTIME_HOURS,
    -- Failure mode breakdown
    SUM(CASE WHEN FAILURE_MODE = 'BEARING_DEFECT' THEN 1 ELSE 0 END) AS BEARING_DEFECT_COUNT,
    SUM(CASE WHEN FAILURE_MODE = 'MISALIGNMENT' THEN 1 ELSE 0 END) AS MISALIGNMENT_COUNT,
    SUM(CASE WHEN FAILURE_MODE = 'UNBALANCE' THEN 1 ELSE 0 END) AS UNBALANCE_COUNT,
    ...
FROM CURATED.DT_MAINTENANCE_HISTORY
GROUP BY PLANT_NAME, DATE_TRUNC('month', ISSUE_OPEN_DATE)
```

This feeds the Streamlit Ticket Management page's monthly trend chart and the semantic view's ticket trend queries.

---

## 8. ML Pipeline — Bearing Failure Prediction

### 8.1 Feature Engineering

The ML pipeline (`05_ml_pipeline.sql`) creates a feature table with 25,614 rows (69 assets x 371 days, minus early rows without enough history).

**Daily aggregation from DT_SENSOR_ENRICHED:**

```sql
daily_sensor_stats AS (
    SELECT
        se.ASSET_ID, se.ASSET_NAME, se.ASSET_TYPE, se.MACHINE_CLASS, se.PLANT_ID,
        se.READING_TS::DATE AS READING_DATE,
        -- Velocity features
        AVG(se.MAX_VEL_RMS) AS AVG_MAX_VEL,
        MAX(se.MAX_VEL_RMS) AS PEAK_VEL,
        STDDEV(se.MAX_VEL_RMS) AS VEL_STDDEV,
        -- Acceleration features
        AVG(se.RSS_ACCEL) AS AVG_RSS_ACCEL,
        MAX(se.RSS_ACCEL) AS PEAK_RSS_ACCEL,
        STDDEV(se.RSS_ACCEL) AS ACCEL_STDDEV,
        -- Temperature features
        AVG(se.TEMPERATURE_C) AS AVG_TEMP,
        MAX(se.TEMPERATURE_C) AS MAX_TEMP,
        -- ISO zone fractions
        AVG(CASE WHEN se.ISO_VEL_ZONE = 'A_GOOD' THEN 1.0 ELSE 0.0 END) AS FRAC_ZONE_A,
        AVG(CASE WHEN se.ISO_VEL_ZONE = 'B_SATISFACTORY' THEN 1.0 ELSE 0.0 END) AS FRAC_ZONE_B,
        -- Z-score features
        AVG(se.VEL_ZSCORE) AS AVG_ZSCORE,
        MAX(ABS(se.VEL_ZSCORE)) AS MAX_ABS_ZSCORE,
        -- Temperature alarm fraction
        AVG(CASE WHEN se.TEMP_STATUS != 'NORMAL' THEN 1.0 ELSE 0.0 END) AS FRAC_TEMP_ALARM
    FROM CURATED.DT_SENSOR_ENRICHED se
    GROUP BY se.ASSET_ID, se.ASSET_NAME, se.ASSET_TYPE, se.MACHINE_CLASS, se.PLANT_ID,
             se.READING_TS::DATE
)
```

**The 23 features:**

| # | Feature | Description | Domain Rationale |
|---|---------|-------------|-----------------|
| 1 | `ASSET_TYPE` | Motor/Compressor/Blower/Pump/Fan | Different equipment types have different failure patterns |
| 2 | `MACHINE_CLASS` | ISO class I-IV | Larger machines tolerate more vibration |
| 3 | `AVG_MAX_VEL` | Daily avg of worst-axis velocity | Overall vibration level |
| 4 | `PEAK_VEL` | Daily peak velocity | Spike detection |
| 5 | `VEL_STDDEV` | Daily velocity standard deviation | Variability = instability |
| 6 | `AVG_RSS_ACCEL` | Daily avg RSS acceleration | High-frequency energy level |
| 7 | `PEAK_RSS_ACCEL` | Daily peak RSS acceleration | Bearing defect impulse intensity |
| 8 | `ACCEL_STDDEV` | Daily acceleration std dev | Acceleration variability |
| 9 | `AVG_TEMP` | Daily avg temperature | Thermal state |
| 10 | `MAX_TEMP` | Daily max temperature | Thermal peaks (lubrication indicator) |
| 11 | `FRAC_ZONE_A` | Fraction of readings in Zone A | How often is the machine "good"? |
| 12 | `FRAC_ZONE_B` | Fraction of readings in Zone B | How often is it "satisfactory"? |
| 13 | `AVG_ZSCORE` | Daily avg z-score | Persistent deviation from baseline |
| 14 | `MAX_ABS_ZSCORE` | Daily max absolute z-score | Worst single-reading anomaly |
| 15 | `FRAC_TEMP_ALARM` | Fraction of readings in warning/alarm | Thermal reliability |
| 16 | `VEL_7D_AVG` | 7-day rolling avg velocity | Trend context |
| 17 | `ACCEL_7D_AVG` | 7-day rolling avg acceleration | Trend context |
| 18 | `TEMP_7D_AVG` | 7-day rolling avg temperature | Trend context |
| 19 | `VEL_DELTA_7D` | Today's velocity - 7-day avg | Rising = deteriorating |
| 20 | `ACCEL_DELTA_7D` | Today's acceleration - 7-day avg | Rising = bearing degrading |
| 21 | `TEMP_DELTA_7D` | Today's temp - 7-day avg | Rising = friction/lubrication |
| 22 | `DAYS_SINCE_LAST_FAILURE` | Days since last failure on this asset | Recency of maintenance |
| 23 | `CUMULATIVE_FAILURES` | Total historical failures | Reliability indicator |

**7-day trends (deltas):**
```sql
d.AVG_MAX_VEL - AVG(d.AVG_MAX_VEL) OVER (
    PARTITION BY d.ASSET_ID ORDER BY d.READING_DATE
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS VEL_DELTA_7D
```

Positive delta means today's reading is above the 7-day average — the trend is rising. This is critical for PdM because an absolute value of 2.0 mm/s might be normal for a compressor but alarming for a fan, while a delta of +0.5 mm/s over the 7-day average is concerning for any asset.

**The labeling strategy:**
```sql
CASE WHEN EXISTS (
    SELECT 1 FROM RAW.FAILURE_INCIDENTS fi2
    WHERE fi2.ASSET_ID = wt.ASSET_ID
    AND fi2.FAILURE_TIMESTAMP::DATE BETWEEN wt.READING_DATE
        AND DATEADD('day', 7, wt.READING_DATE)
) THEN 1 ELSE 0 END AS FAILURE_WITHIN_7D
```

For each asset-day, the label is 1 if any failure incident occurs for that asset within the next 7 days. This creates a binary classification problem: "Given today's sensor features, will this asset fail within 7 days?"

**Label distribution:** ~1.36% positive rate (349 positive out of 25,614 total). This is realistic for predictive maintenance — failures are rare events. The model must handle this class imbalance.

### 8.2 Model Training

**Snowflake ML Classification** is Snowflake's built-in AutoML capability. It wraps multiple classification algorithms (XGBoost, LightGBM, etc.), performs hyperparameter tuning, and selects the best model — all with a single SQL command:

```sql
CREATE OR REPLACE SNOWFLAKE.ML.CLASSIFICATION BEARING_FAILURE_MODEL(
    INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'ML.BEARING_FAILURE_FEATURES_V'),
    TARGET_COLNAME => 'FAILURE_WITHIN_7D',
    CONFIG_OBJECT => {'ON_ERROR': 'SKIP', 'evaluate': TRUE}
);
```

`SYSTEM$REFERENCE('VIEW', ...)` points to the cleaned feature view that excludes:
- The `READING_DATE` column (DATE type — the model should learn from sensor features, not calendar dates)
- Rows with NULL standard deviation (early rows without enough history for window functions)

`'evaluate': TRUE` tells Snowflake to hold out a test set and compute evaluation metrics.

For someone from scikit-learn: this is equivalent to writing a pipeline with `StandardScaler` + `XGBClassifier` inside `RandomizedSearchCV`, plus automated feature encoding for categorical columns (`ASSET_TYPE`, `MACHINE_CLASS`).

### 8.3 Model Evaluation

The model achieves strong results:

| Metric | Failure Class (1) | No-Failure Class (0) |
|--------|-------------------|---------------------|
| Precision | 92% | 99.8% |
| Recall | 85% | 99.9% |
| F1 | 88% | 99.9% |

**In PdM context:**
- **Precision 92%:** When the model predicts failure, it is correct 92% of the time. The 8% false positive rate means ~8 out of 100 predicted failures will not actually occur. In practice, this triggers an unnecessary inspection — a minor cost compared to a missed failure.
- **Recall 85%:** The model catches 85% of actual failures. The 15% false negative rate means ~15 out of 100 actual failures will be missed. This is the more dangerous error — a missed failure could mean unplanned downtime.
- **F1 88%:** The harmonic mean of precision and recall, balancing both error types.

**Top features by importance** (from `SHOW_FEATURE_IMPORTANCE()`):
1. `VEL_STDDEV` — Velocity variability is the strongest predictor
2. `ACCEL_STDDEV` — Acceleration variability
3. `PEAK_RSS_ACCEL` — Acceleration peaks (bearing defects)
4. `MAX_ABS_ZSCORE` — Statistical anomalies
5. `VEL_DELTA_7D` — Rising velocity trend

These make domain sense: failing bearings exhibit increasing variability (stddev) before the absolute levels become alarming, and the 7-day delta captures the "getting worse" trend that precedes failure.

### 8.4 Prediction Pipeline

**Generating predictions for current assets:**
```sql
CREATE OR REPLACE TABLE ML.BEARING_PREDICTIONS AS
WITH latest_features AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ASSET_ID ORDER BY READING_DATE DESC) AS rn
    FROM ML.BEARING_FAILURE_FEATURES WHERE VEL_STDDEV IS NOT NULL
)
SELECT
    ASSET_ID, ASSET_NAME, ASSET_TYPE, PLANT_ID, READING_DATE AS PREDICTION_DATE,
    BEARING_FAILURE_MODEL!PREDICT(INPUT_DATA => {
        'ASSET_TYPE': ASSET_TYPE, 'MACHINE_CLASS': MACHINE_CLASS,
        'AVG_MAX_VEL': AVG_MAX_VEL, 'PEAK_VEL': PEAK_VEL, ...
    }) AS PREDICTION_RESULT
FROM latest_features WHERE rn = 1;
```

The `!PREDICT()` method is called on the model object with a JSON object of feature values. It returns a JSON result containing the predicted class and probabilities.

**PREDICTION_RESULT structure:**
```json
{
  "class": "0",
  "probability": {
    "0": 0.973,
    "1": 0.027
  }
}
```

**Flattened predictions view with risk tiers:**
```sql
CREATE OR REPLACE VIEW ML.BEARING_PREDICTIONS_V AS
SELECT
    bp.PREDICTION_RESULT:class::STRING AS PREDICTED_FAILURE,
    ROUND(bp.PREDICTION_RESULT:probability:"1"::FLOAT, 6) AS FAILURE_PROBABILITY,
    CASE
        WHEN bp.PREDICTION_RESULT:probability:"1"::FLOAT >= 0.75 THEN 'CRITICAL'
        WHEN bp.PREDICTION_RESULT:probability:"1"::FLOAT >= 0.50 THEN 'HIGH'
        WHEN bp.PREDICTION_RESULT:probability:"1"::FLOAT >= 0.10 THEN 'MEDIUM'
        WHEN bp.PREDICTION_RESULT:probability:"1"::FLOAT >= 0.01 THEN 'LOW'
        ELSE 'MINIMAL'
    END AS RISK_TIER,
    bh.BEARING_HEALTH_SCORE, bh.ADR_RISK,
    ...
FROM ML.BEARING_PREDICTIONS bp
JOIN RAW.PLANTS p ON bp.PLANT_ID = p.PLANT_ID
LEFT JOIN CURATED.DT_BEARING_HEALTH bh ON bp.ASSET_ID = bh.ASSET_ID;
```

The `:` syntax (e.g., `PREDICTION_RESULT:probability:"1"::FLOAT`) is Snowflake's semi-structured data access notation, equivalent to JSON path access. This is one of Snowflake's strengths — native JSON querying without needing `json_extract()` functions.

---

## 9. Semantic View — Natural Language Interface

### What Is a Semantic View

A **Semantic View** in Snowflake is a schema-level object that maps business concepts to physical database tables. It provides:
- **Column descriptions:** What each column means in business terms
- **Relationships:** How tables join to each other
- **Synonyms:** Alternative names users might use (e.g., "health" for BEARING_HEALTH_SCORE)
- **Sample values:** Example values to help the NL-to-SQL engine understand data
- **Verified queries:** Pre-validated SQL for common questions

### What Is Cortex Analyst

**Cortex Analyst** is Snowflake's LLM-powered natural language to SQL engine. Given a question like "Which assets are at risk?", it:
1. Reads the Semantic View definition to understand the data model
2. Generates a SQL query grounded in the actual table/column names
3. Executes the query against Snowflake
4. Returns the results

The Semantic View is what makes Cortex Analyst accurate — without it, the LLM would have to guess table/column names.

### The YAML Specification

The semantic view YAML (`06_semantic_view.yaml`, 503 lines) defines 6 logical tables:

**1. dt_bearing_health** — Current health status per asset
```yaml
- name: dt_bearing_health
  base_table:
    database: PREDICTIVE_MAINTENANCE
    schema: CURATED
    table: DT_BEARING_HEALTH
  dimensions:
    - name: asset_id
      synonyms: [equipment id, machine id]
    - name: asset_name
      synonyms: [equipment name, machine name, asset]
      sample_values: [MTR 510 A, COMP 520 B, PUMP 310 A]
    - name: adr_risk
      synonyms: [risk level, risk status, risk classification]
      is_enum: true
      sample_values: [Low, Medium, High, Critical]
    - name: worst_iso_zone
      synonyms: [iso zone, vibration zone, severity zone]
      is_enum: true
  facts:
    - name: bearing_health_score
      synonyms: [health score, health, score, BHS]
      description: Composite health score 0-100. Higher is healthier.
    - name: peak_vel_rms
      synonyms: [peak velocity, max velocity, vibration level]
      description: Peak RMS velocity in mm/s across all sensors for this asset
    ...
```

Key YAML features:
- `synonyms`: Tell Cortex Analyst that "health" means BEARING_HEALTH_SCORE
- `sample_values`: Help the LLM understand the data domain (e.g., asset names follow MTR/COMP/PUMP patterns)
- `is_enum`: Indicates a categorical column with a small set of values
- `description`: Business context for each column

**2-6.** Similar definitions for `dt_oee_metrics`, `dt_maintenance_history`, `dt_vibration_alerts`, `dt_plant_dashboard`, `dt_ticket_analytics`.

**Relationships between tables:**
```yaml
relationships:
  - name: health_to_oee
    left_table: dt_bearing_health
    right_table: dt_oee_metrics
    relationship_columns:
      - left_column: plant_name
        right_column: plant_name
    join_type: many_to_many
    relationship_type: complement
  - name: health_to_maintenance
    left_table: dt_bearing_health
    right_table: dt_maintenance_history
    relationship_columns:
      - left_column: asset_name
        right_column: asset_name
    join_type: one_to_many
    ...
```

**Verified Query Repository (VQR) — 7 verified queries:**

```yaml
verified_queries:
  - name: 1;1
    question: Give an overview of all plants including health scores and OEE
    sql: SELECT PLANT_NAME, TOTAL_ASSETS, AVG_HEALTH_SCORE, MIN_HEALTH_SCORE,
      ROUND(AVG_OEE_30D * 100, 1) AS OEE_PCT, OPEN_TICKETS, ACTIVE_ALERTS
      FROM dt_plant_dashboard ORDER BY AVG_HEALTH_SCORE
  - name: 2;1
    question: Which assets are most at risk of failure?
    sql: SELECT ASSET_NAME, PLANT_NAME, BEARING_HEALTH_SCORE, ADR_RISK, PEAK_VEL_RMS,
      PEAK_RSS_ACCEL, MAX_TEMPERATURE_C, WORST_ISO_ZONE
      FROM dt_bearing_health WHERE ADR_RISK IN ('High','Critical','Medium')
      ORDER BY BEARING_HEALTH_SCORE ASC
  - name: 3;1
    question: What are the active vibration alerts?
    sql: ...
  - name: 4;1
    question: What are the open maintenance tickets?
    sql: ...
  - name: 5;1
    question: Which are the 10 worst health assets?
    sql: ...
  - name: 6;1
    question: What are the maintenance ticket trends by plant and month?
    sql: ...
  - name: 7;1
    question: What are the most common failure modes and their average repair time?
    sql: ...
```

Verified queries serve two purposes: (1) they are used as few-shot examples by Cortex Analyst to improve SQL generation accuracy, and (2) they guarantee correct answers for the most common questions — if a user asks something close to a verified query, Cortex Analyst uses the pre-validated SQL rather than generating new SQL.

**Deployment:**
```sql
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
    'PREDICTIVE_MAINTENANCE.ANALYTICS.VIBRATION_MANAGEMENT',
    $$<yaml content>$$
);
```

`SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML` is a Snowflake system function that parses the YAML and creates the semantic view object. The `$$..$$` syntax is Snowflake's dollar-quoted string literal (like Postgres) for embedding multi-line strings without escaping.

**Testing:** In Snowsight (Snowflake's web UI), navigate to AI & ML > Cortex Analyst, select the semantic view, and type questions. Cortex Analyst shows the generated SQL and results side by side.

---

## 10. Cortex Agent — The Orchestrator

### What Is a Cortex Agent

A **Cortex Agent** in Snowflake is an agentic AI framework that can use tools to answer questions. Unlike Cortex Analyst (which only does NL-to-SQL), an agent can orchestrate multiple tools, maintain conversation context, and decide which tool to use for each question.

### The Agent Specification

The agent spec (`07_agent_spec.yaml`, 25 lines) defines:

```yaml
models:
  orchestration: auto

instructions:
  response: >
    You are a predictive maintenance specialist for industrial rotating equipment
    across 3 chemical/polymer/pharma plants.
    Use process-industry terminology (DE/NDE, MTR/COMP/BLWR/PUMP/FAN naming).
    When discussing vibration data, reference ISO 10816 zones.
    For maintenance recommendations, specify urgency
    (Immediate/Urgent/Scheduled/Monitor).
    Present comparative data in tables. Always ground answers in actual data.
  orchestration: >
    Use the Analyst tool for all data queries about equipment health, vibration,
    OEE, tickets, and maintenance.
    The semantic view covers: bearing health scores, ISO severity zones, OEE metrics,
    maintenance tickets, vibration alerts, and cross-plant dashboards.

tools:
  - tool_spec:
      type: cortex_analyst_text_to_sql
      name: VibrationAnalyst

tool_resources:
  VibrationAnalyst:
    semantic_view: "PREDICTIVE_MAINTENANCE.ANALYTICS.VIBRATION_MANAGEMENT"
    warehouse: "PM_WH"
```

**Key design decisions:**

- `orchestration: auto` — The agent automatically decides when to use the Analyst tool versus answering from its own knowledge.
- **One orchestrator + 1 tool** rather than multiple separate agents. The Cortex Analyst tool wraps the semantic view, giving the agent access to all 6 tables through a single NL-to-SQL interface.
- **Response instructions** embed domain expertise: ISO 10816 references, process-industry terminology, urgency classification. This ensures the agent's responses sound like a vibration specialist, not a generic chatbot.
- **Orchestration instructions** guide tool selection: "Use the Analyst tool for all data queries" prevents the agent from hallucinating data.

### Deployment

```bash
cortex agent-studio agent-deploy --file-path 07_agent_spec.yaml \
    --fqn PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER_AGENT
```

The agent is accessible via:
1. **Snowsight Agents Playground:** AI & ML > Agents > select the agent
2. **REST API:** `POST /api/v2/cortex/agent/run` with the agent FQN
3. **SQL (with limitations):** `DATA_AGENT_RUN()` function

### The Warehouse Resolution Issue

The `DATA_AGENT_RUN` SQL function has a known limitation where it may not correctly resolve the warehouse specified in the agent spec, causing queries to fail with "no active warehouse" errors. The workaround is to use the REST API or Snowsight playground, which handle warehouse resolution correctly. The Streamlit app works around this by using `Cortex Complete` directly with a RAG pattern (see Section 11.3, Page 5).

---

## 11. Streamlit Command Center — The UI

### 11.1 Deployment Model

**Streamlit-in-Snowflake (SiS)** runs Streamlit applications inside Snowflake's infrastructure:
- The Python code is uploaded to an internal stage (a file storage area within Snowflake)
- A `STREAMLIT` object references the stage and configuration
- When a user opens the app in Snowsight, Snowflake provisions a Streamlit runtime
- All data queries run within Snowflake — no network egress

**Deployment chain:**

```bash
# 1. Upload the Python file to Snowflake's stage
snow streamlit deploy --database PREDICTIVE_MAINTENANCE --schema ANALYTICS

# Or manually:
PUT file://08_streamlit_app.py @PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER_STAGE
    AUTO_COMPRESS = FALSE OVERWRITE = TRUE;

# 2. Create the Streamlit object (defined in snowflake.yml)
CREATE STREAMLIT PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER
    ROOT_LOCATION = '@PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER_STAGE'
    MAIN_FILE = '08_streamlit_app.py'
    QUERY_WAREHOUSE = PM_WH;
```

The `snowflake.yml` defines the Streamlit deployment configuration:

```yaml
definition_version: 2
entities:
  pm_command_center:
    type: streamlit
    identifier:
      name: PM_COMMAND_CENTER
    title: "Predictive Maintenance Command Center"
    query_warehouse: PM_WH
    main_file: 08_streamlit_app.py
    pages_dir: pages/
    schema: ANALYTICS
    database: PREDICTIVE_MAINTENANCE
```

**The `environment.yml`** specifies additional Python packages:

```yaml
name: sf_env
channels:
  - snowflake
dependencies:
  - plotly
```

SiS includes `streamlit`, `pandas`, `snowflake-snowpark-python` by default. We add `plotly` for interactive charts (Plotly is more powerful than Streamlit's built-in charts for multi-trace time-series).

**SiS version constraints and workarounds:**

The Streamlit version in SiS (~1.26.x) is behind open-source (~1.39+). This affects:

| Feature | Open-source API | SiS Workaround |
|---------|----------------|----------------|
| Database connection | `st.connection("snowflake")` | `get_active_session()` from `snowflake.snowpark.context` |
| Multi-page navigation | `st.navigation()` + `st.Page()` | Sidebar `st.radio()` with function dispatch |
| Chat messages | `st.chat_message()` | `st.markdown()` with bold role prefix |
| Horizontal divider | `st.divider()` | `st.markdown("---")` |
| Hide dataframe index | `hide_index=True` param | Not available; use default display |
| Rerun after state change | `st.rerun()` | `st.experimental_rerun()` |

The `get_active_session()` function is the key SiS-specific pattern — it returns a Snowpark `Session` object that is pre-authenticated with the user's Snowflake credentials. No connection strings, no credentials in code.

### 11.2 App Architecture

The app (`08_streamlit_app.py`, 709 lines) is a single-file application using a function-per-page pattern:

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark.context import get_active_session

session = get_active_session()

# Cached query helper
@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()

# Page functions
def page_plant_overview(): ...
def page_vibration_monitor(): ...
def page_alert_triage(): ...
def page_ticket_management(): ...
def page_root_cause_chat(): ...

# Navigation dispatch
PAGES = {
    "Plant Overview": page_plant_overview,
    "Vibration Monitor": page_vibration_monitor,
    "Alert Triage": page_alert_triage,
    "Ticket Management": page_ticket_management,
    "Root Cause Chat": page_root_cause_chat,
}

with st.sidebar:
    st.markdown("---")
    selected_page = st.radio("Navigation", list(PAGES.keys()), index=0, key="_nav")

PAGES[selected_page]()
```

**Cached query helper:** `@st.cache_data(ttl=300)` caches query results for 5 minutes. This prevents re-executing expensive SQL on every Streamlit rerun (which happens on every user interaction). The TTL ensures data freshness while avoiding redundant queries.

**Color constants:**
```python
RISK_COLORS = {
    "Low": "#2ecc71",      # green
    "Medium": "#f1c40f",   # yellow
    "High": "#e67e22",     # orange
    "Critical": "#e74c3c", # red
}
```

These provide consistent color coding across all pages for risk levels and alert severities.

### 11.3 Page-by-Page Walkthrough

#### Page 1: Plant Overview

**Purpose:** Executive summary across all plants.

**SQL queries:**
1. `DT_PLANT_DASHBOARD` — Fetches KPI data for selected plants
2. `DT_OEE_METRICS` — 30-day OEE trend by plant (aggregated daily)

**Visualizations:**
- **KPI Row:** 5 metrics — Total Assets, Avg Health Score, Avg OEE (30d), Open Tickets, Active Alerts
- **Plant Comparison Cards:** 3-column layout with per-plant health score, OEE, ticket count, alert count, and a color-coded risk callout
- **Asset Risk Distribution:** Stacked bar chart showing Low/Medium/High/Critical asset counts per plant (Plotly Express)
- **OEE Trend:** Multi-line chart of daily OEE by plant over 30 days (Plotly Express)

**User interaction:** Multi-select plant filter in the sidebar. Selecting/deselecting plants updates all visualizations.

#### Page 2: Vibration Monitor

**Purpose:** Deep dive into a single asset's vibration data.

**SQL queries:**
1. `DT_BEARING_HEALTH` — Asset types for selected plant (for cascading filter)
2. `DT_BEARING_HEALTH` — Asset names for selected type
3. `DT_BEARING_HEALTH` — Current health metrics for selected asset
4. `DT_SENSOR_ENRICHED` — 7-day time-series for selected asset (LIMIT 5000)
5. `DT_SENSOR_ENRICHED` — Latest reading per sensor (using `QUALIFY ROW_NUMBER()`)

**Visualizations:**
- **Health Metrics Row:** Health Score, ADR Risk (color-coded), ISO Zone, Anomaly Detected
- **Measurement Row:** Peak Velocity RMS (mm/s), Peak RSS Accel (g), Max Temperature (C)
- **3-Axis Vibration Trend:** Plotly Go Figure with three traces (X=blue, Y=green, Z=red) showing velocity RMS over 7 days
- **Temperature Trend:** Single-line chart of temperature over 7 days
- **Sensor Table:** Dataframe showing latest reading per sensor (DE and NDE) with all measurements

**User interaction:** Cascading selectboxes: Plant -> Asset Type -> Asset. Changing any filter updates all downstream data.

The `LIMIT 5000` on the time-series query is a performance workaround — without it, querying 7 days x 2 sensors x 24 hours/day = ~336 rows per asset, which is fine. But the LIMIT prevents runaway queries if the filter somehow selects too many assets.

#### Page 3: Alert Triage

**Purpose:** Actionable view of current vibration alerts.

**SQL queries:**
1. `DT_VIBRATION_ALERTS` — All alerts for selected plants, optionally filtered to actionable only
2. `DT_VIBRATION_ALERTS` — Count of actionable alerts

**Visualizations:**
- **Actionable Alerts Metric:** Single number showing how many alerts need attention
- **Alert Cards:** Each alert is an `st.expander` with:
  - Header: severity (color-coded) + asset name + plant name
  - Body: Health Score, Peak Velocity, Peak Accel, Max Temp as metrics
  - Recommended Action text
  - Caption with asset type, group, criticality, ADR risk, last reading time
  - CRITICAL and HIGH alerts are auto-expanded

**User interaction:** Multi-select plant filter + "Actionable only" checkbox. The checkbox filters to `IS_ACTIONABLE = TRUE`, hiding informational/low-severity alerts.

#### Page 4: Ticket Management

**Purpose:** Maintenance ticket tracking and trend analysis.

**SQL queries:**
1. `DT_MAINTENANCE_HISTORY` — Tickets filtered by plant, status, severity
2. `DT_MAINTENANCE_HISTORY` — Summary metrics (total, open, avg MTTR, total downtime)
3. `DT_TICKET_ANALYTICS` — Monthly trend data

**Visualizations:**
- **Summary Metrics Row:** Total Tickets, Open, Avg MTTR (hrs), Total Downtime (hrs)
- **Ticket Table:** Dataframe with key columns (ID, asset, plant, failure mode, severity, status, downtime, MTTR, assigned to, age)
- **Two-Column Chart Row:**
  - Left: **Failure Mode Pie Chart** — Plotly pie showing ticket distribution by failure mode
  - Right: **Monthly Ticket Trend** — Plotly Go Figure with three lines (Total, Closed, Open) over months

**User interaction:** Plant multi-select + Status selectbox (All/OPEN/IN_PROGRESS/CLOSED/ACKNOWLEDGED) + Severity selectbox (All/CRITICAL/HIGH/MEDIUM/LOW).

#### Page 5: Root Cause Chat

**Purpose:** Natural language Q&A about maintenance data.

**Implementation Pattern: RAG (Retrieval-Augmented Generation)**

Due to the `DATA_AGENT_RUN` warehouse resolution issue (see Section 10), the chat page uses a RAG pattern instead of calling the Cortex Agent directly:

1. **Retrieve:** Query real data from multiple tables as context
2. **Augment:** Build a prompt with the data + user question
3. **Generate:** Call `Cortex Complete` (LLM inference) with the augmented prompt

```python
from snowflake.cortex import Complete

# Step 1: Retrieve context
context_df = session.sql("""
    SELECT 'PLANT_DASHBOARD' AS SOURCE, TO_VARCHAR(OBJECT_CONSTRUCT(*)) AS DATA
    FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_PLANT_DASHBOARD
    UNION ALL
    SELECT 'BEARING_HEALTH', TO_VARCHAR(OBJECT_CONSTRUCT(*))
    FROM PREDICTIVE_MAINTENANCE.CURATED.DT_BEARING_HEALTH
    ORDER BY SOURCE
""").to_pandas()

# Also retrieve open tickets and failure mode statistics
tickets_df = session.sql("SELECT ... FROM DT_MAINTENANCE_HISTORY WHERE STATUS != 'CLOSED'").to_pandas()
failure_df = session.sql("SELECT FAILURE_MODE, COUNT(*) ... GROUP BY FAILURE_MODE").to_pandas()

# Step 2: Build augmented prompt
context_str = ""
for _, row in context_df.iterrows():
    context_str += f"\n[{row['SOURCE']}]: {row['DATA']}"
for _, row in tickets_df.iterrows():
    context_str += f"\n[OPEN_TICKET]: {row.to_json()}"
for _, row in failure_df.iterrows():
    context_str += f"\n[FAILURE_STATS]: {row.to_json()}"

prompt = f"""You are a predictive maintenance specialist...
DATA CONTEXT:
{context_str}

USER QUESTION: {query_to_process}

Answer the question based on the data above. Use tables where appropriate."""

# Step 3: Generate response
response_text = Complete("mistral-large2", prompt, session=session)
```

`OBJECT_CONSTRUCT(*)` is a Snowflake function that converts a row to a JSON object — every column becomes a key-value pair. This is used to serialize table data into the LLM prompt.

`Complete("mistral-large2", prompt, session=session)` calls the Mistral Large 2 LLM hosted within Snowflake's Cortex AI service. The model runs inside Snowflake — no data leaves the platform.

**Conversation history** is maintained in `st.session_state.chat_history` (a list of dicts with `role` and `content` keys). Each exchange is rendered with `st.markdown()` using bold role prefixes.

**Sample question buttons** provide quick-start prompts for common queries.

---

## 12. Automation & Notifications

### Email Notification Integration

```sql
CREATE OR REPLACE NOTIFICATION INTEGRATION PM_EMAIL_NOTIFICATIONS
    TYPE = EMAIL
    ENABLED = TRUE
    ALLOWED_RECIPIENTS = (
        'rajesh.patel@atul.co.in',
        'shaishav.desai@atul.co.in',
        ...
        'machpulse@forbesmarshall.com'
    )
    COMMENT = 'Email notifications for vibration alerts and maintenance tickets';
```

A **Notification Integration** in Snowflake is an account-level object that enables sending emails via `SYSTEM$SEND_EMAIL()`. The `ALLOWED_RECIPIENTS` list is a security control — only listed email addresses can receive emails. This prevents accidental spam or data exfiltration via email.

### The 4 Scheduled Tasks

**Task 1: Daily Health Report (7 AM IST)**
```sql
CREATE OR REPLACE TASK DAILY_HEALTH_REPORT
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON 0 7 * * * Asia/Kolkata'
AS
CALL SYSTEM$SEND_EMAIL(
    'PM_EMAIL_NOTIFICATIONS',
    'machpulse@forbesmarshall.com',
    'Daily Equipment Health Report',
    (SELECT LISTAGG(
        PLANT_NAME || ': ' || TOTAL_ASSETS || ' assets | Avg Health: ' || AVG_HEALTH_SCORE ||
        ' | OEE: ' || ROUND(AVG_OEE_30D * 100, 1) || '% | Open Tickets: ' || OPEN_TICKETS ||
        ' | Active Alerts: ' || ACTIVE_ALERTS,
        '\n'
    ) FROM ANALYTICS.DT_PLANT_DASHBOARD ORDER BY PLANT_NAME)
);
```

**Task 2: Weekly OEE Summary (Monday 8 AM IST)**
```sql
CREATE OR REPLACE TASK WEEKLY_OEE_SUMMARY
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON 0 8 * * 1 Asia/Kolkata'
AS
CALL SYSTEM$SEND_EMAIL(
    'PM_EMAIL_NOTIFICATIONS',
    'machpulse@forbesmarshall.com',
    'Weekly OEE Performance Summary',
    (SELECT LISTAGG(...) FROM ANALYTICS.DT_OEE_METRICS
     WHERE RUN_DATE >= DATEADD('day', -7, CURRENT_DATE())
     GROUP BY PLANT_NAME, PRODUCTION_LINE ...)
);
```

**Task 3: Auto-Ticket from ML Predictions (6 AM IST daily)**
```sql
CREATE OR REPLACE TASK AUTO_TICKET_FROM_PREDICTIONS
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON 0 6 * * * Asia/Kolkata'
AS
INSERT INTO RAW.TICKETS (...)
SELECT
    'TK-AUTO-' || TO_CHAR(CURRENT_TIMESTAMP(), 'YYYYMMDD') || '-' || ASSET_ID,
    ASSET_ID,
    CURRENT_TIMESTAMP(),
    CASE
        WHEN FAILURE_PROBABILITY >= 0.75 THEN 'CRITICAL'
        WHEN FAILURE_PROBABILITY >= 0.50 THEN 'HIGH'
        ELSE 'MEDIUM'
    END,
    'OPEN',
    'ML-predicted bearing failure within 7 days...',
    'USR-013',  -- MachPulse System
    'Auto-generated from ML prediction. Failure probability: ' || ROUND(FAILURE_PROBABILITY * 100, 1) || '%',
    BEARING_HEALTH_SCORE
FROM ML.BEARING_PREDICTIONS_V
WHERE FAILURE_PROBABILITY >= 0.10
AND ASSET_ID NOT IN (SELECT ASSET_ID FROM RAW.TICKETS WHERE STATUS != 'CLOSED');
```

This is the automation loop: ML model predicts failure -> task creates a ticket -> Dynamic Tables propagate it through the pipeline -> it appears in the Streamlit Ticket Management page and Alert Triage page.

The `WHERE ASSET_ID NOT IN (SELECT ... WHERE STATUS != 'CLOSED')` clause prevents duplicate tickets — if an asset already has an open ticket, a new one is not created.

**Task 4: Critical Alert Monitor (every 30 minutes)**

Uses a `WHEN SYSTEM$STREAM_HAS_DATA('ALERT_STREAM')` condition to only fire when new critical alerts appear (stream-triggered, not time-triggered). This is an event-driven pattern.

### CRON Schedule Syntax in Snowflake

Snowflake CRON syntax: `'USING CRON <minute> <hour> <day_of_month> <month> <day_of_week> <timezone>'`

- `0 7 * * * Asia/Kolkata` = 7:00 AM IST daily
- `0 8 * * 1 Asia/Kolkata` = 8:00 AM IST on Mondays
- `0 6 * * * Asia/Kolkata` = 6:00 AM IST daily
- `*/30 * * * * Asia/Kolkata` = Every 30 minutes

### Why Tasks Are Created Suspended

All tasks are created suspended (the default) for safety. In a hackathon environment:
- You do not want email tasks firing immediately upon creation
- You do not want auto-ticket creation running before data is verified
- You resume tasks explicitly when ready: `ALTER TASK DAILY_HEALTH_REPORT RESUME;`

---

## 13. File Inventory

| File | Purpose | Lines | Execution Order |
|------|---------|-------|-----------------|
| `01_setup.sql` | Database, schemas, warehouse creation | 43 | 1st |
| `02_synthetic_data.sql` | All 12 RAW tables with synthetic data | 860 | 2nd |
| `03_dynamic_tables_silver.sql` | Silver-layer Dynamic Tables (DT_SENSOR_ENRICHED, DT_BEARING_HEALTH, DT_MAINTENANCE_HISTORY) | ~150* | 3rd |
| `04_dynamic_tables_gold.sql` | Gold-layer Dynamic Tables (DT_OEE_METRICS, DT_VIBRATION_ALERTS, DT_PLANT_DASHBOARD, DT_TICKET_ANALYTICS) | ~200* | 4th |
| `05_ml_pipeline.sql` | Feature engineering, model training, predictions | 108 | 5th |
| `06_semantic_view.yaml` | Semantic View definition (6 tables, 7 VQRs) | 503 | 6th |
| `07_agent_spec.yaml` | Cortex Agent specification | 25 | 7th |
| `07_cortex_agent.sql` | Agent deployment verification | 13 | 7th |
| `08_streamlit_app.py` | 5-page Streamlit Command Center | 709 | 8th |
| `09_automation.sql` | Notification integration + 4 tasks | 140 | 9th |
| `12_demo_queries.sql` | 6 demo scenarios for presentation | 134 | Demo |
| `environment.yml` | SiS Python dependencies (plotly) | 6 | 8th (deploy) |
| `snowflake.yml` | Streamlit deployment config | 13 | 8th (deploy) |
| `PROGRESS.md` | Implementation progress tracker | 186 | Reference |
| `TECHNICAL_WALKTHROUGH.md` | This document | ~3500 | Reference |

*Files 03 and 04 were executed directly during development sessions and may not exist as separate files in the directory. The Dynamic Table definitions are captured in the PROGRESS.md and are reflected in the live Snowflake objects.

---

## 14. How to Run / Reproduce

### Prerequisites

- A Snowflake account with ACCOUNTADMIN role (or equivalent privileges for creating databases, warehouses, and notification integrations)
- Snowflake CLI (`snow`) installed for Streamlit deployment
- CoCo (Cortex Code) for agent deployment

### Step-by-Step

**Step 1: Setup (01_setup.sql)**
```sql
-- Run in Snowsight or via snow sql
-- Creates: PREDICTIVE_MAINTENANCE database, RAW/CURATED/ANALYTICS/ML schemas, PM_WH warehouse
```

**Step 2: Synthetic Data (02_synthetic_data.sql)**
```sql
-- Run in Snowsight (takes ~2-5 minutes for SENSOR_READINGS generation on XS warehouse)
-- Creates: 12 tables with 1.2M+ total rows
-- Verify: run the verification counts at the bottom of the file
```

**Step 3-4: Dynamic Tables (03/04 SQL files)**
```sql
-- Run Silver layer DTs, then Gold layer DTs
-- Dynamic Tables begin refreshing automatically after creation
-- Wait 1-2 minutes for initial refresh, then verify with:
SELECT COUNT(*) FROM CURATED.DT_SENSOR_ENRICHED;    -- expect 1,212,192
SELECT COUNT(*) FROM CURATED.DT_BEARING_HEALTH;     -- expect 69
SELECT COUNT(*) FROM ANALYTICS.DT_PLANT_DASHBOARD;  -- expect 3
```

**Step 5: ML Pipeline (05_ml_pipeline.sql)**
```sql
-- Run feature engineering (CREATE TABLE ... AS SELECT) — takes ~1-2 minutes
-- Run model training (CREATE SNOWFLAKE.ML.CLASSIFICATION) — takes ~3-5 minutes
-- Run prediction generation — takes ~30 seconds
-- Verify:
CALL ML.BEARING_FAILURE_MODEL!SHOW_EVALUATION_METRICS();
SELECT * FROM ML.BEARING_PREDICTIONS_V ORDER BY FAILURE_PROBABILITY DESC LIMIT 10;
```

**Step 6: Semantic View (06_semantic_view.yaml)**
```sql
-- Deploy via Snowsight or CoCo:
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
    'PREDICTIVE_MAINTENANCE.ANALYTICS.VIBRATION_MANAGEMENT',
    $$<paste YAML content here>$$
);

-- Test in Snowsight: AI & ML > Cortex Analyst > select VIBRATION_MANAGEMENT
-- Try: "Which assets are most at risk?"
```

**Step 7: Cortex Agent (07_agent_spec.yaml)**
```bash
# Deploy via CoCo:
cortex agent-studio agent-deploy \
    --file-path 07_agent_spec.yaml \
    --fqn PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER_AGENT

# Test in Snowsight: AI & ML > Agents > PM_COMMAND_CENTER_AGENT
# Try: "Give me an overview of all plants"
```

**Step 8: Streamlit App (08_streamlit_app.py)**
```bash
# Deploy via snow CLI:
snow streamlit deploy \
    --database PREDICTIVE_MAINTENANCE \
    --schema ANALYTICS

# Or open in Snowsight: Streamlit > PM_COMMAND_CENTER
```

**Step 9: Automation (09_automation.sql)**
```sql
-- Run to create notification integration and tasks (all created suspended)
-- Resume when ready:
ALTER TASK PREDICTIVE_MAINTENANCE.ANALYTICS.DAILY_HEALTH_REPORT RESUME;
ALTER TASK PREDICTIVE_MAINTENANCE.ANALYTICS.WEEKLY_OEE_SUMMARY RESUME;
ALTER TASK PREDICTIVE_MAINTENANCE.ANALYTICS.AUTO_TICKET_FROM_PREDICTIONS RESUME;
```

**Step 10: Verify Everything**
```sql
-- Run 12_demo_queries.sql scenarios to validate the full stack
-- Check system stats:
SELECT 'RAW.PLANTS' AS TBL, COUNT(*) AS ROWS FROM RAW.PLANTS
UNION ALL SELECT 'RAW.ASSETS', COUNT(*) FROM RAW.ASSETS
UNION ALL SELECT 'RAW.SENSOR_READINGS', COUNT(*) FROM RAW.SENSOR_READINGS
UNION ALL SELECT 'CURATED.DT_SENSOR_ENRICHED', COUNT(*) FROM CURATED.DT_SENSOR_ENRICHED
UNION ALL SELECT 'CURATED.DT_BEARING_HEALTH', COUNT(*) FROM CURATED.DT_BEARING_HEALTH
UNION ALL SELECT 'ANALYTICS.DT_OEE_METRICS', COUNT(*) FROM ANALYTICS.DT_OEE_METRICS
UNION ALL SELECT 'ANALYTICS.DT_PLANT_DASHBOARD', COUNT(*) FROM ANALYTICS.DT_PLANT_DASHBOARD
UNION ALL SELECT 'ML.BEARING_FAILURE_FEATURES', COUNT(*) FROM ML.BEARING_FAILURE_FEATURES
ORDER BY 1;
```

---

## 15. Known Issues & Workarounds

### Agent Warehouse Resolution with DATA_AGENT_RUN

**Issue:** The `DATA_AGENT_RUN()` SQL function (for calling Cortex Agents from SQL) does not always correctly resolve the warehouse specified in the agent spec. This results in "no active warehouse" errors.

**Workaround:** Use the Cortex Agents REST API or the Snowsight Agents playground instead of the SQL function. For the Streamlit app, the Root Cause Chat page uses a RAG pattern with `Cortex Complete` instead of calling the agent directly.

### SiS Streamlit Version Constraints

**Issue:** Streamlit-in-Snowflake runs an older version (~1.26.x) that lacks many features available in open-source Streamlit 1.39+.

**Workaround:** See the compatibility table in Section 11.1. Key substitutions:
- `get_active_session()` instead of `st.connection("snowflake")`
- `st.radio()` dispatch instead of `st.navigation()`/`st.Page()`
- `st.experimental_rerun()` instead of `st.rerun()`
- `st.markdown("---")` instead of `st.divider()`

### Dynamic Table FULL Refresh Mode

**Issue:** The Dynamic Tables in this project use FULL refresh mode (recompute all rows on each refresh) rather than INCREMENTAL (only process changes). This is because the complex window functions (rolling averages, z-scores, ROW_NUMBER) and multi-table joins require recomputation.

**Impact:** Each refresh of `DT_SENSOR_ENRICHED` processes all 1.2M rows. On an XS warehouse, this takes ~30-60 seconds. In production with larger data volumes, this would need a larger warehouse or an incremental design.

**Mitigation:** The `TARGET_LAG` setting controls refresh frequency. Setting `DOWNSTREAM` means the table only refreshes when a downstream consumer needs it, reducing unnecessary compute.

### Sensor Readings Query Performance

**Issue:** `DT_SENSOR_ENRICHED` has 1.2M rows. Querying it for time-series visualization without proper filtering could be slow.

**Workaround:** The Streamlit app applies multiple filters:
1. `WHERE ASSET_ID = '{asset_id}'` — narrows to 1 asset (~17,568 rows)
2. `AND READING_TS >= DATEADD('day', -7, ...)` — narrows to 7 days (~336 rows)
3. `LIMIT 5000` — safety cap

### SQL Injection in Streamlit

**Issue:** The Streamlit app uses f-string SQL construction (e.g., `f"WHERE PLANT_NAME IN ({plant_list_sql})"`) which could be vulnerable to SQL injection if user input is not sanitized.

**Mitigation:** In SiS, the selectbox/multiselect values come from Snowflake query results (not free-text user input), so the injection risk is limited to the chat input (which is used as an LLM prompt, not directly in SQL). In production, parameterized queries should be used.

---

## 16. What Would Change in Production

### Real Sensor Data Ingestion

Replace synthetic data with real-time sensor streams:
- **Snowpipe Streaming:** For high-throughput, low-latency ingestion from IoT gateways
- **Kafka connector:** For integration with existing message bus infrastructure
- **REST API ingestion:** For BLE-to-cloud gateways that batch sensor readings

The RAW schema structure would remain the same — `SENSOR_READINGS` would be the landing table, and Dynamic Tables would propagate changes automatically.

### Real-Time Alerting with Streams + Tasks

Instead of relying on Dynamic Table refresh lag:
- Create a **stream** on `DT_VIBRATION_ALERTS` to capture new/changed alerts
- Create a **task** triggered by `SYSTEM$STREAM_HAS_DATA()` to send immediate notifications
- The Critical Alert Monitor task (`CRITICAL_ALERT_MONITOR`) already demonstrates this pattern

### Role-Based Access Control (RBAC)

```sql
-- Production roles
CREATE ROLE PM_ADMIN;        -- full access
CREATE ROLE PM_PLANT_MANAGER; -- read all data for their plant
CREATE ROLE PM_ENGINEER;      -- read + write tickets for their plant
CREATE ROLE PM_ANALYST;       -- read sensor data + run reports
CREATE ROLE PM_OPERATOR;      -- read dashboards only

-- Row-level security via secure views
CREATE SECURE VIEW CURATED.MY_PLANT_HEALTH AS
SELECT * FROM CURATED.DT_BEARING_HEALTH
WHERE PLANT_ID = (SELECT PLANT_ID FROM RAW.USERS WHERE EMAIL = CURRENT_USER());
```

### Model Retraining Schedule

The ML model should be retrained periodically as new failure data accumulates:
- Create a task that runs monthly to rebuild `BEARING_FAILURE_FEATURES`
- Retrain the model with the expanded dataset
- Compare new model metrics against the current model
- Swap the model reference if the new model outperforms

### CI/CD with snow CLI

```bash
# snow CLI enables deployment automation:
snow sql -f 01_setup.sql
snow sql -f 02_synthetic_data.sql
snow streamlit deploy --replace
snow cortex agent-deploy ...
```

This can be integrated into GitHub Actions or similar CI/CD pipelines for version-controlled, repeatable deployments.

### Additional Production Considerations

- **Data retention policies:** Archive sensor readings older than 2 years to cold storage
- **Monitoring:** Set up Snowflake Resource Monitors to cap warehouse spend
- **Backup:** Snowflake provides Time Travel (up to 90 days) and Fail-safe (7 days) automatically
- **Multi-region:** For global deployments, use Snowflake's replication to replicate the database across regions
- **API layer:** Expose ML predictions and alert data via Snowflake's REST API for integration with CMMS (Computerized Maintenance Management System) platforms like SAP PM, Maximo, or eMaint

---

*This document was generated as the definitive technical reference for the Predictive Maintenance & OEE Command Center hackathon project. For questions or clarifications, refer to the source files in the project directory or query the deployed Cortex Agent via Snowsight.*

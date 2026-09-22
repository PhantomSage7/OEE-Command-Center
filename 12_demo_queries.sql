-- ============================================================================
-- Demo Queries — Predictive Maintenance & OEE Command Center
-- Run these during the hackathon demo to showcase the system
-- ============================================================================

USE WAREHOUSE PM_WH;
USE DATABASE PREDICTIVE_MAINTENANCE;

-- ============================================================================
-- DEMO SCENARIO 1: Cross-Plant Overview
-- ============================================================================

-- "Give me a snapshot of all 3 plants"
SELECT PLANT_NAME, TOTAL_ASSETS, AVG_HEALTH_SCORE, MIN_HEALTH_SCORE,
       ROUND(AVG_OEE_30D * 100, 1) AS OEE_PCT,
       OPEN_TICKETS, ACTIVE_ALERTS, CRITICAL_ALERTS
FROM ANALYTICS.DT_PLANT_DASHBOARD
ORDER BY AVG_HEALTH_SCORE;

-- "Which assets have the worst health scores?"
SELECT ASSET_NAME, PLANT_NAME, ASSET_TYPE, BEARING_HEALTH_SCORE, ADR_RISK,
       PEAK_VEL_RMS, PEAK_RSS_ACCEL, MAX_TEMPERATURE_C, WORST_ISO_ZONE
FROM CURATED.DT_BEARING_HEALTH
ORDER BY BEARING_HEALTH_SCORE ASC
LIMIT 10;

-- ============================================================================
-- DEMO SCENARIO 2: Bearing Degradation Story (COMP 520 B)
-- ============================================================================

-- "Show me COMP 520 B vibration trend over the last 2 weeks"
SELECT READING_TS, ASSET_NAME, SENSOR_LABEL, MOUNT_POSITION,
       X_VEL_RMS, Y_VEL_RMS, Z_VEL_RMS, MAX_VEL_RMS,
       X_ACCEL_RMS, Y_ACCEL_RMS, Z_ACCEL_RMS, RSS_ACCEL,
       TEMPERATURE_C, ISO_VEL_ZONE
FROM CURATED.DT_SENSOR_ENRICHED
WHERE ASSET_NAME = 'COMP 520 B'
AND READING_TS >= DATEADD('day', -14, CURRENT_TIMESTAMP())
ORDER BY READING_TS;

-- "What's the current health status of COMP 520 B?"
SELECT * FROM CURATED.DT_BEARING_HEALTH WHERE ASSET_NAME = 'COMP 520 B';

-- "Is there an alert for COMP 520 B?"
SELECT * FROM ANALYTICS.DT_VIBRATION_ALERTS WHERE ASSET_NAME = 'COMP 520 B';

-- "What does the ML model predict for COMP 520 B?"
SELECT * FROM ML.BEARING_PREDICTIONS_V WHERE ASSET_NAME = 'COMP 520 B';

-- ============================================================================
-- DEMO SCENARIO 3: OEE Deep Dive
-- ============================================================================

-- "Compare OEE across plants for the last 30 days"
SELECT PLANT_NAME, PRODUCTION_LINE,
       ROUND(AVG(OEE) * 100, 1) AS AVG_OEE,
       ROUND(AVG(AVAILABILITY) * 100, 1) AS AVG_AVAIL,
       ROUND(AVG(PERFORMANCE) * 100, 1) AS AVG_PERF,
       ROUND(AVG(QUALITY) * 100, 1) AS AVG_QUAL,
       ROUND(SUM(UNPLANNED_DOWNTIME_MIN), 0) AS TOTAL_UNPLANNED_DT_MIN
FROM ANALYTICS.DT_OEE_METRICS
WHERE RUN_DATE >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY PLANT_NAME, PRODUCTION_LINE
ORDER BY AVG_OEE;

-- "Show OEE trend by day for last 30 days"
SELECT RUN_DATE, PLANT_NAME, ROUND(AVG(OEE) * 100, 1) AS DAILY_OEE
FROM ANALYTICS.DT_OEE_METRICS
WHERE RUN_DATE >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY RUN_DATE, PLANT_NAME
ORDER BY RUN_DATE;

-- ============================================================================
-- DEMO SCENARIO 4: Failure Mode Analysis
-- ============================================================================

-- "What are the most common failure modes?"
SELECT FAILURE_MODE,
       COUNT(*) AS INCIDENT_COUNT,
       ROUND(AVG(MTTR_HOURS), 1) AS AVG_MTTR,
       ROUND(SUM(DOWNTIME_HOURS), 0) AS TOTAL_DOWNTIME_HRS,
       ROUND(AVG(HEALTH_IMPROVEMENT), 0) AS AVG_HEALTH_IMPROVEMENT
FROM CURATED.DT_MAINTENANCE_HISTORY
WHERE FAILURE_MODE IS NOT NULL
GROUP BY FAILURE_MODE
ORDER BY INCIDENT_COUNT DESC;

-- "Show me open tickets"
SELECT TICKET_ID, ASSET_NAME, PLANT_NAME, SEVERITY, STATUS,
       ISSUE_OPEN_DATE, CORRECTIVE_ACTIONS_REC, TICKET_AGE_DAYS
FROM CURATED.DT_MAINTENANCE_HISTORY
WHERE STATUS != 'CLOSED'
ORDER BY
  CASE SEVERITY WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
  ISSUE_OPEN_DATE;

-- ============================================================================
-- DEMO SCENARIO 5: ML Model Performance
-- ============================================================================

-- "Show ML model evaluation metrics"
CALL ML.BEARING_FAILURE_MODEL!SHOW_EVALUATION_METRICS();

-- "What are the top predictive features?"
CALL ML.BEARING_FAILURE_MODEL!SHOW_FEATURE_IMPORTANCE();

-- ============================================================================
-- DEMO SCENARIO 6: Cortex Agent (test via SQL)
-- Note: Agent works best via Snowsight playground or REST API
-- ============================================================================

-- Test semantic view directly
-- cortex analyst query "Which assets are at risk?" --view PREDICTIVE_MAINTENANCE.ANALYTICS.VIBRATION_MANAGEMENT

-- ============================================================================
-- SYSTEM STATS
-- ============================================================================
SELECT 'RAW.PLANTS' AS TBL, COUNT(*) AS ROWS FROM RAW.PLANTS
UNION ALL SELECT 'RAW.ASSETS', COUNT(*) FROM RAW.ASSETS
UNION ALL SELECT 'RAW.SENSORS', COUNT(*) FROM RAW.SENSORS
UNION ALL SELECT 'RAW.SENSOR_READINGS', COUNT(*) FROM RAW.SENSOR_READINGS
UNION ALL SELECT 'RAW.FAILURE_INCIDENTS', COUNT(*) FROM RAW.FAILURE_INCIDENTS
UNION ALL SELECT 'RAW.TICKETS', COUNT(*) FROM RAW.TICKETS
UNION ALL SELECT 'RAW.ERP_PRODUCTION_RUNS', COUNT(*) FROM RAW.ERP_PRODUCTION_RUNS
UNION ALL SELECT 'CURATED.DT_SENSOR_ENRICHED', COUNT(*) FROM CURATED.DT_SENSOR_ENRICHED
UNION ALL SELECT 'CURATED.DT_BEARING_HEALTH', COUNT(*) FROM CURATED.DT_BEARING_HEALTH
UNION ALL SELECT 'CURATED.DT_MAINTENANCE_HISTORY', COUNT(*) FROM CURATED.DT_MAINTENANCE_HISTORY
UNION ALL SELECT 'ANALYTICS.DT_OEE_METRICS', COUNT(*) FROM ANALYTICS.DT_OEE_METRICS
UNION ALL SELECT 'ANALYTICS.DT_VIBRATION_ALERTS', COUNT(*) FROM ANALYTICS.DT_VIBRATION_ALERTS
UNION ALL SELECT 'ANALYTICS.DT_PLANT_DASHBOARD', COUNT(*) FROM ANALYTICS.DT_PLANT_DASHBOARD
UNION ALL SELECT 'ANALYTICS.DT_TICKET_ANALYTICS', COUNT(*) FROM ANALYTICS.DT_TICKET_ANALYTICS
UNION ALL SELECT 'ML.BEARING_FAILURE_FEATURES', COUNT(*) FROM ML.BEARING_FAILURE_FEATURES
ORDER BY 1;

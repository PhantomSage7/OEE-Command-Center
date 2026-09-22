-- ============================================================================
-- Phase 9: Automation — Streams, Tasks, Alerts, Notifications
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE PM_WH;
USE DATABASE PREDICTIVE_MAINTENANCE;
USE SCHEMA ANALYTICS;

-- ============================================================================
-- 9.1  Email Notification Integration
-- ============================================================================
CREATE OR REPLACE NOTIFICATION INTEGRATION PM_EMAIL_NOTIFICATIONS
    TYPE = EMAIL
    ENABLED = TRUE
    ALLOWED_RECIPIENTS = (
        'rajesh.patel@atul.co.in',
        'shaishav.desai@atul.co.in',
        'meera.wagh@atul.co.in',
        'priya.mehta@vapi-polymers.com',
        'suresh.reddy@vapi-polymers.com',
        'kiran.joshi@vapi-polymers.com',
        'anita.sharma@ankl-pharma.com',
        'vijay.nair@ankl-pharma.com',
        'rohit.gupta@ankl-pharma.com',
        'machpulse@forbesmarshall.com'
    )
    COMMENT = 'Email notifications for vibration alerts and maintenance tickets';

-- ============================================================================
-- 9.2  Daily Health Report Task
-- ============================================================================
CREATE OR REPLACE TASK DAILY_HEALTH_REPORT
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON 0 7 * * * Asia/Kolkata'  -- 7 AM IST daily
    COMMENT = 'Daily equipment health summary report sent via email'
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

-- ============================================================================
-- 9.3  Critical Alert Monitoring Task
-- ============================================================================
CREATE OR REPLACE TASK CRITICAL_ALERT_MONITOR
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON */30 * * * * Asia/Kolkata'  -- Every 30 minutes
    COMMENT = 'Monitors for critical vibration alerts and sends immediate notifications'
    WHEN SYSTEM$STREAM_HAS_DATA('ALERT_STREAM')
AS
CALL SYSTEM$SEND_EMAIL(
    'PM_EMAIL_NOTIFICATIONS',
    'machpulse@forbesmarshall.com',
    'CRITICAL: Vibration Alert Detected',
    (SELECT LISTAGG(
        'Asset: ' || ASSET_NAME || ' | Plant: ' || PLANT_NAME ||
        ' | Health: ' || BEARING_HEALTH_SCORE || ' | Severity: ' || ALERT_SEVERITY ||
        ' | Action: ' || RECOMMENDED_ACTION,
        '\n'
    ) FROM ANALYTICS.DT_VIBRATION_ALERTS WHERE IS_ACTIONABLE = TRUE)
);

-- ============================================================================
-- 9.4  Weekly OEE Summary Task
-- ============================================================================
CREATE OR REPLACE TASK WEEKLY_OEE_SUMMARY
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON 0 8 * * 1 Asia/Kolkata'  -- Monday 8 AM IST
    COMMENT = 'Weekly OEE performance summary by plant and production line'
AS
CALL SYSTEM$SEND_EMAIL(
    'PM_EMAIL_NOTIFICATIONS',
    'machpulse@forbesmarshall.com',
    'Weekly OEE Performance Summary',
    (SELECT LISTAGG(
        PLANT_NAME || ' | ' || PRODUCTION_LINE || ' | Avg OEE: ' || ROUND(AVG(OEE) * 100, 1) || '%' ||
        ' | Availability: ' || ROUND(AVG(AVAILABILITY) * 100, 1) || '%' ||
        ' | Performance: ' || ROUND(AVG(PERFORMANCE) * 100, 1) || '%' ||
        ' | Quality: ' || ROUND(AVG(QUALITY) * 100, 1) || '%',
        '\n'
    ) FROM ANALYTICS.DT_OEE_METRICS
    WHERE RUN_DATE >= DATEADD('day', -7, CURRENT_DATE())
    GROUP BY PLANT_NAME, PRODUCTION_LINE
    ORDER BY PLANT_NAME, PRODUCTION_LINE)
);

-- ============================================================================
-- 9.5  Auto-Ticket Creation Task (from ML predictions)
-- ============================================================================
CREATE OR REPLACE TASK AUTO_TICKET_FROM_PREDICTIONS
    WAREHOUSE = PM_WH
    SCHEDULE = 'USING CRON 0 6 * * * Asia/Kolkata'  -- 6 AM IST daily
    COMMENT = 'Auto-creates maintenance tickets when ML model predicts bearing failure'
AS
INSERT INTO RAW.TICKETS (
    TICKET_ID, ASSET_ID, ISSUE_OPEN_DATE, SEVERITY, STATUS,
    CORRECTIVE_ACTIONS_REC, OPENED_BY, COMMENTS, PRE_REPAIR_HEALTH_SCORE
)
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
    'ML-predicted bearing failure within 7 days. Recommend immediate inspection and vibration analysis.',
    'USR-013',  -- MachPulse System
    'Auto-generated from ML prediction. Failure probability: ' || ROUND(FAILURE_PROBABILITY * 100, 1) || '%',
    BEARING_HEALTH_SCORE
FROM ML.BEARING_PREDICTIONS_V
WHERE FAILURE_PROBABILITY >= 0.10
AND ASSET_ID NOT IN (
    SELECT ASSET_ID FROM RAW.TICKETS WHERE STATUS != 'CLOSED'
);

-- ============================================================================
-- 9.6  Resume tasks (they start suspended by default)
-- ============================================================================
-- Uncomment to activate:
-- ALTER TASK DAILY_HEALTH_REPORT RESUME;
-- ALTER TASK WEEKLY_OEE_SUMMARY RESUME;
-- ALTER TASK AUTO_TICKET_FROM_PREDICTIONS RESUME;
-- ALTER TASK CRITICAL_ALERT_MONITOR RESUME;

-- ============================================================================
-- Verify
-- ============================================================================
SHOW TASKS IN SCHEMA ANALYTICS;

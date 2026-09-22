-- ============================================================================
-- Phase 1: Database, Schemas, and Warehouse Setup
-- Predictive Maintenance & OEE Command Center
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- Create dedicated warehouse
CREATE WAREHOUSE IF NOT EXISTS PM_WH
    WAREHOUSE_SIZE = 'XSMALL'
    WAREHOUSE_TYPE = 'STANDARD'
    AUTO_SUSPEND = 120
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = FALSE
    COMMENT = 'Predictive Maintenance workloads';

USE WAREHOUSE PM_WH;

-- Create database
CREATE DATABASE IF NOT EXISTS PREDICTIVE_MAINTENANCE
    COMMENT = 'Predictive Maintenance & OEE Command Center - Multi-plant vibration management';

USE DATABASE PREDICTIVE_MAINTENANCE;

-- RAW schema: landing zone for sensor streams, ERP data, maintenance records
CREATE SCHEMA IF NOT EXISTS RAW
    COMMENT = 'Bronze layer - raw ingested data from sensors, ERP, and maintenance systems';

-- CURATED schema: cleaned, enriched, joined data
CREATE SCHEMA IF NOT EXISTS CURATED
    COMMENT = 'Silver layer - enriched sensor data, health scores, equipment status';

-- ANALYTICS schema: aggregated metrics, alerts, dashboards
CREATE SCHEMA IF NOT EXISTS ANALYTICS
    COMMENT = 'Gold layer - OEE metrics, vibration alerts, plant dashboards, ticket analytics';

-- ML schema: model training data, predictions, model registry
CREATE SCHEMA IF NOT EXISTS ML
    COMMENT = 'ML layer - failure features, bearing predictions, model registry';

-- Verify
SHOW SCHEMAS IN DATABASE PREDICTIVE_MAINTENANCE;

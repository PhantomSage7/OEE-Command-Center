-- ============================================================================
-- Phase 7: Cortex Agent — PM Command Center
-- Deploy via: cortex agent-studio agent-deploy --file-path 07_agent_spec.yaml
--             --fqn PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER_AGENT
-- ============================================================================
-- Note: The agent is created and deployed. Test via Snowsight Agents playground
-- or Cortex Agents REST API. The DATA_AGENT_RUN SQL function may not resolve
-- the warehouse correctly; use the REST API or Streamlit for testing.

-- Verify agent exists:
DESCRIBE AGENT PREDICTIVE_MAINTENANCE.ANALYTICS.PM_COMMAND_CENTER_AGENT;
SHOW AGENTS IN SCHEMA PREDICTIVE_MAINTENANCE.ANALYTICS;

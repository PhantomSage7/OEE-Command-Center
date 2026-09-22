import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from snowflake.snowpark.context import get_active_session

st.set_page_config(
    layout="wide",
    page_title="PM Command Center",
    page_icon="⚙️",
)

session = get_active_session()

RISK_COLORS = {
    "Low": "#2ecc71",
    "Medium": "#f1c40f",
    "High": "#e67e22",
    "Critical": "#e74c3c",
}
SEVERITY_COLORS = {
    "CRITICAL": "#e74c3c",
    "HIGH": "#e67e22",
    "MEDIUM": "#f1c40f",
    "LOW": "#2ecc71",
}
OEE_LINE_COLORS = px.colors.qualitative.Set2


@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


# ─── Sidebar: global plant filter ────────────────────────────────────────────
def get_plants() -> pd.DataFrame:
    return run_query(
        "SELECT PLANT_ID, PLANT_NAME FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_PLANT_DASHBOARD ORDER BY PLANT_NAME"
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Plant Overview
# ═════════════════════════════════════════════════════════════════════════════
def page_plant_overview():
    st.title("Predictive Maintenance Command Center")

    plants_df = get_plants()
    with st.sidebar:
        st.header("Filters")
        selected_plants = st.multiselect(
            "Plant",
            options=plants_df["PLANT_NAME"].tolist(),
            default=plants_df["PLANT_NAME"].tolist(),
            key="overview_plants",
        )

    if not selected_plants:
        st.warning("Select at least one plant.")
        return

    plant_list_sql = ", ".join(f"'{p}'" for p in selected_plants)

    dashboard_df = run_query(
        f"""
        SELECT * FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_PLANT_DASHBOARD
        WHERE PLANT_NAME IN ({plant_list_sql})
        ORDER BY PLANT_NAME
        """
    )

    if dashboard_df.empty:
        st.info("No data for selected plants.")
        return

    # ── KPI row ──
    total_assets = int(dashboard_df["TOTAL_ASSETS"].sum())
    avg_health = float(dashboard_df["AVG_HEALTH_SCORE"].mean())
    avg_oee = float(dashboard_df["AVG_OEE_30D"].mean())
    open_tickets = int(dashboard_df["OPEN_TICKETS"].sum())
    active_alerts = int(dashboard_df["ACTIVE_ALERTS"].sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Assets", f"{total_assets:,}")
    c2.metric("Avg Health Score", f"{avg_health:.1f}")
    c3.metric("Avg OEE (30d)", f"{avg_oee:.1%}")
    c4.metric("Open Tickets", f"{open_tickets:,}")
    c5.metric("Active Alerts", f"{active_alerts:,}")

    st.markdown("---")

    # ── Plant comparison cards ──
    st.subheader("Plant Comparison")
    cols = st.columns(min(len(dashboard_df), 3))
    for i, row in dashboard_df.iterrows():
        col = cols[i % 3]
        with col:
            st.markdown(f"### {row['PLANT_NAME']}")
            m1, m2 = st.columns(2)
            m1.metric("Health Score", f"{row['AVG_HEALTH_SCORE']:.1f}")
            m2.metric("OEE (30d)", f"{row['AVG_OEE_30D']:.1%}")
            m3, m4 = st.columns(2)
            m3.metric("Open Tickets", int(row["OPEN_TICKETS"]))
            m4.metric("Active Alerts", int(row["ACTIVE_ALERTS"]))
            critical = int(row["ASSETS_CRITICAL_RISK"])
            high = int(row["ASSETS_HIGH_RISK"])
            if critical > 0:
                st.error(f"{critical} critical-risk assets")
            elif high > 0:
                st.warning(f"{high} high-risk assets")
            else:
                st.success("All assets nominal")

    st.markdown("---")

    # ── Asset risk distribution ──
    st.subheader("Asset Health Distribution by Plant")
    risk_data = []
    for _, row in dashboard_df.iterrows():
        for level in ["Low", "Medium", "High", "Critical"]:
            risk_data.append(
                {
                    "Plant": row["PLANT_NAME"],
                    "Risk Level": level,
                    "Count": int(row[f"ASSETS_{level.upper()}_RISK"]),
                }
            )
    risk_df = pd.DataFrame(risk_data)
    fig_risk = px.bar(
        risk_df,
        x="Plant",
        y="Count",
        color="Risk Level",
        barmode="stack",
        color_discrete_map=RISK_COLORS,
        title="Asset Risk Distribution",
    )
    fig_risk.update_layout(legend_traceorder="normal")
    st.plotly_chart(fig_risk, use_container_width=True)

    # ── OEE trend ──
    st.subheader("OEE Trend (Last 30 Days)")
    oee_df = run_query(
        f"""
        SELECT RUN_DATE, PLANT_NAME, AVG(OEE) AS AVG_OEE
        FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_OEE_METRICS
        WHERE PLANT_NAME IN ({plant_list_sql})
          AND RUN_DATE >= DATEADD('day', -30, CURRENT_DATE())
        GROUP BY RUN_DATE, PLANT_NAME
        ORDER BY RUN_DATE
        """
    )
    if not oee_df.empty:
        fig_oee = px.line(
            oee_df,
            x="RUN_DATE",
            y="AVG_OEE",
            color="PLANT_NAME",
            title="Daily Average OEE by Plant",
            labels={"AVG_OEE": "OEE", "RUN_DATE": "Date", "PLANT_NAME": "Plant"},
            color_discrete_sequence=OEE_LINE_COLORS,
        )
        fig_oee.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_oee, use_container_width=True)
    else:
        st.info("No OEE data for the selected period.")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Vibration Monitor
# ═════════════════════════════════════════════════════════════════════════════
def page_vibration_monitor():
    st.title("Vibration Monitor")

    plants_df = get_plants()
    with st.sidebar:
        st.header("Filters")
        plant_pick = st.selectbox(
            "Plant", plants_df["PLANT_NAME"].tolist(), key="vib_plant"
        )

    asset_types_df = run_query(
        f"""
        SELECT DISTINCT ASSET_TYPE
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_BEARING_HEALTH
        WHERE PLANT_NAME = '{plant_pick}'
        ORDER BY ASSET_TYPE
        """
    )
    with st.sidebar:
        asset_type_pick = st.selectbox(
            "Asset Type",
            asset_types_df["ASSET_TYPE"].tolist() if not asset_types_df.empty else [],
            key="vib_asset_type",
        )

    if not asset_type_pick:
        st.info("No asset types found for this plant.")
        return

    assets_df = run_query(
        f"""
        SELECT DISTINCT ASSET_ID, ASSET_NAME
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_BEARING_HEALTH
        WHERE PLANT_NAME = '{plant_pick}' AND ASSET_TYPE = '{asset_type_pick}'
        ORDER BY ASSET_NAME
        """
    )
    with st.sidebar:
        asset_pick = st.selectbox(
            "Asset",
            options=assets_df["ASSET_NAME"].tolist() if not assets_df.empty else [],
            key="vib_asset",
        )

    if not asset_pick:
        st.info("No assets found.")
        return

    asset_id = assets_df.loc[assets_df["ASSET_NAME"] == asset_pick, "ASSET_ID"].iloc[0]

    # ── Current health ──
    health_df = run_query(
        f"""
        SELECT BEARING_HEALTH_SCORE, ADR_RISK, WORST_ISO_ZONE, PEAK_VEL_RMS,
               PEAK_RSS_ACCEL, MAX_TEMPERATURE_C, WORST_TEMP_STATUS, ANOMALY_FLAG
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_BEARING_HEALTH
        WHERE ASSET_ID = '{asset_id}'
        LIMIT 1
        """
    )
    if health_df.empty:
        st.warning("No health data for this asset.")
        return

    h = health_df.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Health Score", f"{h['BEARING_HEALTH_SCORE']:.1f}")
    risk = h["ADR_RISK"]
    risk_color = RISK_COLORS.get(risk, "#95a5a6")
    c2.markdown(
        f"**ADR Risk**<br><span style='color:{risk_color}; font-size:1.4em; font-weight:bold'>{risk}</span>",
        unsafe_allow_html=True,
    )
    c3.metric("ISO Zone", h["WORST_ISO_ZONE"])
    anomaly_label = "Yes" if h["ANOMALY_FLAG"] else "No"
    c4.metric("Anomaly Detected", anomaly_label)

    m1, m2, m3 = st.columns(3)
    m1.metric("Peak Velocity RMS", f"{h['PEAK_VEL_RMS']:.2f} mm/s")
    m2.metric("Peak RSS Accel", f"{h['PEAK_RSS_ACCEL']:.2f} g")
    m3.metric("Max Temperature", f"{h['MAX_TEMPERATURE_C']:.1f} °C")

    st.markdown("---")

    # ── Vibration time-series (7 days, sampled for performance) ──
    st.subheader("3-Axis Vibration Trend (Last 7 Days)")
    vib_df = run_query(
        f"""
        SELECT READING_TS, X_VEL_RMS, Y_VEL_RMS, Z_VEL_RMS, TEMPERATURE_C
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_SENSOR_ENRICHED
        WHERE ASSET_ID = '{asset_id}'
          AND READING_TS >= DATEADD('day', -7, CURRENT_TIMESTAMP())
        ORDER BY READING_TS
        LIMIT 5000
        """
    )
    if not vib_df.empty:
        fig_vib = go.Figure()
        fig_vib.add_trace(
            go.Scatter(
                x=vib_df["READING_TS"],
                y=vib_df["X_VEL_RMS"],
                mode="lines",
                name="X-Axis",
                line=dict(color="#3498db"),
            )
        )
        fig_vib.add_trace(
            go.Scatter(
                x=vib_df["READING_TS"],
                y=vib_df["Y_VEL_RMS"],
                mode="lines",
                name="Y-Axis",
                line=dict(color="#2ecc71"),
            )
        )
        fig_vib.add_trace(
            go.Scatter(
                x=vib_df["READING_TS"],
                y=vib_df["Z_VEL_RMS"],
                mode="lines",
                name="Z-Axis",
                line=dict(color="#e74c3c"),
            )
        )
        fig_vib.update_layout(
            title="Velocity RMS by Axis",
            xaxis_title="Time",
            yaxis_title="Velocity RMS (mm/s)",
            hovermode="x unified",
        )
        st.plotly_chart(fig_vib, use_container_width=True)

        # ── Temperature trend ──
        st.subheader("Temperature Trend (Last 7 Days)")
        fig_temp = px.line(
            vib_df,
            x="READING_TS",
            y="TEMPERATURE_C",
            title="Bearing Temperature",
            labels={"READING_TS": "Time", "TEMPERATURE_C": "Temperature (°C)"},
        )
        fig_temp.update_traces(line_color="#e67e22")
        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.info("No sensor readings found for the last 7 days.")

    # ── Sensor table ──
    st.subheader("Sensor Latest Readings")
    sensor_df = run_query(
        f"""
        SELECT SENSOR_ID, SENSOR_LABEL, MOUNT_LOCATION, MOUNT_POSITION,
               X_VEL_RMS, Y_VEL_RMS, Z_VEL_RMS, X_ACCEL_RMS, Y_ACCEL_RMS,
               Z_ACCEL_RMS, TEMPERATURE_C, ISO_VEL_ZONE, TEMP_STATUS, READING_TS
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_SENSOR_ENRICHED
        WHERE ASSET_ID = '{asset_id}'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY SENSOR_ID ORDER BY READING_TS DESC) = 1
        ORDER BY SENSOR_LABEL
        """
    )
    if not sensor_df.empty:
        st.dataframe(sensor_df, use_container_width=True)
    else:
        st.info("No sensor data available.")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Alert Triage
# ═════════════════════════════════════════════════════════════════════════════
def page_alert_triage():
    st.title("Alert Triage")

    plants_df = get_plants()
    with st.sidebar:
        st.header("Filters")
        selected_plants = st.multiselect(
            "Plant",
            options=plants_df["PLANT_NAME"].tolist(),
            default=plants_df["PLANT_NAME"].tolist(),
            key="alert_plants",
        )
        show_actionable_only = st.checkbox("Actionable only", value=True, key="alert_actionable")

    if not selected_plants:
        st.warning("Select at least one plant.")
        return

    plant_list_sql = ", ".join(f"'{p}'" for p in selected_plants)
    actionable_clause = "AND IS_ACTIONABLE = TRUE" if show_actionable_only else ""

    alerts_df = run_query(
        f"""
        SELECT ASSET_ID, ASSET_NAME, ASSET_TYPE, PLANT_NAME, GROUP_NAME,
               CRITICALITY, BEARING_HEALTH_SCORE, ADR_RISK, ALERT_SEVERITY,
               PEAK_VEL_RMS, PEAK_RSS_ACCEL, MAX_TEMPERATURE_C,
               RECOMMENDED_ACTION, IS_ACTIONABLE, LAST_READING_TS
        FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_VIBRATION_ALERTS
        WHERE PLANT_NAME IN ({plant_list_sql})
          {actionable_clause}
        ORDER BY
            CASE ALERT_SEVERITY
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
                ELSE 5
            END,
            BEARING_HEALTH_SCORE ASC
        LIMIT 500
        """
    )

    actionable_count = int(
        run_query(
            f"""
            SELECT COUNT(*) AS CNT
            FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_VIBRATION_ALERTS
            WHERE PLANT_NAME IN ({plant_list_sql}) AND IS_ACTIONABLE = TRUE
            """
        ).iloc[0]["CNT"]
    )

    st.metric("Actionable Alerts", actionable_count)
    st.markdown("---")

    if alerts_df.empty:
        st.success("No alerts matching current filters.")
        return

    for _, alert in alerts_df.iterrows():
        sev = alert["ALERT_SEVERITY"]
        color = SEVERITY_COLORS.get(sev, "#95a5a6")
        header = f":{color}[**{sev}**] — {alert['ASSET_NAME']} ({alert['PLANT_NAME']})"

        with st.expander(header, expanded=(sev in ("CRITICAL", "HIGH"))):
            ac1, ac2, ac3, ac4 = st.columns(4)
            ac1.metric("Health Score", f"{alert['BEARING_HEALTH_SCORE']:.1f}")
            ac2.metric("Peak Velocity", f"{alert['PEAK_VEL_RMS']:.2f} mm/s")
            ac3.metric("Peak Accel", f"{alert['PEAK_RSS_ACCEL']:.2f} g")
            ac4.metric("Max Temp", f"{alert['MAX_TEMPERATURE_C']:.1f} °C")

            st.markdown(f"**Recommended Action:** {alert['RECOMMENDED_ACTION']}")
            st.caption(
                f"Asset Type: {alert['ASSET_TYPE']} | Group: {alert['GROUP_NAME']} | "
                f"Criticality: {alert['CRITICALITY']} | ADR Risk: {alert['ADR_RISK']} | "
                f"Last Reading: {alert['LAST_READING_TS']}"
            )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Ticket Management
# ═════════════════════════════════════════════════════════════════════════════
def page_ticket_management():
    st.title("Ticket Management")

    plants_df = get_plants()
    with st.sidebar:
        st.header("Filters")
        selected_plants = st.multiselect(
            "Plant",
            options=plants_df["PLANT_NAME"].tolist(),
            default=plants_df["PLANT_NAME"].tolist(),
            key="ticket_plants",
        )
        status_options = ["All", "OPEN", "IN_PROGRESS", "CLOSED", "ACKNOWLEDGED"]
        selected_status = st.selectbox("Status", status_options, key="ticket_status")
        severity_options = ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
        selected_severity = st.selectbox("Severity", severity_options, key="ticket_severity")

    if not selected_plants:
        st.warning("Select at least one plant.")
        return

    plant_list_sql = ", ".join(f"'{p}'" for p in selected_plants)
    status_clause = f"AND STATUS = '{selected_status}'" if selected_status != "All" else ""
    severity_clause = f"AND SEVERITY = '{selected_severity}'" if selected_severity != "All" else ""

    tickets_df = run_query(
        f"""
        SELECT TICKET_ID, ASSET_NAME, ASSET_TYPE, PLANT_NAME, GROUP_NAME,
               FAILURE_MODE, ROOT_CAUSE, SEVERITY, STATUS,
               DOWNTIME_HOURS, MTTR_HOURS, ISSUE_OPEN_DATE, ISSUE_CLOSURE_DATE,
               ASSIGNED_TO_NAME, CORRECTIVE_ACTIONS_REC, CORRECTIVE_ACTIONS_TAKEN,
               PRE_REPAIR_HEALTH_SCORE, POST_REPAIR_HEALTH_SCORE, HEALTH_IMPROVEMENT,
               TICKET_AGE_DAYS
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_MAINTENANCE_HISTORY
        WHERE PLANT_NAME IN ({plant_list_sql})
          {status_clause}
          {severity_clause}
        ORDER BY ISSUE_OPEN_DATE DESC
        LIMIT 500
        """
    )

    # ── Summary metrics ──
    summary_df = run_query(
        f"""
        SELECT COUNT(*) AS TOTAL_TICKETS,
               SUM(CASE WHEN STATUS != 'CLOSED' THEN 1 ELSE 0 END) AS OPEN_COUNT,
               AVG(MTTR_HOURS) AS AVG_MTTR,
               SUM(DOWNTIME_HOURS) AS TOTAL_DOWNTIME
        FROM PREDICTIVE_MAINTENANCE.CURATED.DT_MAINTENANCE_HISTORY
        WHERE PLANT_NAME IN ({plant_list_sql})
          {status_clause}
          {severity_clause}
        """
    )
    s = summary_df.iloc[0]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Tickets", int(s["TOTAL_TICKETS"]))
    k2.metric("Open", int(s["OPEN_COUNT"]))
    k3.metric("Avg MTTR", f"{s['AVG_MTTR']:.1f} hrs" if pd.notna(s["AVG_MTTR"]) else "N/A")
    k4.metric(
        "Total Downtime",
        f"{s['TOTAL_DOWNTIME']:.0f} hrs" if pd.notna(s["TOTAL_DOWNTIME"]) else "N/A",
    )

    st.markdown("---")

    # ── Ticket table ──
    st.subheader("Tickets")
    if not tickets_df.empty:
        display_cols = [
            "TICKET_ID", "ASSET_NAME", "PLANT_NAME", "FAILURE_MODE",
            "SEVERITY", "STATUS", "DOWNTIME_HOURS", "MTTR_HOURS",
            "ASSIGNED_TO_NAME", "ISSUE_OPEN_DATE", "TICKET_AGE_DAYS",
        ]
        st.dataframe(
            tickets_df[display_cols],
            use_container_width=True,
        )
    else:
        st.info("No tickets match the current filters.")

    st.markdown("---")

    # ── Charts side by side ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Failure Mode Distribution")
        if not tickets_df.empty:
            mode_counts = (
                tickets_df.groupby("FAILURE_MODE")
                .size()
                .reset_index(name="Count")
                .sort_values("Count", ascending=False)
            )
            fig_pie = px.pie(
                mode_counts,
                names="FAILURE_MODE",
                values="Count",
                title="Tickets by Failure Mode",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("Monthly Ticket Trend")
        trend_df = run_query(
            f"""
            SELECT MONTH, TOTAL_TICKETS, CLOSED_TICKETS, OPEN_TICKETS,
                   AVG_MTTR_HOURS, TOTAL_DOWNTIME_HOURS
            FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_TICKET_ANALYTICS
            WHERE PLANT_NAME IN ({plant_list_sql})
            ORDER BY MONTH
            """
        )
        if not trend_df.empty:
            agg_trend = (
                trend_df.groupby("MONTH")
                .agg({"TOTAL_TICKETS": "sum", "CLOSED_TICKETS": "sum", "OPEN_TICKETS": "sum"})
                .reset_index()
            )
            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=agg_trend["MONTH"],
                    y=agg_trend["TOTAL_TICKETS"],
                    mode="lines+markers",
                    name="Total",
                    line=dict(color="#3498db"),
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=agg_trend["MONTH"],
                    y=agg_trend["CLOSED_TICKETS"],
                    mode="lines+markers",
                    name="Closed",
                    line=dict(color="#2ecc71"),
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=agg_trend["MONTH"],
                    y=agg_trend["OPEN_TICKETS"],
                    mode="lines+markers",
                    name="Open",
                    line=dict(color="#e74c3c"),
                )
            )
            fig_trend.update_layout(
                title="Ticket Volume by Month",
                xaxis_title="Month",
                yaxis_title="Tickets",
                hovermode="x unified",
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No trend data available.")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Root Cause Chat
# ═════════════════════════════════════════════════════════════════════════════
def page_root_cause_chat():
    st.title("Root Cause Analysis Chat")
    st.caption("Powered by Cortex Agent — ask questions about maintenance, failures, and asset health.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    sample_questions = [
        "Which assets have the worst health scores?",
        "What are the most common failure modes?",
        "Show the average MTTR across all plants",
        "Which plant has the most open tickets?",
        "Give me an overview of all plants",
    ]
    st.markdown("**Try a sample question:**")
    sample_cols = st.columns(len(sample_questions))
    for i, q in enumerate(sample_questions):
        if sample_cols[i].button(q, key=f"sample_{i}", use_container_width=True):
            st.session_state["_pending_query"] = q

    st.markdown("---")

    # Render conversation history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Assistant:** {msg['content']}")

    # Input area
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input("Ask about maintenance, failures, or asset health...", key="_chat_input")
    with col_btn:
        send_clicked = st.button("Send", use_container_width=True)

    query_to_process = None
    if send_clicked and user_input:
        query_to_process = user_input
    elif st.session_state.get("_pending_query"):
        query_to_process = st.session_state.pop("_pending_query")

    if query_to_process:
        st.session_state.chat_history.append({"role": "user", "content": query_to_process})

        with st.spinner("Thinking..."):
            try:
                from snowflake.cortex import Complete

                # Build context from the semantic view data
                context_df = session.sql("""
                    SELECT 'PLANT_DASHBOARD' AS SOURCE, TO_VARCHAR(OBJECT_CONSTRUCT(*)) AS DATA
                    FROM PREDICTIVE_MAINTENANCE.ANALYTICS.DT_PLANT_DASHBOARD
                    UNION ALL
                    SELECT 'BEARING_HEALTH', TO_VARCHAR(OBJECT_CONSTRUCT(*))
                    FROM PREDICTIVE_MAINTENANCE.CURATED.DT_BEARING_HEALTH
                    ORDER BY SOURCE
                """).to_pandas()

                context_str = ""
                for _, row in context_df.iterrows():
                    context_str += f"\n[{row['SOURCE']}]: {row['DATA']}"

                # Also get open tickets
                tickets_df = session.sql("""
                    SELECT TICKET_ID, ASSET_NAME, PLANT_NAME, SEVERITY, STATUS,
                           FAILURE_MODE, CORRECTIVE_ACTIONS_REC, MTTR_HOURS, DOWNTIME_HOURS
                    FROM PREDICTIVE_MAINTENANCE.CURATED.DT_MAINTENANCE_HISTORY
                    WHERE STATUS != 'CLOSED'
                """).to_pandas()
                for _, row in tickets_df.iterrows():
                    context_str += f"\n[OPEN_TICKET]: {row.to_json()}"

                # Get failure mode stats
                failure_df = session.sql("""
                    SELECT FAILURE_MODE, COUNT(*) AS CNT, ROUND(AVG(MTTR_HOURS),1) AS AVG_MTTR,
                           ROUND(SUM(DOWNTIME_HOURS),0) AS TOTAL_DT
                    FROM PREDICTIVE_MAINTENANCE.CURATED.DT_MAINTENANCE_HISTORY
                    WHERE FAILURE_MODE IS NOT NULL GROUP BY FAILURE_MODE ORDER BY CNT DESC
                """).to_pandas()
                for _, row in failure_df.iterrows():
                    context_str += f"\n[FAILURE_STATS]: {row.to_json()}"

                prompt = f"""You are a predictive maintenance specialist for industrial rotating equipment.
You have data from 3 plants with motors, compressors, blowers, pumps, and fans.
Use ISO 10816 vibration severity standards. Be concise and data-driven.

DATA CONTEXT:
{context_str}

USER QUESTION: {query_to_process}

Answer the question based on the data above. Use tables where appropriate."""

                response_text = Complete("mistral-large2", prompt, session=session)

            except Exception as e:
                response_text = f"Error: {e}"

        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.experimental_rerun()


# ═════════════════════════════════════════════════════════════════════════════
# Navigation
# ═════════════════════════════════════════════════════════════════════════════
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

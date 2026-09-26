# =====================================================================
#  PM COMMAND CENTER  ·  Streamlit in Snowflake (SiS)
#  Predictive maintenance / vibration / OEE command console
# ---------------------------------------------------------------------
#  SiS-specific UI notes:
#   * No external @import (Google Fonts). Uses system font stacks.
#   * do_rerun() prefers st.rerun() with a safe fallback.
#   * No st.column_config, st.chat_input, st.chat_message, st.tabs,
#     hide_index, label_visibility, or gap= on st.columns.
#   * Plotly modebar is disabled for a cleaner console look.
# =====================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from snowflake.snowpark.context import get_active_session

APP_NAME = "PM COMMAND CENTER"
APP_TAG = "PREDICTIVE MAINTENANCE &amp; OEE"
DB = "PREDICTIVE_MAINTENANCE"
CORTEX_MODEL = "llama3.1-70b"

st.set_page_config(
    page_title="PM Command Center",
    page_icon="",
    layout="wide",
)

session = get_active_session()

# ── Design tokens ──
BG = "#0A0E14"
PANEL = "#121821"
PANEL2 = "#18202B"
BORDER = "#232D3B"
ACCENT = "#3B82F6"
TEAL = "#14B8A6"
TEXT = "#E6EDF5"
MUTED = "#8A98AB"
NUMERIC = "#F3F7FB"
GREEN = "#22C55E"
YELLOW = "#EAB308"
ORANGE = "#F97316"
RED = "#EF4444"
CYAN = "#06B6D4"
PURPLE = "#8B5CF6"
GRID = "rgba(138,152,171,0.10)"

FONT = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, "Cascadia Mono", Consolas, "Liberation Mono", monospace'

CHART_COLORS = [ACCENT, TEAL, ORANGE, PURPLE, CYAN, YELLOW]
RISK_COLORS = {"LOW_RISK": GREEN, "MEDIUM_RISK": YELLOW, "HIGH_RISK": ORANGE, "CRITICAL_RISK": RED}
RISK_DISPLAY = {"LOW_RISK": "Low", "MEDIUM_RISK": "Medium", "HIGH_RISK": "High", "CRITICAL_RISK": "Critical"}
SEVERITY_COLORS = {"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": YELLOW, "LOW": GREEN}
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

PLOTLY_CFG = {"displayModeBar": False, "responsive": True}

ISO_A_B, ISO_B_C, ISO_C_D = 2.8, 7.1, 18.0


# ═══════════════════════════════════════════════════════════════════════
# SMALL UTILITIES
# ═══════════════════════════════════════════════════════════════════════
def do_rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if fn:
        fn()


def sql_str(value):
    return "'" + str(value).replace("'", "''") + "'"


def sql_in(values):
    return ", ".join(sql_str(v) for v in values)


def now_stamp():
    return datetime.now().strftime("%d %b %Y  %H:%M:%S")


def initials(name):
    parts = [p for p in str(name).split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def health_color(score):
    try:
        score = float(score)
    except (TypeError, ValueError):
        return MUTED
    if score >= 90:
        return GREEN
    if score >= 75:
        return YELLOW
    if score >= 50:
        return ORANGE
    return RED


def oee_color(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return MUTED
    if value >= 0.85:
        return GREEN
    if value >= 0.65:
        return YELLOW
    return RED


def fmt_num(value, decimals=1):
    if value is None or pd.isna(value):
        return "—"
    return format(float(value), "." + str(decimals) + "f")


def safe_text(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return '<span style="color:' + MUTED + ';">Not recorded</span>'
    return str(value).replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def short_plant(name):
    text = str(name)
    if " - " in text:
        text = text.split(" - ")[-1]
    return text[:18]


# ═══════════════════════════════════════════════════════════════════════
# STYLE SHEET
# ═══════════════════════════════════════════════════════════════════════
CSS_TOKENS = """
:root{
  --bg:#0A0E14; --panel:#111827; --panel2:#1A2233; --border:#1F2937; --border2:#2D3A4D;
  --accent:#3B82F6; --teal:#14B8A6; --text:#E2E8F0; --muted:#8494A7; --num:#F1F5F9;
  --green:#22C55E; --yellow:#EAB308; --orange:#F97316; --red:#EF4444;
  --cyan:#06B6D4; --purple:#8B5CF6;
  --font:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,"Cascadia Mono",Consolas,monospace;
  --r:6px; --r-sm:4px;
}
"""

CSS_COMMON = """
.stApp{background:var(--bg);}
html,body{font-family:var(--font);}
.block-container{padding:0 1.4rem 2rem 1.4rem!important;max-width:100%;}
h1,h2,h3,h4,h5,h6,p,span,div,label,li,td,th{font-family:var(--font);color:var(--text);}
a{color:var(--accent);text-decoration:none;}
#MainMenu,footer,header{visibility:hidden!important;height:0!important;min-height:0!important;padding:0!important;margin:0!important;}
header[data-testid="stHeader"]{display:none!important;}
[data-testid="stAppViewBlockContainer"]{padding-top:0!important;}
[data-testid="stToolbar"]{display:none!important;}

.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{
  background:var(--panel2);color:var(--text);border:1px solid var(--border2);
  border-radius:var(--r-sm);font-family:var(--font);font-size:.76rem;font-weight:600;
  letter-spacing:.05em;padding:.5rem .85rem;transition:all .14s ease;box-shadow:none;}
.stButton>button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover{
  background:rgba(59,130,246,.14);border-color:var(--accent);color:#fff;}
label[data-testid="stWidgetLabel"] p{font-size:.67rem;font-weight:600;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);margin-bottom:.15rem;}
.stTextInput input,.stNumberInput input,.stTextArea textarea{
  background:var(--panel2)!important;color:var(--text)!important;border:1px solid var(--border)!important;
  border-radius:var(--r-sm)!important;font-family:var(--font)!important;font-size:.84rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--accent)!important;
  box-shadow:0 0 0 3px rgba(59,130,246,.16)!important;}
div[data-baseweb="select"]>div{background:var(--panel2)!important;border-color:var(--border)!important;
  border-radius:var(--r-sm)!important;font-size:.84rem;}
span[data-baseweb="tag"]{background:rgba(59,130,246,.18)!important;border:1px solid rgba(59,130,246,.35)!important;
  color:#DBEAFE!important;border-radius:var(--r-sm)!important;}
[data-testid="stCheckbox"] p{font-size:.78rem;color:var(--text);text-transform:none;letter-spacing:0;}
hr{border-color:var(--border);}
"""

CSS_APP = """
.topbar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  background:linear-gradient(90deg,var(--panel) 0%,var(--panel) 55%,#141D29 100%);
  border:1px solid var(--border);border-radius:var(--r);padding:.5rem .85rem;margin-bottom:.8rem;}
.tb-mark{width:30px;height:30px;border-radius:8px;flex:none;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,var(--teal),var(--accent));color:#05121D;font-weight:800;font-size:.68rem;letter-spacing:-.02em;}
.tb-title{font-size:.8rem;font-weight:700;letter-spacing:.15em;color:var(--text);line-height:1.1;}
.tb-sub{font-size:.57rem;font-weight:600;letter-spacing:.14em;color:var(--muted);margin-top:2px;}
.tb-sp{flex:1 1 auto;}
.tb-clock{font-family:var(--mono);font-size:.72rem;color:var(--muted);white-space:nowrap;}
.tb-div{width:1px;height:22px;background:var(--border);}
.live{display:inline-flex;align-items:center;gap:6px;font-size:.62rem;font-weight:700;
  letter-spacing:.11em;color:var(--green);white-space:nowrap;}
.live i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);
  animation:blink 2.6s ease-in-out infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}

.alarm{display:flex;align-items:center;gap:10px;border:1px solid rgba(239,68,68,.32);
  border-left:3px solid var(--red);border-radius:var(--r-sm);
  background:linear-gradient(90deg,rgba(239,68,68,.15),rgba(249,115,22,.05));
  padding:.5rem .85rem;margin-bottom:.8rem;font-size:.76rem;font-weight:600;
  letter-spacing:.03em;color:#FCA5A5;}
.alarm b{font-family:var(--mono);color:#fff;font-size:.82rem;}

.kpi{position:relative;height:100%;overflow:hidden;background:var(--panel);
  border:1px solid var(--border);border-radius:var(--r);padding:.72rem .9rem .78rem;
  transition:border-color .15s ease,transform .15s ease;}
.kpi:hover{border-color:var(--border2);transform:translateY(-1px);}
.kpi::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:var(--c,var(--accent));}
.kpi-l{font-size:.62rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;
  color:var(--muted);margin-bottom:.3rem;}
.kpi-v{font-family:var(--mono);font-size:1.6rem;font-weight:700;line-height:1.05;
  color:var(--num);letter-spacing:-.02em;}
.kpi-u{font-family:var(--font);font-size:.75rem;font-weight:500;color:var(--muted);margin-left:4px;}
.kpi-s{font-size:.63rem;color:var(--muted);margin-top:.3rem;}

.card{background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--c,var(--green));
  border-radius:var(--r);padding:.8rem .9rem .85rem;margin-bottom:.7rem;}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:.65rem;}
.card-t{font-size:.86rem;font-weight:700;color:var(--text);line-height:1.2;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:.5rem .9rem;}
.mrow{display:flex;align-items:baseline;justify-content:space-between;gap:6px;}
.mlbl{font-size:.61rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);}
.mval{font-family:var(--mono);font-size:.86rem;font-weight:600;color:var(--num);}
.meter{height:5px;border-radius:3px;background:#1C2431;overflow:hidden;margin-top:5px;}
.meter>i{display:block;height:100%;border-radius:3px;}
.cardfoot{display:flex;gap:8px;flex-wrap:wrap;margin-top:.7rem;padding-top:.6rem;border-top:1px solid var(--border);}

.chip{display:inline-flex;align-items:center;gap:5px;padding:.15rem .5rem;border-radius:999px;
  font-size:.62rem;font-weight:700;letter-spacing:.06em;white-space:nowrap;border:1px solid transparent;}
.dot{width:7px;height:7px;border-radius:50%;flex:none;}
"""

CSS_APP2 = """
.sec{display:flex;align-items:center;gap:10px;margin:1.05rem 0 .55rem;}
.sec-t{font-size:.68rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);white-space:nowrap;}
.sec-r{flex:1;height:1px;background:var(--border);}
.sec-h{font-size:.64rem;color:#6E7C90;white-space:nowrap;}

.tw{max-height:600px;overflow:auto;border:1px solid var(--border);border-radius:var(--r);}
table.dt{width:100%;border-collapse:separate;border-spacing:0;font-size:.78rem;}
table.dt thead th{position:sticky;top:0;z-index:2;background:#0F151E;color:var(--muted);
  font-size:.6rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  padding:.55rem .7rem;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap;}
table.dt td{padding:.45rem .7rem;border-bottom:1px solid rgba(35,45,59,.75);vertical-align:middle;}
table.dt tbody tr:hover td{background:rgba(59,130,246,.06);}
table.dt tbody tr.crit td{background:rgba(239,68,68,.05);}
table.dt .mono{font-family:var(--mono);color:var(--num);}
table.dt .r{text-align:right;}
table.dt .act{font-size:.72rem;color:#A9B6C7;max-width:300px;}
.cb{display:flex;align-items:center;gap:8px;}
.cb>span{width:24px;text-align:right;}
.cbt{width:54px;height:4px;border-radius:2px;background:#1C2431;overflow:hidden;flex:none;}
.cbt>i{display:block;height:4px;border-radius:2px;}

.empty{border:1px dashed var(--border2);border-radius:var(--r);background:rgba(18,24,33,.55);
  padding:1.5rem;text-align:center;color:var(--muted);font-size:.8rem;}
.ok{border:1px solid rgba(34,197,94,.3);background:rgba(34,197,94,.07);color:#86EFAC;
  border-radius:var(--r);padding:.9rem;text-align:center;font-size:.8rem;font-weight:600;letter-spacing:.04em;}
"""

CSS_APP3 = """
[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"]{display:none!important;}
[data-testid="stDataFrame"]{font-family:var(--mono);font-size:.78rem;}
[data-testid="stExpander"]{border:1px solid var(--border)!important;border-radius:var(--r)!important;background:var(--panel);}
[data-testid="stExpander"] summary p{font-size:.76rem;font-weight:600;color:var(--text);}
div[data-testid="stAlert"]{border-radius:var(--r);font-size:.8rem;}

.chat-user{background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);border-radius:var(--r);padding:.7rem 1rem;margin:0.4rem 0 0.4rem 15%;color:var(--text);font-size:.85rem;}
.chat-asst{background:var(--panel);border:1px solid var(--border);border-radius:var(--r);padding:.7rem 1rem;margin:0.4rem 15% 0.4rem 0;color:var(--text);font-size:.85rem;}
.chat-user strong,.chat-asst strong{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}

.fbar{background:var(--panel);border:1px solid var(--border);border-radius:var(--r);padding:.4rem .7rem;margin-bottom:.7rem;}
"""

CSS_LOGIN = """
[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"]{display:none!important;}
.block-container{padding:0 .8rem 0 .8rem!important;max-width:100%!important;}
footer,.reportview-container .main footer{display:none!important;}
[data-testid="stBottom"]{display:none!important;}
.stApp{background:linear-gradient(150deg,#0B1220 0%,#102436 52%,#0B1220 100%)!important;}
[data-testid="stForm"] .stTextInput{margin-bottom:.25rem;}
[data-testid="stForm"] label[data-testid="stWidgetLabel"] p{margin-bottom:.05rem;}
.lg-wrap{padding:2rem .4rem 0 .4rem;}
.lg-brand{display:flex;align-items:center;gap:11px;margin-bottom:1.1rem;}
.lg-mark{width:36px;height:36px;border-radius:9px;flex:none;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,var(--teal),var(--accent));color:#04121E;font-size:.82rem;font-weight:800;letter-spacing:-.03em;}
.lg-name{font-size:.82rem;font-weight:700;letter-spacing:.13em;color:var(--text);}
.lg-tag{font-size:.52rem;font-weight:600;letter-spacing:.14em;color:var(--muted);margin-top:2px;}
.lg-h1{font-size:1.45rem;font-weight:600;letter-spacing:-.03em;color:#fff;margin-bottom:.3rem;}
.lg-p{font-size:.74rem;line-height:1.5;color:var(--muted);margin-bottom:.8rem;max-width:400px;}
.lg-note{margin-top:.6rem;padding:.5rem .7rem;border:1px solid var(--border);border-radius:var(--r-sm);
  background:rgba(18,24,33,.7);font-size:.6rem;line-height:1.45;color:var(--muted);}
.lg-note b{color:var(--text);}
.lg-foot{margin-top:.6rem;font-size:.55rem;line-height:1.5;color:#5F6D80;}
[data-testid="stForm"]{border:1px solid var(--border);border-radius:10px;background:var(--panel);
  padding:.85rem .95rem .7rem;box-shadow:0 18px 44px rgba(0,0,0,.35);}
[data-testid="stForm"] .stFormSubmitButton>button{width:100%;min-height:38px;
  background:linear-gradient(135deg,var(--teal),var(--accent));border:none;color:#04121E;
  font-size:.74rem;font-weight:800;letter-spacing:.09em;}
[data-testid="stForm"] .stFormSubmitButton>button:hover{filter:brightness(1.1);color:#04121E;}
.hero{position:relative;overflow:hidden;border-radius:12px;padding:2.5rem;
  display:flex;align-items:center;border:1px solid var(--border);
  background:radial-gradient(1000px 560px at 78% 8%,rgba(20,184,166,.16),transparent 62%),
             linear-gradient(150deg,#0B1220 0%,#102436 52%,#0B1220 100%);}
.hero-grid{position:absolute;top:0;left:0;right:0;bottom:0;
  background-image:linear-gradient(rgba(138,152,171,.05) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(138,152,171,.05) 1px,transparent 1px);
  background-size:44px 44px;}
.hero-in{position:relative;z-index:2;max-width:620px;}
.hero-kick{display:inline-block;padding:.32rem .65rem;border:1px solid rgba(20,184,166,.28);
  border-radius:5px;color:var(--teal);font-size:.59rem;font-weight:800;letter-spacing:.16em;margin-bottom:1.2rem;}
.hero-h{font-size:2.7rem;font-weight:300;line-height:1.14;letter-spacing:-.04em;color:#F6FAFF;margin-bottom:1rem;}
.hero-h b{font-weight:500;color:var(--teal);}
.hero-p{font-size:.85rem;line-height:1.75;color:var(--muted);max-width:520px;margin-bottom:2rem;}
.hero-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem;}
.hero-card{background:rgba(10,14,20,.6);border:1px solid rgba(138,152,171,.13);border-radius:9px;padding:.85rem;}
.hero-card b{display:block;font-size:.9rem;font-weight:700;margin-bottom:.3rem;letter-spacing:.04em;}
.hero-card span{font-size:.63rem;line-height:1.45;color:var(--muted);}
@media (max-width:1000px){.hero{display:none;}}

.sso-btn>button{background:var(--panel)!important;color:var(--muted)!important;border:1px solid var(--border)!important;}
.sso-btn>button:hover{background:var(--panel2)!important;color:var(--text)!important;}
"""


def load_css(extra_parts=None):
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    st.markdown("<style>" + CSS_TOKENS + "</style>", unsafe_allow_html=True)
    st.markdown("<style>" + CSS_COMMON + "</style>", unsafe_allow_html=True)
    if extra_parts:
        for part in extra_parts:
            st.markdown("<style>" + part + "</style>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════
def topbar():
    name = st.session_state.get("user_name", "")
    role = st.session_state.get("user_role", "")
    scope = st.session_state.get("user_plant_name") or ("ALL PLANTS" if role == "ADMIN" else "-")
    st.markdown(
        '<div class="topbar">'
        '<div class="tb-mark">PM</div>'
        '<div><div class="tb-title">' + APP_NAME + '</div>'
        '<div class="tb-sub">' + APP_TAG + '</div></div>'
        '<div class="tb-sp"></div>'
        '<div class="tb-clock">' + now_stamp() + '</div>'
        '<div class="tb-div"></div>'
        + chip(role.replace("_", " ") or "-", ACCENT)
        + chip(scope, TEAL)
        + '<div class="tb-div"></div>'
        '<div class="live"><i></i>LIVE</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def chip(text, color, dot=False):
    d = '<span class="dot" style="background:' + color + '"></span>' if dot else ""
    return (
        '<span class="chip" style="background:' + color + '1A;color:' + color
        + ';border-color:' + color + '33;">' + d + str(text) + '</span>'
    )


def kpi(label, value, sub="", color=ACCENT, unit=""):
    u = '<span class="kpi-u">' + unit + '</span>' if unit else ""
    s = '<div class="kpi-s">' + sub + '</div>' if sub else ""
    return (
        '<div class="kpi" style="--c:' + color + ';">'
        '<div class="kpi-l">' + label + '</div>'
        '<div class="kpi-v">' + str(value) + u + '</div>' + s + '</div>'
    )


def meter(pct, color):
    pct = max(0.0, min(100.0, float(pct)))
    return '<div class="meter"><i style="width:' + format(pct, ".0f") + '%;background:' + color + '"></i></div>'


def metric_row(label, value, color=None):
    style = ' style="color:' + color + '"' if color else ""
    return '<div class="mrow"><span class="mlbl">' + label + '</span><span class="mval"' + style + '>' + str(value) + '</span></div>'


def section(title, hint=""):
    h = '<span class="sec-h">' + hint + '</span>' if hint else ""
    st.markdown(
        '<div class="sec"><span class="sec-t">' + title + '</span><span class="sec-r"></span>' + h + '</div>',
        unsafe_allow_html=True,
    )


def empty_state(message):
    st.markdown('<div class="empty">' + message + '</div>', unsafe_allow_html=True)


def ok_state(message):
    st.markdown('<div class="ok">' + message + '</div>', unsafe_allow_html=True)


def alarm_banner(count):
    if count and count > 0:
        plural = "S" if count != 1 else ""
        st.markdown(
            '<div class="alarm">&#9888;&nbsp; <b>' + str(count) + '</b> ACTIVE ALERT' + plural
            + ' REQUIRING ATTENTION</div>',
            unsafe_allow_html=True,
        )


def gauge(score, size=170):
    color = health_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(score),
            number=dict(font=dict(size=26, family=MONO, color=NUMERIC), suffix=""),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=0, dtick=25, tickfont=dict(size=9, color=MUTED)),
                bar=dict(color=color, thickness=0.28),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 50], color="rgba(239,68,68,0.13)"),
                    dict(range=[50, 75], color="rgba(234,179,8,0.13)"),
                    dict(range=[75, 90], color="rgba(249,115,22,0.10)"),
                    dict(range=[90, 100], color="rgba(34,197,94,0.14)"),
                ],
                threshold=dict(line=dict(color=color, width=3), thickness=0.85, value=float(score)),
            ),
        )
    )
    fig.update_layout(
        height=size,
        margin=dict(l=18, r=18, t=12, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED, family=FONT),
    )
    return fig


def style_chart(fig, ytitle="", xtitle="", height=340, legend=True, percent_y=False):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=48, r=18, t=26, b=34),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=11, color=MUTED),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PANEL2, bordercolor=BORDER, font=dict(family=FONT, size=11, color=TEXT)),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(size=10, color=MUTED), bgcolor="rgba(0,0,0,0)", title_text="",
        ),
        xaxis=dict(title=xtitle, gridcolor=GRID, zeroline=False, linecolor=BORDER,
                   tickfont=dict(family=MONO, size=10, color=MUTED)),
        yaxis=dict(title=ytitle, gridcolor=GRID, zeroline=False, linecolor=BORDER,
                   tickfont=dict(family=MONO, size=10, color=MUTED)),
        title=None,
    )
    if percent_y:
        fig.update_yaxes(tickformat=".0%")
    return fig


def show_chart(fig):
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)


# ═══════════════════════════════════════════════════════════════════════
# DATA ACCESS
# ═══════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def run_query(sql):
    return session.sql(sql).to_pandas()


@st.cache_data(ttl=600)
def get_user_pages(role):
    df = run_query(
        "SELECT PAGE_NAME FROM " + DB + ".RAW.ROLE_PERMISSIONS "
        "WHERE ROLE = " + sql_str(role) + " AND HAS_ACCESS = TRUE ORDER BY PAGE_NAME"
    )
    return df["PAGE_NAME"].tolist()


@st.cache_data(ttl=600)
def get_plant_name(plant_id):
    df = run_query(
        "SELECT PLANT_NAME FROM " + DB + ".RAW.PLANTS WHERE PLANT_ID = " + sql_str(plant_id)
    )
    return None if df.empty else str(df.iloc[0]["PLANT_NAME"])


def plant_scope_sql(col="PLANT_NAME"):
    if st.session_state.get("user_role") == "ADMIN":
        return ""
    pname = st.session_state.get("user_plant_name")
    if pname:
        return " AND " + col + " = " + sql_str(pname)
    return ""


@st.cache_data(ttl=300)
def get_plants(scope):
    return run_query(
        "SELECT DISTINCT PLANT_ID, PLANT_NAME FROM " + DB + ".ANALYTICS.DT_PLANT_DASHBOARD "
        "WHERE 1=1 " + scope + " ORDER BY PLANT_NAME"
    )


def plant_picker(key, label="Plant", multi=True):
    plants = get_plants(plant_scope_sql())
    options = plants["PLANT_NAME"].tolist()
    if not options:
        return []
    if multi:
        return st.multiselect(label, options=options, default=options, key=key)
    return [st.selectbox(label, options=options, key=key)]


# ═══════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════
def check_login(email, password):
    df = session.sql(
        "SELECT USER_ID, USER_NAME, EMAIL, ROLE, PLANT_ID FROM " + DB + ".RAW.USERS "
        "WHERE LOWER(EMAIL) = LOWER(" + sql_str(email) + ") "
        "  AND PASSWORD_HASH = SHA2(" + sql_str(password) + ") "
        "  AND IS_ACTIVE = TRUE"
    ).to_pandas()
    return None if df.empty else df.iloc[0].to_dict()


def start_session(user):
    plant_id = str(user["PLANT_ID"]) if user["PLANT_ID"] else None
    if plant_id in ("None", "", "null"):
        plant_id = None
    st.session_state.update(
        authenticated=True,
        user_id=user["USER_ID"],
        user_name=user["USER_NAME"],
        user_email=user["EMAIL"],
        user_role=user["ROLE"],
        user_plant_id=plant_id,
        user_plant_name=get_plant_name(plant_id) if plant_id else None,
    )
    try:
        session.sql(
            "UPDATE " + DB + ".RAW.USERS SET LAST_LOGIN = CURRENT_TIMESTAMP() "
            "WHERE USER_ID = " + sql_str(user["USER_ID"])
        ).collect()
    except Exception:
        pass


def end_session():
    for key in [
        "authenticated", "user_id", "user_name", "user_email", "user_role",
        "user_plant_id", "user_plant_name", "chat_history",
    ]:
        st.session_state.pop(key, None)


# ═══════════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════════
def page_login():
    load_css([CSS_LOGIN])

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown(
            '<div style="text-align:center;margin:12vh 0 2rem 0;">'
            '<div class="lg-mark" style="margin:0 auto 1rem auto;">PM</div>'
            '<div class="lg-name" style="text-align:center;">' + APP_NAME + '</div>'
            '<div class="lg-tag" style="text-align:center;">INDUSTRIAL MONITORING PLATFORM</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Work email", placeholder="name@company.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pw")
            submitted = st.form_submit_button("SIGN IN", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Enter your work email and password.")
            else:
                user = check_login(email.strip(), password)
                if user:
                    start_session(user)
                    do_rerun()
                else:
                    st.error("Unable to sign in. Check your credentials or contact your administrator.")


# ═══════════════════════════════════════════════════════════════════════
# PAGE 1 - PLANT OVERVIEW
# ═══════════════════════════════════════════════════════════════════════
def page_plant_overview():
    f1, f2 = st.columns([3, 1])
    with f1:
        selected = plant_picker("overview_plants")
    if not selected:
        empty_state("Select at least one plant to load the fleet overview.")
        return

    plants_sql = sql_in(selected)
    dash = run_query(
        "SELECT * FROM " + DB + ".ANALYTICS.DT_PLANT_DASHBOARD "
        "WHERE PLANT_NAME IN (" + plants_sql + ") ORDER BY PLANT_NAME"
    )
    if dash.empty:
        empty_state("No dashboard rows for the selected plants.")
        return

    total_assets = int(dash["TOTAL_ASSETS"].sum())
    avg_health = float(dash["AVG_HEALTH_SCORE"].mean())
    avg_oee = float(dash["AVG_OEE_30D"].mean())
    open_tickets = int(dash["OPEN_TICKETS"].sum())
    active_alerts = int(dash["ACTIVE_ALERTS"].sum())
    crit_assets = int(dash["ASSETS_CRITICAL_RISK"].sum())

    alarm_banner(active_alerts)

    cols = st.columns(6)
    cols[0].markdown(kpi("Assets Monitored", format(total_assets, ","), str(len(dash)) + " plant(s)", ACCENT), unsafe_allow_html=True)
    cols[1].markdown(kpi("Fleet Health", format(avg_health, ".1f"), "Bearing composite", health_color(avg_health)), unsafe_allow_html=True)
    cols[2].markdown(kpi("Avg OEE", format(avg_oee * 100, ".1f"), "Avail x Perf x Qual", oee_color(avg_oee), unit="%"), unsafe_allow_html=True)
    cols[3].markdown(kpi("Critical Assets", str(crit_assets), "Immediate intervention", RED if crit_assets else GREEN), unsafe_allow_html=True)
    cols[4].markdown(kpi("Open Tickets", str(open_tickets), "Pending maintenance", RED if open_tickets > 5 else YELLOW if open_tickets else GREEN), unsafe_allow_html=True)
    cols[5].markdown(kpi("Active Alerts", str(active_alerts), "Requiring attention", RED if active_alerts > 3 else YELLOW if active_alerts else GREEN), unsafe_allow_html=True)

    section("Plant Status", str(len(dash)) + " sites")
    per_row = 3
    for start in range(0, len(dash), per_row):
        block = dash.iloc[start:start + per_row]
        row_cols = st.columns(per_row)
        for offset in range(per_row):
            if offset >= len(block):
                continue
            with row_cols[offset]:
                st.markdown(plant_card(block.iloc[offset]), unsafe_allow_html=True)

    section("Asset Risk Distribution")
    rows = []
    for _, r in dash.iterrows():
        for label, key in (("Low", "ASSETS_LOW_RISK"), ("Medium", "ASSETS_MEDIUM_RISK"), ("High", "ASSETS_HIGH_RISK"), ("Critical", "ASSETS_CRITICAL_RISK")):
            rows.append({"Plant": short_plant(r["PLANT_NAME"]), "Risk": label, "Assets": int(r[key])})
    risk_df = pd.DataFrame(rows)
    fig = px.bar(risk_df, x="Plant", y="Assets", color="Risk", barmode="stack",
                 color_discrete_map={"Low": GREEN, "Medium": YELLOW, "High": ORANGE, "Critical": RED})
    style_chart(fig, ytitle="Assets", height=360)
    show_chart(fig)

    section("OEE Trend (30 Days)")
    oee = run_query(
        "SELECT RUN_DATE, PLANT_NAME, AVG(OEE) AS AVG_OEE FROM " + DB + ".ANALYTICS.DT_OEE_METRICS "
        "WHERE PLANT_NAME IN (" + plants_sql + ") "
        "  AND RUN_DATE >= DATEADD('day', -30, CURRENT_DATE()) "
        "GROUP BY RUN_DATE, PLANT_NAME ORDER BY RUN_DATE"
    )
    if oee.empty:
        empty_state("No OEE records in the last 30 days.")
    else:
        fig = px.line(oee, x="RUN_DATE", y="AVG_OEE", color="PLANT_NAME", color_discrete_sequence=CHART_COLORS)
        style_chart(fig, ytitle="OEE", height=360, percent_y=True)
        show_chart(fig)


def plant_card(row):
    health = float(row["AVG_HEALTH_SCORE"])
    oee = float(row["AVG_OEE_30D"])
    crit = int(row["ASSETS_CRITICAL_RISK"])
    high = int(row["ASSETS_HIGH_RISK"])
    tickets = int(row["OPEN_TICKETS"])
    alerts = int(row["ACTIVE_ALERTS"])
    if crit:
        accent, status = RED, chip(str(crit) + " CRITICAL", RED, dot=True)
    elif high:
        accent, status = ORANGE, chip(str(high) + " HIGH RISK", ORANGE, dot=True)
    else:
        accent, status = GREEN, chip("NOMINAL", GREEN, dot=True)
    hc, oc = health_color(health), oee_color(oee)
    return (
        '<div class="card" style="--c:' + accent + ';">'
        '<div class="card-h"><span class="card-t">' + str(row["PLANT_NAME"]) + '</span>' + status + '</div>'
        '<div>' + metric_row("Health score", format(health, ".1f"), hc) + meter(health, hc) + '</div>'
        '<div style="margin-top:.6rem;">' + metric_row("OEE 30d", format(oee * 100, ".1f") + "%", oc)
        + meter(oee * 100, oc) + '</div>'
        '<div class="cardfoot">'
        + chip(str(int(row["TOTAL_ASSETS"])) + " ASSETS", MUTED)
        + chip(str(tickets) + " TICKETS", YELLOW if tickets else MUTED)
        + chip(str(alerts) + " ALERTS", RED if alerts else MUTED)
        + '</div></div>'
    )


# ═══════════════════════════════════════════════════════════════════════
# PAGE 2 - VIBRATION MONITOR
# ═══════════════════════════════════════════════════════════════════════
def downsample(df, max_points=1500):
    if len(df) <= max_points:
        return df
    step = len(df) // max_points + 1
    return df.iloc[::step]


def page_vibration_monitor():
    f1, f2, f3 = st.columns([1, 1, 1])
    with f1:
        plant = plant_picker("vib_plant", multi=False)
        plant = plant[0] if plant else None
    asset_type = None
    asset_name = None
    if plant:
        types = run_query(
            "SELECT DISTINCT ASSET_TYPE FROM " + DB + ".CURATED.DT_BEARING_HEALTH "
            "WHERE PLANT_NAME = " + sql_str(plant) + " ORDER BY ASSET_TYPE"
        )
        if not types.empty:
            with f2:
                asset_type = st.selectbox("Asset type", types["ASSET_TYPE"].tolist(), key="vib_type")
    assets = pd.DataFrame()
    if plant and asset_type:
        assets = run_query(
            "SELECT ASSET_ID, ASSET_NAME, CRITICALITY, GROUP_NAME, BEARING_HEALTH_SCORE "
            "FROM " + DB + ".CURATED.DT_BEARING_HEALTH "
            "WHERE PLANT_NAME = " + sql_str(plant) + " AND ASSET_TYPE = " + sql_str(asset_type) + " "
            "ORDER BY BEARING_HEALTH_SCORE ASC"
        )
        if not assets.empty:
            with f3:
                asset_name = st.selectbox("Asset (worst first)", assets["ASSET_NAME"].tolist(), key="vib_asset")

    if not plant or not asset_type or not asset_name:
        empty_state("No assets available for this selection.")
        return

    asset_row = assets.loc[assets["ASSET_NAME"] == asset_name].iloc[0]
    asset_id = asset_row["ASSET_ID"]

    health = run_query(
        "SELECT BEARING_HEALTH_SCORE, ADR_RISK, WORST_ISO_ZONE, PEAK_VEL_RMS, PEAK_RSS_ACCEL, "
        "       MAX_TEMPERATURE_C, WORST_TEMP_STATUS, ANOMALY_FLAG "
        "FROM " + DB + ".CURATED.DT_BEARING_HEALTH WHERE ASSET_ID = " + sql_str(asset_id) + " LIMIT 1"
    )
    if health.empty:
        empty_state("No health record for this asset.")
        return
    h = health.iloc[0]
    score = float(h["BEARING_HEALTH_SCORE"])
    anomaly = bool(h["ANOMALY_FLAG"])
    temp_status = str(h["WORST_TEMP_STATUS"])
    temp_color = RED if temp_status == "ALARM" else YELLOW if temp_status == "WARNING" else GREEN
    risk = str(h["ADR_RISK"])

    st.markdown(
        '<div class="card" style="--c:' + health_color(score) + ';">'
        '<div class="card-h"><span class="card-t" style="font-size:1rem;">' + str(asset_name) + '</span>'
        '<span>' + chip(str(asset_type), ACCENT) + " " + chip(str(asset_row.get("CRITICALITY", "-")), PURPLE) + '</span></div>'
        '<div style="display:flex;gap:.5rem;flex-wrap:wrap;">'
        + chip("HEALTH " + format(score, ".0f"), health_color(score), dot=True)
        + chip("ISO " + str(h["WORST_ISO_ZONE"]).replace("_", " ").upper(), CYAN)
        + chip("ADR " + RISK_DISPLAY.get(risk, risk).upper(), RISK_COLORS.get(risk, MUTED))
        + chip("TEMP " + format(float(h["MAX_TEMPERATURE_C"]), ".1f") + " C " + temp_status, temp_color)
        + chip("ANOMALY DETECTED" if anomaly else "NO ANOMALY", RED if anomaly else GREEN, dot=True)
        + '</div></div>',
        unsafe_allow_html=True,
    )

    g_col, k1, k2, k3 = st.columns([1, 1, 1, 1])
    with g_col:
        show_chart(gauge(score, 168))
    k1.markdown(kpi("ADR Risk", RISK_DISPLAY.get(risk, risk), "Automated diagnostic", RISK_COLORS.get(risk, MUTED)), unsafe_allow_html=True)
    k2.markdown(kpi("Peak Velocity", format(float(h["PEAK_VEL_RMS"]), ".2f"), "RMS worst axis", ACCENT, unit="mm/s"), unsafe_allow_html=True)
    k3.markdown(kpi("Peak Accel", format(float(h["PEAK_RSS_ACCEL"]), ".2f"), "Root sum of squares", ACCENT, unit="m/s2"), unsafe_allow_html=True)

    section("3-Axis Vibration Trend (7 Days)")
    readings = run_query(
        "SELECT READING_TS, X_VEL_RMS, Y_VEL_RMS, Z_VEL_RMS, TEMPERATURE_C "
        "FROM " + DB + ".CURATED.DT_SENSOR_ENRICHED "
        "WHERE ASSET_ID = " + sql_str(asset_id) + " "
        "  AND READING_TS >= DATEADD('day', -7, CURRENT_TIMESTAMP()) "
        "ORDER BY READING_TS"
    )
    if readings.empty:
        empty_state("No sensor readings in the selected window.")
    else:
        plot_df = downsample(readings)
        left, right = st.columns([2, 1])
        with left:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=plot_df["READING_TS"], y=plot_df["X_VEL_RMS"], mode="lines", name="X-Axis (V)", line=dict(color=ACCENT, width=1.4)))
            fig.add_trace(go.Scatter(x=plot_df["READING_TS"], y=plot_df["Y_VEL_RMS"], mode="lines", name="Y-Axis (H)", line=dict(color=TEAL, width=1.4)))
            fig.add_trace(go.Scatter(x=plot_df["READING_TS"], y=plot_df["Z_VEL_RMS"], mode="lines", name="Z-Axis (A)", line=dict(color=ORANGE, width=1.4)))
            style_chart(fig, ytitle="mm/s RMS", height=380)
            show_chart(fig)
        with right:
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=plot_df["READING_TS"], y=plot_df["TEMPERATURE_C"], mode="lines", name="Temp",
                                       line=dict(color=RED, width=1.5), fill="tozeroy", fillcolor="rgba(239,68,68,0.07)"))
            fig_t.add_hline(y=80, line_dash="dash", line_color=YELLOW, line_width=1, annotation_text="WARNING 80", annotation_font=dict(size=8, color=YELLOW))
            fig_t.add_hline(y=100, line_dash="dash", line_color=RED, line_width=1, annotation_text="ALARM 100", annotation_font=dict(size=8, color=RED))
            style_chart(fig_t, ytitle="deg C", height=380, legend=False)
            show_chart(fig_t)

    section("Sensor Latest Readings")
    sensors = run_query(
        "SELECT SENSOR_LABEL, MOUNT_POSITION, ISO_VEL_ZONE, X_VEL_RMS, Y_VEL_RMS, Z_VEL_RMS, "
        "       X_ACCEL_RMS, Y_ACCEL_RMS, Z_ACCEL_RMS, TEMPERATURE_C "
        "FROM " + DB + ".CURATED.DT_SENSOR_ENRICHED "
        "WHERE ASSET_ID = " + sql_str(asset_id) + " "
        "QUALIFY ROW_NUMBER() OVER (PARTITION BY SENSOR_ID ORDER BY READING_TS DESC) = 1 "
        "ORDER BY SENSOR_LABEL"
    )
    if not sensors.empty:
        st.dataframe(sensors, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════
# PAGE 3 - ALERT TRIAGE
# ═══════════════════════════════════════════════════════════════════════
def page_alert_triage():
    f1, f2 = st.columns([3, 1])
    with f1:
        selected = plant_picker("alert_plants")
    with f2:
        actionable_only = st.checkbox("Actionable only", value=True, key="alert_actionable")

    if not selected:
        empty_state("Select at least one plant to triage alerts.")
        return

    plants_sql = sql_in(selected)
    actionable_clause = " AND IS_ACTIONABLE = TRUE" if actionable_only else ""
    alerts = run_query(
        "SELECT ASSET_ID, ASSET_NAME, ASSET_TYPE, PLANT_NAME, GROUP_NAME, CRITICALITY, "
        "       BEARING_HEALTH_SCORE, ADR_RISK, ALERT_SEVERITY, PEAK_VEL_RMS, PEAK_RSS_ACCEL, "
        "       MAX_TEMPERATURE_C, RECOMMENDED_ACTION, IS_ACTIONABLE, LAST_READING_TS "
        "FROM " + DB + ".ANALYTICS.DT_VIBRATION_ALERTS "
        "WHERE PLANT_NAME IN (" + plants_sql + ")" + actionable_clause + " "
        "ORDER BY CASE ALERT_SEVERITY WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 "
        "         WHEN 'MEDIUM' THEN 3 ELSE 4 END, BEARING_HEALTH_SCORE ASC "
        "LIMIT 500"
    )

    counts = alerts["ALERT_SEVERITY"].value_counts().to_dict() if not alerts.empty else {}
    tiles = st.columns(5)
    for i, level in enumerate(SEVERITY_ORDER):
        n = int(counts.get(level, 0))
        tiles[i].markdown(kpi(level.title(), str(n), "alerts", SEVERITY_COLORS[level] if n else MUTED), unsafe_allow_html=True)
    actionable_n = int(alerts["IS_ACTIONABLE"].sum()) if not alerts.empty else 0
    tiles[4].markdown(kpi("Actionable", str(actionable_n), "work order candidates", ACCENT), unsafe_allow_html=True)

    if alerts.empty:
        ok_state("ALL SYSTEMS NOMINAL - NO ALERTS MATCHING THE CURRENT FILTERS")
        return

    section("Alert Queue", format(len(alerts), ",") + " rows")
    rows_html = []
    for _, a in alerts.iterrows():
        severity = str(a["ALERT_SEVERITY"])
        color = SEVERITY_COLORS.get(severity, MUTED)
        hs = float(a["BEARING_HEALTH_SCORE"])
        hc = health_color(hs)
        temp = float(a["MAX_TEMPERATURE_C"])
        tc = RED if temp >= 100 else YELLOW if temp >= 80 else NUMERIC
        rows_html.append(
            '<tr class="' + ("crit" if severity == "CRITICAL" else "") + '">'
            '<td>' + chip(severity, color, dot=True) + '</td>'
            '<td><div style="font-weight:600;">' + str(a["ASSET_NAME"]) + '</div>'
            '<div style="font-size:.68rem;color:' + MUTED + ';">' + str(a["ASSET_TYPE"])
            + " - " + str(a["GROUP_NAME"]) + '</div></td>'
            '<td style="font-size:.72rem;color:' + MUTED + ';">' + str(a["PLANT_NAME"]) + '</td>'
            '<td><div class="cb"><span class="mono">' + format(hs, ".0f") + '</span>'
            '<div class="cbt"><i style="width:' + format(max(0, min(100, hs)), ".0f") + '%;background:' + hc + '"></i></div></div></td>'
            '<td class="mono r">' + format(float(a["PEAK_VEL_RMS"]), ".2f") + '</td>'
            '<td class="mono r">' + format(float(a["PEAK_RSS_ACCEL"]), ".2f") + '</td>'
            '<td class="mono r" style="color:' + tc + ';">' + format(temp, ".1f") + '</td>'
            '<td class="act">' + str(a["RECOMMENDED_ACTION"]) + '</td></tr>'
        )
    st.markdown(
        '<div class="tw"><table class="dt"><thead><tr>'
        '<th>Severity</th><th>Asset</th><th>Plant</th><th>Health</th>'
        '<th class="r">Vel mm/s</th><th class="r">Accel m/s2</th><th class="r">Temp C</th>'
        '<th>Recommended action</th></tr></thead><tbody>'
        + "".join(rows_html) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════
# PAGE 4 - TICKET MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════
def page_ticket_management():
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        selected = plant_picker("ticket_plants")
    with f2:
        status = st.selectbox("Status", ["All", "OPEN", "IN_PROGRESS", "ACKNOWLEDGED", "CLOSED"], key="ticket_status")
    with f3:
        severity = st.selectbox("Severity", ["All"] + SEVERITY_ORDER, key="ticket_severity")

    if not selected:
        empty_state("Select at least one plant to load maintenance tickets.")
        return

    plants_sql = sql_in(selected)
    where = "WHERE PLANT_NAME IN (" + plants_sql + ")"
    if status != "All":
        where += " AND STATUS = " + sql_str(status)
    if severity != "All":
        where += " AND SEVERITY = " + sql_str(severity)

    tickets = run_query(
        "SELECT TICKET_ID, ASSET_NAME, ASSET_TYPE, PLANT_NAME, GROUP_NAME, FAILURE_MODE, ROOT_CAUSE, "
        "       SEVERITY, STATUS, DOWNTIME_HOURS, MTTR_HOURS, ISSUE_OPEN_DATE, ISSUE_CLOSURE_DATE, "
        "       ASSIGNED_TO_NAME, CORRECTIVE_ACTIONS_REC, CORRECTIVE_ACTIONS_TAKEN, "
        "       PRE_REPAIR_HEALTH_SCORE, POST_REPAIR_HEALTH_SCORE, HEALTH_IMPROVEMENT, TICKET_AGE_DAYS "
        "FROM " + DB + ".CURATED.DT_MAINTENANCE_HISTORY " + where + " "
        "ORDER BY ISSUE_OPEN_DATE DESC LIMIT 500"
    )
    summary = run_query(
        "SELECT COUNT(*) AS TOTAL_TICKETS, "
        "       SUM(CASE WHEN STATUS <> 'CLOSED' THEN 1 ELSE 0 END) AS OPEN_COUNT, "
        "       AVG(MTTR_HOURS) AS AVG_MTTR, SUM(DOWNTIME_HOURS) AS TOTAL_DOWNTIME "
        "FROM " + DB + ".CURATED.DT_MAINTENANCE_HISTORY " + where
    ).iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi("Total Tickets", str(int(summary["TOTAL_TICKETS"] or 0)), "Matching filters", ACCENT), unsafe_allow_html=True)
    oc = int(summary["OPEN_COUNT"] or 0)
    k2.markdown(kpi("Open", str(oc), "Pending resolution", YELLOW if oc > 0 else GREEN), unsafe_allow_html=True)
    mttr = summary["AVG_MTTR"]
    k3.markdown(kpi("Avg MTTR", fmt_num(mttr, 1) + "h" if pd.notna(mttr) else "N/A", "Mean time to repair", CYAN), unsafe_allow_html=True)
    dt_val = summary["TOTAL_DOWNTIME"]
    k4.markdown(kpi("Total Downtime", fmt_num(dt_val, 0) + "h" if pd.notna(dt_val) else "N/A", "Equipment hours lost", RED), unsafe_allow_html=True)

    section("Tickets")
    if not tickets.empty:
        display_cols = ["TICKET_ID", "ASSET_NAME", "PLANT_NAME", "FAILURE_MODE", "SEVERITY", "STATUS", "DOWNTIME_HOURS", "MTTR_HOURS", "ASSIGNED_TO_NAME", "ISSUE_OPEN_DATE", "TICKET_AGE_DAYS"]
        st.dataframe(tickets[display_cols], use_container_width=True)
    else:
        empty_state("No tickets match the current filters.")

    col_l, col_r = st.columns(2)
    with col_l:
        section("Failure Mode Distribution")
        if not tickets.empty and tickets["FAILURE_MODE"].notna().any():
            mode_counts = tickets[tickets["FAILURE_MODE"].notna()].groupby("FAILURE_MODE").size().reset_index(name="Count").sort_values("Count", ascending=False)
            fig_pie = px.pie(mode_counts, names="FAILURE_MODE", values="Count", color_discrete_sequence=CHART_COLORS, hole=0.45)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label", textfont_size=10, textfont_color=TEXT)
            style_chart(fig_pie, height=350, legend=False)
            show_chart(fig_pie)
    with col_r:
        section("Monthly Ticket Trend")
        trend = run_query(
            "SELECT MONTH, SUM(TOTAL_TICKETS) AS TOTAL_TICKETS, SUM(CLOSED_TICKETS) AS CLOSED_TICKETS, "
            "       SUM(OPEN_TICKETS) AS OPEN_TICKETS "
            "FROM " + DB + ".ANALYTICS.DT_TICKET_ANALYTICS "
            "WHERE PLANT_NAME IN (" + plants_sql + ") GROUP BY MONTH ORDER BY MONTH"
        )
        if not trend.empty:
            fig_tr = go.Figure()
            fig_tr.add_trace(go.Scatter(x=trend["MONTH"], y=trend["TOTAL_TICKETS"], mode="lines+markers", name="Total", line=dict(color=ACCENT, width=2), marker=dict(size=4)))
            fig_tr.add_trace(go.Scatter(x=trend["MONTH"], y=trend["CLOSED_TICKETS"], mode="lines+markers", name="Closed", line=dict(color=GREEN, width=2), marker=dict(size=4)))
            fig_tr.add_trace(go.Scatter(x=trend["MONTH"], y=trend["OPEN_TICKETS"], mode="lines+markers", name="Open", line=dict(color=RED, width=2), marker=dict(size=4)))
            style_chart(fig_tr, ytitle="Tickets", height=350)
            show_chart(fig_tr)


# ═══════════════════════════════════════════════════════════════════════
# PAGE 5 - ROOT CAUSE CHAT
# ═══════════════════════════════════════════════════════════════════════
SUGGESTED_QUESTIONS = [
    "Which assets have the worst health scores?",
    "What are the most common failure modes?",
    "Show the average MTTR across all plants",
    "Which plant has the most open tickets?",
    "Give me an overview of all plants",
]


def page_root_cause_chat():
    f1, f2 = st.columns([4, 1])
    with f1:
        st.markdown('<span style="font-size:.72rem;color:' + MUTED + ';">Model: ' + CORTEX_MODEL + '</span>', unsafe_allow_html=True)
    with f2:
        if st.button("CLEAR CONVERSATION", use_container_width=True, key="chat_clear"):
            st.session_state.chat_history = []
            do_rerun()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    section("Suggested Queries")
    sample_cols = st.columns(len(SUGGESTED_QUESTIONS))
    for i, q in enumerate(SUGGESTED_QUESTIONS):
        if sample_cols[i].button(q, key="sample_" + str(i), use_container_width=True):
            st.session_state["_pending_query"] = q

    st.markdown("---")

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown('<div class="chat-user"><strong>OPERATOR</strong><br>' + msg["content"] + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chat-asst"><strong>ANALYST</strong><br>' + msg["content"] + '</div>', unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_input = st.text_input("Ask about maintenance, failures, or asset health...", key="_chat_input")
        with col_btn:
            st.markdown('<div style="height:.85rem;"></div>', unsafe_allow_html=True)
            send_clicked = st.form_submit_button("SEND", use_container_width=True)

    query_to_process = None
    if send_clicked and user_input:
        query_to_process = user_input
    elif st.session_state.get("_pending_query"):
        query_to_process = st.session_state.pop("_pending_query")

    if query_to_process:
        st.session_state.chat_history.append({"role": "user", "content": query_to_process})
        with st.spinner("Analyzing plant data..."):
            try:
                plant_scope = plant_scope_sql("PLANT_NAME")
                context_df = session.sql(
                    "SELECT 'PLANT_DASHBOARD' AS SOURCE, TO_VARCHAR(OBJECT_CONSTRUCT(*)) AS DATA "
                    "FROM " + DB + ".ANALYTICS.DT_PLANT_DASHBOARD WHERE 1=1 " + plant_scope + " "
                    "UNION ALL "
                    "SELECT 'BEARING_HEALTH', TO_VARCHAR(OBJECT_CONSTRUCT(*)) "
                    "FROM " + DB + ".CURATED.DT_BEARING_HEALTH WHERE 1=1 " + plant_scope + " "
                    "ORDER BY SOURCE"
                ).to_pandas()
                context_str = ""
                for _, row in context_df.iterrows():
                    context_str += "\n[" + row["SOURCE"] + "]: " + str(row["DATA"])
                tickets_df = session.sql(
                    "SELECT TICKET_ID, ASSET_NAME, PLANT_NAME, SEVERITY, STATUS, "
                    "       FAILURE_MODE, CORRECTIVE_ACTIONS_REC, MTTR_HOURS, DOWNTIME_HOURS "
                    "FROM " + DB + ".CURATED.DT_MAINTENANCE_HISTORY WHERE STATUS != 'CLOSED' " + plant_scope
                ).to_pandas()
                for _, row in tickets_df.iterrows():
                    context_str += "\n[OPEN_TICKET]: " + row.to_json()
                failure_df = session.sql(
                    "SELECT FAILURE_MODE, COUNT(*) AS CNT, ROUND(AVG(MTTR_HOURS),1) AS AVG_MTTR, "
                    "       ROUND(SUM(DOWNTIME_HOURS),0) AS TOTAL_DT "
                    "FROM " + DB + ".CURATED.DT_MAINTENANCE_HISTORY "
                    "WHERE FAILURE_MODE IS NOT NULL " + plant_scope + " GROUP BY FAILURE_MODE ORDER BY CNT DESC"
                ).to_pandas()
                for _, row in failure_df.iterrows():
                    context_str += "\n[FAILURE_STATS]: " + row.to_json()

                prompt_text = (
                    "You are a predictive maintenance specialist for industrial rotating equipment. "
                    "You have data from 3 plants with motors, compressors, blowers, pumps, and fans. "
                    "Use ISO 10816 vibration severity standards. Be concise and data-driven.\n\n"
                    "DATA CONTEXT:\n" + context_str + "\n\n"
                    "USER QUESTION: " + query_to_process + "\n\n"
                    "Answer the question based on the data above. Use tables where appropriate."
                )
                safe_prompt = prompt_text.replace("'", "''")
                result_df = session.sql("SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', '" + safe_prompt + "') AS RESPONSE").to_pandas()
                if not result_df.empty:
                    response_text = str(result_df.iloc[0]["RESPONSE"])
                else:
                    response_text = "No response received."
            except Exception as e:
                response_text = "Error: " + str(e)
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        do_rerun()


# ═══════════════════════════════════════════════════════════════════════
# PAGE 6 - USER ADMIN
# ═══════════════════════════════════════════════════════════════════════
ROLE_OPTIONS = ["ADMIN", "PLANT_MANAGER", "MAINT_ENGINEER", "VIB_ANALYST", "OPERATOR"]


def page_user_admin():
    users = session.sql(
        "SELECT U.USER_ID, U.USER_NAME, U.EMAIL, U.ROLE, U.PLANT_ID, U.IS_ACTIVE, U.LAST_LOGIN, "
        "       P.PLANT_NAME "
        "FROM " + DB + ".RAW.USERS U "
        "LEFT JOIN " + DB + ".RAW.PLANTS P ON U.PLANT_ID = P.PLANT_ID "
        "ORDER BY U.USER_NAME"
    ).to_pandas()

    total = len(users)
    active = int(users["IS_ACTIVE"].sum()) if total else 0

    cols = st.columns(4)
    cols[0].markdown(kpi("Users", str(total), "registered accounts", ACCENT), unsafe_allow_html=True)
    cols[1].markdown(kpi("Active", str(active), "enabled accounts", GREEN), unsafe_allow_html=True)
    cols[2].markdown(kpi("Disabled", str(total - active), "blocked accounts", RED if total - active else MUTED), unsafe_allow_html=True)
    cols[3].markdown(kpi("Roles", str(users["ROLE"].nunique()) if total else "0", "distinct roles", PURPLE), unsafe_allow_html=True)

    section("User Directory")
    if not users.empty:
        st.dataframe(users[["USER_ID", "USER_NAME", "EMAIL", "ROLE", "PLANT_NAME", "IS_ACTIVE", "LAST_LOGIN"]], use_container_width=True)

    section("Add New User")
    plants_ref = run_query("SELECT PLANT_ID, PLANT_NAME FROM " + DB + ".RAW.PLANTS ORDER BY PLANT_NAME")
    plant_options = ["None (all plants)"] + plants_ref["PLANT_NAME"].tolist()

    with st.form("add_user_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Full name", key="new_user_name")
            new_email = st.text_input("Email", key="new_user_email", placeholder="name@company.com")
            new_password = st.text_input("Temporary password", type="password", value="Welcome@123", key="new_user_pw")
        with c2:
            new_role = st.selectbox("Role", ROLE_OPTIONS, key="new_user_role")
            new_plant = st.selectbox("Plant scope", plant_options, key="new_user_plant")
        created = st.form_submit_button("CREATE USER")

    if created:
        if not new_name or not new_email or not new_password:
            st.error("Name, email and password are all required.")
        else:
            exists = session.sql(
                "SELECT COUNT(*) AS CNT FROM " + DB + ".RAW.USERS "
                "WHERE LOWER(EMAIL) = LOWER(" + sql_str(new_email.strip()) + ")"
            ).to_pandas()
            if int(exists.iloc[0]["CNT"]) > 0:
                st.error("A user with this email already exists.")
            else:
                max_id = session.sql(
                    "SELECT MAX(CAST(REPLACE(USER_ID, 'USR-', '') AS INT)) AS MAX_NUM FROM " + DB + ".RAW.USERS"
                ).to_pandas()
                raw_max = max_id.iloc[0]["MAX_NUM"]
                next_num = int(raw_max) + 1 if pd.notna(raw_max) else 1
                new_id = "USR-" + format(next_num, "03d")
                if new_plant == "None (all plants)":
                    plant_value = "None"
                else:
                    plant_value = plants_ref.loc[plants_ref["PLANT_NAME"] == new_plant, "PLANT_ID"].iloc[0]
                session.sql(
                    "INSERT INTO " + DB + ".RAW.USERS "
                    "(USER_ID, USER_NAME, EMAIL, ROLE, PLANT_ID, PASSWORD_HASH, IS_ACTIVE, CREATED_AT) "
                    "SELECT " + sql_str(new_id) + ", " + sql_str(new_name.strip()) + ", "
                    + sql_str(new_email.strip()) + ", " + sql_str(new_role) + ", "
                    + sql_str(plant_value) + ", SHA2(" + sql_str(new_password) + "), TRUE, CURRENT_TIMESTAMP()"
                ).collect()
                st.success("User " + new_name + " (" + new_id + ") created.")
                do_rerun()

    section("Toggle User Status")
    if not users.empty:
        t1, t2 = st.columns([3, 1])
        with t1:
            target = st.selectbox("User", users["USER_NAME"].tolist(), key="toggle_user")
        row = users.loc[users["USER_NAME"] == target].iloc[0]
        currently_active = bool(row["IS_ACTIVE"])
        with t2:
            st.markdown('<div style="height:1.3rem;"></div>', unsafe_allow_html=True)
            if st.button("DISABLE" if currently_active else "ENABLE", use_container_width=True, key="toggle_btn"):
                session.sql(
                    "UPDATE " + DB + ".RAW.USERS SET IS_ACTIVE = "
                    + ("FALSE" if currently_active else "TRUE")
                    + " WHERE USER_ID = " + sql_str(row["USER_ID"])
                ).collect()
                st.success(str(target) + " has been " + ("disabled." if currently_active else "enabled."))
                do_rerun()

    section("Role to Page Access")
    perms = run_query(
        "SELECT ROLE, PAGE_NAME, HAS_ACCESS FROM " + DB + ".RAW.ROLE_PERMISSIONS ORDER BY ROLE, PAGE_NAME"
    )
    if not perms.empty:
        matrix = perms.pivot_table(index="PAGE_NAME", columns="ROLE", values="HAS_ACCESS", aggfunc="first").fillna(False)
        st.dataframe(matrix, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════
# NAVIGATION + AUTH GATE
# ═══════════════════════════════════════════════════════════════════════
ALL_PAGES = {
    "Plant Overview": page_plant_overview,
    "Vibration Monitor": page_vibration_monitor,
    "Alert Triage": page_alert_triage,
    "Ticket Management": page_ticket_management,
    "Root Cause Chat": page_root_cause_chat,
    "User Admin": page_user_admin,
}


def top_nav(page_names):
    if "_nav" not in st.session_state or st.session_state["_nav"] not in page_names:
        st.session_state["_nav"] = page_names[0]

    name = st.session_state.get("user_name", "")
    role = st.session_state.get("user_role", "")
    scope = st.session_state.get("user_plant_name") or ("All plants" if role == "ADMIN" else "-")

    topbar()

    nav_cols = st.columns(len(page_names) + 2)
    for i, page in enumerate(page_names):
        is_active = (st.session_state["_nav"] == page)
        if is_active:
            nav_cols[i].markdown(
                '<div style="text-align:center;padding:.3rem 0;border-bottom:2px solid ' + ACCENT + ';">'
                '<span style="font-size:.74rem;font-weight:600;color:#fff;">' + page + '</span></div>',
                unsafe_allow_html=True,
            )
        else:
            if nav_cols[i].button(page, key="nav_" + page, use_container_width=True):
                st.session_state["_nav"] = page
                do_rerun()

    with nav_cols[-2]:
        st.markdown(
            '<div style="text-align:right;padding:.25rem 0;">'
            '<span style="font-size:.7rem;color:' + MUTED + ';">' + str(name) + ' &middot; '
            + role.replace("_", " ") + ' &middot; ' + scope + '</span></div>',
            unsafe_allow_html=True,
        )
    if nav_cols[-1].button("LOG OUT", key="logout_btn", use_container_width=True):
        end_session()
        do_rerun()

    return st.session_state["_nav"]


def main():
    if not st.session_state.get("authenticated"):
        page_login()
        return

    load_css([CSS_APP, CSS_APP2, CSS_APP3])
    allowed = get_user_pages(st.session_state["user_role"])
    pages = {name: fn for name, fn in ALL_PAGES.items() if name in allowed}

    if not pages:
        topbar()
        st.error("Your role has no page access configured. Contact your administrator.")
        if st.button("LOG OUT", use_container_width=True, key="logout_noaccess"):
            end_session()
            do_rerun()
        return

    selected = top_nav(list(pages.keys()))
    pages[selected]()


main()

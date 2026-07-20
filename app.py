import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io, datetime

# ────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────
st.set_page_config(
    page_title="QRadar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter','Malgun Gothic',sans-serif;font-size:13px}
[data-testid="stSidebar"]{background:#0f1729;border-right:1px solid #1e2d4a}
[data-testid="stSidebar"] *{color:#c8d4e8!important}
[data-testid="stSidebar"] hr{border-color:#1e2d4a!important}
[data-testid="metric-container"]{
    background:linear-gradient(135deg,#1a2744 0%,#1e3055 100%);
    border:1px solid #2a3f6f;border-radius:10px;padding:14px 16px;
    box-shadow:0 2px 8px rgba(0,0,0,0.3)
}
[data-testid="stMetricValue"]{font-size:1.5rem!important;font-weight:700!important;color:#e8f0ff!important}
[data-testid="stMetricLabel"]{font-size:0.72rem!important;color:#7a9cc8!important;font-weight:500!important}
[data-testid="stMetricDelta"]{font-size:0.72rem!important}
.qradar-header{
    background:linear-gradient(135deg,#0f1729 0%,#1a2744 50%,#0d2550 100%);
    border:1px solid #2a3f6f;border-radius:12px;
    padding:20px 28px;margin-bottom:18px;
    box-shadow:0 4px 20px rgba(0,0,0,0.4);
    display:flex;align-items:center;justify-content:space-between
}
.qradar-header .title{font-size:1.6rem;font-weight:800;color:#fff;letter-spacing:-0.5px}
.qradar-header .title span{color:#3a8fff}
.qradar-header .sub{font-size:0.78rem;color:#7a9cc8;margin-top:4px}
.qradar-header .status{text-align:right}
.qradar-header .status .dot{
    display:inline-block;width:8px;height:8px;border-radius:50%;
    background:#00e676;box-shadow:0 0 8px #00e676;margin-right:6px;
    animation:pulse 2s infinite
}
@keyframes pulse{0%{{opacity:1}}50%{{opacity:0.4}}100%{{opacity:1}}}
.sec-title{
    font-size:0.82rem;font-weight:700;color:#a0b8d8;
    border-left:3px solid #3a8fff;padding-left:10px;
    margin:14px 0 10px;letter-spacing:0.3px
}
.ai-box{
    background:linear-gradient(135deg,#0d1f3c,#111e36);
    border:1px solid #2a4a7f;border-radius:10px;padding:16px 18px;
    border-left:4px solid #3a8fff
}
.ai-box .ai-title{font-size:0.8rem;font-weight:700;color:#3a8fff;margin-bottom:8px}
.ai-box .ai-content{font-size:0.8rem;color:#c0d0e8;line-height:1.8}
[data-testid="stDataFrame"]{border-radius:8px;overflow:hidden}
div[data-testid="stTabs"] button{font-size:0.8rem;font-weight:600;color:#7a9cc8}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#3a8fff!important}
div[data-baseweb="select"] > div{background:#1a2744!important;border-color:#2a3f6f!important}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────
INVALID = [-9999999, -9999999.0, -99.0, -99, -95.0, -95, -100.0, -100]
HOURS = [f'{h:02d}' for h in range(24)]
PLOT_COLORS = ['#00AAFF','#00FF88','#FF4444','#FFCC00','#CC44FF','#00E5FF','#FF6600','#AAFFCC']

PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(10,18,35,0.95)',
    font=dict(color='#a0b8d8', family='Inter, Malgun Gothic', size=11),
    margin=dict(l=8, r=8, t=36, b=8),
    legend=dict(orientation='h', y=-0.25, font=dict(size=10, color='#7a9cc8'), bgcolor='rgba(0,0,0,0)'),
    xaxis=dict(gridcolor='#1e2d4a', linecolor='#2a3f6f', tickfont=dict(size=10)),
    yaxis=dict(gridcolor='#1e2d4a', linecolor='#2a3f6f', tickfont=dict(size=10)),
    title_font=dict(size=13, color='#c0d0e8'),
    hovermode='x unified',
)

FILE_SIGNATURES = {
    '품질KPI':

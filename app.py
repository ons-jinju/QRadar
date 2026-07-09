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

/* 사이드바 */
[data-testid="stSidebar"]{background:#0f1729;border-right:1px solid #1e2d4a}
[data-testid="stSidebar"] *{color:#c8d4e8!important}
[data-testid="stSidebar"] .stSelectbox>div>div{background:#1a2744;border:1px solid #2a3f6f;color:#e0e8f5!important}
[data-testid="stSidebar"] hr{border-color:#1e2d4a!important}

/* 메트릭 카드 */
[data-testid="metric-container"]{
    background:linear-gradient(135deg,#1a2744 0%,#1e3055 100%);
    border:1px solid #2a3f6f;border-radius:10px;padding:14px 16px;
    box-shadow:0 2px 8px rgba(0,0,0,0.3)
}
[data-testid="stMetricValue"]{font-size:1.5rem!important;font-weight:700!important;color:#e8f0ff!important}
[data-testid="stMetricLabel"]{font-size:0.72rem!important;color:#7a9cc8!important;font-weight:500!important}
[data-testid="stMetricDelta"]{font-size:0.72rem!important}

/* 헤더 */
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
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}

/* 섹션 타이틀 */
.sec-title{
    font-size:0.82rem;font-weight:700;color:#a0b8d8;
    border-left:3px solid #3a8fff;padding-left:10px;
    margin:14px 0 10px;letter-spacing:0.3px
}

/* 카드 패널 */
.panel{
    background:#111e36;border:1px solid #1e2d4a;border-radius:10px;
    padding:16px;margin-bottom:14px;
}

/* KPI 배지 */
.kpi-badge{
    display:inline-block;padding:2px 10px;border-radius:12px;
    font-size:11px;font-weight:700;margin-right:4px
}
.badge-red{background:rgba(220,50,50,0.15);color:#ff6b6b;border:1px solid rgba(220,50,50,0.3)}
.badge-amber{background:rgba(255,160,0,0.15);color:#ffa500;border:1px solid rgba(255,160,0,0.3)}
.badge-green{background:rgba(0,200,100,0.15);color:#00e676;border:1px solid rgba(0,200,100,0.3)}
.badge-blue{background:rgba(58,143,255,0.15);color:#3a8fff;border:1px solid rgba(58,143,255,0.3)}

/* 모니터링 카드 */
.monitor-card{
    background:#111e36;border:1px solid #1e2d4a;border-radius:10px;
    padding:14px 16px;text-align:center;cursor:pointer;
    transition:all .2s;height:90px;display:flex;flex-direction:column;
    align-items:center;justify-content:center;
}
.monitor-card:hover{border-color:#3a8fff;background:#162236}
.monitor-card .icon{font-size:1.5rem;margin-bottom:5px}
.monitor-card .label{font-size:11px;color:#7a9cc8;font-weight:500}

/* AI 요약 */
.ai-box{
    background:linear-gradient(135deg,#0d1f3c,#111e36);
    border:1px solid #2a4a7f;border-radius:10px;padding:16px 18px;
    border-left:4px solid #3a8fff
}
.ai-box .ai-title{font-size:0.8rem;font-weight:700;color:#3a8fff;margin-bottom:8px}
.ai-box .ai-content{font-size:0.8rem;color:#c0d0e8;line-height:1.8}

/* 테이블 */
[data-testid="stDataFrame"]{border-radius:8px;overflow:hidden}

/* 탭 */
div[data-testid="stTabs"] button{
    font-size:0.8rem;font-weight:600;color:#7a9cc8;
    border-radius:6px 6px 0 0;
}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#3a8fff!important}

/* 날짜 선택기 */
.date-range-box{
    background:#111e36;border:1px solid #1e2d4a;border-radius:10px;
    padding:12px 16px;margin-bottom:14px;
    display:flex;align-items:center;gap:12px;flex-wrap:wrap
}

div[data-baseweb="select"] > div{background:#1a2744!important;border-color:#2a3f6f!important}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────
INVALID = [-9999999, -9999999.0, -99.0, -99, -95.0, -95, -100.0, -100]
HOURS = [f'{h:02d}' for h in range(24)]

PLOT_COLORS = ['#3a8fff','#00e676','#ff6b6b','#ffa500','#b388ff','#00bcd4','#ff4081','#69f0ae']

PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(15,25,45,0.6)',
    font=dict(color='#a0b8d8', family='Inter, Malgun Gothic', size=11),
    margin=dict(l=8, r=8, t=36, b=8),
    legend=dict(
        orientation='h', y=-0.25, font=dict(size=10, color='#7a9cc8'),
        bgcolor='rgba(0,0,0,0)'
    ),
    xaxis=dict(gridcolor='#1e2d4a', linecolor='#2a3f6f', tickfont=dict(size=10)),
    yaxis=dict(gridcolor='#1e2d4a', linecolor='#2a3f6f', tickfont=dict(size=10)),
    title_font=dict(size=13, color='#c0d0e8'),
    hovermode='x unified',
)

FILE_SIGNATURES = {
    '품질KPI': ['pmprbuseddlavg','rrc_succ_rate','erab_succ_rate'],
    'CEI':     ['HDVCFI','DATACFI','NEI','SEI'],
    'CQ':      ['CQ 1등급 비율','CQ전체건수','DL속도불량 건수'],
}

# ────────────────────────────────────────────
# 유틸
# ────────────────────────────────────────────
def clean(df):
    return df.replace(INVALID, np.nan)

def read_csv_auto(raw):
    for enc in ['utf-8-sig','euc-kr','utf-8','cp949']:
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except: continue
    raise ValueError("인코딩 인식 실패")

def detect_type(df):
    cols = set(df.columns)
    for t, req in FILE_SIGNATURES.items():
        if all(c in cols for c in req): return t
    return 'unknown'

def parse_dates(df):
    for dc in ['dt','std_dhm','date']:
        if dc in df.columns:
            df['_date'] = pd.to_datetime(df[dc].astype(str).str[:8], format='%Y%m%d', errors='coerce')
            df['_일자'] = df['_date'].dt.strftime('%m/%d')
            df['_dt_raw'] = df[dc].astype(str).str[:8]
            break
    if 'hh' in df.columns:
        df['_시'] = df['hh'].astype(str).str.zfill(2)
    return df

@st.cache_data(show_spinner=False)
def load_file(raw, fname):
    ext = fname.rsplit('.',1)[-1].lower()
    if ext in ('xlsx','xls'):
        xf = pd.ExcelFile(io.BytesIO(raw))
        df = pd.read_excel(io.BytesIO(raw), sheet_name=xf.sheet_names[0])
    else:
        df = read_csv_auto(raw)
    df = clean(df)
    ftype = detect_type(df)
    df = parse_dates(df)
    return df, ftype

def color_val(v, good_dir='high', warn=70, bad=60):
    if pd.isna(v): return '—'
    if good_dir == 'high':
        c = '🟢' if v>=warn else ('🟡' if v>=bad else '🔴')
    else:
        c = '🟢' if v<=warn else ('🟡' if v<=bad*1.5 else '🔴')
    return f"{c} {v:.2f}"

def make_line(df, x, ys, title, colors=None, thresh=None, thresh_label=''):
    fig = go.Figure()
    cols = colors or PLOT_COLORS
    for i,(y,label) in enumerate(ys):
        sub = df[[x,y]].dropna()
        fig.add_trace(go.Scatter(
            x=sub[x], y=sub[y], name=label,
            mode='lines+markers', marker=dict(size=4),
            line=dict(width=2, color=cols[i % len(cols)])
        ))
    if thresh is not None:
        fig.add_hline(y=thresh, line_dash='dash', line_color='#ff6b6b',
                      annotation_text=thresh_label, annotation_font_size=10,
                      annotation_font_color='#ff6b6b')
    layout = dict(**PLOTLY_LAYOUT, title=title, height=280)
    layout['xaxis']['title'] = ''
    fig.update_layout(**layout)
    return fig

def make_bar(df, x, y, title, color_scale=None, thresh=None):
    cs = color_scale or [[0,'#00e676'],[0.4,'#ffa500'],[0.7,'#ff6b6b'],[1,'#cc0000']]
    fig = px.bar(df, x=x, y=y, color=y, color_continuous_scale=cs, title=title)
    if thresh:
        fig.add_hline(y=thresh, line_dash='dash', line_color='#ff6b6b')
    layout = dict(**PLOTLY_LAYOUT, height=280, coloraxis_showscale=False)
    fig.update_layout(**layout)
    fig.update_traces(marker_line_width=0)
    return fig

def make_heatmap(pivot, title, thresh):
    colorscale = [
        [0, '#0d1f3c'],
        [max(thresh/100-0.001,0), '#0d1f3c'],
        [thresh/100, '#7a3000'],
        [0.50, '#cc4400'],
        [0.70, '#ff2200'],
        [1.0, '#ff0000'],
    ]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=colorscale, zmin=0, zmax=100,
        text=pivot.values.round(1), texttemplate='%{text}',
        textfont=dict(size=8, color='#c0d0e8'),
        hovertemplate='%{y}<br>%{x}시: %{z:.1f}%<extra></extra>',
        colorbar=dict(title='%', thickness=10, tickfont=dict(color='#a0b8d8')),
    ))
    layout = dict(**PLOTLY_LAYOUT, title=title,
                  height=max(280, len(pivot)*24+80))
    layout['xaxis']['title'] = '시각(시)'
    layout['yaxis']['autorange'] = 'reversed'
    fig.update_layout(**layout)
    return fig

# ────────────────────────────────────────────
# 날짜 필터 적용
# ────────────────────────────────────────────
def apply_date_filter(df, mode, single_date, date_range):
    if '_date' not in df.columns: return df
    if mode == '단일 날짜':
        return df[df['_date'].dt.date == single_date]
    else:
        s, e = date_range
        return df[(df['_date'].dt.date >= s) & (df['_date'].dt.date <= e)]

# ────────────────────────────────────────────
# AI 요약 생성
# ────────────────────────────────────────────
def generate_ai_summary(df, ftype, prb_thresh):
    lines = []
    if ftype == '품질KPI':
        prb_max = df['pmprbuseddlavg'].max() if 'pmprbuseddlavg' in df.columns else None
        rrc_min = df['rrc_succ_rate'].min() if 'rrc_succ_rate' in df.columns else None
        cd_max  = df['cd_rate'].max() if 'cd_rate' in df.columns else None
        sinr    = df['pmsinrpucchdistr'].mean() if 'pmsinrpucchdistr' in df.columns else None
        bad_cnt = int((df['pmprbuseddlavg'] >= prb_thresh).sum()) if 'pmprbuseddlavg' in df.columns else 0
        name_col = 'eqp_origin_nm'
        bad_sites = df[df['pmprbuseddlavg']>=prb_thresh][name_col].nunique() if name_col in df.columns else 0

        if prb_max and pd.notna(prb_max):
            status = '⚠️ 고부하' if prb_max>=prb_thresh else '✅ 양호'
            lines.append(f"• DL PRB 최대 **{prb_max:.1f}%** ({status}) — 불량({prb_thresh}%↑) {bad_cnt}건, {bad_sites}개 국소")
        if rrc_min and pd.notna(rrc_min):
            status = '⚠️ 주의' if rrc_min<99 else '✅ 정상'
            lines.append(f"• RRC 접속성공률 최저 **{rrc_min:.2f}%** ({status})")
        if cd_max and pd.notna(cd_max):
            status = '⚠️ 발생' if cd_max>0 else '✅ 없음'
            lines.append(f"• CD율 최대 **{cd_max:.3f}%** ({status})")
        if sinr and pd.notna(sinr):
            status = '✅ 양호' if sinr>2 else '⚠️ 낮음'
            lines.append(f"• SINR(PUCCH) 평균 **{sinr:.2f} dB** ({status})")
        if bad_cnt > 0:
            worst = df.nlargest(1,'pmprbuseddlavg')[name_col].values[0] if name_col in df.columns else '-'
            lines.append(f"• 🔴 최고부하 국소: **{worst}**")
        else:
            lines.append("• 🟢 분석 기간 내 PRB 불량 국소 없음")

    elif ftype == 'CEI':
        hdv = df['HDVCFI'].mean() if 'HDVCFI' in df.columns else None
        data = df['DATACFI'].mean() if 'DATACFI' in df.columns else None
        nei = df['NEI'].mean() if 'NEI' in df.columns else None
        if hdv and pd.notna(hdv):
            lines.append(f"• HDV CFI 평균 **{hdv:.1f}점** ({'✅' if hdv>=80 else '⚠️'})")
        if data and pd.notna(data):
            lines.append(f"• DATA CFI 평균 **{data:.1f}점** ({'✅' if data>=80 else '⚠️'})")
        if nei and pd.notna(nei):
            lines.append(f"• NEI 평균 **{nei:.1f}점** ({'✅' if nei>=80 else '⚠️'})")

    elif ftype == 'CQ':
        cq1 = df['CQ 1등급 비율'].mean() if 'CQ 1등급 비율' in df.columns else None
        dl_bad = df['DL속도불량 건수'].sum() if 'DL속도불량 건수' in df.columns else None
        if cq1 and pd.notna(cq1):
            lines.append(f"• CQ 1등급 비율 평균 **{cq1:.1f}%** ({'✅' if cq1>=85 else '⚠️'})")
        if dl_bad and pd.notna(dl_bad):
            lines.append(f"• DL속도불량 총 **{int(dl_bad):,}건**")
        worst = df.nsmallest(3,'CQ 1등급 비율')['cell_nm'].tolist() if 'cell_nm' in df.columns else []
        if worst:
            lines.append(f"• 🔴 불량 상위 셀: {', '.join([str(w) for w in worst])}")

    return '\n'.join(lines) if lines else "분석 데이터가 부족합니다."

# ────────────────────────────────────────────
# 렌더러 — 품질KPI
# ────────────────────────────────────────────
def render_quality(df, prb_thresh, view_mode):
    nc = 'eqp_origin_nm'
    fc = 'freq_typ_nm'

    # ── 요약 지표
    prb_max  = df['pmprbuseddlavg'].max() if 'pmprbuseddlavg' in df.columns else np.nan
    rrc_avg  = df['rrc_succ_rate'].mean() if 'rrc_succ_rate' in df.columns else np.nan
    erab_avg = df['erab_succ_rate'].mean() if 'erab_succ_rate' in df.columns else np.nan
    cd_max   = df['cd_rate'].max() if 'cd_rate' in df.columns else np.nan
    sinr_avg = df['pmsinrpucchdistr'].mean() if 'pmsinrpucchdistr' in df.columns else np.nan
    conc_max = df['pmactiveuedlmax'].max() if 'pmactiveuedlmax' in df.columns else np.nan

    m = st.columns(6)
    m[0].metric("DL PRB 최대", f"{prb_max:.1f}%" if pd.notna(prb_max) else "—",
                delta="⚠ 불량" if pd.notna(prb_max) and prb_max>=prb_thresh else "✅ 정상")
    m[1].metric("RRC 성공률", f"{rrc_avg:.2f}%" if pd.notna(rrc_avg) else "—")
    m[2].metric("ERAB 성공률", f"{erab_avg:.2f}%" if pd.notna(erab_avg) else "—")
    m[3].metric("CD율 최대", f"{cd_max:.3f}%" if pd.notna(cd_max) else "—",
                delta="⚠ 발생" if pd.notna(cd_max) and cd_max>0 else "✅ 없음")
    m[4].metric("SINR(PUCCH)", f"{sinr_avg:.2f}" if pd.notna(sinr_avg) else "—")
    m[5].metric("최대 동시접속", f"{int(conc_max):,}" if pd.notna(conc_max) else "—")

    st.markdown("---")

    # ── 시간별 / 일별 탭
    time_tabs = st.tabs(["⏰ 시간별 추이", "📅 일별 추이"])

    with time_tabs[0]:  # 시간별
        if '_시' not in df.columns:
            st.info("시간(hh) 컬럼이 없습니다.")
        else:
            g = df.groupby('_시').agg(
                DL_PRB=('pmprbuseddlavg','mean'),
                UL_PRB=('pmprbutildlmax','mean') if 'pmprbutildlmax' in df.columns else ('pmprbuseddlavg','mean'),
                RRC성공률=('rrc_succ_rate','mean'),
                ERAB성공률=('erab_succ_rate','mean'),
                CD율=('cd_rate','mean') if 'cd_rate' in df.columns else ('rrc_succ_rate','count'),
                DL_Volume=('pmpdcpvoldldrb_thruput','mean') if 'pmpdcpvoldldrb_thruput' in df.columns else ('pmprbuseddlavg','count'),
                SINR=('pmsinrpucchdistr','mean') if 'pmsinrpucchdistr' in df.columns else ('pmprbuseddlavg','count'),
            ).reset_index()

            c1,c2 = st.columns(2)
            with c1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=g['_시'],y=g['DL_PRB'],name='DL PRB',
                    mode='lines+markers',line=dict(color='#3a8fff',width=2),marker=dict(size=5)))
                if 'UL_PRB' in g.columns:
                    fig.add_trace(go.Scatter(x=g['_시'],y=g['UL_PRB'],name='UL PRB(MAX)',
                        mode='lines+markers',line=dict(color='#ffa500',width=2),marker=dict(size=5)))
                fig.add_hline(y=prb_thresh,line_dash='dash',line_color='#ff6b6b',
                              annotation_text=f'불량기준 {prb_thresh}%',annotation_font_color='#ff6b6b')
                layout = dict(**PLOTLY_LAYOUT, title='시간대별 PRB 사용률 (%)', height=260)
                fig.update_layout(**layout)
                st.plotly_chart(fig,use_container_width=True)

            with c2:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=g['_시'],y=g['DL_Volume'],name='DL Throughput',
                    mode='lines+markers',line=dict(color='#00e676',width=2),marker=dict(size=5)))
                layout2 = dict(**PLOTLY_LAYOUT, title='시간대별 DL Throughput (kbps)', height=260)
                fig2.update_layout(**layout2)
                st.plotly_chart(fig2,use_container_width=True)

            c3,c4 = st.columns(2)
            with c3:
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=g['_시'],y=g['RRC성공률'],name='RRC',
                    mode='lines+markers',line=dict(color='#3a8fff',width=2),marker=dict(size=4)))
                fig3.add_trace(go.Scatter(x=g['_시'],y=g['ERAB성공률'],name='ERAB',
                    mode='lines+markers',line=dict(color='#b388ff',width=2),marker=dict(size=4)))
                fig3.add_hline(y=99,line_dash='dash',line_color='#ff6b6b',
                               annotation_text='99% 기준',annotation_font_color='#ff6b6b')
                layout3 = dict(**PLOTLY_LAYOUT, title='시간대별 접속성공률 (%)', height=260)
                fig3.update_layout(**layout3)
                st.plotly_chart(fig3,use_container_width=True)

            with c4:
                fig4 = go.Figure()
                fig4.add_trace(go.Scatter(x=g['_시'],y=g['SINR'],name='SINR(PUCCH)',
                    mode='lines+markers',line=dict(color='#00bcd4',width=2),marker=dict(size=4)))
                layout4 = dict(**PLOTLY_LAYOUT, title='시간대별 SINR(PUCCH)', height=260)
                fig4.update_layout(**layout4)
                st.plotly_chart(fig4,use_container_width=True)

    with time_tabs[1]:  # 일별
        if '_일자' not in df.columns:
            st.info("날짜 컬럼이 없습니다.")
        else:
            gd = df.groupby('_일자').agg(
                DL_PRB_max=('pmprbuseddlavg','max'),
                DL_PRB_avg=('pmprbuseddlavg','mean'),
                RRC성공률=('rrc_succ_rate','mean'),
                DL_Volume=('pmpdcpvoldldrb_thruput','mean') if 'pmpdcpvoldldrb_thruput' in df.columns else ('pmprbuseddlavg','count'),
            ).reset_index()

            c1,c2 = st.columns(2)
            with c1:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=gd['_일자'],y=gd['DL_PRB_max'],name='PRB 최대',
                    marker_color=['#ff6b6b' if v>=prb_thresh else '#3a8fff' for v in gd['DL_PRB_max']]))
                fig.add_trace(go.Scatter(x=gd['_일자'],y=gd['DL_PRB_avg'],name='PRB 평균',
                    mode='lines+markers',line=dict(color='#ffa500',width=2)))
                fig.add_hline(y=prb_thresh,line_dash='dash',line_color='#ff6b6b')
                layout = dict(**PLOTLY_LAYOUT, title='일별 DL PRB (최대/평균)', height=260, barmode='overlay')
                fig.update_layout(**layout)
                st.plotly_chart(fig,use_container_width=True)
            with c2:
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=gd['_일자'],y=gd['DL_Volume'],name='DL Volume',
                    marker_color='#00e676'))
                layout2 = dict(**PLOTLY_LAYOUT, title='일별 DL Throughput 평균', height=260)
                fig2.update_layout(**layout2)
                st.plotly_chart(fig2,use_container_width=True)

    # ── 불량 히트맵
    st.markdown('<div class="sec-title">🔴 DL PRB 불량 시간대 히트맵</div>', unsafe_allow_html=True)
    if '_시' in df.columns and nc in df.columns:
        pivot = df.groupby([nc,'_시'])['pmprbuseddlavg'].max().unstack('_시')
        pivot = pivot.reindex(columns=HOURS, fill_value=0).fillna(0)
        # 불량 셀만
        bad_mask = (pivot >= prb_thresh).any(axis=1)
        if bad_mask.any():
            st.plotly_chart(make_heatmap(pivot[bad_mask], f'PRB ≥ {prb_thresh}% 발생 국소', prb_thresh),
                            use_container_width=True)
        else:
            st.success(f"✅ DL PRB {prb_thresh}% 이상 불량 없음")

    # ── SINR 분포
    st.markdown('<div class="sec-title">📡 SINR / 간섭 분포</div>', unsafe_allow_html=True)
    sinr_cols = [c for c in ['pmsinrpucchdistr','pmsinrpuschdistr'] if c in df.columns]
    inter_col = 'pmradiorecinterferencepwr'
    c1,c2 = st.columns(2)
    with c1:
        if sinr_cols and nc in df.columns:
            sinr_df = df.groupby(nc)[sinr_cols].mean().reset_index().sort_values(sinr_cols[0])
            fig5 = px.bar(sinr_df.head(20), x=nc, y=sinr_cols[0], title='SINR PUCCH 평균 (하위 20, 낮을수록 불량)',
                         color=sinr_cols[0],
                         color_continuous_scale=[[0,'#ff2200'],[0.5,'#ffa500'],[1,'#00e676']])
            fig5.update_layout(**dict(**PLOTLY_LAYOUT, height=280, coloraxis_showscale=False))
            fig5.update_xaxes(tickangle=-35, tickfont=dict(size=9))
            st.plotly_chart(fig5, use_container_width=True)
    with c2:
        if inter_col in df.columns and nc in df.columns:
            inter_df = df.groupby(nc)[inter_col].mean().reset_index().sort_values(inter_col, ascending=False)
            fig6 = px.bar(inter_df.head(20), x=nc, y=inter_col, title='간섭전력 평균 (상위 20, 높을수록 불량)',
                         color=inter_col,
                         color_continuous_scale=[[0,'#00e676'],[0.5,'#ffa500'],[1,'#ff2200']])
            fig6.update_layout(**dict(**PLOTLY_LAYOUT, height=280, coloraxis_showscale=False))
            fig6.update_xaxes(tickangle=-35, tickfont=dict(size=9))
            st.plotly_chart(fig6, use_container_width=True)

    # ── CEI/CFI
    st.markdown('<div class="sec-title">📊 CEI / CFI 품질지수</div>', unsafe_allow_html=True)
    cfi_cols = [c for c in ['new_hdv_cfi_value','new_data_cfi_value'] if c in df.columns]
    if cfi_cols and nc in df.columns:
        cfi_df = df.groupby(nc)[cfi_cols].mean().reset_index()
        cfi_df.columns = [nc] + ['HDV CFI','DATA CFI'][:len(cfi_cols)]
        c1,c2 = st.columns(2)
        with c1:
            fig7 = px.bar(cfi_df.sort_values('HDV CFI').head(20), x=nc, y='HDV CFI',
                         title='HDV CFI (하위 20)',
                         color='HDV CFI',
                         color_continuous_scale=[[0,'#ff2200'],[0.5,'#ffa500'],[1,'#00e676']])
            fig7.add_hline(y=80, line_dash='dash', line_color='#ff6b6b')
            fig7.update_layout(**dict(**PLOTLY_LAYOUT, height=280, coloraxis_showscale=False))
            fig7.update_xaxes(tickangle=-35, tickfont=dict(size=9))
            st.plotly_chart(fig7, use_container_width=True)
        if len(cfi_cols)>1:
            with c2:
                fig8 = px.bar(cfi_df.sort_values('DATA CFI').head(20), x=nc, y='DATA CFI',
                             title='DATA CFI (하위 20)',
                             color='DATA CFI',
                             color_continuous_scale=[[0,'#ff2200'],[0.5,'#ffa500'],[1,'#00e676']])
                fig8.add_hline(y=80, line_dash='dash', line_color='#ff6b6b')
                fig8.update_layout(**dict(**PLOTLY_LAYOUT, height=280, coloraxis_showscale=False))
                fig8.update_xaxes(tickangle=-35, tickfont=dict(size=9))
                st.plotly_chart(fig8, use_container_width=True)
    else:
        st.info("CFI 컬럼이 없거나 유효한 값이 없습니다.")

# ────────────────────────────────────────────
# 렌더러 — CEI
# ────────────────────────────────────────────
def render_cei(df, prb_thresh, view_mode):
    nc = 'enb_name'
    cfi_cols = [c for c in ['HDVCFI','DATACFI','NEI','SEI'] if c in df.columns]

    m = st.columns(len(cfi_cols))
    labels = {'HDVCFI':'HDV CFI','DATACFI':'DATA CFI','NEI':'NEI','SEI':'SEI'}
    for i,col in enumerate(cfi_cols):
        val = df[col].mean()
        m[i].metric(labels.get(col,col), f"{val:.1f}" if pd.notna(val) else "—",
                    delta="✅ 양호" if pd.notna(val) and val>=80 else "⚠️ 주의")

    st.markdown("---")
    time_tabs = st.tabs(["📅 일별 트렌드", "🏢 국소별 현황", "🔍 세부항목"])

    with time_tabs[0]:
        if '_일자' in df.columns:
            gd = df.groupby('_일자')[cfi_cols].mean().reset_index()
            fig = go.Figure()
            for i,col in enumerate(cfi_cols):
                fig.add_trace(go.Scatter(x=gd['_일자'],y=gd[col],name=labels.get(col,col),
                    mode='lines+markers',line=dict(color=PLOT_COLORS[i],width=2),marker=dict(size=6)))
            fig.add_hline(y=80,line_dash='dash',line_color='#ff6b6b',annotation_text='80점 기준')
            layout = dict(**PLOTLY_LAYOUT, title='일별 CFI/CEI 트렌드', height=300)
            fig.update_layout(**layout)
            st.plotly_chart(fig,use_container_width=True)

    with time_tabs[1]:
        if nc in df.columns:
            site_df = df.groupby(nc)[cfi_cols].mean().reset_index()
            for col in cfi_cols:
                bad = site_df[site_df[col]<80].sort_values(col).head(15)
                if not bad.empty:
                    fig = px.bar(bad, x=nc, y=col, title=f'{labels.get(col,col)} 불량 국소 (80점 미만)',
                                color=col,
                                color_continuous_scale=[[0,'#ff2200'],[0.5,'#ffa500'],[1,'#00e676']])
                    fig.add_hline(y=80,line_dash='dash',line_color='#ff6b6b')
                    fig.update_layout(**dict(**PLOTLY_LAYOUT,height=260,coloraxis_showscale=False))
                    fig.update_xaxes(tickangle=-35,tickfont=dict(size=9))
                    st.plotly_chart(fig,use_container_width=True)

    with time_tabs[2]:
        detail_cols = [c for c in df.columns if any(k in c for k in ['접속','음질','단절','커버리지','속도','화면전환'])]
        if detail_cols:
            st.dataframe(df.groupby(nc)[detail_cols[:8]].mean().round(2).reset_index(),
                        use_container_width=True, height=300)

# ────────────────────────────────────────────
# 렌더러 — CQ
# ────────────────────────────────────────────
def render_cq(df, prb_thresh, view_mode):
    nc = 'cell_nm'
    grade_cols = [c for c in ['1등급 건수','2등급 건수','3등급 건수','4등급 건수','5등급 건수'] if c in df.columns]
    bad_cols = [c for c in ['DL속도불량 건수','UL속도불량 건수','Latency불량 건수',
                             'Jitter불량 건수','Packet불량 건수'] if c in df.columns]

    cq1_avg = df['CQ 1등급 비율'].mean() if 'CQ 1등급 비율' in df.columns else np.nan
    total   = int(df['CQ전체건수'].sum()) if 'CQ전체건수' in df.columns else 0
    dl_bad  = int(df['DL속도불량 건수'].sum()) if 'DL속도불량 건수' in df.columns else 0
    lat_bad = int(df['Latency불량 건수'].sum()) if 'Latency불량 건수' in df.columns else 0

    m = st.columns(4)
    m[0].metric("CQ 1등급 비율 평균", f"{cq1_avg:.1f}%" if pd.notna(cq1_avg) else "—",
                delta="✅ 양호" if pd.notna(cq1_avg) and cq1_avg>=85 else "⚠️ 주의")
    m[1].metric("CQ 총 건수", f"{total:,}")
    m[2].metric("DL속도불량", f"{dl_bad:,}건")
    m[3].metric("Latency불량", f"{lat_bad:,}건")

    st.markdown("---")
    time_tabs = st.tabs(["📈 CQ 트렌드", "🏆 CQ Top 50 불량", "⚠ 불량 유형", "📊 등급 분포"])

    with time_tabs[0]:
        if '_일자' in df.columns and 'CQ 1등급 비율' in df.columns:
            gd = df.groupby('_일자')['CQ 1등급 비율'].mean().reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=gd['_일자'],y=gd['CQ 1등급 비율'],name='CQ 1등급 비율',
                mode='lines+markers',line=dict(color='#3a8fff',width=2),
                fill='tozeroy',fillcolor='rgba(58,143,255,0.1)'))
            fig.add_hline(y=85,line_dash='dash',line_color='#ff6b6b',annotation_text='목표 85%')
            layout = dict(**PLOTLY_LAYOUT, title='일별 CQ 1등급 비율 트렌드', height=280)
            fig.update_layout(**layout)
            st.plotly_chart(fig,use_container_width=True)

    with time_tabs[1]:  # CQ Top 50 불량
        if nc in df.columns and 'CQ 1등급 비율' in df.columns:
            top50_cols = [nc,'network_type','CQ 1등급 비율','CQ전체건수'] + grade_cols[:3] + bad_cols[:3]
            top50_cols = [c for c in top50_cols if c in df.columns]
            top50 = df.groupby(nc)[top50_cols[1:]].mean().reset_index()
            top50 = top50.nsmallest(50,'CQ 1등급 비율')
            for col in top50.select_dtypes('float64').columns:
                top50[col] = top50[col].round(2)
            st.dataframe(top50, use_container_width=True, height=450)

    with time_tabs[2]:  # 불량 유형
        if bad_cols and nc in df.columns:
            bad_df = df.groupby(nc)[bad_cols].sum().reset_index()
            bad_df['총불량'] = bad_df[bad_cols].sum(axis=1)
            bad_df = bad_df.nlargest(15,'총불량')
            fig2 = px.bar(bad_df, x=nc, y=bad_cols, barmode='stack',
                         title='불량 유형별 건수 (상위 15 셀)',
                         color_discrete_sequence=PLOT_COLORS)
            fig2.update_layout(**dict(**PLOTLY_LAYOUT, height=300))
            fig2.update_xaxes(tickangle=-35, tickfont=dict(size=9))
            st.plotly_chart(fig2,use_container_width=True)

    with time_tabs[3]:  # 등급 분포
        if grade_cols:
            total_grades = df[grade_cols].sum()
            c1,c2 = st.columns(2)
            with c1:
                fig3 = px.pie(values=total_grades.values, names=total_grades.index,
                             title='전체 CQ 등급 분포',
                             color_discrete_sequence=['#3a8fff','#00e676','#ffa500','#ff6b6b','#cc0000'])
                fig3.update_layout(**dict(**PLOTLY_LAYOUT, height=300))
                st.plotly_chart(fig3,use_container_width=True)
            with c2:
                if '_일자' in df.columns:
                    gd2 = df.groupby('_일자')[grade_cols].sum().reset_index()
                    fig4 = px.bar(gd2, x='_일자', y=grade_cols, barmode='stack',
                                 title='일별 CQ 등급 건수',
                                 color_discrete_sequence=['#3a8fff','#00e676','#ffa500','#ff6b6b','#cc0000'])
                    fig4.update_layout(**dict(**PLOTLY_LAYOUT, height=300))
                    st.plotly_chart(fig4,use_container_width=True)

# ────────────────────────────────────────────
# 모니터링 카드
# ────────────────────────────────────────────
def render_monitor_cards():
    st.markdown('<div class="sec-title">🖥 모니터링 바로가기</div>', unsafe_allow_html=True)
    cards = [
        ("🔴","gREMS","장애 모니터링"),
        ("📊","MIBOS","성능 현황"),
        ("📡","EMS","장비 관리"),
        ("📈","CQ Portal","체감품질"),
        ("🗺","GIS","지도 현황"),
        ("📋","보고서","주간 보고"),
    ]
    cols = st.columns(len(cards))
    for i,(icon,name,desc) in enumerate(cards):
        with cols[i]:
            st.markdown(f"""
            <div class="monitor-card">
              <div class="icon">{icon}</div>
              <div style="font-size:12px;font-weight:700;color:#c0d0e8">{name}</div>
              <div class="label">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

# ────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 10px'>
      <div style='font-size:1.4rem;font-weight:800;color:#fff'>Q<span style="color:#3a8fff">Radar</span></div>
      <div style='font-size:10px;color:#5a7aa8;margin-top:2px'>Network Quality Radar</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**📂 파일 업로드**")
    st.caption("xlsx / csv · 여러 파일 동시 가능")
    uploaded_files = st.file_uploader(
        "파일 선택",
        type=['csv','xlsx','xls'],
        accept_multiple_files=True,
        label_visibility='collapsed'
    )

    st.markdown("---")
    st.markdown("**📅 날짜 필터**")
    date_mode = st.radio("모드", ["날짜 범위","단일 날짜"], horizontal=True, label_visibility='collapsed')

    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    if date_mode == "날짜 범위":
        d_start = st.date_input("시작일", week_ago, label_visibility='collapsed')
        d_end   = st.date_input("종료일", today, label_visibility='collapsed')
        date_range = (d_start, d_end)
        single_date = None
    else:
        single_date = st.date_input("날짜 선택", today, label_visibility='collapsed')
        date_range = None

    st.markdown("---")
    st.markdown("**⚙ 분석 설정**")
    prb_thresh = st.slider("PRB 불량 기준 (%)", 10, 70, 30, 5)

    st.markdown("---")
    st.markdown("<div style='font-size:10px;color:#3a5a80;text-align:center'>진주품질개선팀 · 내부용</div>",
                unsafe_allow_html=True)

# ────────────────────────────────────────────
# 헤더
# ────────────────────────────────────────────
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
date_label = f"{d_start} ~ {d_end}" if date_mode=="날짜 범위" else str(single_date)

st.markdown(f"""
<div class="qradar-header">
  <div>
    <div class="title">📡 Q<span>Radar</span></div>
    <div class="sub">Network Quality Radar · 진주품질개선팀 · {date_label}</div>
  </div>
  <div class="status">
    <div style="font-size:12px;color:#7a9cc8"><span class="dot"></span>LIVE</div>
    <div style="font-size:11px;color:#4a6a90;margin-top:4px">{now_str}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# 모니터링 카드 (항상 상단)
render_monitor_cards()
st.markdown("---")

# ────────────────────────────────────────────
# 파일 없으면 안내
# ────────────────────────────────────────────
if not uploaded_files:
    st.markdown("""
    <div style='background:#111e36;border:1px dashed #2a3f6f;border-radius:12px;
                padding:40px;text-align:center;color:#5a7aa8'>
      <div style='font-size:2.5rem;margin-bottom:12px'>📂</div>
      <div style='font-size:1rem;font-weight:600;color:#7a9cc8;margin-bottom:8px'>파일을 업로드해 주세요</div>
      <div style='font-size:0.8rem;line-height:1.8'>
        👈 왼쪽 사이드바에서 파일 선택<br>
        <span style='color:#3a8fff'>품질KPI</span> · <span style='color:#00e676'>CEI/CFI</span> · <span style='color:#ffa500'>CQ등급</span> CSV/xlsx 자동 인식<br>
        여러 파일을 한 번에 업로드할 수 있어요
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ────────────────────────────────────────────
# 파일 로드
# ────────────────────────────────────────────
loaded = []
for uf in uploaded_files:
    raw = uf.read()
    try:
        df, ftype = load_file(raw, uf.name)
        # 날짜 필터
        df = apply_date_filter(df, date_mode, single_date, date_range)
        loaded.append((uf.name, df, ftype))
        type_labels = {'품질KPI':'📶 품질KPI','CEI':'📊 CEI/CFI','CQ':'🏆 CQ등급','unknown':'❓ 기타'}
        st.sidebar.success(f"{type_labels.get(ftype,ftype)}\n{uf.name[:22]}")
    except Exception as e:
        st.sidebar.error(f"❌ {uf.name[:18]}: {e}")

if not loaded:
    st.error("파일을 읽을 수 없습니다. 파일을 확인해 주세요.")
    st.stop()

# ────────────────────────────────────────────
# 파일별 탭
# ────────────────────────────────────────────
if len(loaded) == 1:
    fname, df, ftype = loaded[0]
    file_tabs = None
else:
    icon_map = {'품질KPI':'📶','CEI':'📊','CQ':'🏆'}
    tab_names = [f"{icon_map.get(ft,'❓')} {fn[:15]}" for fn,_,ft in loaded]
    file_tabs = st.tabs(tab_names)

view_mode = '둘 다'  # 항상 둘 다 탭으로

def render_file(fname, df, ftype):
    type_labels = {'품질KPI':'📶 품질KPI (PRB·접속·SINR·CEI)','CEI':'📊 CEI/CFI 체감품질지수','CQ':'🏆 CQ 등급 현황','unknown':'❓ 미인식'}
    st.markdown(f"<div class='sec-title'>{type_labels.get(ftype,ftype)} · <code style='font-size:10px'>{fname}</code></div>", unsafe_allow_html=True)

    if df.empty:
        st.warning("선택한 날짜 범위에 데이터가 없습니다.")
        return

    # AI 요약
    summary = generate_ai_summary(df, ftype, prb_thresh)
    st.markdown(f"""
    <div class="ai-box">
      <div class="ai-title">🤖 AI 분석 요약</div>
      <div class="ai-content">{summary.replace(chr(10),'<br>')}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    # 렌더러
    if ftype == '품질KPI':   render_quality(df, prb_thresh, view_mode)
    elif ftype == 'CEI':     render_cei(df, prb_thresh, view_mode)
    elif ftype == 'CQ':      render_cq(df, prb_thresh, view_mode)
    else:
        st.warning("자동 인식 실패. 수치 컬럼을 직접 선택해 분석하세요.")
        num_cols = df.select_dtypes(include='number').columns.tolist()
        str_cols = df.select_dtypes(include='object').columns.tolist()
        c1,c2 = st.columns(2)
        xc = c1.selectbox("X축", str_cols+num_cols, key=f"ux_{fname}")
        yc = c2.selectbox("Y축", num_cols, key=f"uy_{fname}")
        if xc and yc:
            fig = px.bar(df.head(50), x=xc, y=yc)
            fig.update_layout(**dict(**PLOTLY_LAYOUT, height=300))
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df.head(100), use_container_width=True)

if file_tabs:
    for i,(fname,df,ftype) in enumerate(loaded):
        with file_tabs[i]:
            render_file(fname,df,ftype)
else:
    fname,df,ftype = loaded[0]
    render_file(fname,df,ftype)

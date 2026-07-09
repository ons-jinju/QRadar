import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io, re

# ────────────────────────────────────────────
# 페이지 설정
# ────────────────────────────────────────────
st.set_page_config(
    page_title="진주품질 대시보드",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
html,body,[class*="css"]{font-family:'Malgun Gothic',sans-serif}
[data-testid="metric-container"]{background:#fff;border:1px solid #e0e4f0;border-radius:8px;padding:12px 16px}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1.5rem;font-weight:700;color:#1a2744}
[data-testid="metric-container"] [data-testid="stMetricLabel"]{font-size:0.73rem;color:#7a84a8}
[data-testid="stSidebar"]{background:#1a2744}
[data-testid="stSidebar"] *{color:#e0e6f5!important}
.main-header{background:linear-gradient(135deg,#1a2744,#243b6e);color:#fff;
             padding:16px 22px;border-radius:8px;margin-bottom:16px;border-bottom:3px solid #3a5fcc}
.main-header h1{font-size:1.35rem;font-weight:700;margin:0}
.main-header p{font-size:0.76rem;color:#b0bde0;margin:3px 0 0}
.sec-title{font-size:0.83rem;font-weight:700;color:#3a4470;
           border-left:3px solid #3a5fcc;padding-left:8px;margin:6px 0 10px}
.file-type-badge{display:inline-block;padding:3px 10px;border-radius:12px;
                 font-size:11px;font-weight:700;margin-right:6px}
div[data-testid="stTabs"] button{font-size:0.83rem}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────
# 파일 타입 자동 감지
# ────────────────────────────────────────────
FILE_SIGNATURES = {
    '품질KPI': {
        'required': ['pmprbuseddlavg', 'rrc_succ_rate', 'erab_succ_rate'],
        'date_col': 'dt', 'hour_col': 'hh',
        'name_col': 'eqp_origin_nm', 'cell_col': 'cell_num',
        'freq_col': 'freq_typ_nm', 'area_col': 'sgg_nm',
        'label': '📶 품질KPI (PRB·접속·SINR·CEI)',
        'color': '#1861c2',
    },
    'CEI/CFI': {
        'required': ['HDVCFI', 'DATACFI', 'NEI', 'SEI'],
        'date_col': 'dt', 'hour_col': None,
        'name_col': 'enb_name', 'cell_col': 'cell_id',
        'freq_col': 'freq_nm', 'area_col': 'gu_name',
        'label': '📊 CEI/CFI (체감품질지수)',
        'color': '#0a7c55',
    },
    'CQ등급': {
        'required': ['CQ 1등급 비율', 'CQ전체건수', 'DL속도불량 건수'],
        'date_col': 'dt', 'hour_col': None,
        'name_col': 'cell_nm', 'cell_col': 'cell_id',
        'freq_col': None, 'area_col': 'op_team_org_nm',
        'label': '🏆 CQ등급 (체감품질등급)',
        'color': '#c55a00',
    },
}

INVALID_VALUES = [-9999999, -9999999.0, -99.0, -99, -95.0, -95, -100.0, -100]

def detect_file_type(df):
    cols = set(df.columns)
    for ftype, sig in FILE_SIGNATURES.items():
        if all(c in cols for c in sig['required']):
            return ftype
    return 'unknown'

def clean_df(df):
    """무효값 NaN 처리"""
    df = df.copy()
    for v in INVALID_VALUES:
        df = df.replace(v, np.nan)
    return df

def read_csv_auto(raw_bytes):
    for enc in ['utf-8-sig', 'euc-kr', 'utf-8', 'cp949']:
        try:
            return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
        except Exception:
            continue
    raise ValueError("CSV 인코딩을 인식할 수 없습니다.")

@st.cache_data(show_spinner=False)
def load_and_detect(raw_bytes, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in ('xlsx', 'xls'):
        try:
            xf = pd.ExcelFile(io.BytesIO(raw_bytes))
            sheets = xf.sheet_names
            # 첫 시트 시도
            df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sheets[0])
        except Exception as e:
            raise ValueError(f"엑셀 읽기 오류: {e}")
    else:
        df = read_csv_auto(raw_bytes)

    df = clean_df(df)
    ftype = detect_file_type(df)

    # 날짜 파싱
    sig = FILE_SIGNATURES.get(ftype, {})
    date_col = sig.get('date_col', 'dt')
    if date_col and date_col in df.columns:
        df['_date'] = pd.to_datetime(df[date_col].astype(str), format='%Y%m%d', errors='coerce')
        df['_일자'] = df['_date'].dt.strftime('%m/%d')
    hour_col = sig.get('hour_col')
    if hour_col and hour_col in df.columns:
        df['_시'] = df[hour_col].astype(str).str.zfill(2)
    elif 'hh' in df.columns:
        df['_시'] = df['hh'].astype(str).str.zfill(2)

    return df, ftype

# ────────────────────────────────────────────
# 분석 함수 — 품질KPI
# ────────────────────────────────────────────
HOURS = [f'{h:02d}' for h in range(24)]

def render_quality_kpi(df, filters):
    sig = FILE_SIGNATURES['품질KPI']
    name_col = sig['name_col']
    freq_col = sig['freq_col']

    # ── 요약 지표
    prb_max  = df['pmprbuseddlavg'].max()
    prb_mean = df['pmprbuseddlavg'].mean()
    rrc_mean = df['rrc_succ_rate'].mean()
    erab_mean= df['erab_succ_rate'].mean()
    cd_sum   = df['cd_call'].sum() if 'cd_call' in df.columns else 0
    sinr_mean= df['pmsinrpucchdistr'].mean() if 'pmsinrpucchdistr' in df.columns else None

    cols = st.columns(5)
    cols[0].metric("DL PRB 최대", f"{prb_max:.1f}%" if pd.notna(prb_max) else "N/A",
                   delta="⚠ 불량" if prb_max >= filters['prb_thresh'] else "✅ 정상")
    cols[1].metric("DL PRB 평균", f"{prb_mean:.1f}%" if pd.notna(prb_mean) else "N/A")
    cols[2].metric("RRC 성공률 평균", f"{rrc_mean:.2f}%" if pd.notna(rrc_mean) else "N/A")
    cols[3].metric("ERAB 성공률 평균", f"{erab_mean:.2f}%" if pd.notna(erab_mean) else "N/A")
    cols[4].metric("SINR(PUCCH) 평균", f"{sinr_mean:.2f}" if sinr_mean and pd.notna(sinr_mean) else "N/A")

    st.markdown("---")
    tab_labels = ["📶 PRB", "📡 접속/CD", "📈 SINR·간섭", "🔴 불량 히트맵", "📊 CEI/CFI", "📋 테이블"]
    tabs = st.tabs(tab_labels)

    # ── PRB 탭
    with tabs[0]:
        st.markdown('<div class="sec-title">DL PRB 사용률 분석</div>', unsafe_allow_html=True)

        if '_일자' in df.columns and '_시' in df.columns:
            g = df.groupby(['_일자','_시'])['pmprbuseddlavg'].mean().reset_index()
            fig = go.Figure()
            for d in sorted(g['_일자'].dropna().unique()):
                sub = g[g['_일자']==d]
                fig.add_trace(go.Scatter(x=sub['_시'], y=sub['pmprbuseddlavg'],
                                         name=d, mode='lines+markers',
                                         marker=dict(size=4), line=dict(width=1.5)))
            fig.add_hline(y=filters['prb_thresh'], line_dash='dash', line_color='red',
                          annotation_text=f"불량기준 {filters['prb_thresh']}%")
            fig.update_layout(title='시간대별 평균 DL PRB (%)', height=300,
                               margin=dict(l=5,r=5,t=40,b=30),
                               xaxis_title='시각', legend=dict(orientation='h',y=-0.3,font=dict(size=10)),
                               title_font=dict(size=13,color='#1a2744'))
            st.plotly_chart(fig, use_container_width=True)

        # 국소별 PRB 최대
        if name_col in df.columns:
            sp = df.groupby(name_col)['pmprbuseddlavg'].max().sort_values(ascending=False).head(20).reset_index()
            fig2 = px.bar(sp, x=name_col, y='pmprbuseddlavg',
                          color='pmprbuseddlavg',
                          color_continuous_scale=[[0,'#4caf8a'],[0.3,'#f5c060'],[0.6,'#e07030'],[1,'#b01f1f']],
                          title='국소별 DL PRB 최대 (상위 20)')
            fig2.add_hline(y=filters['prb_thresh'], line_dash='dash', line_color='red')
            fig2.update_layout(height=320, margin=dict(l=5,r=5,t=40,b=80),
                                xaxis_tickangle=-35, coloraxis_showscale=False,
                                title_font=dict(size=13,color='#1a2744'))
            st.plotly_chart(fig2, use_container_width=True)

    # ── 접속/CD 탭
    with tabs[1]:
        st.markdown('<div class="sec-title">접속성공률 / CD율</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if name_col in df.columns:
                acc_cols = [c for c in ['rrc_succ_rate','erab_succ_rate','rd_acc_succ_rate','pmho_succ_rate'] if c in df.columns]
                acc = df.groupby(name_col)[acc_cols].mean().reset_index()
                for ac in acc_cols:
                    acc[ac] = acc[ac].round(2)
                st.markdown("**접속성공률 (국소별 평균)**")
                st.dataframe(acc.sort_values(acc_cols[0] if acc_cols else name_col).head(20),
                             use_container_width=True, height=300)
        with c2:
            if 'cd_rate' in df.columns and name_col in df.columns:
                cd = df.groupby(name_col)['cd_rate'].mean().sort_values(ascending=False).head(15).reset_index()
                fig3 = px.bar(cd, x=name_col, y='cd_rate', title='국소별 CD율 평균 (상위 15)',
                              color='cd_rate',
                              color_continuous_scale=[[0,'#4caf8a'],[0.5,'#f5c060'],[1,'#b01f1f']])
                fig3.update_layout(height=300, margin=dict(l=5,r=5,t=40,b=80),
                                    xaxis_tickangle=-35, coloraxis_showscale=False,
                                    title_font=dict(size=13,color='#1a2744'))
                st.plotly_chart(fig3, use_container_width=True)

    # ── SINR·간섭 탭
    with tabs[2]:
        st.markdown('<div class="sec-title">SINR / 간섭전력</div>', unsafe_allow_html=True)
        sinr_cols = [c for c in ['pmsinrpucchdistr','pmsinrpuschdistr'] if c in df.columns]
        inter_cols = [c for c in ['pmradiorecinterferencepwr','pmradiorecinterferencepwrpucch'] if c in df.columns]

        c1, c2 = st.columns(2)
        with c1:
            if sinr_cols and name_col in df.columns:
                sinr_df = df.groupby(name_col)[sinr_cols].mean().reset_index().sort_values(sinr_cols[0])
                fig4 = px.bar(sinr_df.head(20), x=name_col, y=sinr_cols[0],
                              title='SINR PUCCH 평균 (낮을수록 불량)',
                              color=sinr_cols[0],
                              color_continuous_scale=[[0,'#b01f1f'],[0.5,'#f5c060'],[1,'#4caf8a']])
                fig4.update_layout(height=300, margin=dict(l=5,r=5,t=40,b=80),
                                    xaxis_tickangle=-35, coloraxis_showscale=False,
                                    title_font=dict(size=13,color='#1a2744'))
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("SINR 컬럼이 없습니다.")
        with c2:
            if inter_cols and name_col in df.columns:
                inter_df = df.groupby(name_col)[inter_cols[0]].mean().reset_index().sort_values(inter_cols[0])
                fig5 = px.bar(inter_df.head(20), x=name_col, y=inter_cols[0],
                              title='간섭전력 평균 (높을수록 불량)',
                              color=inter_cols[0],
                              color_continuous_scale=[[0,'#4caf8a'],[0.5,'#f5c060'],[1,'#b01f1f']])
                fig5.update_layout(height=300, margin=dict(l=5,r=5,t=40,b=80),
                                    xaxis_tickangle=-35, coloraxis_showscale=False,
                                    title_font=dict(size=13,color='#1a2744'))
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("간섭전력 컬럼이 없습니다.")

    # ── 불량 히트맵 탭
    with tabs[3]:
        st.markdown(f'<div class="sec-title">DL PRB ≥ {filters["prb_thresh"]}% 불량 시간대</div>', unsafe_allow_html=True)
        if '_시' in df.columns and name_col in df.columns:
            sel_day = None
            if '_일자' in df.columns:
                days = sorted(df['_일자'].dropna().unique())
                sel_day = st.selectbox("날짜", days, key='qkpi_day')
                plot_df = df[df['_일자']==sel_day]
            else:
                plot_df = df

            pivot = plot_df.groupby([name_col,'_시'])['pmprbuseddlavg'].max().unstack('_시')
            pivot = pivot.reindex(columns=HOURS, fill_value=np.nan).fillna(0)

            colorscale = [
                [0,                               '#e8f5ee'],
                [max(filters['prb_thresh']/100-0.001, 0), '#e8f5ee'],
                [filters['prb_thresh']/100,        '#f5c4a0'],
                [0.50,  '#e87030'],
                [0.70,  '#b01f1f'],
                [1.0,   '#7a0000'],
            ]
            fig6 = go.Figure(go.Heatmap(
                z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
                colorscale=colorscale, zmin=0, zmax=100,
                text=pivot.values.round(1), texttemplate='%{text}',
                textfont=dict(size=8),
                hovertemplate='%{y}<br>%{x}시: %{z:.1f}%<extra></extra>',
                colorbar=dict(title='PRB%', thickness=12),
            ))
            fig6.update_layout(
                height=max(300, len(pivot)*26+100),
                margin=dict(l=10,r=10,t=30,b=30),
                xaxis=dict(title='시각(시)', tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=9), autorange='reversed'),
                plot_bgcolor='white',
            )
            st.plotly_chart(fig6, use_container_width=True)

            # 불량 요약
            bad = plot_df[plot_df['pmprbuseddlavg'] >= filters['prb_thresh']]
            if not bad.empty:
                st.markdown(f"**불량 국소 요약 ({len(bad[name_col].unique())}개)**")
                sumtbl = bad.groupby(name_col).agg(
                    불량시간수=('_시','count'),
                    PRB_최대=('pmprbuseddlavg','max'),
                    발생시간=('_시', lambda x: ', '.join(sorted(x.astype(str))))
                ).reset_index().sort_values('PRB_최대', ascending=False)
                st.dataframe(sumtbl, use_container_width=True, height=250)
        else:
            st.info("시간대 컬럼('hh')이 없어 히트맵을 표시할 수 없습니다.")

    # ── CEI/CFI 탭
    with tabs[4]:
        st.markdown('<div class="sec-title">CEI / CFI 품질지수</div>', unsafe_allow_html=True)
        cei_cols = [c for c in ['lte_cei_value','tot_cei_value','hdv_cei_value','wcdr_cei_value'] if c in df.columns]
        cfi_cols = [c for c in ['new_hdv_cfi_value','new_data_cfi_value'] if c in df.columns]
        all_qi = cei_cols + cfi_cols

        if all_qi and name_col in df.columns:
            qi_df = df.groupby(name_col)[all_qi].mean().reset_index()
            for qc in all_qi:
                qi_df[qc] = qi_df[qc].round(2)
            if cfi_cols:
                fig7 = px.scatter(qi_df.dropna(subset=cfi_cols[:1]),
                                   x=cfi_cols[0], y=cfi_cols[1] if len(cfi_cols)>1 else cfi_cols[0],
                                   hover_name=name_col, title='HDV CFI vs DATA CFI',
                                   color=cfi_cols[0],
                                   color_continuous_scale=[[0,'#b01f1f'],[0.5,'#f5c060'],[1,'#4caf8a']])
                fig7.update_layout(height=320, margin=dict(l=5,r=5,t=40,b=30),
                                    title_font=dict(size=13,color='#1a2744'))
                st.plotly_chart(fig7, use_container_width=True)
            st.dataframe(qi_df.sort_values(all_qi[0] if all_qi else name_col).head(20),
                         use_container_width=True, height=250)
        else:
            st.info("CEI/CFI 값이 모두 무효값(NaN)이거나 컬럼이 없습니다.")

    # ── 테이블 탭
    with tabs[5]:
        show_cols = [c for c in [name_col, freq_col, '_일자', '_시',
                                   'pmprbuseddlavg','pmprbutildlmax',
                                   'rrc_succ_rate','erab_succ_rate','cd_rate',
                                   'pmsinrpucchdistr','new_data_cfi_value']
                     if c and c in df.columns]
        st.dataframe(df[show_cols].reset_index(drop=True), use_container_width=True, height=450)
        csv_out = df[show_cols].to_csv(index=False, encoding='utf-8-sig')
        st.download_button("⬇ CSV 다운로드", csv_out, "quality_kpi.csv", "text/csv")


# ────────────────────────────────────────────
# 분석 함수 — CEI/CFI
# ────────────────────────────────────────────
def render_cei_cfi(df, filters):
    sig = FILE_SIGNATURES['CEI/CFI']
    name_col = sig['name_col']
    freq_col = sig['freq_col']

    # 요약
    cols = st.columns(4)
    for i, (label, col) in enumerate([('HDV CFI','HDVCFI'),('DATA CFI','DATACFI'),
                                        ('NEI','NEI'),('SEI','SEI')]):
        val = df[col].mean() if col in df.columns else None
        cols[i].metric(label, f"{val:.1f}" if val and pd.notna(val) else "N/A")

    st.markdown("---")
    tabs = st.tabs(["📊 CFI 현황", "📈 일자별 트렌드", "🔍 세부항목", "📋 테이블"])

    # CFI 현황
    with tabs[0]:
        cfi_cols = [c for c in ['HDVCFI','DATACFI','NEI','SEI'] if c in df.columns]
        if name_col in df.columns and cfi_cols:
            cfi_df = df.groupby(name_col)[cfi_cols].mean().reset_index()
            # 불량 (70점 미만)
            bad_thresh = filters.get('cfi_thresh', 70)
            for qc in cfi_cols:
                fig = px.histogram(df[qc].dropna(), nbins=30, title=f'{qc} 분포',
                                    color_discrete_sequence=['#3a5fcc'])
                fig.add_vline(x=bad_thresh, line_dash='dash', line_color='red',
                              annotation_text=f'불량기준 {bad_thresh}')
                fig.update_layout(height=250, margin=dict(l=5,r=5,t=40,b=20),
                                   title_font=dict(size=12,color='#1a2744'))
                st.plotly_chart(fig, use_container_width=True)

    # 일자별 트렌드
    with tabs[1]:
        if '_일자' in df.columns:
            cfi_cols = [c for c in ['HDVCFI','DATACFI'] if c in df.columns]
            g = df.groupby('_일자')[cfi_cols].mean().reset_index()
            fig2 = px.line(g, x='_일자', y=cfi_cols, markers=True, title='일자별 CFI 트렌드')
            fig2.add_hline(y=filters.get('cfi_thresh',70), line_dash='dash', line_color='red')
            fig2.update_layout(height=300, margin=dict(l=5,r=5,t=40,b=30),
                                title_font=dict(size=13,color='#1a2744'))
            st.plotly_chart(fig2, use_container_width=True)

    # 세부항목
    with tabs[2]:
        detail_cols = [c for c in df.columns if any(k in c for k in ['접속','음질','단절','커버리지','속도','화면전환'])
                       and c in df.columns]
        if detail_cols and name_col in df.columns:
            det = df.groupby(name_col)[detail_cols[:8]].mean().reset_index()
            st.dataframe(det.round(2), use_container_width=True, height=350)

    # 테이블
    with tabs[3]:
        key = [c for c in [name_col, freq_col, '_일자','HDVCFI','DATACFI','NEI','SEI'] if c and c in df.columns]
        st.dataframe(df[key].reset_index(drop=True), use_container_width=True, height=450)
        st.download_button("⬇ CSV", df[key].to_csv(index=False,encoding='utf-8-sig'),
                           "cei_data.csv","text/csv")


# ────────────────────────────────────────────
# 분석 함수 — CQ등급
# ────────────────────────────────────────────
def render_cq(df, filters):
    sig = FILE_SIGNATURES['CQ등급']
    name_col = sig['name_col']

    # 요약
    cols = st.columns(4)
    cols[0].metric("CQ 1등급 비율 평균", f"{df['CQ 1등급 비율'].mean():.1f}%" if 'CQ 1등급 비율' in df.columns else "N/A")
    cols[1].metric("총 CQ 건수", f"{int(df['CQ전체건수'].sum()):,}" if 'CQ전체건수' in df.columns else "N/A")
    cols[2].metric("DL속도불량 건수", f"{int(df['DL속도불량 건수'].sum()):,}" if 'DL속도불량 건수' in df.columns else "N/A")
    cols[3].metric("Latency불량 건수", f"{int(df['Latency불량 건수'].sum()):,}" if 'Latency불량 건수' in df.columns else "N/A")

    st.markdown("---")
    tabs = st.tabs(["🏆 CQ등급 분포", "📈 일자별 트렌드", "⚠ 불량 현황", "📋 테이블"])

    grade_cols = [c for c in ['1등급 건수','2등급 건수','3등급 건수','4등급 건수','5등급 건수'] if c in df.columns]

    # CQ 분포
    with tabs[0]:
        if grade_cols:
            total = df[grade_cols].sum()
            fig = px.pie(values=total.values, names=total.index,
                         title='CQ 등급 전체 분포',
                         color_discrete_sequence=['#2196f3','#4caf50','#ff9800','#f44336','#9c27b0'])
            fig.update_layout(height=320, title_font=dict(size=13,color='#1a2744'))
            st.plotly_chart(fig, use_container_width=True)

        if name_col in df.columns and 'CQ 1등급 비율' in df.columns:
            cq1 = df.groupby(name_col)['CQ 1등급 비율'].mean().sort_values().head(20).reset_index()
            fig2 = px.bar(cq1, x=name_col, y='CQ 1등급 비율',
                          title='CQ 1등급 비율 하위 20개 (불량 우선)',
                          color='CQ 1등급 비율',
                          color_continuous_scale=[[0,'#b01f1f'],[0.5,'#f5c060'],[1,'#4caf8a']])
            fig2.update_layout(height=300, margin=dict(l=5,r=5,t=40,b=80),
                                xaxis_tickangle=-35, coloraxis_showscale=False,
                                title_font=dict(size=13,color='#1a2744'))
            st.plotly_chart(fig2, use_container_width=True)

    # 일자별 트렌드
    with tabs[1]:
        if '_일자' in df.columns and 'CQ 1등급 비율' in df.columns:
            g = df.groupby('_일자')['CQ 1등급 비율'].mean().reset_index()
            fig3 = px.line(g, x='_일자', y='CQ 1등급 비율', markers=True,
                           title='일자별 CQ 1등급 비율 트렌드')
            fig3.add_hline(y=filters.get('cq_thresh',85), line_dash='dash', line_color='red',
                           annotation_text='목표 기준')
            fig3.update_layout(height=280, margin=dict(l=5,r=5,t=40,b=30),
                                title_font=dict(size=13,color='#1a2744'))
            st.plotly_chart(fig3, use_container_width=True)

    # 불량 현황
    with tabs[2]:
        bad_cols = [c for c in ['DL속도불량 건수','UL속도불량 건수','Latency불량 건수',
                                 'Jitter불량 건수','Packet불량 건수','첫바이트도착시간 건수'] if c in df.columns]
        if bad_cols and name_col in df.columns:
            bad_df = df.groupby(name_col)[bad_cols].sum().reset_index()
            bad_df['총불량'] = bad_df[bad_cols].sum(axis=1)
            bad_df = bad_df.sort_values('총불량', ascending=False).head(15)
            fig4 = px.bar(bad_df, x=name_col, y=bad_cols, barmode='stack',
                          title='불량 유형별 건수 (상위 15 셀)',
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig4.update_layout(height=320, margin=dict(l=5,r=5,t=40,b=80),
                                xaxis_tickangle=-35, title_font=dict(size=13,color='#1a2744'),
                                legend=dict(font=dict(size=10)))
            st.plotly_chart(fig4, use_container_width=True)

    # 테이블
    with tabs[3]:
        key = [c for c in [name_col, '_일자', 'CQ 1등급 비율'] + grade_cols + bad_cols if c in df.columns]
        st.dataframe(df[key].reset_index(drop=True), use_container_width=True, height=450)
        st.download_button("⬇ CSV", df[key].to_csv(index=False,encoding='utf-8-sig'),
                           "cq_data.csv","text/csv")


# ────────────────────────────────────────────
# 미인식 파일 처리
# ────────────────────────────────────────────
def render_unknown(df):
    st.warning("파일 형식을 자동으로 인식하지 못했습니다. 수치 컬럼을 직접 선택해서 분석해 보세요.")
    num_cols = df.select_dtypes(include='number').columns.tolist()
    str_cols = df.select_dtypes(include='object').columns.tolist()

    c1, c2 = st.columns(2)
    with c1:
        x_col = st.selectbox("X축 (문자/날짜)", str_cols + num_cols)
    with c2:
        y_col = st.selectbox("Y축 (수치)", num_cols)

    if x_col and y_col:
        fig = px.bar(df.head(50), x=x_col, y=y_col, title=f'{x_col} × {y_col}')
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df.head(100), use_container_width=True, height=400)


# ────────────────────────────────────────────
# 사이드바
# ────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 품질 대시보드")
    st.markdown("---")
    st.markdown("**📂 파일 업로드**")
    st.caption("xlsx / csv 자동 인식")
    uploaded_files = st.file_uploader(
        "파일 선택 (복수 업로드 가능)",
        type=['csv','xlsx','xls'],
        accept_multiple_files=True,
        label_visibility='collapsed'
    )
    st.markdown("---")
    st.markdown("**⚙ 분석 설정**")
    prb_thresh = st.slider("PRB 불량 기준 (%)", 10, 70, 30, 5)
    cfi_thresh = st.slider("CFI 불량 기준 (점)", 50, 95, 70, 5)
    cq_thresh  = st.slider("CQ 1등급 목표 (%)", 50, 99, 85, 5)
    st.markdown("---")
    st.markdown("<div style='font-size:10px;color:#6070a0'>진주품질개선팀 · 내부용</div>",
                unsafe_allow_html=True)

filters = {'prb_thresh': prb_thresh, 'cfi_thresh': cfi_thresh, 'cq_thresh': cq_thresh}

# ────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📡 진주 네트워크 품질 대시보드</h1>
  <p>파일 업로드 → 자동 인식 → 분석 · 품질KPI / CEI·CFI / CQ등급 · xlsx / csv 지원</p>
</div>
""", unsafe_allow_html=True)

if not uploaded_files:
    st.info("👈 사이드바에서 파일을 업로드해 주세요. 여러 파일을 한 번에 올릴 수 있습니다.")
    st.markdown("""
    **자동 인식 파일 유형**

    | 유형 | 주요 컬럼 | 분석 내용 |
    |------|-----------|-----------|
    | 📶 품질KPI | `pmprbuseddlavg`, `rrc_succ_rate` 등 | PRB·접속·SINR·간섭·CEI·히트맵 |
    | 📊 CEI/CFI | `HDVCFI`, `DATACFI`, `NEI`, `SEI` | 체감품질지수 트렌드·세부항목 |
    | 🏆 CQ등급 | `CQ 1등급 비율`, `DL속도불량 건수` 등 | 등급분포·불량유형·트렌드 |
    | ❓ 기타 | 모든 CSV/xlsx | 컬럼 직접 선택 후 분석 |
    """)
    st.stop()

# ── 파일별 탭 생성
file_results = []
for uf in uploaded_files:
    raw = uf.read()
    try:
        df, ftype = load_and_detect(raw, uf.name)
        file_results.append((uf.name, df, ftype))
        sig = FILE_SIGNATURES.get(ftype, {})
        st.sidebar.success(f"{sig.get('label', ftype)} ✅\n{uf.name[:25]}")
    except Exception as e:
        st.sidebar.error(f"❌ {uf.name[:20]}: {e}")

if not file_results:
    st.error("업로드된 파일을 읽을 수 없습니다.")
    st.stop()

# ── 파일이 1개면 바로, 여러 개면 탭으로
if len(file_results) == 1:
    fname, df, ftype = file_results[0]
    sig = FILE_SIGNATURES.get(ftype, {})
    st.markdown(f"**{sig.get('label', fname)}** · `{fname}`")

    # 필터
    days = sorted(df['_일자'].dropna().unique()) if '_일자' in df.columns else []
    name_col = sig.get('name_col','')
    sites = sorted(df[name_col].dropna().unique()) if name_col and name_col in df.columns else []

    fc1, fc2 = st.columns([2,3])
    with fc1:
        sel_days = st.multiselect("📅 날짜", days, default=days) if days else days
    with fc2:
        sel_sites = st.multiselect("🏢 국소/장비 (전체=선택 안함)", sites, placeholder="전체") if sites else []

    if sel_days:
        df = df[df['_일자'].isin(sel_days)]
    if sel_sites and name_col in df.columns:
        df = df[df[name_col].isin(sel_sites)]

    if ftype == '품질KPI':    render_quality_kpi(df, filters)
    elif ftype == 'CEI/CFI':  render_cei_cfi(df, filters)
    elif ftype == 'CQ등급':   render_cq(df, filters)
    else:                     render_unknown(df)

else:
    tab_names = [r[0][:20] for r in file_results]
    tabs = st.tabs(tab_names)
    for i, (fname, df, ftype) in enumerate(file_results):
        with tabs[i]:
            sig = FILE_SIGNATURES.get(ftype, {})
            st.markdown(f"**{sig.get('label', '미인식')}** · `{fname}`")
            if ftype == '품질KPI':    render_quality_kpi(df, filters)
            elif ftype == 'CEI/CFI':  render_cei_cfi(df, filters)
            elif ftype == 'CQ등급':   render_cq(df, filters)
            else:                     render_unknown(df)

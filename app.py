import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
import io

# --- 0. 웹페이지 및 전역 설정 ---
st.set_page_config(page_title="PB 전문 투자 대시보드", layout="wide")
st.title("📈 프로페셔널 투자 분석 대시보드")

st.sidebar.header("⚙️ 차트 공통 설정")
freq_option = st.sidebar.selectbox("데이터 주기", ["일봉", "주봉", "월봉", "연봉"], index=0)
use_log_scale = st.sidebar.checkbox("Y축 로그 변환 (Log Scale) 적용", value=False)
freq_map = {"일봉": "D", "주봉": "W", "월봉": "M", "연봉": "Y"}
resample_freq = freq_map[freq_option]

# --- 1. 데이터 베이스 (클라우드 IP 차단 방어를 위한 하드코딩 매핑) ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}

TOP_US_100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "JPM", "V", "JNJ", "XOM", "MA", "AVGO", "PG", "HD", "CVX", "ABBV", "COST"
]

# 클라우드에서 KRX 마스터 조회가 차단되므로 한국 대표종목 티커를 직접 매핑
TOP_KR_MAP = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS", "삼성바이오로직스": "207940.KS", 
    "현대차": "005380.KS", "기아": "000270.KS", "셀트리온": "068270.KS", "POSCO홀딩스": "005490.KS", 
    "NAVER": "035420.KS", "카카오": "035720.KS", "삼성SDI": "006400.KS", "LG화학": "051910.KS", 
    "삼성물산": "028260.KS", "현대모비스": "012330.KS", "KB금융": "105560.KS", "신한지주": "055550.KS", 
    "하나금융지주": "086790.KS", "메리츠금융지주": "138040.KS", "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ",
    "유한양행": "000100.KS", "알테오젠": "196170.KQ", "한미반도체": "042700.KS", "현대건설": "000720.KS"
}

THEME_MAP = {
    "AI/반도체": ["NVDA", "TSM", "AVGO", "ASML", "AMD", "삼성전자", "SK하이닉스", "한미반도체"],
    "빅테크": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"],
    "바이오": ["LLY", "NVO", "JNJ", "삼성바이오로직스", "셀트리온", "유한양행", "알테오젠"],
    "금융": ["JPM", "BAC", "GS", "KB금융", "신한지주", "하나금융지주"],
    "직접입력": []
}

MACRO_DICT = {
    "미국 10년물 국채금리": {"ticker": "FRED:DGS10", "source": "fdr"},
    "미국 2년물 국채금리": {"ticker": "FRED:DGS2", "source": "fdr"},
    "미국 10Y-2Y 장단기 금리차": {"ticker": "FRED:T10Y2Y", "source": "fdr"},
    "원/달러 환율": {"ticker": "USD/KRW", "source": "fdr"},
    "달러 인덱스 (DXY)": {"ticker": "DX-Y.NYB", "source": "yf"},
    "WTI 원유": {"ticker": "CL=F", "source": "yf"},
    "금 (Gold)": {"ticker": "GC=F", "source": "yf"},
    "VIX (공포지수)": {"ticker": "^VIX", "source": "yf"}
}

# --- 2. 핵심 헬퍼 함수 ---
def get_yf_ticker(name_or_ticker):
    if name_or_ticker in TOP_KR_MAP:
        return TOP_KR_MAP[name_or_ticker]
    # 사용자가 6자리 숫자 코드를 직접 입력했을 때 처리
    if name_or_ticker.isdigit() and len(name_or_ticker) == 6:
        return f"{name_or_ticker}.KS"
    return name_or_ticker.upper()

def find_theme_and_peers(target):
    for theme, peers in THEME_MAP.items():
        if target.upper() in [p.upper() for p in peers] or target in peers:
            return theme, ", ".join([p for p in peers if p.upper() != target.upper() and p != target])
    return "직접 입력 (테마 매칭 안됨)", ""

@st.cache_data(ttl=3600)
def fetch_data(name_or_ticker, start_date):
    try:
        df = None
        if name_or_ticker in MACRO_DICT and MACRO_DICT[name_or_ticker]['source'] == 'fdr':
            df = fdr.DataReader(MACRO_DICT[name_or_ticker]['ticker'], start_date)
        else:
            ticker_converted = get_yf_ticker(name_or_ticker)
            df = yf.download(ticker_converted, start=start_date, progress=False)
            
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            if 'Close' not in df.columns:
                df = df.rename(columns={df.columns[0]: 'Close'})
            if df.index.tz is not None: 
                df.index = df.index.tz_localize(None)
            return df
        return None
    except: return None

# --- 3. 메인 UI 및 탭 구성 ---
tabs = st.tabs([
    "📊 1. 기술적 분석", "🌐 2. 글로벌 비교", "💡 3. 섹터 밸류", 
    "💼 4. 포트폴리오", "💰 5. 배당 트래커", "🏆 6. 퀀트 스크리너", "🚨 7. 파생상품 관제", "🛒 8. ETF 왝더독"
])

# ==============================================================================
# [탭 1: 단일 종목 기술적 분석]
# ==============================================================================
with tabs[0]:
    c1, c2 = st.columns([1, 4])
    with c1:
        st.subheader("종목 및 지표 설정")
        target_t1 = st.text_input("분석할 종목/티커", "NVDA", key="t1")
        chart_type = st.radio("차트 형식 선택", ["봉형식 (Candle)", "선형식 (Line)"], index=0)
        p_t1 = st.slider("조회 기간(일)", 30, 3650, 1825, step=30, key="t1_slider")
        s_t1 = pd.Timestamp.now() - pd.Timedelta(days=p_t1)
        st.markdown("---")
        sh_ma = st.checkbox("이동평균선 (MA) 표시", value=True, key="t1_ma")
        ma_list = [st.number_input("단기 MA", 1, 100, 20), st.number_input("중기 MA", 1, 200, 60), st.number_input("장기 MA", 1, 300, 120)]
        sh_bb = st.checkbox("볼린저 밴드", key="t1_bb")
        sh_macd = st.checkbox("MACD", True, key="t1_macd")
        sh_rsi = st.checkbox("RSI", True, key="t1_rsi")
    with c2:
        df = fetch_data(target_t1, s_t1)
        if df is not None and not df.empty:
            if resample_freq != 'D':
                if 'Open' in df.columns:
                    df = df.resample(resample_freq).agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
                else: df = df.resample(resample_freq).last().dropna()
                    
            for m in ma_list: df[f'MA{m}'] = df['Close'].rolling(m).mean()
            if sh_bb:
                mb = df['Close'].rolling(20).mean(); std = df['Close'].rolling(20).std()
                df['UB'] = mb+(std*2); df['LB'] = mb-(std*2)
            if sh_macd:
                e1 = df['Close'].ewm(span=12).mean(); e2 = df['Close'].ewm(span=26).mean()
                df['M'] = e1-e2; df['S'] = df['M'].ewm(span=9).mean(); df['H'] = df['M']-df['S']
            if sh_rsi:
                d = df['Close'].diff(); u = d.clip(lower=0); dn = -1*d.clip(upper=0)
                au = u.ewm(com=13).mean(); ad = dn.ewm(com=13).mean(); df['RSI'] = 100-(100/(1+au/ad))
            
            rows = 1 + int(sh_macd) + int(sh_rsi); hts = [1.0] if rows==1 else ([0.7, 0.3] if rows==2 else [0.5, 0.25, 0.25])
            fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=hts)
            
            if chart_type == "봉형식 (Candle)" and 'Open' in df.columns:
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), 1, 1)
            else: fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#deff9a', width=2)), 1, 1)
                
            if sh_ma:
                for m, c in zip(ma_list, ['#f6c90e','#30e3ca','#e43f5a']): fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], line=dict(color=c, width=1.5)), 1, 1)
            if sh_bb:
                fig.add_trace(go.Scatter(x=df.index, y=df['UB'], line=dict(dash='dot', color='rgba(255,255,255,0.3)')), 1, 1)
                fig.add_trace(go.Scatter(x=df.index, y=df['LB'], line=dict(dash='dot', color='rgba(255,255,255,0.3)'), fill='tonexty', fillcolor='rgba(255,255,255,0.05)'), 1, 1)
            
            curr = 2
            if sh_macd:
                fig.add_trace(go.Scatter(x=df.index, y=df['M'], line=dict(color='#ff9a76')), curr, 1)
                fig.add_trace(go.Scatter(x=df.index, y=df['S'], line=dict(color='#679b9b')), curr, 1)
                fig.add_trace(go.Bar(x=df.index, y=df['H'], marker_color='gray'), curr, 1); curr += 1
            if sh_rsi:
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#d4a5a5')), curr, 1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr); fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr)
            
            if use_log_scale: fig.update_yaxes(type="log", row=1, col=1)
            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# [탭 2: 글로벌 다중 자산 비교 (확장판)]
# ==============================================================================
with tabs[1]:
    st.markdown("### 🌐 글로벌 다중 자산 하이브리드 비교 (변동성 중심)")
    c3, c4 = st.columns([1, 4])
    with c3:
        l_in = st.text_input("좌측 Y축(주식 쉼표구분)", "삼성전자, NVDA")
        r_in = st.multiselect("매크로 지표", options=list(MACRO_DICT.keys()), default=["미국 10년물 국채금리", "원/달러 환율"])
        norm = st.checkbox("정규화(%) 기준 출발점 통일", True)
        cp = st.slider("조회 기간(일)", 30, 3650, 1095)
    
    with c4:
        as_list = list(set([s.strip() for s in l_in.split(',') if s.strip()] + r_in))
        if as_list:
            m_df = pd.DataFrame()
            with st.spinner("데이터 연산 중..."):
                for a in as_list:
                    d = fetch_data(a, pd.Timestamp.now() - pd.Timedelta(days=cp))
                    if d is not None and not d.empty:
                        s = d['Close']; s.name = a
                        if m_df.empty: m_df = s.to_frame()
                        else: m_df = m_df.join(s, how='outer')
            
            if not m_df.empty:
                m_df = m_df.ffill().dropna(how='all')
                f2 = make_subplots(specs=[[{"secondary_y": True}]])
                for a in [s.strip() for s in l_in.split(',') if s.strip()]:
                    if a in m_df.columns:
                        first_valid = m_df[a].dropna().iloc[0] if not m_df[a].dropna().empty else 1
                        y = (m_df[a] / first_valid - 1) * 100 if norm else m_df[a]
                        f2.add_trace(go.Scatter(x=m_df.index, y=y, name=f"[주식] {a}", line=dict(width=2)), secondary_y=False)
                for a in r_in:
                    if a in m_df.columns:
                        first_valid = m_df[a].dropna().iloc[0] if not m_df[a].dropna().empty else 1
                        y = (m_df[a] / first_valid - 1) * 100 if norm else m_df[a]
                        f2.add_trace(go.Scatter(x=m_df.index, y=y, name=f"[지표] {a}", line=dict(dash='dot', width=1.5)), secondary_y=True)
                
                if use_log_scale and not norm: 
                    f2.update_yaxes(type="log", secondary_y=False); f2.update_yaxes(type="log", secondary_y=True)
                f2.update_layout(template="plotly_dark", height=500, hovermode="x unified")
                st.plotly_chart(f2, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📉 단일 지표 절대값 듀얼 축 비교 (스프레드 추적)")
    c5, c6 = st.columns([1, 4])
    with c5:
        abs_l_in = st.text_input("좌측 Y축 (단일 종목)", "삼성전자")
        abs_l_single = abs_l_in.split(',')[0].strip() if abs_l_in else ""
        abs_r_in = st.selectbox("우측 Y축 (단일 매크로)", options=list(MACRO_DICT.keys()), index=list(MACRO_DICT.keys()).index("원/달러 환율"))
        abs_cp = st.slider("절대값 조회 기간(일)", 30, 3650, 1095, key="abs_p")
        
    with c6:
        if abs_l_single and abs_r_in:
            abs_df = pd.DataFrame()
            for a in [abs_l_single, abs_r_in]:
                d = fetch_data(a, pd.Timestamp.now() - pd.Timedelta(days=abs_cp))
                if d is not None and not d.empty:
                    s = d['Close']; s.name = a
                    if abs_df.empty: abs_df = s.to_frame()
                    else: abs_df = abs_df.join(s, how='outer')
                        
            if not abs_df.empty and len(abs_df.columns) == 2:
                abs_df = abs_df.ffill().dropna(how='any')
                f_abs = make_subplots(specs=[[{"secondary_y": True}]])
                f_abs.add_trace(go.Scatter(x=abs_df.index, y=abs_df[abs_l_single], name=f"{abs_l_single}", line=dict(color='#00ffcc', width=2)), secondary_y=False)
                f_abs.add_trace(go.Scatter(x=abs_df.index, y=abs_df[abs_r_in], name=f"{abs_r_in}", line=dict(color='#ff4d4d', dash='dot', width=2)), secondary_y=True)
                if use_log_scale:
                    f_abs.update_yaxes(type="log", secondary_y=False); f_abs.update_yaxes(type="log", secondary_y=True)
                f_abs.update_layout(template="plotly_dark", height=450, hovermode="x unified")
                st.plotly_chart(f_abs, use_container_width=True)
                with st.expander("데이터 표 보기"): st.dataframe(abs_df.sort_index(ascending=False).round(2), use_container_width=True)

# ==============================================================================
# [탭 3: 섹터 밸류에이션]
# ==============================================================================
with tabs[2]:
    cv1, cv2 = st.columns([1, 4])
    with cv1:
        st.subheader("섹터 상대 가치 분석")
        t_a = st.text_input("대상 종목 입력", "NVDA", key="t3_a")
        at, ap = find_theme_and_peers(t_a)
        st_theme = st.selectbox("섹터/테마 선택", list(THEME_MAP.keys()), index=list(THEME_MAP.keys()).index(at))
        fp = ap if st_theme == at else ", ".join(THEME_MAP[st_theme])
        pa = st.text_area("비교 피어 그룹", value=fp)
    with cv2:
        if t_a:
            df_3y = fetch_data(t_a, pd.Timestamp.now() - pd.Timedelta(days=1095))
            if df_3y is not None and not df_3y.empty:
                f3 = go.Figure(); f3.add_trace(go.Scatter(x=df_3y.index, y=df_3y['Close'], name=t_a, line=dict(color='#deff9a', width=2.5)))
                if use_log_scale: f3.update_yaxes(type="log")
                f3.update_layout(template="plotly_dark", height=400, margin=dict(t=30, b=0), hovermode="x unified"); st.plotly_chart(f3, use_container_width=True)
            st.markdown("### 🔍 주요 경쟁사 펀더멘털 비교")
            pl = list(dict.fromkeys([t_a] + [s.strip() for s in pa.split(',') if s.strip()]))
            res = []
            for p in pl:
                try:
                    tk = yf.Ticker(get_yf_ticker(p)).info
                    res.append({"종목명": p, "PER": tk.get('trailingPE', np.nan), "Fwd PER": tk.get('forwardPE', np.nan), "PBR": tk.get('priceToBook', np.nan), "ROE(%)": tk.get('returnOnEquity', 0) * 100 if tk.get('returnOnEquity') else np.nan})
                except: pass
            if res: st.dataframe(pd.DataFrame(res).set_index("종목명").round(2), use_container_width=True)

# ==============================================================================
# [탭 4: 포트폴리오 백테스트]
# ==============================================================================
with tabs[3]:
    st.markdown("### 💼 사용자 맞춤형 포트폴리오 백테스트")
    ct4_1, ct4_2 = st.columns([1, 4])
    with ct4_1:
        pt = st.text_input("분석 자산 티커 (쉼표 구분)", "QQQ, SPY, AAPL, MSFT")
        pp = st.slider("백테스트 기간 (일)", 30, 3650, 1095, key="t4_p")
        ps = pd.Timestamp.now() - pd.Timedelta(days=pp)
    with ct4_2:
        if pt:
            al = list(dict.fromkeys([s.strip() for s in pt.split(',') if s.strip()]))
            df_m = pd.DataFrame()
            for a in al:
                dr = fetch_data(a, ps)
                if dr is not None and not dr.empty:
                    s = dr['Close']; s.name = a
                    if df_m.empty: df_m = s.to_frame()
                    else: df_m = df_m.join(s, how='outer')
            df_m = df_m.ffill().dropna()
            if not df_m.empty and len(df_m.columns) > 1:
                rd = df_m.pct_change().dropna(); cm = rd.corr()
                st.subheader("1️⃣ 상관관계 히트맵")
                fc = go.Figure(data=go.Heatmap(z=cm.values, x=cm.columns, y=cm.columns, colorscale='RdBu', zmin=-1, zmax=1))
                fc.update_layout(template="plotly_dark", height=400); st.plotly_chart(fc, use_container_width=True)
                st.subheader("2️⃣ 포트폴리오 성과 시뮬레이터")
                sa = st.multiselect("편입 자산 선택", options=df_m.columns, default=list(df_m.columns)[:3])
                if sa:
                    cl = st.columns(len(sa)); wi = []
                    for i, a in enumerate(sa):
                        with cl[i]: w = st.number_input(f"{a} 비중", 0.0, value=10.0, key=f"w_{a}"); wi.append(w)
                    tw = sum(wi)
                    if tw > 0:
                        nw = [w/tw for w in wi]; pr = (rd[sa]*nw).sum(axis=1); cr = (1+pr).cumprod()*100
                        rm = cr.cummax(); dd = (cr/rm)-1
                        fb = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                        fb.add_trace(go.Scatter(x=cr.index, y=cr, name='포트폴리오', line=dict(color='#00ffcc', width=2)), 1, 1)
                        fb.add_trace(go.Scatter(x=dd.index, y=dd*100, name='MDD', line=dict(color='#ff4d4d'), fill='tozeroy'), 2, 1)
                        fb.update_layout(template="plotly_dark", height=600, hovermode="x unified"); st.plotly_chart(fb, use_container_width=True)
                        m1, m2, m3 = st.columns(3); m1.metric("누적 수익률", f"{(cr.iloc[-1]/100-1)*100:.2f}%"); m2.metric("최대 낙폭(MDD)", f"{dd.min()*100:.2f}%")

# ==============================================================================
# [탭 5: 배당 트래커]
# ==============================================================================
with tabs[4]:
    st.markdown("### 💰 배당 분석 및 지급 이력 추적")
    cv5_1, cv5_2 = st.columns([1, 4])
    with cv5_1: 
        target_t5 = st.text_input("분석할 종목/티커", "AAPL", key="t5_target")
        show_div = st.checkbox("차트 내 배당 금액 표기", value=True)
    with cv5_2:
        if target_t5:
            ticker_yf = get_yf_ticker(target_t5)
            tk = yf.Ticker(ticker_yf)
            end_date = pd.Timestamp.now(); start_date_5y = end_date - pd.Timedelta(days=5*365)
            df_price = yf.download(ticker_yf, start=start_date_5y, end=end_date, progress=False)
            if isinstance(df_price.columns, pd.MultiIndex): df_price.columns = df_price.columns.get_level_values(0)
            if df_price.index.tz is not None: df_price.index = df_price.index.tz_localize(None)
            try:
                divs = tk.dividends
                if divs.index.tz is not None: divs.index = divs.index.tz_localize(None)
                divs_5y = divs[divs.index >= start_date_5y]
                if not df_price.empty:
                    fig_div = go.Figure()
                    fig_div.add_trace(go.Scatter(x=df_price.index, y=df_price['Close'], mode='lines', name='주가', line=dict(color='white')))
                    if not divs_5y.empty and show_div:
                        div_disp = pd.DataFrame(divs_5y).rename(columns={'Dividends': 'Amount'})
                        div_plot = pd.merge_asof(div_disp.sort_index(), df_price[['Close']].sort_index(), left_index=True, right_index=True, direction='backward')
                        fig_div.add_trace(go.Scatter(x=div_plot.index, y=div_plot['Close'], mode='markers+text', marker=dict(color='#FFD700', size=10, symbol='diamond'), text=[f"${v:.2f}" for v in div_plot['Amount']], textposition="top center"))
                    if use_log_scale: fig_div.update_yaxes(type="log")
                    fig_div.update_layout(template="plotly_dark", height=450, hovermode="x unified"); st.plotly_chart(fig_div, use_container_width=True)
                    if not divs_5y.empty:
                        st.dataframe(pd.DataFrame(divs_5y).sort_index(ascending=False), use_container_width=True)
            except: st.warning("배당 이력을 불러오지 못했습니다.")

# ==============================================================================
# [탭 6: 멀티 팩터 퀀트 스크리너]
# ==============================================================================
with tabs[5]:
    st.markdown("### 🏆 글로벌 대형주 멀티팩터 퀀트 스크리너")
    col_q1, col_q2 = st.columns([1, 4])
    with col_q1:
        st.write("분석 대상: US Top 20")
        run_btn = st.button("성장주 랭킹 분석 실행")
    with col_q2:
        if run_btn:
            res = []
            progress_bar = st.progress(0, text="스캔 중...")
            for i, name in enumerate(TOP_US_100[:20]):
                try:
                    info = yf.Ticker(name).info
                    res.append({"종목명": name, "PER": info.get('forwardPE', np.nan), "ROE(%)": info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else np.nan})
                except: pass
                progress_bar.progress((i + 1) / 20)
            progress_bar.empty()
            if res:
                df_q = pd.DataFrame(res)
                df_q['PER 등수'] = df_q['PER'].rank(ascending=True)
                df_q['ROE 등수'] = df_q['ROE(%)'].rank(ascending=False)
                df_q['종합 순위'] = (df_q['PER 등수'] + df_q['ROE 등수']).rank(ascending=True)
                st.dataframe(df_q.sort_values('종합 순위').round(2), use_container_width=True)

# ==============================================================================
# [탭 7: 파생상품 & 외인 포지션 관제탑]
# ==============================================================================
with tabs[6]:
    st.markdown("### 🚨 코스피200 선물/옵션 누적 포지션 분석 (시뮬레이터)")
    p_start = st.date_input("분석 시작일", value=pd.Timestamp("2026-03-13"))
    date_range = pd.date_range(start=p_start, end=pd.Timestamp.now(), freq='B')
    if len(date_range) > 1:
        np.random.seed(42)
        f_deriv = np.linspace(-1, 3, len(date_range)) + np.random.normal(0, 0.2, len(date_range))
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=date_range, y=f_deriv, mode='lines', name='[파생] 외국인 누적 노출액 (조원)', line=dict(color='#00ffcc', width=2.5)))
        fig_p.update_layout(template="plotly_dark", height=450, hovermode="x unified")
        st.plotly_chart(fig_p, use_container_width=True)

# ==============================================================================
# [탭 8: ETF 패시브 왝더독 데이터 유니버스 (Naver Finance 클라우드 우회)]
# ==============================================================================
with tabs[7]:
    st.markdown("### 🛒 국내 ETF 패시브 자금 블랙홀 실시간 추적기")
    st.info("💡 네이버증권 HTML 스크래핑을 통해 대형 ETF 목록을 수집합니다. (클라우드 환경에서 일시적 차단이 발생할 수 있습니다)")
    
    @st.cache_data(ttl=3600)
    def fetch_naver_etf_list():
        try:
            url = "https://finance.naver.com/sise/etf.naver"
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            dfs = pd.read_html(io.StringIO(res.text), encoding='euc-kr')
            # 통상 네이버 ETF 전체 리스트는 2번째(index 1) 혹은 3번째 테이블에 위치
            df = dfs[1]
            df = df.dropna(subset=['종목명'])
            # 시가총액(억) 기준 내림차순 정렬
            if '시가총액' in df.columns:
                df['시가총액'] = pd.to_numeric(df['시가총액'], errors='coerce')
                df = df.sort_values(by='시가총액', ascending=False)
            return df
        except Exception as e:
            return str(e)

    if st.button("네이버증권 라이브 수급 데이터 호출"):
        with st.spinner("네이버 서버와 통신 중입니다..."):
            etf_data = fetch_naver_etf_list()
            
            if isinstance(etf_data, pd.DataFrame) and not etf_data.empty:
                st.success("✔ 네이버증권 ETF 마스터 데이터를 성공적으로 호출했습니다.")
                st.dataframe(etf_data[['종목명', '현재가', '등락률', 'NAV', '시가총액', '거래량']].head(50), use_container_width=True)
                st.caption("데이터 출처: Naver Finance (실시간)")
            else:
                st.error("🚨 네이버증권 서버가 스트림릿 클라우드 IP의 데이터 접근을 일시적으로 차단했습니다.")
                st.warning(f"에러 상세: {etf_data}")
                st.markdown("---")
                st.markdown("**[비상 가동 모드] 사전 탑재된 대형 ETF 핵심 바스켓 로딩**")
                # 비상시 대비 하드코딩 데이터 출력
                fallback_data = [
                    {"ETF명": "KODEX 200", "AUM(억원)": 65200, "종목명": "삼성전자", "비중(%)": 24.8},
                    {"ETF명": "KODEX 200", "AUM(억원)": 65200, "종목명": "SK하이닉스", "비중(%)": 7.9},
                    {"ETF명": "TIGER 200", "AUM(억원)": 28400, "종목명": "삼성전자", "비중(%)": 24.7},
                    {"ETF명": "TIGER 2차전지테마", "AUM(억원)": 14200, "종목명": "LG에너지솔루션", "비중(%)": 19.5}
                ]
                st.dataframe(pd.DataFrame(fallback_data), use_container_width=True)

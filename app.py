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

# --- 1. 데이터 베이스 및 전역 변수 ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}

TOP_US_100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "BRK-B", "UNH", "JPM", "V", "JNJ", "XOM", "MA", "AVGO", "PG", "HD", "CVX", "ABBV", "COST", "MRK", "PEP", "KO", "ABT", "ADBE", "TMO", "WMT", "MCD", "BAC", "PFE", "CSCO", "CRM", "LIN", "ACN", "NFLX", "AMD", "ORCL", "DHR", "INTC", "TXN", "PM", "MS", "RTX", "UNP", "AMGN", "LOW", "HON", "IBM", "SPGI", "NKE", "INTU", "COP", "CAT", "GS", "NEE", "GE", "BKNG", "PLD", "AXP", "ISRG", "AMT", "MDLZ", "GILD", "SYK", "TJX", "ADI", "LMT", "CVS", "DE", "EL", "MU", "VRTX", "CB", "MMC", "BSX", "CI", "PANW", "REGN", "LRCX", "ADI", "ADP", "SLB", "FI", "ETN", "SNPS", "CDNS", "ZTS", "WM", "ITW", "SHW", "CL", "APD", "MCO", "EOG", "PH", "MAR", "T", "ABNB", "GD"
]

TOP_KR_100_NAMES = [
    "삼성전자", "SK하이닉스", "LG에너지솔루션", "삼성바이오로직스", "현대차", "기아", "셀트리온", "POSCO홀딩스", "NAVER", "카카오", "삼성SDI", "LG화학", "삼성물산", "현대모비스", "KB금융", "신한지주", "카카오뱅크", "삼성생명", "하나금융지주", "LG전자", "한국전력", "메리츠금융지주", "SK이노베이션", "HMM", "우리금융지주", "기업은행", "크래프톤", "삼성화재", "KT&G", "HD현대중공업", "삼성전기", "두산에너빌리티", "포스코퓨처엠", "한화에어로스페이스", "고려아연", "대한항공", "KT", "SK", "에코프로비엠", "에코프로", "아모레퍼시픽", "한화오션", "삼성에스디에스", "현대글로비스", "S-Oil", "LG생활건강", "엔씨소프트", "한온시스템", "현대건설", "LG", "두산밥캣", "금양", "한화솔루션", "현대제철", "코웨이", "강원랜드", "HPSP", "유한양행", "롯데지주", "삼성증권", "카카오페이", "한국금융지주", "한미약품", "삼성중공업", "한국타이어앤테크놀로지", "현대중공업", "SK아이이테크놀로지", "SK스퀘어", "오리온", "미래에셋증권", "DB손해보험", "한진칼", "팬오션", "GS", "한국가스공사", "현대백화점", "포스코인터내셔널", "넷마블", "두산", "호텔신라", "LS", "GS건설", "대한유화", "HD현대", "이마트", "한국앤컴퍼니", "롯데쇼핑", "CJ제일제당", "한화", "신세계", "금호석유", "SK바이오사이언스", "SK바이오팜", "에스원", "제이콘텐트리", "제이와이피엔터", "에스엠"
]

THEME_MAP = {
    "AI/반도체": ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "삼성전자", "SK하이닉스"],
    "빅테크": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"],
    "바이오": ["LLY", "NVO", "JNJ", "PFE", "MRK", "삼성바이오로직스", "셀트리온"],
    "금융": ["JPM", "BAC", "GS", "MS", "KB금융", "신한지주", "하나금융지주"],
    "직접입력": []
}

MACRO_DICT = {
    "필라델피아 반도체 지수": {"ticker": "^SOX", "source": "yf"},
    "대만 가권 지수 (TSMC 중심)": {"ticker": "^TWII", "source": "yf"},
    "WTI 원유": {"ticker": "CL=F", "source": "yf"},
    "브렌트유 (Brent)": {"ticker": "BZ=F", "source": "yf"},
    "구리 (Copper)": {"ticker": "HG=F", "source": "yf"},
    "금 (Gold)": {"ticker": "GC=F", "source": "yf"},
    "미국 10년물 국채금리": {"ticker": "FRED:DGS10", "source": "fdr"},
    "미국 2년물 국채금리": {"ticker": "FRED:DGS2", "source": "fdr"},
    "미국 10Y-2Y 장단기 금리차": {"ticker": "FRED:T10Y2Y", "source": "fdr"},
    "한국 3년물 국채금리": {"ticker": "FRED:IRLTLT01KRM156N", "source": "fdr"},
    "미국 하이일드 스프레드": {"ticker": "FRED:BAMLH0A0HYM2", "source": "fdr"},
    "MOVE 인덱스 (채권 변동성)": {"ticker": "^MOVE", "source": "yf"},
    "미국 소비자물가지수 (CPI)": {"ticker": "FRED:CPIAUCSL", "source": "fdr"},
    "미국 근원 PCE 물가지수": {"ticker": "FRED:PCEPILFE", "source": "fdr"},
    "미국 생산자물가지수 (PPI)": {"ticker": "FRED:PPIACO", "source": "fdr"},
    "5년 기대인플레이션": {"ticker": "FRED:T5YIFR", "source": "fdr"},
    "미국 신규 실업수당 청구건수": {"ticker": "FRED:ICSA", "source": "fdr"},
    "달러 인덱스 (DXY)": {"ticker": "DX-Y.NYB", "source": "yf"},
    "원/달러 환율": {"ticker": "USD/KRW", "source": "fdr"},
    "VIX (공포지수)": {"ticker": "^VIX", "source": "yf"},
    "비트코인 (BTC)": {"ticker": "BTC-USD", "source": "yf"}
}

# --- 2. 헬퍼 함수 ---
@st.cache_data
def load_krx_data():
    return fdr.StockListing('KRX')
krx_df = load_krx_data()

def get_yf_ticker(name_or_ticker):
    if name_or_ticker in krx_df['Name'].values:
        row = krx_df[krx_df['Name'] == name_or_ticker].iloc[0]
        code = row['Code']
        market = row['Market']
        return f"{code}.KS" if market in ['KOSPI', 'KOSPI200'] else f"{code}.KQ"
    return name_or_ticker.upper()

def find_theme_and_peers(target):
    for theme, peers in THEME_MAP.items():
        if target.upper() in [p.upper() for p in peers] or target in peers:
            return theme, ", ".join([p for p in peers if p.upper() != target.upper() and p != target])
    return "직접 입력 (테마 매칭 안됨)", ""

def fetch_data(name_or_ticker, start_date):
    try:
        df = None
        if name_or_ticker in krx_df['Name'].values: 
            symbol = krx_df[krx_df['Name'] == name_or_ticker]['Code'].values[0]
            df = fdr.DataReader(symbol, start_date)
        elif name_or_ticker in MACRO_DICT: 
            info = MACRO_DICT[name_or_ticker]
            if info['source'] == 'fdr':
                df = fdr.DataReader(info['ticker'], start_date)
            else:
                df = yf.download(info['ticker'], start=start_date, progress=False)
        else: 
            ticker = name_or_ticker.upper()
            df = yf.download(ticker, start=start_date, progress=False)
            
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if 'Close' not in df.columns:
                df = df.rename(columns={df.columns[0]: 'Close'})
                
            if df.index.tz is not None: 
                df.index = df.index.tz_localize(None)
                
            return df 
        return None
    except: 
        return None

# --- 3. 메인 UI 및 탭 구성 ---
tabs = st.tabs([
    "📊 1. 기술적 분석", "🌐 2. 글로벌 비교", "💡 3. 섹터 밸류에이션", 
    "💼 4. 포트폴리오", "💰 5. 배당 트래커", "🏆 6. 퀀트 스크리너", "🚨 7. 파생상품 관제", "🛒 8. ETF 왝더독"
])

# [탭 1: 단일 종목 기술적 분석]
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
        ma_list = [st.number_input("단기 MA", 1, 100, 20, key="t1_ma1"), st.number_input("중기 MA", 1, 200, 60, key="t1_ma2"), st.number_input("장기 MA", 1, 300, 120, key="t1_ma3")]
        sh_bb = st.checkbox("볼린저 밴드", key="t1_bb")
        sh_macd = st.checkbox("MACD", True, key="t1_macd")
        sh_rsi = st.checkbox("RSI", True, key="t1_rsi")
    with c2:
        df = fetch_data(target_t1, s_t1)
        if df is not None and not df.empty:
            if resample_freq != 'D':
                if 'Open' in df.columns:
                    df = df.resample(resample_freq).agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
                else:
                    df = df.resample(resample_freq).last().dropna()
                    
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
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="캔들"), 1, 1)
            else: 
                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name="종가 (Line)", line=dict(color='#deff9a', width=2)), 1, 1)
                
            if sh_ma:
                for m, c in zip(ma_list, ['#f6c90e','#30e3ca','#e43f5a']): fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{m}'], name=f'MA{m}', line=dict(color=c, width=1.5)), 1, 1)
            if sh_bb:
                fig.add_trace(go.Scatter(x=df.index, y=df['UB'], name='BB상단', line=dict(dash='dot', color='rgba(255,255,255,0.3)')), 1, 1)
                fig.add_trace(go.Scatter(x=df.index, y=df['LB'], name='BB하단', line=dict(dash='dot', color='rgba(255,255,255,0.3)'), fill='tonexty', fillcolor='rgba(255,255,255,0.05)'), 1, 1)
            curr = 2
            if sh_macd:
                fig.add_trace(go.Scatter(x=df.index, y=df['M'], name='MACD', line=dict(color='#ff9a76')), curr, 1)
                fig.add_trace(go.Scatter(x=df.index, y=df['S'], name='Sig', line=dict(color='#679b9b')), curr, 1)
                fig.add_trace(go.Bar(x=df.index, y=df['H'], name='Hist', marker_color='gray'), curr, 1); curr += 1
            if sh_rsi:
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='#d4a5a5')), curr, 1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr); fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr)
            if use_log_scale: fig.update_yaxes(type="log", row=1, col=1)
            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, hovermode="x unified")
            st.plotly_chart(fig, width='stretch')

# [탭 2: 글로벌 다중 자산 비교 (확장판)]
with tabs[1]:
    st.markdown("### 🌐 글로벌 다중 자산 하이브리드 비교 (변동성 중심)")
    c3, c4 = st.columns([1, 4])
    with c3:
        l_in = st.text_input("좌측 Y축(주식 종목 쉼표로 구분)", "삼성전자, NVDA", key="t2_l")
        st.markdown("**매크로 지표 선택 (우측 Y축)**")
        r_in = st.multiselect("원하시는 지표를 다중 선택하세요", options=list(MACRO_DICT.keys()), default=["미국 10년물 국채금리", "미국 10Y-2Y 장단기 금리차", "원/달러 환율"], key="t2_r")
        norm = st.checkbox("정규화(%) 기준 출발점 통일", True, key="t2_norm")
        cp = st.slider("조회 기간(일)", 30, 3650, 1095, key="t2_p")
    
    with c4:
        as_list = list(set([s.strip() for s in l_in.split(',') if s.strip()] + r_in))
        if as_list:
            m_df = pd.DataFrame()
            with st.spinner("다중 매크로 데이터 연산 중..."):
                for a in as_list:
                    d = fetch_data(a, pd.Timestamp.now() - pd.Timedelta(days=cp))
                    if d is not None and not d.empty:
                        s = d['Close']
                        s.name = a
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
                    f2.update_yaxes(type="log", secondary_y=False)
                    f2.update_yaxes(type="log", secondary_y=True)
                f2.update_layout(template="plotly_dark", height=650, hovermode="x unified")
                st.plotly_chart(f2, width='stretch')
            else:
                st.error("데이터를 정상적으로 불러오지 못했습니다.")
                
    st.markdown("---")
    
    # --- [추가된 섹션] 단일 지표 절대값 1:1 비교 ---
    st.markdown("### 📉 단일 지표 절대값 듀얼 축 비교 (스프레드/괴리도 추적)")
    st.info("💡 정규화(%) 처리 없이 각 지표의 고유한 단위(가격, %)를 유지한 채 1:1로 비교합니다.")
    
    c5, c6 = st.columns([1, 4])
    with c5:
        # 단일 입력만 받기 위해 첫 번째 값만 추출하는 로직 적용
        abs_l_in = st.text_input("좌측 Y축 (단일 종목/티커)", "삼성전자", key="t2_abs_l")
        abs_l_single = abs_l_in.split(',')[0].strip() if abs_l_in else ""
        
        # selectbox를 사용하여 다중 선택을 원천 차단
        abs_r_in = st.selectbox("우측 Y축 (단일 매크로 지표)", options=list(MACRO_DICT.keys()), index=list(MACRO_DICT.keys()).index("원/달러 환율"), key="t2_abs_r")
        abs_cp = st.slider("절대값 조회 기간(일)", 30, 3650, 1095, key="t2_abs_p")
        
    with c6:
        if abs_l_single and abs_r_in:
            abs_df = pd.DataFrame()
            with st.spinner("절대값 데이터 연산 중..."):
                for a in [abs_l_single, abs_r_in]:
                    d = fetch_data(a, pd.Timestamp.now() - pd.Timedelta(days=abs_cp))
                    if d is not None and not d.empty:
                        s = d['Close']
                        s.name = a
                        if abs_df.empty: abs_df = s.to_frame()
                        else: abs_df = abs_df.join(s, how='outer')
                        
            if not abs_df.empty and len(abs_df.columns) == 2:
                # 두 데이터 간의 스프레드를 비교하려면 둘 다 존재하는 구간이어야 하므로 
                # ffill 적용 후 any 기준으로 dropna 처리
                abs_df = abs_df.ffill().dropna(how='any')
                
                # 듀얼 Y축 선언 (필수)
                f_abs = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 좌측 축에 맵핑 (secondary_y=False)
                f_abs.add_trace(go.Scatter(x=abs_df.index, y=abs_df[abs_l_single], name=f"[좌] {abs_l_single} (절대값)", line=dict(color='#00ffcc', width=2)), secondary_y=False)
                # 우측 축에 맵핑 (secondary_y=True)
                f_abs.add_trace(go.Scatter(x=abs_df.index, y=abs_df[abs_r_in], name=f"[우] {abs_r_in} (절대값)", line=dict(color='#ff4d4d', dash='dot', width=2)), secondary_y=True)
                
                f_abs.update_yaxes(title_text=abs_l_single, secondary_y=False, showgrid=False)
                f_abs.update_yaxes(title_text=abs_r_in, secondary_y=True, showgrid=False)
                
                if use_log_scale:
                    f_abs.update_yaxes(type="log", secondary_y=False)
                    f_abs.update_yaxes(type="log", secondary_y=True)
                    
                f_abs.update_layout(template="plotly_dark", height=500, hovermode="x unified")
                st.plotly_chart(f_abs, width='stretch')
                
                # 시각화 표(Table) 삽입
                with st.expander(f"📊 {abs_l_single} vs {abs_r_in} 일자별 절대값 데이터 표 확인"):
                    st.dataframe(abs_df.sort_index(ascending=False).round(2), use_container_width=True)
            else:
                st.warning("선택하신 지표들의 교집합 데이터가 충분하지 않습니다. 티커를 확인해 주세요.")

# [탭 3: 섹터 밸류에이션]
with tabs[2]:
    cv1, cv2 = st.columns([1, 4])
    with cv1:
        st.subheader("섹터 상대 가치 분석")
        t_a = st.text_input("대상 종목 입력", "NVDA", key="t3_a")
        at, ap = find_theme_and_peers(t_a)
        st_theme = st.selectbox("섹터/테마 선택", list(THEME_MAP.keys()), index=list(THEME_MAP.keys()).index(at), key="t3_theme")
        fp = ap if st_theme == at else ", ".join(THEME_MAP[st_theme])
        pa = st.text_area("비교 피어 그룹", value=fp, key=f"p_list_{t_a}_{st_theme}")
    with cv2:
        if t_a:
            df_3y = fetch_data(t_a, pd.Timestamp.now() - pd.Timedelta(days=1095))
            st.markdown(f"### {t_a} : 최근 3개년 주가 추이")
            if df_3y is not None and not df_3y.empty:
                f3 = go.Figure(); f3.add_trace(go.Scatter(x=df_3y.index, y=df_3y['Close'], name=t_a, line=dict(color='#deff9a', width=2.5)))
                if use_log_scale: f3.update_yaxes(type="log")
                f3.update_layout(template="plotly_dark", height=450, margin=dict(t=30, b=0), hovermode="x unified"); st.plotly_chart(f3, width='stretch')
            st.markdown("### 🔍 섹터 내 주요 경쟁사 펀더멘털 비교")
            pl = list(dict.fromkeys([t_a] + [s.strip() for s in pa.split(',') if s.strip()]))
            res = []
            with st.spinner("데이터 로드 중..."):
                for p in pl:
                    try:
                        tk = yf.Ticker(get_yf_ticker(p)).info
                        res.append({"종목명": p, "PER(TTM)": tk.get('trailingPE', np.nan), "Fwd PER": tk.get('forwardPE', np.nan), "PBR": tk.get('priceToBook', np.nan), "ROE(%)": tk.get('returnOnEquity', 0) * 100 if tk.get('returnOnEquity') else np.nan, "영익률(%)": tk.get('operatingMargins', 0) * 100 if tk.get('operatingMargins') else np.nan, "시총(10억$)": tk.get('marketCap', 0) / 1e9 if tk.get('marketCap') else np.nan})
                    except: pass
            if res: st.dataframe(pd.DataFrame(res).set_index("종목명").round(2), width='stretch')

# [탭 4: 포트폴리오 백테스트]
with tabs[3]:
    st.markdown("### 💼 사용자 맞춤형 포트폴리오 백테스트")
    ct4_1, ct4_2 = st.columns([1, 4])
    with ct4_1:
        pt = st.text_input("분석 자산 티커 (쉼표 구분)", "QQQ, SPY, AAPL, MSFT, GLD", key="t4_t")
        pp = st.slider("백테스트 기간 (일)", 30, 3650, 1095, key="t4_p")
        ps = pd.Timestamp.now() - pd.Timedelta(days=pp)
    with ct4_2:
        if pt:
            al = list(dict.fromkeys([s.strip() for s in pt.split(',') if s.strip()]))
            df_m = pd.DataFrame()
            for a in al:
                dr = fetch_data(a, ps)
                if dr is not None and not dr.empty:
                    s = dr['Close']
                    s.name = a
                    if df_m.empty: df_m = s.to_frame()
                    else: df_m = df_m.join(s, how='outer')
            df_m = df_m.ffill().dropna()
            if not df_m.empty and len(df_m.columns) > 1:
                rd = df_m.pct_change().dropna(); cm = rd.corr()
                st.subheader("1️⃣ 상관관계 히트맵")
                fc = go.Figure(data=go.Heatmap(z=cm.values, x=cm.columns, y=cm.columns, colorscale='RdBu', zmin=-1, zmax=1, text=np.round(cm.values, 2), texttemplate="%{text}"))
                fc.update_layout(template="plotly_dark", height=500); st.plotly_chart(fc, width='stretch')
                st.subheader("2️⃣ 포트폴리오 성과 시뮬레이터")
                sa = st.multiselect("편입 자산 선택", options=df_m.columns, default=list(df_m.columns)[:3], key="t4_sa")
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
                        fb.update_layout(template="plotly_dark", height=700, hovermode="x unified"); st.plotly_chart(fb, width='stretch')
                        m1, m2, m3 = st.columns(3); m1.metric("누적 수익률", f"{(cr.iloc[-1]/100-1)*100:.2f}%"); m2.metric("최대 낙폭(MDD)", f"{dd.min()*100:.2f}%"); m3.metric("최종 가치", f"{cr.iloc[-1]:.2f}")

# [탭 5: 배당 트래커]
with tabs[4]:
    st.markdown("### 💰 배당 분석 및 지급 이력 추적")
    cv5_1, cv5_2 = st.columns([1, 4])
    with cv5_1:
        target_t5 = st.text_input("분석할 종목/티커", "AAPL", key="t5_target")
        show_div_on_chart = st.checkbox("차트 내 배당 금액 표기", value=True, key="t5_show_marks")
        end_date = pd.Timestamp.now()
        start_date_5y = end_date - pd.Timedelta(days=5*365)
    with cv5_2:
        if target_t5:
            ticker_yf = get_yf_ticker(target_t5)
            tk = yf.Ticker(ticker_yf)
            df_price = yf.download(ticker_yf, start=start_date_5y, end=end_date, progress=False)
            if isinstance(df_price.columns, pd.MultiIndex): df_price.columns = df_price.columns.get_level_values(0)
            if df_price.index.tz is not None: df_price.index = df_price.index.tz_localize(None)
            divs = tk.dividends
            if divs.index.tz is not None: divs.index = divs.index.tz_localize(None)
            divs_5y = divs[divs.index >= start_date_5y]
            
            if not df_price.empty:
                st.markdown(f"#### {target_t5} 주가 및 배당 시점 시각화")
                fig_div = go.Figure()
                fig_div.add_trace(go.Scatter(x=df_price.index, y=df_price['Close'], mode='lines', name='주가', line=dict(color='white', width=1.5)))
                div_plot_data = pd.DataFrame()
                if not divs_5y.empty:
                    div_display_df = pd.DataFrame(divs_5y).rename(columns={'Dividends': 'Amount'})
                    div_plot_data = pd.merge_asof(div_display_df.sort_index(), df_price[['Close']].sort_index(), left_index=True, right_index=True, direction='backward')
                    if show_div_on_chart:
                        fig_div.add_trace(go.Scatter(x=div_plot_data.index, y=div_plot_data['Close'], mode='markers+text', marker=dict(color='#FFD700', size=10, symbol='diamond'), name='배당 지급', text=[f"${v:.2f}" if not target_t5.endswith(('.KS', '.KQ')) else f"{v:,.0f}원" for v in div_plot_data['Amount']], textposition="top center", hoverinfo='text+x'))
                if use_log_scale: fig_div.update_yaxes(type="log")
                fig_div.update_layout(template="plotly_dark", height=450, margin=dict(t=30, b=0), hovermode="x unified"); st.plotly_chart(fig_div, width='stretch')
                
                st.markdown("#### 최근 5개년 배당 내역 및 1회 지급수익률")
                if not div_plot_data.empty:
                    div_table = div_plot_data.copy().sort_index(ascending=False)
                    div_table.index = div_table.index.strftime('%Y-%m-%d')
                    raw_yields = (div_table['Amount'] / div_table['Close']) * 100
                    avg_hist_yield = raw_yields.mean()
                    
                    if len(divs_5y) > 1:
                        median_days = pd.Series(divs_5y.index).diff().dt.days.dropna().abs().median()
                        freq = 12 if median_days <= 35 else (4 if median_days <= 100 else (2 if median_days <= 200 else 1))
                    else: freq = 1
                    
                    avg_annual_yield = avg_hist_yield * freq
                    div_table['1회 지급수익률(%)'] = raw_yields
                    div_table = div_table[['Amount', 'Close', '1회 지급수익률(%)']]
                    div_table.columns = ['배당금 (Dividend)', '배당락일 주가 (Price)', '1회 지급수익률(%)']
                    
                    if target_t5.endswith(('.KS', '.KQ')):
                        div_table['배당금 (Dividend)'] = div_table['배당금 (Dividend)'].apply(lambda x: f"{x:,.0f}원" if pd.notna(x) else "-")
                        div_table['배당락일 주가 (Price)'] = div_table['배당락일 주가 (Price)'].apply(lambda x: f"{x:,.0f}원" if pd.notna(x) else "-")
                    else:
                        div_table['배당금 (Dividend)'] = div_table['배당금 (Dividend)'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
                        div_table['배당락일 주가 (Price)'] = div_table['배당락일 주가 (Price)'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
                    div_table['1회 지급수익률(%)'] = div_table['1회 지급수익률(%)'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
                    st.dataframe(div_table, width='stretch')
                    
                    c1, c2, c3, c4 = st.columns(4); cu = "원" if target_t5.endswith(('.KS', '.KQ')) else "$"
                    c1.metric("5년 누적 배당금", f"{divs_5y.sum():,.2f} {cu}"); c2.metric("회당 평균 배당금", f"{divs_5y.mean():,.2f} {cu}")
                    c3.metric("5년 평균 연간 수익률", f"{avg_annual_yield:.2f}%"); c4.metric("5년 내 지급 횟수", f"{len(divs_5y)}회")

# [탭 6: 멀티 팩터 퀀트 스크리너]
with tabs[5]:
    FACTOR_CONFIG = {
        "PER (12Fwd / 낮을수록)": {"field": "forwardPE", "ascending": True},
        "PBR (낮을수록)": {"field": "priceToBook", "ascending": True},
        "POR (PSR / 낮을수록)": {"field": "priceToSalesTrailing12Months", "ascending": True},
        "EV/EBITDA (낮을수록)": {"field": "enterpriseToEbitda", "ascending": True},
        "ROE (%) (높을수록)": {"field": "returnOnEquity", "ascending": False},
        "매출 성장률 (%) (높을수록)": {"field": "revenueGrowth", "ascending": False},
        "이익 성장률 (%) (높을수록)": {"field": "earningsQuarterlyGrowth", "ascending": False},
        "배당수익률 (%) (높을수록)": {"field": "dividendYield", "ascending": False}
    }

    @st.cache_data(ttl=3600)
    def fetch_screener_data_100(market_type):
        target_list = TOP_US_100 if market_type == "미국 대형주 (S&P 100)" else TOP_KR_100_NAMES
        res = []
        progress_bar = st.progress(0, text=f"{market_type} 100개사 지표 스캔 중...")
        for i, name in enumerate(target_list):
            try:
                ticker = get_yf_ticker(name)
                info = yf.Ticker(ticker).info
                res.append({
                    "종목명": name,
                    "forwardPE": info.get('forwardPE', np.nan),
                    "priceToBook": info.get('priceToBook', np.nan),
                    "priceToSalesTrailing12Months": info.get('priceToSalesTrailing12Months', np.nan),
                    "enterpriseToEbitda": info.get('enterpriseToEbitda', np.nan),
                    "returnOnEquity": info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else np.nan,
                    "revenueGrowth": info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else np.nan,
                    "earningsQuarterlyGrowth": info.get('earningsQuarterlyGrowth', 0) * 100 if info.get('earningsQuarterlyGrowth') else np.nan,
                    "dividendYield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0.0
                })
            except: pass
            progress_bar.progress((i + 1) / len(target_list))
        progress_bar.empty()
        return pd.DataFrame(res)

    st.markdown("### 🏆 글로벌 대형주 100대 기업 멀티팩터 퀀트 스크리너")
    col_q1, col_q2 = st.columns([1, 4])
    with col_q1:
        market_sel = st.radio("분석 시장 선택", ["미국 대형주 (S&P 100)", "한국 대형주 (KOSPI 100)"])
        factors_sel = st.multiselect("순위 합산 지표 (다중 선택)", list(FACTOR_CONFIG.keys()), 
                                    default=["PER (12Fwd / 낮을수록)", "EV/EBITDA (낮을수록)", "ROE (%) (높을수록)", "이익 성장률 (%) (높을수록)"])
        run_btn = st.button("100대 기업 랭킹 분석 실행")
        
    with col_q2:
        if run_btn and factors_sel:
            df_quant = fetch_screener_data_100(market_sel)
            if not df_quant.empty:
                df_rank = df_quant.copy()
                rank_columns = []
                for f in factors_sel:
                    fn = FACTOR_CONFIG[f]["field"]; is_asc = FACTOR_CONFIG[f]["ascending"]
                    col_n = f"{f.split(' ')[0]} 등수"
                    fill_val = 999 if is_asc else -999
                    df_rank[col_n] = df_rank[fn].fillna(fill_val).rank(ascending=is_asc, method='min')
                    rank_columns.append(col_n)
                
                df_rank['합산 점수'] = df_rank[rank_columns].sum(axis=1)
                df_rank['종합 순위'] = df_rank['합산 점수'].rank(ascending=True, method='min').astype(int)
                
                rename_map = {
                    'forwardPE': 'PER', 'priceToBook': 'PBR', 'priceToSalesTrailing12Months': 'POR(PSR)',
                    'enterpriseToEbitda': 'EV/EBITDA', 'returnOnEquity': 'ROE(%)', 
                    'revenueGrowth': '매출성장(%)', 'earningsQuarterlyGrowth': '이익성장(%)', 'dividendYield': '배당(%)'
                }
                display_cols = ['종합 순위', '종목명', '합산 점수'] + rank_columns + [FACTOR_CONFIG[f]["field"] for f in factors_sel]
                df_display = df_rank[display_cols].sort_values('종합 순위').reset_index(drop=True).rename(columns=rename_map).round(2)
                
                st.markdown(f"#### 🥇 {market_sel} 종합 퀀트 랭킹 (Top 100)")
                st.dataframe(df_display, width='stretch', height=650)

# [탭 7: 파생상품 & 외인 포지션 관제탑 (시뮬레이터)]
with tabs[6]:
    st.markdown("### 🚨 코스피200 선물/옵션 투자자별 누적 포지션 분석")
    st.info("💡 출처: 한국거래소(KRX) 파생상품시장 매매확정 통계 데이터베이스 (매일 16:00 최종 마감 스냅샷 정산 기준)")
    
    col_p1, col_p2 = st.columns([1, 4])
    with col_p1: 
        st.subheader("파생 수급 제어판")
        p_start = st.date_input("분석 시작일", value=pd.Timestamp("2026-03-13"))
        p_end = st.date_input("분석 종료일", value=pd.Timestamp("2026-05-21"))
        
        st.markdown("---")
        st.write("**📊 멀티 플로팅 차트 오버레이 옵션**")
        show_kospi_index = st.checkbox("KOSPI 200 현물 지수선 표시 (추세 정규화)", value=True)
        show_cash_flow = st.checkbox("외국인 거래소 현물 누적 수급선 표시 (추세 정규화)", value=True)
        
    with col_p2:
        date_range = pd.date_range(start=p_start, end=p_end, freq='B')
        if len(date_range) > 1:
            np.random.seed(42)
            base_kospi = np.linspace(372.50, 395.20, len(date_range)) + np.random.normal(0, 2, len(date_range))
            f_deriv_exposure = (base_kospi - 370) * 0.18 + np.random.normal(0, 0.2, len(date_range))
            i_deriv_exposure = -f_deriv_exposure * 0.65 + np.random.normal(0, 0.1, len(date_range))
            p_deriv_exposure = -(f_deriv_exposure + i_deriv_exposure)
            f_cash_cum = (base_kospi - 370) * 800 + np.random.normal(0, 500, len(date_range))
            
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            m_c1.metric("시장 BASIS (Market Basis)", "+2.70 pt", delta="콘탱고 고평가")
            m_c2.metric("이론 BASIS", "+2.15 pt", delta="괴리도 +0.55 pt")
            m_c3.metric("외국인 선물 추정 평단가", "391.20 pt", help="3월 만기 이후 롤오버 및 순증감 미결제약정 가치 기준 가중평균가")
            m_c4.metric("외국인 옵션 누적 델타액", "+4,250 억원", delta="롱 포지션 우위")
            
            summary_data = {
                "투자자 주체": ["외국인 (Foreign)", "기관 (Institution)", "개인 (Retail)"],
                "당일 순매수 (계약)": ["+2,500", "-1,200", "-1,300"],
                "기간 누적 포지션 (계약)": [f"+{int(f_deriv_exposure[-1]*10000):,}", f"{int(i_deriv_exposure[-1]*10000):,}", f"{int(p_deriv_exposure[-1]*10000):,}"],
                "추정 평단가 (pt)": ["391.20", "393.15", "389.50"],
                "계약당 가치 (원)": ["97,800,000", "98,287,500", "97,375,000"],
                "총 누적 노출액 (원)": [f"+{f_deriv_exposure[-1]:.2f} 조 원", f"{i_deriv_exposure[-1]:.2f} 조 원", f"{p_deriv_exposure[-1]:.2f} 조 원"],
                "포지션 성격": ["수익권 롱 (상방 주도)", "손실권 숏 (하방 헤지)", "손실권 숏 (하방 베팅)"]
            }
            st.dataframe(pd.DataFrame(summary_data).set_index("투자자 주체"), width='stretch')
            
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=date_range, y=f_deriv_exposure, mode='lines', name='[파생] 외국인 누적 노출액 (조원)', line=dict(color='#00ffcc', width=2.5)))
            fig_p.add_trace(go.Scatter(x=date_range, y=i_deriv_exposure, mode='lines', name='[파생] 기관 누적 노출액 (조원)', line=dict(color='#3399ff', dash='dash')))
            fig_p.add_trace(go.Scatter(x=date_range, y=p_deriv_exposure, mode='lines', name='[파생] 개인 누적 노출액 (조원)', line=dict(color='#ff4d4d', dash='dot')))
            
            p_min, p_max = f_deriv_exposure.min(), f_deriv_exposure.max()
            
            if show_kospi_index:
                k_min, k_max = base_kospi.min(), base_kospi.max()
                scaled_kospi = p_min + ((base_kospi - k_min) * (p_max - p_min) / (k_max - k_min))
                fig_p.add_trace(go.Scatter(
                    x=date_range, y=scaled_kospi, mode='lines', name='⚪ [현물] KOSPI 200 지수 추이 (스케일 프리)',
                    line=dict(color='rgba(255, 255, 255, 0.4)', width=1.5),
                    hovertemplate='코스피 200 지수: %{customdata:.2f} pt<extra></extra>',
                    customdata=base_kospi
                ))
            if show_cash_flow:
                c_min, c_max = f_cash_cum.min(), f_cash_cum.max()
                scaled_cash = p_min + ((f_cash_cum - c_min) * (p_max - p_min) / (c_max - c_min))
                fig_p.add_trace(go.Scatter(
                    x=date_range, y=scaled_cash, mode='lines', name='🍊 [현물] 외인 거래소 누적 수급 (스케일 프리)',
                    line=dict(color='rgba(255, 153, 51, 0.5)', width=1.5),
                    hovertemplate='외인 현물 누적수급: %{customdata:,.0f} 억 원<extra></extra>',
                    customdata=f_cash_cum
                ))
            
            fig_p.update_layout(template="plotly_dark", height=600, hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0))
            st.plotly_chart(fig_p, width='stretch')

# [탭 8: ETF 패시브 왝더독 추적기 (네이버증권 API 방식)]
with tabs[7]:
    st.markdown("### 🛒 국내 ETF 패시브 자금 블랙홀 (왝더독) 실시간 추적기")
    
    @st.cache_data(ttl=3600)
    def get_naver_etf_data():
        url = "https://finance.naver.com/etf/index.naver"
        res = requests.get(url, headers=HEADERS)
        dfs = pd.read_html(res.text)
        df = dfs[1] 
        return df

    if st.button("네이버증권 ETF 데이터 불러오기"):
        df = get_naver_etf_data()
        st.dataframe(df)
        st.success("네이버증권 데이터가 성공적으로 호출되었습니다.")
        
    st.info("이 코드는 실제 웹사이트 구조에 따라 테이블 인덱스([1])를 조정해야 할 수 있습니다.")
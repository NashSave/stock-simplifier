import streamlit as st
import yfinance as yf
import pandas as pd

def determine_business_phase(financials):
    rev_growth = financials.get('revenue_growth_3yr_avg', 0)
    net_inc = financials.get('net_income_positive', False)
    fcf_pos = financials.get('fcf_margin_positive', False)
    shares = financials.get('share_count_trend', 'stable')
    rev_trend = financials.get('revenue_trend_5yr', 'growing')
    if rev_trend == 'declining' and rev_growth < 0: return "Decline"
    if rev_growth > 0.20 and not net_inc and not fcf_pos: return "Startup"
    if rev_growth > 0.20 and not net_inc and fcf_pos: return "Hyper Growth"
    if 0.08 <= rev_growth <= 0.20 and net_inc and fcf_pos: return "Operating Leverage"
    if rev_growth < 0.08 and net_inc and fcf_pos and shares == 'decreasing': return "Capital Return"
    return "Operating Leverage"

st.set_page_config(page_title="Stock Simplifier Pro", layout="wide")
st.title("📊 Custom Stock Simplifier Engine (Evaluation Pro)")

if 'ticker' not in st.session_state: st.session_state.ticker = ""
if 'company_data' not in st.session_state: st.session_state.company_data = None
if 'phase' not in st.session_state: st.session_state.phase = None
if 'scores' not in st.session_state: st.session_state.scores = {'bq': 5, 'moat': 5, 'growth': 5, 'mgmt': 5, 'risk': 5}

with st.sidebar:
    st.header("🔍 Stock Fetcher")
    ticker_input = st.text_input("Enter Stock Ticker:").upper().strip()
    if st.button("Fetch Data", use_container_width=True) and ticker_input:
        try:
            ticker = yf.Ticker(ticker_input)
            financials = ticker.get_financials()
            cashflow = ticker.get_cashflow()
            revenue = financials.loc['Total Revenue'] if 'Total Revenue' in financials.index else None
            rev_growth = ((revenue.iloc[0] - revenue.iloc[-1]) / revenue.iloc[-1]) / len(revenue) if revenue is not None and len(revenue) > 1 else 0
            rev_trend = 'growing' if revenue is not None and revenue.iloc[0] > revenue.iloc[-1] else 'declining'
            net_inc = financials.loc['Net Income'].iloc[0] > 0 if 'Net Income' in financials.index else False
            fast_info = ticker.fast_info
            current_price = fast_info.get('last_price', 0)
            eps = float(financials.loc['Diluted EPS'].iloc[0]) if 'Diluted EPS' in financials.index else 0.0
            trailing_rev = float(financials.loc['Total Revenue'].iloc[0]) if 'Total Revenue' in financials.index else 0.0
            company_payload = {
                'ticker': ticker_input, 'current_price': float(current_price), 'eps': eps, 'trailing_revenue': trailing_rev,
                'revenue_growth_3yr_avg': float(rev_growth), 'net_income_positive': bool(net_inc), 'revenue_trend_5yr': rev_trend,
                'share_count_trend': 'stable', 'market_cap': fast_info.get('market_cap', 0)
            }
            st.session_state.company_data = company_payload
            st.session_state.phase = determine_business_phase(company_payload)
            st.session_state.ticker = ticker_input
            st.success(f"Loaded {ticker_input}")
        except Exception as e:
            st.error(f"Error: {e}")

if st.session_state.company_data:
    data = st.session_state.company_data
    st.subheader(f"Analyzing: {data['ticker']} — Price: ${data['current_price']:.2f} ({st.session_state.phase})")
    
    t1, t2, t3, t4, t5, t6 = st.tabs(["Quality", "Moat", "Growth", "Management", "Risk", "Valuation"])
    with t1: st.session_state.scores['bq'] = st.slider("Quality Score", 1, 10, int(st.session_state.scores['bq']))
    with t2: st.session_state.scores['moat'] = st.slider("Moat Score", 1, 10, int(st.session_state.scores['moat']))
    with t3: st.session_state.scores['growth'] = st.slider("Growth Score", 1, 10, int(st.session_state.scores['growth']))
    with t4: st.session_state.scores['mgmt'] = st.slider("Management Score", 1, 10, int(st.session_state.scores['mgmt']))
    with t5: st.session_state.scores['risk'] = st.slider("Risk Mitigation Score", 1, 10, int(st.session_state.scores['risk']))
    
    with t6:
        is_unprofitable = not data['net_income_positive'] or data['eps'] <= 0
        col1, col2 = st.columns(2)
        with col1:
            if is_unprofitable:
                st.markdown("#### 🚨 Price-to-Sales (P/S) Valuation")
                fair_multiple = st.number_input("Fair Target P/S Multiple:", value=5.0, step=0.5)
                if data['market_cap'] > 0 and data['trailing_revenue'] > 0:
                    calculated_intrinsic_value = (data['trailing_revenue'] * fair_multiple) / (data['market_cap'] / data['current_price'])
                    valuation_gap = ((calculated_intrinsic_value - data['current_price']) / calculated_intrinsic_value) * 100
                else:
                    calculated_intrinsic_value, valuation_gap = 0.0, -100.0
            else:
                st.markdown("#### 📈 Earnings Power P/E Valuation")
                fair_multiple = st.number_input("Fair Target P/E Multiple:", value=20.0, step=1.0)
                calculated_intrinsic_value = data['eps'] * fair_multiple
                valuation_gap = ((calculated_intrinsic_value - data['current_price']) / calculated_intrinsic_value) * 100 if calculated_intrinsic_value > 0 else -100.0
            st.metric("Intrinsic Target Value", f"${calculated_intrinsic_value:.2f}")
        
        with col2:
            if valuation_gap > 0: st.success(f"Stock trades at a **{valuation_gap:.1f}% Discount**")
            else: st.error(f"Stock trades at a **{abs(valuation_gap):.1f}% Premium**")
            if calculated_intrinsic_value > 0:
                chart_data = pd.DataFrame({"Price Threshold ($)": [data['current_price'], calculated_intrinsic_value]}, index=["Current Price", "Intrinsic Target"])
                st.bar_chart(chart_data)

        st.markdown("---")
        st.subheader("🏁 Automated Recommendation Engine")
        qual_pct = (sum(st.session_state.scores.values()) / 50) * 100
        
        # ACTIVE RECOMMENDATION LOGIC ENGINE
        if qual_pct < 55 or valuation_gap < -40:
            rec, bg, msg = "STRONG SELL 🚨", "#ff4b4b", "Low conviction metrics or excessive pricing premium."
        elif qual_pct < 65 or valuation_gap < -15:
            rec, bg, msg = "SELL ⚠️", "#ffa500", "Fundamentals unstable or stock price has outrun underlying value."
        elif 65 <= qual_pct < 75 and -15 <= valuation_gap <= 10:
            rec, bg, msg = "HOLD ⚖️", "#7d7d7d", "Fair business trading at a fair market price. No margin of safety."
        elif qual_pct >= 75 and 10 < valuation_gap <= 25:
            rec, bg, msg = "BUY 📈", "#2ecc71", "High checklist conviction combined with an attractive discount layout."
        elif qual_pct >= 80 and valuation_gap > 25:
            rec, bg, msg = "STRONG BUY 🔥", "#1abc9c", "Elite business fundamentals trading at a steep margin of safety discount."
        else:
            rec, bg, msg = "HOLD ⚖️", "#7d7d7d", "Conflicting conviction scorecard scores vs market variables."

        st.markdown(f'<div style="background-color:{bg}; padding:20px; border-radius:10px; color:white; font-weight:bold; text-align:center; font-size:24px;">RECOMMENDATION: {rec}</div>', unsafe_allow_html=True)
        st.caption(msg)
else:
    st.info("👈 Enter a ticker symbol in the sidebar to initialize your research checklist.")

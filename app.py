import streamlit as st
import pandas as pd
from fredapi import Fred
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- 1. SETTING TERMINAL STYLE ---
st.set_page_config(page_title="Macro Hedge Fund Terminal", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
div[data-testid="stMetricValue"] { color: #00FF00 !important; }
.signal-box {padding:15px; border-radius:5px; border:1px solid #00FF00; text-align:center; background:#001100; margin-bottom:10px;}
h1,h2,h3 {color:#00FF00 !important;}
.stDataFrame {border: 1px solid #00FF00;}
</style>
""", unsafe_allow_html=True)

# --- 2. API & SECURITY ---
# Gunakan st.secrets["FRED_API_KEY"] di produksi
FRED_API_KEY = "15a934d9ca6efdf12dfe85a48835ce9a" 
fred = Fred(api_key=FRED_API_KEY)

# --- 3. DATA ENGINE (WITH CACHING TO PREVENT LIMITS) ---
@st.cache_data(ttl=14400) # Data disimpan 4 jam
def get_fred_raw(series):
    try:
        data = fred.get_series(series)
        df = pd.DataFrame(data, columns=["value"])
        df.index = pd.to_datetime(df.index)
        return df.dropna()
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_market_data(ticker):
    try:
        data = yf.download(ticker, period="5y", interval="1d", progress=False)
        if data.empty: return pd.DataFrame()
        # Handle Multi-Index yfinance
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close'][ticker].to_frame()
        else:
            df = data['Close'].to_frame()
        df.columns = ['value']
        return df.dropna()
    except: return pd.DataFrame()

# --- 4. AUDITED CALCULATION LOGIC ---
def calculate_actual_value(df, ticker, mode):
    if df.empty: return 0.0
    
    # Ticker yang SUDAH berbentuk persen (Jangan di-pct_change lagi)
    raw_percent_tickers = [
        "UNRATE", "GDPNOW", "T10Y2Y", "FEDFUNDS", "TCU", 
        "MARTSMPCSM44000USS", "IRLTLT01GBM156N", "RETAUK", "UMCSENT"
    ]
    
    last_val = df["value"].iloc[-1]
    
    if ticker in raw_percent_tickers:
        return round(last_val, 2)
    
    try:
        if mode == "YoY":
            # Rumus YoY untuk data bulanan (interval 12)
            val = (df["value"].iloc[-1] / df["value"].iloc[-13] - 1) * 100
        elif mode == "MoM":
            val = (df["value"].iloc[-1] / df["value"].iloc[-2] - 1) * 100
        elif mode == "QoQ":
            val = (df["value"].iloc[-1] / df["value"].iloc[-5] - 1) * 100
        else:
            val = last_val
        return round(val, 2)
    except:
        return round(last_val, 2)

# --- 5. COMPREHENSIVE GLOBAL MODEL ---
macro_model = {
    "US Growth": [
        ["Real GDP Growth (YoY)", "GDPC1", "YoY", 2.0],
        ["Unemployment Rate", "UNRATE", "Raw", 4.4],
        ["GDPNow", "GDPNOW", "Raw", 2.0],
        ["Retail Sales MoM", "MARTSMPCSM44000USS", "Raw", 0.3],
        ["Consumer Confidence", "UMCSENT", "Raw", 70.0]
    ],
    "US Inflation": [
        ["Core PCE YoY", "PCEPILFE", "YoY", 2.0],
        ["CPI YoY", "CPIAUCNS", "YoY", 2.0],
        ["Core CPI MoM", "CPILFESL", "MoM", 0.2],
        ["PPI MoM", "PPIACO", "MoM", 0.2]
    ],
    "UK & Global": [
        ["UK 10Y Gilt", "IRLTLT01GBM156N", "Raw", 4.0],
        ["Japan Policy Rate", "JPNINTRATEMCCORM", "Raw", 0.1],
        ["Euro Inflation (HICP)", "CP0000EZ19M086NEST", "YoY", 2.0],
        ["China Manufacturing PMI", "CHIPMIADJMEI", "Raw", 50.0]
    ],
    "Market & Liquidity": [
        ["DXY Index", "DX-Y.NYB", "Market", 100.0],
        ["Gold Spot", "GC=F", "Market", 5000.0],
        ["VIX Index", "^VIX", "Market", 25.0],
        ["Fed Funds Rate", "FEDFUNDS", "Raw", 3.5]
    ]
}

# --- 6. PROCESSING ENGINE ---
rows = []
scores = {"Growth": 0, "Inflation": 0, "Global": 0}

for category, items in macro_model.items():
    for name, ticker, mode, threshold in items:
        if mode == "Market":
            df = get_market_data(ticker)
        else:
            df = get_fred_raw(ticker)
            
        val = calculate_actual_value(df, ticker, mode)
        
        # Scoring Logic
        # Bad if High: Inflation, Unemployment, VIX, Fed Funds
        bad_if_high = ["Inflation", "Unemployment", "VIX", "Fed Funds", "CPI", "PCE", "PPI"]
        is_bad_high = any(x in name for x in bad_if_high)
        
        if is_bad_high:
            score = 1 if val < threshold else -1
        else:
            score = 1 if val > threshold else -1
            
        if "Growth" in category: scores["Growth"] += score
        if "Inflation" in category: scores["Inflation"] += score
        
        rows.append([category, name, val, threshold, score])

df_macro = pd.DataFrame(rows, columns=["Category", "Indicator", "Value", "Threshold", "Score"])

# --- 7. REGIME DETECTION ---
if scores["Growth"] >= 0 and scores["Inflation"] >= 0:
    regime = "GOLDILOCKS"
elif scores["Growth"] >= 0 and scores["Inflation"] < 0:
    regime = "OVERHEATING"
elif scores["Growth"] < 0 and scores["Inflation"] < 0:
    regime = "STAGFLATION"
else:
    regime = "RECESSION"

# --- 8. UI DASHBOARD ---
st.title("📟 RICKY STRATEGIC MACRO TERMINAL v2.0")
st.markdown(f"**Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Growth Score", scores["Growth"])
m2.metric("Inflation Score", scores["Inflation"])
m3.subheader(f"Regime: {regime}")
vix_val = df_macro[df_macro['Indicator'] == 'VIX Index']['Value'].values[0]
m4.metric("Market Volatility", f"{vix_val}%", "RISK-OFF" if vix_val > 25 else "NORMAL")

st.divider()

# ASSET SIGNALS
signals = {
    "GOLDILOCKS": {"EQUITY": "LONG", "GOLD": "NEUTRAL", "USD": "SHORT", "BONDS": "LONG"},
    "OVERHEATING": {"EQUITY": "LONG", "GOLD": "LONG", "USD": "LONG", "BONDS": "SHORT"},
    "STAGFLATION": {"EQUITY": "SHORT", "GOLD": "STRONG LONG", "USD": "LONG", "BONDS": "SHORT"},
    "RECESSION": {"EQUITY": "STRONG SHORT", "GOLD": "NEUTRAL", "USD": "SHORT", "BONDS": "STRONG LONG"}
}

st.subheader("🎯 Tactical Signals")
cols = st.columns(4)
current_signals = signals[regime]
for i, (asset, action) in enumerate(current_signals.items()):
    color = "#00FF00" if "LONG" in action else "#FF3131" if "SHORT" in action else "#AAAAAA"
    cols[i].markdown(f"<div class='signal-box'><b>{asset}</b><br><span style='color:{color}; font-size:1.5rem;'>{action}</span></div>", unsafe_allow_html=True)

st.divider()

# MAIN DATA TABLE
st.subheader("📊 Macro Indicator Audit (Real-Time vs Threshold)")
def style_score(v):
    color = '#00FF00' if v > 0 else '#FF3131'
    return f'color: {color}; font-weight: bold;'

st.dataframe(df_macro.style.applymap(style_score, subset=['Score']), use_container_width=True)

# CHART ANALYSIS
st.divider()
st.subheader("📈 Historical Trend Analysis")
selected_ind = st.selectbox("Pilih Indikator:", df_macro["Indicator"])
selected_ticker = next(item[1] for cat in macro_model.values() for item in cat if item[0] == selected_ind)
selected_mode = next(item[2] for cat in macro_model.values() for item in cat if item[0] == selected_ind)

hist_df = get_market_data(selected_ticker) if "Market" in selected_ind or "Spot" in selected_ind else get_fred_raw(selected_ticker)

if not hist_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['value'], name="Raw Data", line=dict(color="#00FF00")))
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

if st.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

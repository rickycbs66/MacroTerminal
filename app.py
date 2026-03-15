import streamlit as st
import pandas as pd
from fredapi import Fred
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# SETTING TERMINAL STYLE
st.set_page_config(page_title="Macro Hedge Fund Terminal", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
div[data-testid="stMetricValue"] { color: #00FF00 !important; }
.signal-box {padding:20px; border-radius:10px; border:2px solid #333; text-align:center; background:#111; margin-bottom:10px;}
h1,h2,h3 {color:#00FF00 !important;}
</style>
""", unsafe_allow_html=True)

# KONEKSI API
FRED_API_KEY = "15a934d9ca6efdf12dfe85a48835ce9a"
fred = Fred(api_key=FRED_API_KEY)

@st.cache_data(ttl=3600)
def get_fred_series(series):
    try:
        data = fred.get_series(series)
        df = pd.DataFrame(data, columns=["value"])
        df.index = pd.to_datetime(df.index)
        return df.dropna()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_market_data(ticker):
    try:
        # Penanganan khusus Multi-Index yfinance agar tidak KeyError: 'value'
        data = yf.download(ticker, period="5y", interval="1d", progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close'][ticker].to_frame()
        else:
            df = data['Close'].to_frame()
        df.columns = ['value']
        return df.dropna()
    except: return pd.DataFrame()

# MODEL INDIKATOR MAKRO
macro_model = {
    "Growth": [
        ["GDP Growth", "A191RL1Q225SBEA", 2.0],
        ["Real GDP Growth YoY", "GDPC1", 2.0],        # Data Kuartalan
        ["GDPNow (Current Q)", "GDPNOW", 2.0],       # Nowcast (Real-time)
        ["Unemployment Rate", "UNRATE", 4.4],
        ["Retail Sales", "MARTSMPCSM44000USS", 0.3],
        ["Industrial Production", "INDPRO", 0.0],
        ["Durable Goods Orders", "DGORDER", 0.0],
        ["Consumer Confidence", "UMCSENT", 70.0]
    ],
    "Inflation": [
        ["Core PCE YoY", "PCEPILFE", 2.0],
        ["Core PCE MoM", "PCEPILFE", 0.2],
        ["CPI MoM", "CPIAUCSL", 0.2],
        ["Core CPI MoM", "CPILFESL", 0.2],
        ["CPI YoY", "CPIAUCSL", 2.0],
        ["Core CPI YoY", "CPILFESL", 2.0],
        ["PPI MoM", "PPIACO", 0.2],
        ["Unit Labor Cost YoY", "ULCNFB", 2.0]
    ],
    "Market Indicators": [
        ["US Dollar Index (DXY)", "DX-Y.NYB", 100.0],
        ["Gold Price (Spot)", "GC=F", 5000.0]
    ],
    "Liquidity": [
        ["Gov Spending Growth", "GCE", 2.0],
        ["Fiscal Deficit (Monthly)", "MTSDS133FMS", -100000.0]
    ],
    "Supply": [
        ["Oil Price (WTI)", "CL=F", 75.0],
        ["Fed Funds Rate", "FEDFUNDS", 3.5],
        ["Productivity Growth", "OPHNFB", 1.5],
        ["Capacity Utilization", "TCU", 78.0]
    ]
}

# FUNGSI LOGIKA
def estimate_pce_smart(cpi_val):
    return round(cpi_val - 0.65, 2)

def get_economic_calendar():
    events = [{"Event": "CPI Inflation", "Date": "12-15 setiap bulan"},
              {"Event": "Non-Farm Payrolls", "Date": "Jumat pertama setiap bulan"},
              {"Event": "PCE Price Index", "Date": "Minggu terakhir setiap bulan"},
              {"Event": "FOMC Meeting", "Date": "Sesuai Jadwal Fed"}]
    return pd.DataFrame(events)

def process_macro():
    rows, scores = [], {"Growth": 0, "Inflation": 0, "Market Indicators": 0, "Supply": 0, "Liquidity": 0}
    market_tickers = ["DX-Y.NYB", "GC=F", "CL=F"]
    already_percent = ["MARTSMPCSM44000USS", "GDPNOW", "A191RL1Q225SBEA"]

    for category, items in macro_model.items():
        for name, ticker, threshold in items:
            df = get_market_data(ticker) if ticker in market_tickers else get_fred_series(ticker)
            if df.empty: continue
            last_val = df["value"].iloc[-1]
            if ticker in already_percent:
                val = round(last_val, 2)

            # Konversi otomatis ke persen jika nama mengandung MoM/YoY
            if "MoM" in name:
                val = round(df["value"].pct_change().iloc[-1] * 100, 2)
            elif "YoY" in name or "Growth" in name:
                freq = 4 if ticker in ["ULCNFB", "GDPC1", "OPHNFB"] else 12
                val = round(df["value"].pct_change(freq).iloc[-1] * 100, 2)  
            else:
                val = round(last_val, 2)

            # Logika Skor (Balikkan untuk Unemployment/Suku Bunga)
            if pd.isna(val):
                score = 0
                val = 0
            else:
                if name in ["Unemployment Rate", "Fed Funds Rate", "Fiscal Deficit (Monthly)"]:
                    score = -1 if val > threshold else 1
                else:
                    score = 1 if val > threshold else -1

            scores[category] += score
            rows.append([category, name, ticker, val, threshold, score])

    return pd.DataFrame(rows, columns=["Category","Indicator","Ticker","Value","Threshold","Score"]), scores

# DATA FETCHING
df_macro, scores = process_macro()
regime = "GOLDILOCKS" if scores["Growth"] > 0 and scores["Inflation"] <= 0 else \
         "OVERHEATING" if scores["Growth"] > 0 and scores["Inflation"] > 0 else \
         "STAGFLATION" if scores["Growth"] <= 0 and scores["Inflation"] > 0 else "RECESSION"

# Estimasi PCE
cpi_yoy_row = df_macro[df_macro["Indicator"]=="CPI YoY"]
cpi_yoy_val = cpi_yoy_row["Value"].iloc[0] if not cpi_yoy_row.empty else 0
est_pce_val = estimate_pce_smart(cpi_yoy_val)

# BUILD UI DASHBOARD
st.title(" MACRO TERMINAL ANALYSIS ")

# METRICS
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Growth Score", scores["Growth"])
c2.metric("Inflation Score", scores["Inflation"])
c3.metric("Est. Next PCE", f"{est_pce_val}%")
c4.metric("Macro Regime", regime)
c5.metric("Market Sentiment", "BULLISH" if scores["Growth"] > 0 else "BEARISH")

st.divider()

# ASSET SIGNALS
signals = {"GOLDILOCKS": {"EQUITY": "LONG", "GOLD": "NEUTRAL", "USD": "SHORT", "BONDS": "LONG"},
           "OVERHEATING": {"EQUITY": "LONG", "GOLD": "LONG", "USD": "LONG", "BONDS": "SHORT"},
           "STAGFLATION": {"EQUITY": "SHORT", "GOLD": "STRONG LONG", "USD": "LONG", "BONDS": "SHORT"},
           "RECESSION": {"EQUITY": "STRONG SHORT", "GOLD": "NEUTRAL", "USD": "SHORT", "BONDS": "STRONG LONG"}}[regime]

st.subheader(" Asset Allocation Signals")
cols = st.columns(4)
for i, (asset, action) in enumerate(signals.items()):
    color = "#00FF00" if "LONG" in action else "#FF0000" if "SHORT" in action else "#888"
    cols[i].markdown(f"<div class='signal-box'><p>{asset}</p><h2 style='color:{color};'>{action}</h2></div>", unsafe_allow_html=True)

st.divider()

# CALENDAR & CHART
col_left, col_right = st.columns([1, 2])
with col_left:
    st.subheader(" Economic Calendar")
    st.table(get_economic_calendar())
with col_right:
    st.subheader(" Inflation Tracking: Core CPI vs Core PCE")
    core_cpi = (get_fred_series("CPILFESL")['value'].pct_change(12) * 100).tail(36)
    core_pce = (get_fred_series("PCEPILFE")['value'].pct_change(12) * 100).tail(36) 
    
    fig_track = go.Figure()
    fig_track.add_trace(go.Scatter(x=core_cpi.index, y=core_cpi, name="Core CPI YoY (%)", mode='lines', line=dict(color="cyan", width=3)))
    fig_track.add_trace(go.Scatter(x=core_pce.index, y=core_pce, name="Core PCE YoY (%)", mode='lines', line=dict(color="lime", width=3)))
    fig_track.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_track, use_container_width=True)

st.divider()
st.subheader(" Macro Indicators ")
st.dataframe(df_macro, use_container_width=True)

st.divider()
st.subheader(" Historical Indicator ")
selected_name = st.selectbox("Select Indicator to Analyze:", df_macro["Indicator"])
row_info = df_macro[df_macro["Indicator"] == selected_name].iloc[0]

# Penentuan sumber data untuk grafik historis
if row_info["Ticker"] in ["DX-Y.NYB", "GC=F", "CL=F"]:
    hist_raw = get_market_data(row_info["Ticker"])
else:
    hist_raw = get_fred_series(row_info["Ticker"])

if not hist_raw.empty:
    if "MoM" in selected_name:
        plot_data = (hist_raw['value'].pct_change() * 100).dropna()
    elif "YoY" in selected_name or "Growth" in selected_name or "GDP" in selected_name:
        plot_data = (hist_raw['value'].pct_change(12) * 100).dropna()
    else:
        plot_data = hist_raw['value']

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(x=plot_data.index, y=plot_data, name=selected_name, line=dict(color='#00FF00', width=2)))
    fig_hist.add_hline(y=row_info["Threshold"], line_dash="dash", line_color="red", annotation_text="Threshold")
    fig_hist.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig_hist, use_container_width=True)

if st.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

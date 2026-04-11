import streamlit as st
import pandas as pd
from fredapi import Fred
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIG & TERMINAL STYLE ---
st.set_page_config(page_title="Macro Strategic Terminal", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
    div[data-testid="stMetricValue"] { color: #00FF00 !important; }
    .signal-box {padding:20px; border-radius:10px; border:1px solid #00FF00; text-align:center; background:#001100; margin-bottom:10px;}
    h1,h2,h3 {color:#00FF00 !important;}
    .stDataFrame {border: 1px solid #333;}
</style>
""", unsafe_allow_html=True)

# --- 2. API SETUP ---
# Ganti dengan API Key FRED Anda
FRED_API_KEY = "15a934d9ca6efdf12dfe85a48835ce9a" 
fred = Fred(api_key=FRED_API_KEY)

# --- 3. DATA ENGINE (ANTI-LIMIT CACHING) ---
@st.cache_data(ttl=14400) # Cache 4 jam
def get_fred_data(ticker):
    try:
        data = fred.get_series(ticker)
        df = pd.DataFrame(data, columns=["value"])
        df.index = pd.to_datetime(df.index)
        return df.dropna()
    except: return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache 1 jam untuk data market
def get_market_data(ticker):
    try:
        data = yf.download(ticker, period="5y", interval="1d", progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close'][ticker].to_frame()
        else:
            df = data['Close'].to_frame()
        df.columns = ['value']
        return df.dropna()
    except: return pd.DataFrame()

# --- 4. CALCULATION AUDIT LOGIC ---
def calculate_metric(df, ticker, mode):
    if df.empty: return 0.0
    
    # Indikator yang sudah berbentuk PERSEN (Jangan di-YoY lagi)
    raw_rate_tickers = [
        "UNRATE", "GDPNOW", "T10Y2Y", "FEDFUNDS", "TCU", 
        "MARTSMPCSM44000USS", "IRLTLT01GBM156N", "UMCSENT", "CHIPMIADJMEI"
    ]
    
    last_val = df["value"].iloc[-1]
    
    if ticker in raw_rate_tickers:
        return round(last_val, 2)
    
    try:
        if mode == "YoY":
            # Perhitungan pertumbuhan tahunan dari angka indeks
            val = ((df["value"].iloc[-1] / df["value"].iloc[-13]) - 1) * 100
        elif mode == "MoM":
            val = ((df["value"].iloc[-1] / df["value"].iloc[-2]) - 1) * 100
        else:
            val = last_val
        return round(val, 2)
    except:
        return round(last_val, 2)

# --- 5. GLOBAL MACRO MODEL ---
# Struktur: [Nama, Ticker, Mode, Threshold]
macro_model = {
    "US Growth": [
        ["Real GDP YoY", "GDPC1", "YoY", 2.0],
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
    "Global Indicators": [
        ["UK 10Y Gilt Yield", "IRLTLT01GBM156N", "Raw", 4.0],
        ["Euro HICP Inflation", "CP0000EZ19M086NEST", "YoY", 2.0],
        ["China Mfg PMI", "CHIPMIADJMEI", "Raw", 50.0],
        ["Japan Policy Rate", "JPNINTRATEMCCORM", "Raw", 0.1]
    ],
    "Market Sentiment": [
        ["DXY Index", "DX-Y.NYB", "Market", 100.0],
        ["Gold Spot", "GC=F", "Market", 5000.0],
        ["VIX Index", "^VIX", "Market", 25.0],
        ["Fed Funds Rate", "FEDFUNDS", "Raw", 3.5]
    ]
}

# --- 6. PROCESSING ---
rows = []
scores = {"Growth": 0, "Inflation": 0}

for category, items in macro_model.items():
    for name, ticker, mode, threshold in items:
        if mode == "Market":
            df = get_market_data(ticker)
        else:
            df = get_fred_data(ticker)
            
        val = calculate_metric(df, ticker, mode)
        
        # Scoring Logic (Bad if High for specific indicators)
        bad_high = ["Unemployment", "Inflation", "VIX", "CPI", "PCE", "PPI", "Fed Funds"]
        is_bad_high = any(x in name for x in bad_high)
        
        if is_bad_high:
            score = 1 if val < threshold else -1
        else:
            score = 1 if val > threshold else -1
            
        if "Growth" in category: scores["Growth"] += score
        if "Inflation" in category: scores["Inflation"] += score
        
        rows.append({"Category": category, "Indicator": name, "Value": val, "Threshold": threshold, "Score": score})

df_macro = pd.DataFrame(rows)

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
st.title("📟 RICKY STRATEGIC MACRO TERMINAL")
st.write(f"Last Terminal Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("GROWTH SCORE", scores["Growth"])
m2.metric("INFLATION SCORE", scores["Inflation"])
m3.subheader(f"REGIME: {regime}")
vix_val = df_macro[df_macro['Indicator'] == 'VIX Index']['Value'].values[0] if not df_macro[df_macro['Indicator'] == 'VIX Index'].empty else 0
m4.metric("VOLATILITY (VIX)", f"{vix_val}", "RISK-OFF" if vix_val > 25 else "BULLISH")

st.divider()

# ASSET SIGNALS
signals = {
    "GOLDILOCKS": {"EQUITY": "LONG", "GOLD": "NEUTRAL", "USD": "SHORT", "BONDS": "LONG"},
    "OVERHEATING": {"EQUITY": "LONG", "GOLD": "LONG", "USD": "LONG", "BONDS": "SHORT"},
    "STAGFLATION": {"EQUITY": "SHORT", "GOLD": "STRONG LONG", "USD": "LONG", "BONDS": "SHORT"},
    "RECESSION": {"EQUITY": "STRONG SHORT", "GOLD": "NEUTRAL", "USD": "SHORT", "BONDS": "STRONG LONG"}
}

st.subheader("🎯 Tactical Allocation Signals")
sig_cols = st.columns(4)
current_sig = signals[regime]
for i, (asset, action) in enumerate(current_sig.items()):
    color = "#00FF00" if "LONG" in action else "#FF3131" if "SHORT" in action else "#888888"
    sig_cols[i].markdown(f"<div class='signal-box'><b>{asset}</b><br><span style='color:{color}; font-size:1.5rem;'>{action}</span></div>", unsafe_allow_html=True)

st.divider()

# TABLE AUDIT (FIXED ATTRIBUTEERROR)
st.subheader("📊 Macro Indicator Audit Trail")

def style_score(val):
    if val == 1: return 'color: #00FF00; font-weight: bold;'
    elif val == -1: return 'color: #FF3131; font-weight: bold;'
    return ''

# Menggunakan .map() bukan .applymap() untuk kompatibilitas Pandas 2.x
if not df_macro.empty:
    styled_df = df_macro.style.map(style_score, subset=['Score'])
    st.dataframe(styled_df, use_container_width=True)

# CHART
st.divider()
st.subheader("📈 Historical Data Visualization")
selected_name = st.selectbox("Analyze Indicator Trend:", df_macro["Indicator"])
selected_row = df_macro[df_macro["Indicator"] == selected_name].iloc[0]

# Fetch historical again for chart
ticker_to_plot = next(item[1] for cat in macro_model.values() for item in cat if item[0] == selected_name)
is_mkt = "Market" in selected_row["Category"]
hist_data = get_market_data(ticker_to_plot) if is_mkt else get_fred_data(ticker_to_plot)

if not hist_data.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['value'], line=dict(color='#00FF00', width=2)))
    fig.add_hline(y=selected_row["Threshold"], line_dash="dash", line_color="red", annotation_text="Threshold")
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

if st.button("🔄 FORCE REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

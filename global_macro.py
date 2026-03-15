import streamlit as st
import pandas as pd
from fredapi import Fred
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

# 1. SETTING STYLE TERMINAL
st.set_page_config(page_title="Global Macro Strategic Terminal", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
h1,h2,h3 {color:#00FF00 !important;}
div[data-testid="stMetricValue"] { color: #00FF00 !important; }
table { color: #00FF00 !important; background-color: #111 !important; border: 1px solid #333 !important; }
input { background-color: #111 !important; color: #00FF00 !important; border: 1px solid #00FF00 !important; }
</style>
""", unsafe_allow_html=True)

# 2. SISTEM KEAMANAN PIN
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.markdown("<h2 style='text-align: center;'>🔐 GLOBAL FX STRATEGIC LOGIN</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        password = st.text_input("Masukkan PIN Akses:", type="password")
        if st.button("Masuk"):
            if password == st.secrets.get("APP_PASSWORD", "8888"):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("PIN Salah! Akses Ditolak.")
    return False

if not check_password():
    st.stop()

# 3. KONEKSI API FRED
try:
    fred = Fred(api_key=st.secrets["FRED_API_KEY"])
except:
    st.error("API Key FRED tidak ditemukan di Secrets!")
    st.stop()

# 4. MODEL INDIKATOR GLOBAL (TICKER VALID)
macro_model = {
    "🇬🇧 UNITED KINGDOM (GBP)": [
        ["UK CPI Inflation YoY", "GBRCPIALLMINMEI", 2.0],
        ["UK Core CPI YoY", "GBRCPICOREMINMEI", 2.0],
        ["UK Unemployment Rate", "LRUNTTTTGBM156S", 4.4],
        ["UK 10Y Gilt Yield", "IRLTLT01GBM156N", 4.0]
    ],
    "🇪🇺 EUROZONE (EUR)": [
        ["Eurozone HICP Inflation", "CPHPTT01EZM659N", 2.0],
        ["German ZEW Sentiment", "DEUSNT01ATM664N", 0.0],
        ["Eurozone GDP Growth", "CLVMNACSCAB1GQEZ", 0.5],
        ["DAX 40 Index", "^GDAXI", 15000]
    ],
    "🇯🇵 JAPAN (JPY)": [
        ["Japan Core CPI YoY", "JPNCPIALLMINMEI", 2.0],
        ["Japan 10Y JGB Yield", "IRLTLT01JPM156N", 0.8],
        ["Japan GDP Growth", "JPNGDPNQDSMEI", 0.2],
        ["Nikkei 225 Index", "^N225", 35000]
    ]
}

# 5. FUNGSI DATA FETCHING 
@st.cache_data(ttl=3600)
def get_fred_series(series):
    try:
        data = fred.get_series(series)
        df = pd.DataFrame(data, columns=["value"])
        return df.dropna()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_market_data(ticker):
    try:
        data = yf.download(ticker, period="5y", interval="1d", progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'][ticker].to_frame() if isinstance(data.columns, pd.MultiIndex) else data['Close'].to_frame()
        df.columns = ['value']
        return df.dropna()
    except: return pd.DataFrame()

# 6. LOGIKA PROSES 
def process_macro():
    rows = []
    market_tickers = ["^GDAXI", "^N225"]
    already_percent = [
        "LRUNTTTTGBM156S", "IRLTLT01GBM156N", "IRLTLT01JPM156N", "DEUSNT01ATM664N"
    ]

    for category, items in macro_model.items():
        for name, ticker, threshold in items:
            # Ambil Data
            df = get_market_data(ticker) if ticker in market_tickers else get_fred_series(ticker)
            
            if df.empty:
                rows.append([category, name, 0.0, threshold, "⚪ NO DATA"])
                continue
            
            last_val = df["value"].iloc[-1]
            if ticker in already_percent:
                # Ambil nilai mentah (Yield, Unemployment, Sentiment)
                val = round(last_val, 2)
            elif "YoY" in name or "Growth" in name or "Inflation" in name:
                # Jika GDP pakai freq 4 (Kuartal), selain itu freq 12 (Bulan)
                freq = 4 if "GDP" in name else 12
                val = round(df["value"].pct_change(freq).iloc[-1] * 100, 2)
            else:
                val = round(last_val, 2)
            
            # Penentuan Status Visual
            if "CPI" in name or "Inflation" in name:
                status = "🔴 HOT" if val > threshold else "🟢 TARGET"
            elif "GDP" in name or "Sentiment" in name:
                status = "🟢 GROWTH" if val > threshold else "🔴 SLOW"
            elif "Yield" in name:
                status = "📈 HAWKISH" if val > threshold else "📉 DOVISH"
            else:
                status = "⚪ MONITOR"

            rows.append([category, name, val, threshold, status])
            
    return pd.DataFrame(rows, columns=["Category", "Indicator", "Value", "Threshold", "Status"])

# 7. TAMPILAN UI DASHBOARD
st.title("🌏 GLOBAL FX STRATEGIC MONITOR")
st.subheader("BoE | ECB | BoJ: High-Impact Analysis")

df_results = process_macro()

# Tampilkan per kolom wilayah
cols = st.columns(3)
regions = list(macro_model.keys())

for i, region in enumerate(regions):
    with cols[i]:
        st.markdown(f"### {region}")
        # Filter data per wilayah
        region_df = df_results[df_results['Category'] == region][['Indicator', 'Value', 'Status']]
        st.table(region_df)

st.divider()

# 8. FX BIAS LOGIC (Berdasarkan Nilai Aktual)
st.subheader("💡 Global FX Strategic Bias")
b1, b2, b3 = st.columns(3)

# Ambil nilai krusial untuk bias
uk_cpi = df_results[df_results['Indicator'] == "UK CPI Inflation YoY"]['Value'].values[0] if not df_results[df_results['Indicator'] == "UK CPI Inflation YoY"].empty else 0
eu_zew = df_results[df_results['Indicator'] == "German ZEW Sentiment"]['Value'].values[0] if not df_results[df_results['Indicator'] == "German ZEW Sentiment"].empty else 0
jp_yld = df_results[df_results['Indicator'] == "Japan 10Y JGB Yield"]['Value'].values[0] if not df_results[df_results['Indicator'] == "Japan 10Y JGB Yield"].empty else 0

with b1:
    st.info(f"**GBP Bias:** {'🔴 HAWKISH' if uk_cpi > 3.0 else '🟢 DOVISH'}")
    st.write(f"Inflasi UK ({uk_cpi}%) tetap tinggi. GBP cenderung Strong.")

with b2:
    st.info(f"**EUR Bias:** {'🟢 BULLISH' if eu_zew > 0 else '🔴 BEARISH'}")
    st.write(f"Sentimen ZEW ({eu_zew}) menentukan arah EUR/USD.")

with b3:
    st.info(f"**JPY Bias:** {'🔴 STRENGTHENING' if jp_yld > 0.8 else '🟢 WEAK'}")
    st.write(f"Yield JPN ({jp_yld}%) mendekati batas kritis BoJ.")

if st.button("🔄 REFRESH GLOBAL DATA"):
    st.cache_data.clear()
    st.rerun()


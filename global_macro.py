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
# 4. MODEL DATA
global_macro = {
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

# 5. LOGIKA DATA PROCESSING 
def process_macro():
    rows = []
    raw_tickers = ["LRUNTTTTGBM156S", "IRLTLT01GBM156N", "IRLTLT01JPM156N", "DEUSNT01ATM664N"]
    
    for category, items in global_macro.items():
        for name, ticker, threshold in items:
            try:
                if ticker.startswith("^"):
                    df = yf.download(ticker, period="5d", progress=False)
                    val = round(float(df['Close'].iloc[-1]), 2)
                else:
                    data = fred.get_series(ticker)
                    if data.empty: 
                        val = 0.0
                    elif ticker in raw_tickers:
                        val = round(float(data.iloc[-1]), 2)
                    else:
                        freq = 4 if "GDP" in name else 12
                        val = round(float(data.pct_change(freq).iloc[-1] * 100), 2)
            except:
                val = 0.0
            
            # Logika Status
            if "CPI" in name or "Inflation" in name:
                status = "🔴 HOT" if val > threshold else "🟢 TARGET"
            elif "Yield" in name:
                status = "📈 HAWKISH" if val > threshold else "📉 DOVISH"
            else:
                status = "🟢 OK" if val > threshold else "🔴 SLOW"
                
            rows.append([category, name, val, threshold, status])
    return pd.DataFrame(rows, columns=["Category", "Indicator", "Value", "Threshold", "Status"])

# 6. TAMPILAN DASHBOARD
st.title(" GLOBAL FX STRATEGIC MONITOR (MARCH 2026)")
df_results = process_macro()

cols = st.columns(3)
regions = list(global_macro.keys())
for i, region in enumerate(regions):
    with cols[i]:
        st.markdown(f"### {region}")
        st.table(df_results[df_results['Category'] == region][['Indicator', 'Value', 'Status']])

# 7. BIAS FX (LOGIKA OTOMATIS BERDASARKAN DATA)
st.divider()
st.subheader(" Global FX Strategic Bias")
uk_inf = df_results[df_results['Indicator']=="UK CPI Inflation YoY"]['Value'].values[0]
eu_inf = df_results[df_results['Indicator']=="Eurozone HICP Inflation"]['Value'].values[0]
jp_yld = df_results[df_results['Indicator']=="Japan 10Y JGB Yield"]['Value'].values[0]

b1, b2, b3 = st.columns(3)
with b1:
    st.error(f"**GBP Bias:** {'🔴 HAWKISH' if uk_inf > 2.5 else '🟢 NEUTRAL'}\n\nInflasi UK {uk_inf}% (Target 2%). GBP Strong.")
with b2:
    st.info(f"**EUR Bias:** {'🟡 STABLE' if eu_inf < 2.5 else '🔴 HOT'}\n\nInflasi EU {eu_inf}%. Pantau ECB.")
with b3:
    st.success(f"**JPY Bias:** {'🔴 STRONG' if jp_yld > 1.0 else '🟢 WEAK'}\n\nYield JPN {jp_yld}%. Selisih bunga dengan US menipis.")

if st.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()


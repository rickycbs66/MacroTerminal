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
table { color: #00FF00 !important; background-color: #111 !important; border: 1px solid #333 !important; }
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
            if password == st.secrets.get("APP_PASSWORD"):
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

# 4. MODEL DATA (DIPERBAIKI: DITAMBAH KOLOM DTYPE)
global_macro_config = {
    "🇬🇧 UNITED KINGDOM (GBP)": [
        ["UK CPI Inflation YoY", "GBRCPIALLMINMEI", 2.0, "yoy"],
        ["UK Core CPI YoY", "GBRCPICOREMINMEI", 2.0, "yoy"],
        ["UK Unemployment Rate", "LRUNTTTTGBM156S", 4.4, "raw"],
        ["UK 10Y Gilt Yield", "IRLTLT01GBM156N", 4.0, "raw"]
    ],
    "🇪🇺 EUROZONE (EUR)": [
        ["Eurozone HICP Inflation", "CPHPTT01EZM659N", 2.0, "yoy"],
        ["German ZEW Sentiment", "DEUSNT01ATM664N", 0.0, "raw"],
        ["Eurozone GDP Growth", "CLVMNACSCAB1GQEZ", 0.5, "yoy_q"],
        ["DAX 40 Index", "^GDAXI", 15000, "yf"]
    ],
    "🇯🇵 JAPAN (JPY)": [
        ["Japan Core CPI YoY", "JPNCPIALLMINMEI", 2.0, "yoy"],
        ["Japan 10Y JGB Yield", "IRLTLT01JPM156N", 0.8, "raw"],
        ["Japan GDP Growth", "JPNGDPNQDSMEI", 0.2, "yoy_q"],
        ["Nikkei 225 Index", "^N225", 35000, "yf"]
    ]
}

# 5. LOGIKA DATA PROCESSING
@st.cache_data(ttl=3600)
def process_macro():
    all_results = []
    for region, items in global_macro_config.items():
        for name, ticker, threshold, dtype in items:
            try:
                if dtype == "yf":
                    df = yf.download(ticker, period="5d", progress=False)
                    val = round(float(df['Close'].iloc[-1]), 2)
                else:
                    data = fred.get_series(ticker)
                    if data.empty:
                        val = 0.0
                    elif dtype == "raw":
                        val = round(float(data.dropna().iloc[-1]), 2)
                    elif dtype == "yoy":
                        val = round(float(data.pct_change(12).dropna().iloc[-1] * 100), 2)
                    elif dtype == "yoy_q":
                        val = round(float(data.pct_change(4).dropna().iloc[-1] * 100), 2)
            except:
                val = 0.0
            
            if "CPI" in name or "Inflation" in name:
                status = "🔴 HOT" if val > threshold else "🟢 TARGET"
            elif "Yield" in name:
                status = "📈 HAWKISH" if val > threshold else "📉 DOVISH"
            else:
                status = "🟢 OK" if val > threshold else "🔴 SLOW"
            
            all_results.append([region, name, val, threshold, status])
    return pd.DataFrame(all_results, columns=["Region", "Indicator", "Value", "Threshold", "Status"])

# 6. TAMPILAN DASHBOARD
st.title("🌏 GLOBAL FX STRATEGIC MONITOR (MARCH 2026)")
df_results = process_macro()

cols = st.columns(3)
regions = list(global_macro_config.keys())
for i, region in enumerate(regions):
    with cols[i]:
        st.markdown(f"### {region}")
        # PERBAIKAN: Nama kolom harus sesuai dengan df_results yaitu 'Region'
        region_data = df_results[df_results['Region'] == region][['Indicator', 'Value', 'Status']]
        st.table(region_data)

# 7. BIAS FX
st.divider()
st.subheader("💡 Global FX Strategic Bias")

def get_val(indicator_name):
    filt = df_results[df_results['Indicator'] == indicator_name]['Value']
    return float(filt.iloc[0]) if not filt.empty else 0.0

uk_inf = get_val("UK CPI Inflation YoY")
eu_inf = get_val("Eurozone HICP Inflation")
jp_yld = get_val("Japan 10Y JGB Yield")

b1, b2, b3 = st.columns(3)
with b1:
    st.error(f"**GBP Bias:** {'🔴 HAWKISH' if uk_inf > 2.5 else '🟢 NEUTRAL'}\n\nInflasi UK {uk_inf}% (Target 2.0%). GBP Strong.")
with b2:
    st.info(f"**EUR Bias:** {'🟡 STABLE' if eu_inf < 2.5 else '🔴 HOT'}\n\nInflasi EU {eu_inf}%. Pantau ECB.")
with b3:
    st.success(f"**JPY Bias:** {'🔴 STRONG' if jp_yld > 1.0 else '🟢 WEAK'}\n\nYield JPN {jp_yld}%. Sinyal pengetatan BoJ.")

if st.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()


import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Global Macro Strategic Terminal", layout="wide")
JAPAN_APP_ID = "cf3e53ebb23656d51ee03e9af9f696163b5b4c16"
# 1. KONFIGURASI TAMPILAN (Cyberpunk Style)
st.set_page_config(page_title="Global Macro Terminal v2", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
.stTable { background-color: #111 !important; color: #00FF00 !important; }
h1, h2, h3 { color: #00FF00 !important; border-bottom: 1px solid #00FF00; }
div[data-testid="stMetricValue"] { color: #00FF00 !important; }
</style>
""", unsafe_allow_html=True)

# 2. SISTEM KEAMANAN PIN
def check_password():
    if st.session_state.get("password_correct", False): return True
    st.markdown("<h2 style='text-align: center;'>🔐 GLOBAL MACRO LOGIN</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        password = st.text_input("Masukkan PIN Akses:", type="password")
        if st.button("Masuk"):
            # Ganti '1234' dengan st.secrets["APP_PASSWORD"] jika di deploy
            if password == "1234": 
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("PIN Salah!")
    return False

if not check_password(): st.stop()
# FUNGSI AMBIL DATA SPESIFIK 

@st.cache_data(ttl=3600)
def fetch_uk_ons(series_id):
    """Ambil data ONS UK (CPI, GDP, Retail, Wage, Ind. Prod)"""
    url = f"https://ons.gov.uk{series_id}/dataset/mm23/data"
    try:
        res = requests.get(url, timeout=15).json()
        latest = res.get('months', res.get('years'))[-1]
        return float(latest['value']), latest['date']
    except: return 0.0, "ERR"

@st.cache_data(ttl=3600)
def fetch_eurostat(code, unit="PC4_ANY"):
    """Eurostat: unit=PC4_ANY (YoY), unit=PCH_PRE (MoM), unit=CLV_PCH_PRE (QoQ)"""
    url = f"https://europa.eu{code}?geo=EA20&lastTimePeriod=1&unit={unit}"
    try:
        res = requests.get(url, timeout=15).json()
        val = list(res['value'].values())[0]
        time = list(res['dimension']['time']['category']['label'].values())[0]
        return float(val), time
    except: return 0.0, "ERR"

@st.cache_data(ttl=3600)
def fetch_japan_estat(stats_id):
    """e-Stat Japan (CPI, Unemp, Household, Industrial Prod)"""
    url = f"https://e-stat.go.jp{JAPAN_APP_ID}&statsDataId={stats_id}&limit=1"
    try:
        res = requests.get(url, timeout=15).json()
        data_inf = res['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
        val = data_inf['$'] if isinstance(data_inf, dict) else data_inf[0]['$']
        time = data_inf['@time'] if isinstance(data_inf, dict) else data_inf[0]['@time']
        return float(val), time
    except: return 0.0, "ERR"

def fetch_market(ticker):
    """Data Yield & Index via Yahoo Finance"""
    try:
        data = yf.Ticker(ticker).fast_info['last_price']
        return float(data), "Live"
    except: return 0.0, "ERR"

# --- MAIN ENGINE ---
st.title(" GLOBAL FX STRATEGIC MONITOR ")

c1, c2, c3 = st.columns(3)

# 🇬🇧 UNITED KINGDOM
with c1:
    st.header("🇬🇧 UNITED KINGDOM (GBP)")
    uk_metrics = [
        ["UK CPI Inflation YoY", "l522", 2.0, "ons"],
        ["UK Core CPI YoY", "l55o", 2.0, "ons"],
        ["UK Unemployment Rate", "mgsx", 4.4, "ons"],
        ["UK GDP Growth YoY", "ihyp", 0.5, "ons"],
        ["UK Retail Sales YoY", "j564", 1.0, "ons"],
        ["UK Wage Growth YoY", "kai9", 3.0, "ons"],
        ["UK Industrial Prod YoY", "k22a", 0.0, "ons"],
        ["UK 10Y Gilt Yield", "067140.L", 4.0, "yf"]
    ]
    res_uk = []
    for m in uk_metrics:
        val, dt = fetch_uk_ons(m[1]) if m[3] == "ons" else fetch_market(m[1])
        status = "🔴 HOT" if val > m[2] else "🟢 TARGET"
        res_uk.append({"Indicator": m[0], "Val": val, "Status": status, "Date": dt})
    st.table(pd.DataFrame(res_uk))

# 🇪🇺 EUROZONE
with c2:
    st.header("🇪🇺 EUROZONE (EUR)")
    eu_metrics = [
        ["Eurozone HICP Inflation", "prc_hicp_manr", 2.0, "PC4_ANY"],
        ["Eurozone Unemp Rate", "une_rt_m", 6.5, "PC"],
        ["German ZEW Sentiment", "ei_isue_m", 0.0, "BS-CS-SMI"],
        ["Eurozone GDP Growth", "teina011", 0.5, "CLV_PCH_PRE"],
        ["Eurozone Trade Balance", "ext_st_ea20sitc", 10000, "MIO_EUR"],
        ["DAX 40 Index", "^GDAXI", 15000, "yf"]
    ]
    res_eu = []
    for m in eu_metrics:
        if m[3] == "yf":
            val, dt = fetch_market(m[1])
        else:
            val, dt = fetch_eurostat(m[1], m[3])
        status = "🟢 OK" if val > m[2] else "🔴 SLOW"
        res_eu.append({"Indicator": m[0], "Val": val, "Status": status, "Date": dt})
    st.table(pd.DataFrame(res_eu))

# 🇯🇵 JAPAN
with c3:
    st.header("🇯🇵 JAPAN (JPY)")
    jp_metrics = [
        ["Japan Core CPI MoM", "0003423127", 0.1, "estat"], # ID misal
        ["Japan Unemp Rate", "0003008544", 2.5, "estat"],
        ["Japan Household Spend", "0003017234", 1.0, "estat"],
        ["Japan Industrial Prod", "0003076161", 0.0, "estat"],
        ["Japan Core CPI YoY", "0003423127", 2.0, "estat"],
        ["Japan 10Y JGB Yield", "^JG=F", 0.8, "yf"],
        ["Japan GDP Growth", "0003109786", 0.2, "estat"],
        ["Nikkei 225 Index", "^N225", 35000, "yf"]
    ]
    res_jp = []
    for m in jp_metrics:
        val, dt = fetch_japan_estat(m[1]) if m[3] == "estat" else fetch_market(m[1])
        status = "📈 HAWKISH" if val > m[2] else "📉 DOVISH"
        res_jp.append({"Indicator": m[0], "Val": val, "Status": status, "Date": dt})
    st.table(pd.DataFrame(res_jp))

st.divider()
st.subheader("💡 Global FX Strategic Bias")
st.info(f"Monitor Terintegrasi: GBP, EUR, JPY. Refresh untuk data terbaru.")

if st.button("🔄 REFRESH ALL DATA"):
    st.cache_data.clear()
    st.rerun()




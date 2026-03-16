%%writefile global_macro.py
import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime

# 1. KONFIGURASI TAMPILAN (Cyberpunk Style)
st.set_page_config(page_title="Global Macro Strategic Terminal", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
.stTable { background-color: #111 !important; color: #00FF00 !important; }
h1, h2, h3 { color: #00FF00 !important; border-bottom: 1px solid #00FF00; }
div[data-testid="stMetricValue"] { color: #00FF00 !important; }
</style>
""", unsafe_allow_html=True)

try:
    JAPAN_APP_ID = st.secrets["ESTAT_API_KEY"]
except:
    JAPAN_APP_ID = "cf3e53ebb23656d51ee03e9af9f696163b5b4c16"
    st.warning("E-Stat API Key not found in st.secrets. Using default key, which may not work.")

# 2. SISTEM KEAMANAN PIN
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    st.markdown("<h2 style='text-align: center;'>🔐 GLOBAL MACRO LOGIN</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        password = st.text_input("Masukkan PIN Akses:", type="password")
        if st.button("Masuk"):
            if password == "1234":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("PIN Salah!")
    return False
if not check_password():
    st.stop()

# DATA FETCH FUNCTIONS
@st.cache_data(ttl=3600)
def fetch_uk_ons(series_id):
    url = f"https://api.ons.gov.uk/timeseries/{series_id}/dataset/mm23/data"
    try:
        res = requests.get(url, timeout=15).json()
        latest = res["months"][-1]
        return float(latest["value"]), latest["date"]
    except Exception as e:
        print(f"Error fetching UK ONS data for {series_id}: {e}")
        return 0.0, "ERR"

@st.cache_data(ttl=3600)
def fetch_eurostat(code, unit):
    url = f"https://ec.europa.eu/eurostat/api/discover/v2/tgm/table?table={code}"
    try:
        res = requests.get(url, timeout=10).json()
        # Handle cases where value might be empty or missing
        if not res.get("value"):
            print(f"Eurostat value not found for {code}")
            return 0.0, "ERR"
        value = list(res["value"].values())[0]
        time_key = list(res["dimension"]["time"]["category"]["label"].values())[0]
        return float(value), time_key
    except Exception as e:
        print(f"Error fetching Eurostat data for {code}: {e}")
        return 0.0, "ERR"

@st.cache_data(ttl=3600)
def fetch_japan_estat(stats_id):
    url = f"https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?appId={JAPAN_APP_ID}&statsDataId={stats_id}&limit=1"
    try:
        res = requests.get(url, timeout=15).json()
        # Check for data existence before accessing
        if not res.get("GET_STATS_DATA") or not res["GET_STATS_DATA"].get("STATISTICAL_DATA") or not res["GET_STATS_DATA"]["STATISTICAL_DATA"].get("DATA_INF"):
            print(f"Japan E-Stat data structure invalid or empty for {stats_id}")
            return 0.0, "ERR"

        data_inf = res["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
        if isinstance(data_inf, list):
            val = data_inf[0]["$"]
            date = data_inf[0]["@time"]
        else:
            val = data_inf["$"]
            date = data_inf["@time"]
        return float(val), date
    except Exception as e:
        print(f"Error fetching Japan E-Stat data for {stats_id}: {e}")
        return 0.0, "ERR"

def fetch_market(ticker):
    try:
        data = yf.Ticker(ticker)
        # Use info.get to safely access keys that might not exist
        val = data.fast_info.get("last_price")
        if val is None:
            print(f"Could not get last_price for ticker {ticker}")
            return 0.0, "ERR"
        return float(val), "Live"
    except Exception as e:
        print(f"Error fetching market data for {ticker}: {e}")
        return 0.0, "ERR"

# DASHBOARD
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
        if m[3] == "ons":
            val, dt = fetch_uk_ons(m[1])
        else:
            val, dt = fetch_market(m[1])
        status = "🔴 HOT" if val > m[2] else "🟢 TARGET"
        res_uk.append({
            "Indicator": m[0],
            "Val": val,
            "Status": status,
            "Date": dt
        })
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
        res_eu.append({
            "Indicator": m[0],
            "Val": val,
            "Status": status,
            "Date": dt
        })
    st.table(pd.DataFrame(res_eu))

# 🇯🇵 JAPAN
with c3:
    st.header("🇯🇵 JAPAN (JPY)")
    jp_metrics = [

        ["Japan Core CPI MoM", "0003423127", 0.1, "estat"],
        ["Japan Unemp Rate", "0003008544", 2.5, "estat"],
        ["Japan Household Spend", "0003017234", 1.0, "estat"],
        ["Japan Industrial Prod", "0003076161", 0.0, "estat"],
        ["Japan Core CPI YoY", "0003423127", 2.0, "estat"],
        ["Japan 10Y JGB Yield", "^N225", 0.8, "yf"],
        ["Japan GDP Growth", "0003109786", 0.2, "estat"],
        ["Nikkei 225 Index", "^N225", 35000, "yf"]

    ]
    res_jp = []
    for m in jp_metrics:
        if m[3] == "estat":
            val, dt = fetch_japan_estat(m[1])
        else:
            val, dt = fetch_market(m[1])
        status = "📈 HAWKISH" if val > m[2] else "📉 DOVISH"
        res_jp.append({
            "Indicator": m[0],
            "Val": val,
            "Status": status,
            "Date": dt

        })
    st.table(pd.DataFrame(res_jp))

st.divider()
st.subheader(" Global FX Strategic Bias")
st.info("Monitor Terintegrasi: GBP, EUR, JPY. Refresh untuk data terbaru.")
if st.button("🔄 REFRESH ALL DATA"):
    st.cache_data.clear()
    st.rerun()


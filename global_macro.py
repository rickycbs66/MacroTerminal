import streamlit as st
import pandas as pd
from fredapi import Fred
import yfinance as yf
import plotly.graph_objects as go

# 1. KONFIGURASI TAMPILAN
st.set_page_config(page_title="Global FX Macro Terminal", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #000000; color: #00FF00; font-family: 'Courier New'; }
.signal-box {padding:15px; border-radius:10px; border:1px solid #333; text-align:center; background:#111;}
h1,h2,h3 {color:#00FF00 !important;}
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
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("PIN Salah! Akses Ditolak.")
    return False

if not check_password():
    st.stop()

# 3. KONEKSI API
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except:
    FRED_API_KEY = "15a934d9ca6efdf12dfe85a48835ce9a"
fred = Fred(api_key=FRED_API_KEY)

# 4. MODEL INDIKATOR GLOBAL (MARKET MOVERS)
global_macro = {
    "🇬🇧 UNITED KINGDOM (GBP)": [
        ["UK CPI Inflation YoY", "GBRCPIALLMINMEI", 2.0],
        ["UK Core CPI YoY", "GBRCPICOREMINMEI", 2.0],
        ["UK Unemployment Rate", "LRUNTTTTGBM156S", 4.2],
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

# 5. FUNGSI AMBIL DATA
@st.cache_data(ttl=3600)
def get_macro_val_smart(ticker, name):
    try:
        if ticker.startswith("^"):
            df = yf.download(ticker, period="5d", progress=False)
            return round(float(df['Close'].iloc[-1]), 2)
        
        data = fred.get_series(ticker)
        if data.empty: return 0.0
         raw_val_tickers = [
            "LRUNTTTTGBM156S", 
            "IRLTLT01GBM156N", 
            "DEUSNT01ATM664N", 
            "IRLTLT01JPM156N"  
        ]
        if ticker in raw_val_tickers:
            return round(float(data.iloc[-1]), 2)    
        if any(x in name for x in ["CPI", "Inflation", "GDP"]):
            freq = 4 if "GDP" in name else 12
            val_yoy = (data.pct_change(freq).iloc[-1]) * 100
            return round(float(val_yoy), 2)
        return round(float(data.iloc[-1]), 2)
    except:
        return 0.0 

# 6. UI DASHBOARD 
st.title(" GLOBAL FX STRATEGIC MONITOR")
st.subheader("BoE | ECB | BoJ: High-Impact Analysis")

cols = st.columns(3)
regions = list(global_macro.keys())

for i, region in enumerate(regions):
    with cols[i]:
        st.markdown(f"### {region}")
        data_rows = []
        for name, ticker, threshold in global_macro[region]:
            val = get_macro_val_smart(ticker, name)
            if "CPI" in name or "Inflation" in name:
                status = "🔴 HOT" if val > threshold else "🟢 TARGET"
            elif "Sentiment" in name or "GDP" in name:
                status = "🟢 GROWTH" if val > threshold else "🔴 SLOW"
            elif "Yield" in name:
                status = "📈 HAWKISH" if val > threshold else "📉 DOVISH"
            else:
                status = "⚪️ MONITOR"
            data_rows.append({"Indikator": name, "Value": val, "Status": status})
        st.table(pd.DataFrame(data_rows))

st.divider()

# 7. AUTOMATIC FX BIAS (LOGIKA TRADING)
st.subheader(" Global FX Strategic Bias")
uk_inf = get_macro_val_smart("GBRCPIALLMINMEI", "CPI")
eu_zew = get_macro_val_smart("DEUSNT01ATM664N", "Sentiment")
jp_yld = get_macro_val_smart("IRLTLT01JPM156N", "Yield")

b1, b2, b3 = st.columns(3)
with b1:
    st.markdown("### 🇬🇧 GBP Bias")
    if uk_inf > 3.0: st.error(f"**HAWKISH**\n\nInflasi UK Tinggi ({uk_inf}%). **GBP STRONG**")
    else: st.success(f"**DOVISH**\n\nInflasi Melandai. **GBP WEAK**")
with b2:
    st.markdown("### 🇪🇺 EUR Bias")
    if eu_zew < 0: st.error(f"**BEARISH**\n\nSentimen Jerman Buruk ({eu_zew}). **EURUSD TERTEKAN**")
    else: st.success(f"**BULLISH**\n\nSentimen Membaik. **EUR STRONG**")
with b3:
    st.markdown("### 🇯🇵 JPY Bias")
    if jp_yld > 0.8: st.error(f"**STRENGTHENING**\n\nYield JGB Naik ({jp_yld}%). **JPY STRONG**")
    else: st.info(f"**WEAK JPY**\n\nYield Rendah. **JPY WEAK vs USD**")

if st.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

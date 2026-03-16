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
@st.cache_data(ttl=3600)
def fetch_ons_direct(url, data_type="months"):
    """
    data_type bisa: 'months', 'quarters', atau 'years' 
    tergantung pada jenis indikatornya.
    """
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        # Navigasi otomatis berdasarkan ketersediaan key
        if data_type in data:
            latest = data[data_type][-1]
        elif 'months' in data:
            latest = data['months'][-1]
        elif 'quarters' in data:
            latest = data['quarters'][-1]
        else:
            latest = data['years'][-1]
            
        return float(latest['value']), latest['date']
    except Exception as e:
        return 0.0, f"ERR: {str(e)[:10]}"

# 3. MAPPING URL VALID (SESUAI PERMINTAAN ANDA)
# Format: [Label, URL, Threshold, Tipe_Data]
uk_macro_links = [
    ["UK CPI Inflation YoY", "https://ons.gov.uk", 2.0, "months"],
    ["UK Core CPI YoY", "https://ons.gov.uk", 2.0, "months"],
    ["UK Unemployment Rate", "https://ons.gov.uk", 4.4, "months"],
    ["UK Wage Growth YoY", "https://ons.gov.uk", 3.0, "months"],
    ["UK GDP Growth QoQ", "https://ons.gov.uk", 0.2, "quarters"],
    ["UK GDP Growth YoY", "https://ons.gov.uk", 0.5, "quarters"],
    ["UK Retail Sales Index", "https://ons.gov.uk", 1.0, "months"],
    ["UK Industrial Prod", "https://ons.gov.uk", 0.0, "months"]
]

# 4. RENDER DASHBOARD
st.title("🇬🇧 UK MACRO STRATEGIC TERMINAL (ONS OFFICIAL)")
st.subheader(f"Data Source: Office for National Statistics | {datetime.now().strftime('%d %B %Y')}")

# Pengolahan Data ke DataFrame
results = []
for label, url, threshold, d_type in uk_macro_links:
    val, dt = fetch_ons_direct(url, d_type)
    
    # Logika Status Presisi
    if "CPI" in label or "Inflation" in label:
        status = "🔴 HOT" if val > threshold else "🟢 TARGET"
    elif "Unemployment" in label:
        status = "🔴 SLOW" if val > threshold else "🟢 OK"
    elif "GDP" in label or "Retail" in label or "Industrial" in label:
        status = "🟢 GROWTH" if val > threshold else "🔴 SLOW"
    else:
        status = "⚪ MONITOR"
        
    results.append({
        "Economic Indicator": label,
        "Current Value": f"{val:.2f}%" if "Index" not in label else val,
        "Threshold": threshold,
        "Status": status,
        "Release Date": dt
    })

# Tampilan Tabel
df = pd.DataFrame(results)
st.table(df)

# 5. LOGIKA BIAS GBP
st.divider()
st.subheader("💡 GBP Strategic Bias")
cpi_now = float(results[0]["Current Value"].replace('%', ''))
gdp_now = float(results[5]["Current Value"].replace('%', ''))

if cpi_now > 2.0 and gdp_now > 0.0:
    st.error(f"**GBP BIAS: HAWKISH** - Inflasi ({cpi_now}%) di atas target dengan pertumbuhan positif. BoE kemungkinan mempertahankan suku bunga tinggi.")
elif cpi_now < 2.0:
    st.success("**GBP BIAS: DOVISH** - Inflasi melandai di bawah target. Potensi pemotongan suku bunga.")
else:
    st.info("**GBP BIAS: NEUTRAL** - Menunggu rilis data tenaga kerja/upah lebih lanjut.")

if st.button("🔄 REFRESH ONS DATA"):
    st.cache_data.clear()
    st.rerun()




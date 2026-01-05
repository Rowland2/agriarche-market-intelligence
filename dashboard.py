import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# =====================================================
# 1. BRANDING & CSS (FIXED FOR VISIBILITY)
# =====================================================
st.set_page_config(page_title="Agriarche Commodity Dashboard", layout="wide")

PRIMARY_COLOR = "#1F7A3F" 
ACCENT_COLOR = "#F4B266"  
BG_COLOR = "#F5F7FA"
LOGO_PATH = "assets/logo.png"

st.markdown(f"""
    <style>
        header {{ visibility: hidden; }}
        .stApp {{ background-color: {BG_COLOR}; }}
        
        /* SIDEBAR STYLING */
        section[data-testid="stSidebar"] {{ 
            background-color: {ACCENT_COLOR} !important; 
        }}
        
        /* FIX: Dropdown text visibility without breaking main charts */
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }}

        div[role="listbox"] ul li {{
            color: #000000 !important;
        }}

        section[data-testid="stSidebar"] .stMarkdown p, 
        section[data-testid="stSidebar"] label {{
            color: #000000 !important;
            font-weight: bold !important;
        }}

        h1, h2, h3 {{ color: {PRIMARY_COLOR} !important; }}
    </style>
""", unsafe_allow_html=True)

# =====================================================
# 2. DATA LOADERS
# =====================================================

@st.cache_data
def load_historical_data():
    paths = ["Predictive Analysis Commodity pricing.xlsx", "data/Predictive Analysis Commodity pricing.xlsx"]
    f = next((p for p in paths if os.path.exists(p)), None)
    if not f: return pd.DataFrame()
    
    df = pd.read_excel(f)
    df.columns = [str(c).strip() for c in df.columns]
    
    date_col = next((c for c in df.columns if any(k in c.lower() for k in ["date", "timestamp"])), None)
    price_col = next((c for c in df.columns if any(k in c.lower() for k in ["price", "clean"])), None)
    comm_col = next((c for c in df.columns if "commodity" in c.lower()), None)

    if date_col and price_col and comm_col:
        df["ds"] = pd.to_datetime(df[date_col], errors="coerce")
        df["price"] = pd.to_numeric(df[price_col], errors="coerce")
        df["commodity"] = df[comm_col].astype(str).str.strip()
        df = df.dropna(subset=["ds", "price", "commodity"])
        df["year"] = df["ds"].dt.year
        df["month_name"] = df["ds"].dt.month_name()
        df["day"] = df["ds"].dt.day
    return df

@st.cache_data
def load_live_excel_data():
    path = "data/clean_prices.xlsx"
    if os.path.exists(path):
        ldf = pd.read_excel(path)
        ldf.columns = [str(c).strip() for c in ldf.columns]
        
        new_cols = {}
        date_assigned = False
        for col in ldf.columns:
            low_col = col.lower()
            if not date_assigned and any(k in low_col for k in ['date', 'scraped_at', 'time']):
                new_cols[col] = 'Date'
                date_assigned = True
            elif 'price' in low_col: new_cols[col] = 'Price'
            elif 'commodity' in low_col: new_cols[col] = 'Commodity'
            elif 'location' in low_col or 'market' in low_col: new_cols[col] = 'Location'
            elif 'trend' in low_col or 'change' in low_col: new_cols[col] = 'Trend'
        
        ldf = ldf.rename(columns=new_cols)
        if 'Date' in ldf.columns:
            ldf['Date'] = pd.to_datetime(ldf['Date'], errors='coerce')
            ldf['Month'] = ldf['Date'].dt.month_name()
        return ldf
    return pd.DataFrame()

# =====================================================
# 3. INTERFACE EXECUTION (ORDER MATTERS)
# =====================================================
# Load data first to prevent NameError
df_hist = load_historical_data()
df_live = load_live_excel_data()

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)

st.markdown("<h1 style='text-align:center;'>Commodity Price Intelligence</h1>", unsafe_allow_html=True)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Market Filters")
months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

if not df_hist.empty:
    st.sidebar.subheader("📊 Historical Analysis")
    sel_hist_comm = st.sidebar.selectbox("Select Commodity", sorted(df_hist["commodity"].unique()))
    sel_hist_month = st.sidebar.selectbox("Select Month", months_list, index=datetime.now().month - 1)
    years_avail = sorted(df_hist["year"].unique())
    compare_years = st.sidebar.multiselect("Compare Years", years_avail, default=years_avail)

st.sidebar.markdown("---")

if not df_live.empty:
    st.sidebar.subheader("🌐 Live Market Controls")
    live_comm_list = ["All"] + sorted(df_live['Commodity'].astype(str).unique().tolist())
    sel_live_comm = st.sidebar.selectbox("Filter Live Commodity", live_comm_list)
    sel_live_month = st.sidebar.selectbox("Filter Live Month", ["All"] + months_list)

# --- TREND CHART ---
if not df_hist.empty:
    st.subheader(f"Price Trend: {sel_hist_comm} in {sel_hist_month}")
    dfc = df_hist[(df_hist["commodity"] == sel_hist_comm) & 
                  (df_hist["year"].isin(compare_years)) & 
                  (df_hist["month_name"] == sel_hist_month)].copy()
    
    dfc["year"] = dfc["year"].astype(str)
    dfc_grouped = dfc.groupby(["year", "day"], as_index=False)["price"].mean()

    if not dfc_grouped.empty:
        fig = px.line(dfc_grouped, x="day", y="price", color="year", markers=True,
                      text=dfc_grouped["price"].apply(lambda x: f"{x/1000:.1f}k"),
                      color_discrete_map={"2024": PRIMARY_COLOR, "2025": ACCENT_COLOR},
                      labels={"day": "Day of Month", "price": "Price (₦)"})
        
        # FIXED: Corrected 'titlefont' to 'title': {'font': ...}
        fig.update_layout(
            plot_bgcolor="white", 
            paper_bgcolor="white", 
            font=dict(color="black"),
            xaxis=dict(
                tickfont=dict(color="black"), 
                title=dict(text="Day of Month", font=dict(color="black")), 
                showline=True, 
                linecolor="black"
            ),
            yaxis=dict(
                tickfont=dict(color="black"), 
                title=dict(text="Price (₦)", font=dict(color="black")), 
                showline=True, 
                linecolor="black"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

# --- LIVE TABLE ---
st.markdown("---")
st.header("🌐 Real-time Commodity Prices")

if not df_live.empty:
    display_df = df_live.copy()
    if sel_live_comm != "All":
        display_df = display_df[display_df['Commodity'] == sel_live_comm]
    if sel_live_month != "All" and 'Month' in display_df.columns:
        display_df = display_df[display_df['Month'] == sel_live_month]

    st.dataframe(
        display_df.drop(columns=['Month'], errors='ignore'),
        use_container_width=True,
        hide_index=True
    )
































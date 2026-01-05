import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# =====================================================
# 1. BRANDING & CSS
# =====================================================
st.set_page_config(page_title="Agriarche Commodity Dashboard", layout="wide")

PRIMARY_COLOR = "#1F7A3F"  # Agriarche Green
ACCENT_COLOR = "#F4B266"   # Agriarche Gold
BG_COLOR = "#F5F7FA"
LOGO_PATH = "assets/logo.png"

st.markdown(f"""
    <style>
        header {{ visibility: hidden; }}
        .stApp {{ background-color: {BG_COLOR}; }}
        section[data-testid="stSidebar"] {{ background-color: {ACCENT_COLOR} !important; }}

        /* Visible Headers */
        h1, h2, h3 {{ color: {PRIMARY_COLOR} !important; font-weight: bold; }}
        
        /* Black Dropdowns with White Text */
        div[data-baseweb="select"] > div, div[data-baseweb="popover"] ul {{
            background-color: #000000 !important; color: #FFFFFF !important;
        }}
        div[role="listbox"] div {{ background-color: #000000 !important; color: #FFFFFF !important; }}
    </style>
""", unsafe_allow_html=True)

# =====================================================
# 2. DATA LOADERS
# =====================================================

@st.cache_data
def load_historical_data():
    f = "Predictive Analysis Commodity pricing.xlsx"
    if not os.path.exists(f): return pd.DataFrame()
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
        
        # FIXED: Prevent duplicate "Date" columns which caused the crash
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
# 3. INTERFACE EXECUTION
# =====================================================
df_hist = load_historical_data()
df_live = load_live_excel_data()

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)

st.markdown("<h1 style='text-align:center;'>Commodity Price Intelligence</h1>", unsafe_allow_html=True)

# --- SIDEBAR: CONSOLIDATED FILTERS ---
st.sidebar.header("Market Filters")
months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# 1. Historical Controls
st.sidebar.subheader("📊 Historical Analysis")
if not df_hist.empty:
    sel_hist_comm = st.sidebar.selectbox("Select Commodity", sorted(df_hist["commodity"].unique()))
    sel_hist_month = st.sidebar.selectbox("Select Month", months_list, index=datetime.now().month - 1)
    years_avail = sorted(df_hist["year"].unique())
    compare_years = st.sidebar.multiselect("Compare Years", years_avail, default=years_avail)

st.sidebar.markdown("---")

# 2. Live Market Controls
st.sidebar.subheader("🌐 Live Market Controls")
if not df_live.empty:
    live_comm_list = ["All"] + sorted(df_live['Commodity'].astype(str).unique().tolist())
    sel_live_comm = st.sidebar.selectbox("Filter Live Commodity", live_comm_list)
    
    live_month_list = ["All"] + months_list
    sel_live_month = st.sidebar.selectbox("Filter Live Month", live_month_list)
else:
    st.sidebar.warning("No live data found in Excel.")

# --- SECTION 1: HISTORICAL TREND CHART ---
if not df_hist.empty:
    st.subheader(f"Price Trend: {sel_hist_comm} in {sel_hist_month}")
    dfc = df_hist[(df_hist["commodity"] == sel_hist_comm) & 
                 (df_hist["year"].isin(compare_years)) & 
                 (df_hist["month_name"] == sel_hist_month)].copy()
    
    dfc["year"] = dfc["year"].astype(str)
    dfc_grouped = dfc.groupby(["year", "day"], as_index=False)["price"].mean()

    if not dfc_grouped.empty:
        fig = px.line(dfc_grouped, x="day", y="price", color="year", markers=True,
                      text=dfc_grouped["price"].apply(lambda x: f"{x/1000:.0f}k"),
                      color_discrete_map={"2024": PRIMARY_COLOR, "2025": ACCENT_COLOR},
                      labels={"day": "Day of Month", "price": "Price (₦)"})
        
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=60, r=30, t=50, b=60),
            font=dict(color="black", size=12),
            xaxis=dict(title="Day of Month", showgrid=False, showline=True, linecolor='black', tickfont=dict(color="black"), dtick=5),
            yaxis=dict(title="Average Price (₦)", gridcolor='lightgrey', showgrid=True, showline=True, linecolor='black', tickformat="~s", tickfont=dict(color="black")),
            legend=dict(font=dict(color="black"))
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)

# --- SECTION 2: LIVE MARKET BOARD ---
st.markdown("---")
st.header("🌐 Real-time Commodity Prices")

if not df_live.empty:
    # 1. Apply Filtering from Sidebar
    display_df = df_live.copy()
    if sel_live_comm != "All":
        display_df = display_df[display_df['Commodity'] == sel_live_comm]
    if sel_live_month != "All" and 'Month' in display_df.columns:
        display_df = display_df[display_df['Month'] == sel_live_month]

    # 2. Main Area Search Bar
    search_query = st.text_input("🔍 Search for a location or keyword (e.g., 'Kaduna')")
    if search_query:
        display_df = display_df[display_df.apply(lambda row: search_query.lower() in row.astype(str).str.lower().values, axis=1)]

    # 3. Final Table Display
    st.dataframe(
        display_df.drop(columns=['Month'], errors='ignore'),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.TextColumn("Price", help="Latest price stored in Excel"),
            "Trend": st.column_config.TextColumn("Trend", width="small")
        }
    )
else:
    st.info("Please update the 'data/clean_prices.xlsx' file to see live data.")































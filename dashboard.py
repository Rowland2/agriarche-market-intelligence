import os
import glob
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from io import BytesIO

# Import for PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# =====================================================
# 1. BRANDING & CSS
# =====================================================
st.set_page_config(page_title="Agriarche Commodity Dashboard", layout="wide")

PRIMARY_COLOR = "#1F7A3F" 
ACCENT_COLOR = "#F4B266"  
BG_COLOR = "#F5F7FA"
LOGO_PATH = "assets/logo.png"

# --- COMMODITY INTELLIGENCE DATA ---
COMMODITY_INFO = {
    "Soybeans": {"desc": "A raw leguminous crop used for oil and feed.", "markets": "Mubi, Giwa, and Kumo", "abundance": "Nov, Dec, and April", "note": "A key industrial driver for the poultry and vegetable oil sectors."},
    "Cowpea Brown": {"desc": "Protein-rich legume popular in local diets.", "markets": "Dawanau and Potiskum", "abundance": "Oct through Jan", "note": "Supply depends on Northern storage."},
    "Cowpea White": {"desc": "Staple bean variety used for commercial flour.", "markets": "Dawanau and Bodija", "abundance": "Oct and Nov", "note": "High demand in South drives prices."},
    "Honey beans": {"desc": "Premium sweet brown beans (Oloyin).", "markets": "Oyingbo and Dawanau", "abundance": "Oct to Dec", "note": "Often carries a price premium."},
    "Maize": {"desc": "Primary cereal crop for food and industry.", "markets": "Giwa, Makarfi, and Funtua", "abundance": "Sept to Nov", "note": "Correlates strongly with Sorghum trends."},
    "Rice Paddy": {"desc": "Raw rice before milling/processing.", "markets": "Argungu and Kano", "abundance": "Nov and Dec", "note": "Foundations for processed rice pricing."},
    "Rice processed": {"desc": "Milled and polished local rice.", "markets": "Kano, Lagos, and Onitsha", "abundance": "Year-round", "note": "Price fluctuates with fuel/milling costs."},
    "Sorghum": {"desc": "Drought-resistant grain staple.", "markets": "Dawanau and Gombe", "abundance": "Dec and Jan", "note": "Market substitute for Maize."},
    "Millet": {"desc": "Fast-growing cereal for the lean season.", "markets": "Dawanau and Potiskum", "abundance": "Sept and Oct", "note": "First harvest after rainy season."},
    "Groundnut gargaja": {"desc": "Local peanut variety for oil extraction.", "markets": "Dawanau and Gombe", "abundance": "Oct and Nov", "note": "Sahel region specialty."},
    "Groundnut kampala": {"desc": "Large, premium roasting groundnuts.", "markets": "Kano and Dawanau", "abundance": "Oct and Nov", "note": "Higher oil content than Gargaja."}
}

# --- MASTER NORMALIZATION FUNCTION ---
def normalize_name(text):
    """Syncs various spellings to a master name."""
    text = str(text).lower().strip()
    if "soya" in text or "soy" in text: return "Soybeans"
    if "maize" in text or "corn" in text: return "Maize"
    if "cowpea" in text and "brown" in text: return "Cowpea Brown"
    if "cowpea" in text and "white" in text: return "Cowpea White"
    if "honey" in text: return "Honey beans"
    if "rice" in text and "paddy" in text: return "Rice Paddy"
    if "rice" in text and "process" in text: return "Rice processed"
    if "sorghum" in text and "red" in text: return "Sorghum red"
    if "sorghum" in text and "white" in text: return "Sorghum white"
    if "sorghum" in text and "yellow" in text: return "Sorghum yellow"
    if "sorghum" in text: return "Sorghum"
    if "groundnut" in text and "gargaja" in text: return "Groundnut gargaja"
    if "groundnut" in text and "kampala" in text: return "Groundnut kampala"
    return text.capitalize()

st.markdown(f"""
    <style>
        header {{ visibility: hidden; }}
        .stApp {{ background-color: {BG_COLOR}; }}
        section[data-testid="stSidebar"] {{ background-color: {ACCENT_COLOR} !important; }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }}
        div[role="listbox"] ul li {{ color: #000000 !important; }}
        section[data-testid="stSidebar"] .stMarkdown p, 
        section[data-testid="stSidebar"] label {{
            color: #000000 !important;
            font-weight: bold !important;
        }}
        h1, h2, h3 {{ color: {PRIMARY_COLOR} !important; }}
        
        /* KPI Card Styling */
        .metric-container {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid {PRIMARY_COLOR};
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            width: 100%;
            text-align: center;
        }}
        .metric-label {{ font-size: 14px; color: #666; font-weight: bold; }}
        .metric-value {{ font-size: 24px; color: {PRIMARY_COLOR}; font-weight: 800; }}

        /* Strategy Cards */
        .strategy-card {{
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }}
        .best-buy {{ background-color: #2E7D32; border-bottom: 5px solid #1B5E20; }}
        .worst-buy {{ background-color: #C62828; border-bottom: 5px solid #8E0000; }}

        /* AI Advisor Styling */
        .advisor-container {{
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid {PRIMARY_COLOR};
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}

        .stAlert p {{ color: #000000 !important; }}
    </style>
""", unsafe_allow_html=True)

 # =====================================================
# 2. UPDATED PDF GENERATOR FUNCTION
# =====================================================
from reportlab.lib.units import inch
from reportlab.platypus import Flowable

class HorizontalLine(Flowable):
    def __init__(self, width, height, color):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.color = color
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.line(0, 0, self.width, 0)

def generate_pdf_report(month_name, report_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], textColor=colors.HexColor(PRIMARY_COLOR), spaceAfter=12)
    market_header_style = ParagraphStyle('MarketHeader', parent=styles['Heading2'], textColor=colors.HexColor(PRIMARY_COLOR), spaceBefore=15, spaceAfter=5)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Heading3'], textColor=colors.black, spaceBefore=8)
    body_style = styles['Normal']
    
    elements = []
    
    # --- REPORT HEADER ---
    elements.append(Paragraph(f"Agriarche Market Intelligence Report", title_style))
    elements.append(Paragraph(f"Analysis Month: {month_name}", styles['Heading3']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    elements.append(Spacer(1, 20))

    # --- WATERMARK LOGIC ---
    def add_watermark(canvas, doc):
        canvas.saveState()
        if os.path.exists(LOGO_PATH):
            canvas.setFillAlpha(0.1)
            canvas.drawImage(LOGO_PATH, letter[0]/2 - 1.5*inch, letter[1]/2 - 1.5*inch, width=3*inch, preserveAspectRatio=True, mask='auto')
        canvas.restoreState()

    # --- CONTENT GENERATION (GROUPED BY MARKET) ---
    summary_table_data = [["Market", "Commodity", "Avg Price/Kg (N)", "High/Kg (N)", "Low/Kg (N)"]]
    unique_markets = sorted(report_df["Market"].unique())

    for market in unique_markets:
        market_df = report_df[report_df["Market"] == market]
        elements.append(Paragraph(f"Location: {market}", market_header_style))
        elements.append(HorizontalLine(6.5*inch, 1, colors.grey))
        
        for comm in sorted(market_df["commodity"].unique()):
            comm_df = market_df[market_df["commodity"] == comm]
            target_val = "price_per_kg" if "price_per_kg" in comm_df.columns else "price"
            
            avg_p = comm_df[target_val].mean()
            high_p = comm_df[target_val].max()
            low_p = comm_df[target_val].min()
            
            elements.append(Paragraph(f"<b>{comm}</b>", sub_style))
            text = (f"In {market}, the average price for {comm} was <b>N{avg_p:,.2f}/Kg</b>. "
                    f"Prices peaked at N{high_p:,.2f}/Kg with a floor of N{low_p:,.2f}/Kg.")
            elements.append(Paragraph(text, body_style))
            
            summary_table_data.append([market, comm, f"{avg_p:,.2f}", f"{high_p:,.2f}", f"{low_p:,.2f}"])
        
        elements.append(Spacer(1, 10))

    # --- PRICE SUMMARY TABLE ---
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Comprehensive Market Summary Table", market_header_style))
    elements.append(Spacer(1, 10))

    t = Table(summary_table_data, colWidths=[110, 140, 90, 80, 80], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F4B266")), # UPDATED HEADER COLOR
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black), # Switched to black for better contrast on orange
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
    ]))
    elements.append(t)

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)
    return buffer

# =====================================================
# 3. DATA LOADERS
# =====================================================
@st.cache_data
def load_kasuwa_internal_data():
    target_file = "Predictive Analysis Commodity pricing.xlsx"
    paths = [target_file, f"data/{target_file}"]
    f = next((p for p in paths if os.path.exists(p)), None)
    
    if not f:
        possible = glob.glob("predictive*.xlsx") + glob.glob("data/predictive*.xlsx")
        if not possible: return pd.DataFrame()
        f = possible[0]
    
    try:
        df = pd.read_excel(f)
        df.columns = [str(c).strip() for c in df.columns]
        
        date_col = next((c for c in df.columns if any(k in c.lower() for k in ["timestamp", "start time", "date"])), None)
        price_col = next((c for c in df.columns if any(k in c.lower() for k in ["price_per_kg", "price", "clean"])), None)
        comm_col = next((c for c in df.columns if "commodity" in c.lower()), None)
        market_col = next((c for c in df.columns if any(k in c.lower() for k in ["market", "location"])), None)

        if date_col and price_col and comm_col:
            df["ds"] = pd.to_datetime(df[date_col], errors="coerce")
            df["price"] = pd.to_numeric(df[price_col], errors="coerce")
            df["commodity"] = df[comm_col].apply(normalize_name)
            df["Market"] = df[market_col].astype(str).str.strip() if market_col else "Unknown"
                
            df = df.dropna(subset=["ds", "price", "commodity"])
            df["year"] = df["ds"].dt.year
            df["month_name"] = df["ds"].dt.month_name()
            df["day"] = df["ds"].dt.day
            
            # Explicitly ensure price_per_kg is calculated if column is missing but bag price is there
            if "price_per_kg" not in df.columns:
                df["price_per_kg"] = df["price"]
                
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_other_sources_data():
    path = "data/clean_prices.xlsx"
    if os.path.exists(path):
        try:
            ldf = pd.read_excel(path)
            ldf.columns = [str(c).strip() for c in ldf.columns]
            ldf = ldf.loc[:, ~ldf.columns.duplicated()]
            
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
            
            ldf = ldf.rename(columns=new_cols)
            if 'Date' in ldf.columns:
                ldf['Date'] = pd.to_datetime(ldf['Date'], errors='coerce')
                ldf['Month'] = ldf['Date'].dt.month_name()
            if 'Location' in ldf.columns:
                ldf['Location'] = ldf['Location'].astype(str).str.strip()
            if 'Price' in ldf.columns:
                ldf['Price'] = pd.to_numeric(ldf['Price'], errors='coerce')
            if 'Commodity' in ldf.columns:
                ldf['Commodity'] = ldf['Commodity'].apply(normalize_name)
            return ldf
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# =====================================================
# 4. INTERFACE EXECUTION
# =====================================================
df_hist = load_kasuwa_internal_data()
df_live = load_other_sources_data()

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)

st.markdown("<h1 style='text-align:center;'>Commodity Pricing Intelligence Dashboard</h1>", unsafe_allow_html=True)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Market Filters")
months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

if not df_hist.empty:
    st.sidebar.subheader("📊 Kasuwa Internal Price Analysis")
    sel_hist_comm = st.sidebar.selectbox("Select Commodity", sorted(df_hist["commodity"].unique()))
    hist_market_list = ["All Markets"] + sorted(df_hist["Market"].unique().tolist())
    sel_hist_market = st.sidebar.selectbox("Select Kasuwa internal price Market", hist_market_list)
    sel_hist_month = st.sidebar.selectbox("Select Month", months_list, index=0)
    years_avail = sorted(df_hist["year"].unique())
    compare_years = st.sidebar.multiselect("Year", years_avail, default=years_avail)
else:
    sel_hist_month = "January"
    sel_hist_comm = "None"

st.sidebar.markdown("---")

# SAFETY WRAPPER FOR OTHER SOURCES FILTERS
if not df_live.empty:
    st.sidebar.subheader("🌐 Other sources Controls")
    
    live_comm_list = ["All"]
    if 'Commodity' in df_live.columns:
        live_comm_list += sorted(df_live['Commodity'].dropna().unique().tolist())
    sel_live_comm = st.sidebar.selectbox("Filter Other sources Commodity", live_comm_list)

    live_market_list = ["All"]
    if 'Location' in df_live.columns:
        live_market_list += sorted(df_live['Location'].dropna().unique().tolist())
    sel_live_market = st.sidebar.selectbox("Filter Other sources Market", live_market_list)
    
    sel_live_month = st.sidebar.selectbox("Filter Other sources Month", ["All"] + months_list)
else:
    sel_live_comm = "All"
    sel_live_market = "All"
    sel_live_month = "All"

# --- TREND CHART SECTION ---
if not df_hist.empty:
    dfc = df_hist[(df_hist["commodity"] == sel_hist_comm) & 
                  (df_hist["year"].isin(compare_years)) & 
                  (df_hist["month_name"] == sel_hist_month)].copy()
    
    if sel_hist_market != "All Markets":
        dfc = dfc[dfc["Market"] == sel_hist_market]
    
    dfc["year"] = dfc["year"].astype(str)
    target_col = "price_per_kg" if "price_per_kg" in dfc.columns else "price"

    dfc_grouped = dfc.groupby(["year", "day"], as_index=False)[target_col].mean()

    title_suffix = f"in {sel_hist_month}"
    if sel_hist_market != "All Markets": title_suffix += f" ({sel_hist_market})"
    st.subheader(f"Kasuwa Internal Price Trend (per Kg): {sel_hist_comm} {title_suffix}")

    if not dfc_grouped.empty:
        fig = px.line(dfc_grouped, x="day", y=target_col, color="year", markers=True,
                      text=dfc_grouped[target_col].apply(lambda x: f"<b>{x:,.0f}</b>"),
                      color_discrete_map={"2024": PRIMARY_COLOR, "2025": ACCENT_COLOR, "2026": "#E67E22"},
                      labels={"day": "Day of Month", target_col: "Price per Kg (₦)"})
        
        fig.update_traces(textposition="top center")
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white", 
            font=dict(color="black", family="Arial Black"),
            xaxis=dict(
                title=dict(text="<b>Day of Month</b>", font=dict(size=16, color="black")),
                tickfont=dict(size=14, color="black", family="Arial Black"), 
                showline=True, linecolor="black", linewidth=3, gridcolor="#eeeeee"
            ),
            yaxis=dict(
                title=dict(text="<b>Price per Kg (₦)</b>", font=dict(size=16, color="black")),
                tickfont=dict(size=14, color="black", family="Arial Black"), 
                showline=True, linecolor="black", linewidth=3, gridcolor="#eeeeee"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        avg_p = dfc[target_col].mean()
        max_p = dfc[target_col].max()
        min_p = dfc[target_col].min()

        # --- KPI CARDS ---
        st.markdown(f"""
            <div class='metric-container'>
                <div class='metric-card'><div class='metric-label'>Avg Kasuwa internal price</div><div class='metric-value'>₦{avg_p:,.0f}</div></div>
                <div class='metric-card'><div class='metric-label'>Highest Kasuwa internal price</div><div class='metric-value'>₦{max_p:,.0f}</div></div>
                <div class='metric-card'><div class='metric-label'>Lowest Kasuwa internal price</div><div class='metric-value'>₦{min_p:,.0f}</div></div>
            </div>
        """, unsafe_allow_html=True)

        # --- COMMODITY INTELLIGENCE BOX ---
        c_info = COMMODITY_INFO.get(sel_hist_comm, {"desc": "Market data profiling in progress...", "markets": "Northern Hubs", "abundance": "Seasonal", "note": "Monitoring price shifts."})
        st.markdown(f"""
            <div class="advisor-container" style="border-left: 5px solid {ACCENT_COLOR};">
                <p style="color: #1F2937; font-size: 16px; margin: 0; line-height: 1.6;">
                    <b>🌾 {sel_hist_comm} Intelligence:</b><br>
                    {c_info['desc']} Primary sourcing markets include <b>{c_info['markets']}</b>. 
                    Periods of high abundance: <b>{c_info['abundance']}</b>.<br>
                    <i><b>Market Note:</b> {c_info['note']}</i>
                </p>
            </div>
        """, unsafe_allow_html=True)

        # =====================================================
        # STANDALONE KASUWA INTERNAL PRICE DATA TABLE
        # =====================================================
        st.markdown("---")
        st.subheader("📚 Kasuwa internal price Data Archive")
        st.write("Search through all Kasuwa internal price records regardless of sidebar filters.")
        
        hist_search = st.text_input("🔍 Search Kasuwa internal price Records", placeholder="Search by market, year, or commodity...", key="hist_search_bar")
        hist_display = df_hist.copy()
        
        if "ds" in hist_display.columns:
            hist_display["Date"] = hist_display["ds"].dt.strftime('%Y-%m-%d')

        if "price_per_kg" not in hist_display.columns:
            hist_display["Price per KG"] = hist_display["price"]
        else:
            hist_display["Price per KG"] = hist_display["price_per_kg"]
        
        display_cols = ["Date", "commodity", "Market", "Price per KG", "price", "year", "month_name"]
        hist_display = hist_display[[c for c in display_cols if c in hist_display.columns]]
        
        hist_display = hist_display.rename(columns={
            "commodity": "Commodity",
            "price": "Total Price (₦)",
            "Price per KG": "Price/KG (₦)"
        })

        if hist_search:
            mask = hist_display.apply(lambda row: row.astype(str).str.contains(hist_search, case=False).any(), axis=1)
            hist_display = hist_display[mask]
        
        st.dataframe(
            hist_display.sort_values(by="Date", ascending=False).style.format({
                "Price/KG (₦)": "{:,.2f}",
                "Total Price (₦)": "{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )

# =====================================================
# 5. MONTHLY INTELLIGENCE REPORT & AI ADVISOR
# =====================================================
st.markdown("---")
st.header(f"📋 Monthly Intelligence Report: {sel_hist_month}")

report_data = df_hist[df_hist["month_name"] == sel_hist_month] if not df_hist.empty else pd.DataFrame()
if not report_data.empty:
    pdf_buffer = generate_pdf_report(sel_hist_month, report_data)
    st.download_button(
        label="📥 Download Monthly Intelligence Report (PDF)",
        data=pdf_buffer,
        file_name=f"Agriarche_Market_Report_{sel_hist_month}.pdf",
        mime="application/pdf"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # STRATEGIC SOURCING CARDS
    strategy_df = df_hist[(df_hist["commodity"] == sel_hist_comm) & 
                          (df_hist["month_name"] == sel_hist_month)]
    
    if not strategy_df.empty:
        target_val = "price_per_kg" if "price_per_kg" in strategy_df.columns else "price"
        m_ranks = strategy_df.groupby("Market")[target_val].mean().sort_values()
        best_m = m_ranks.index[0]
        best_p = m_ranks.iloc[0]
        worst_m = m_ranks.index[-1]
        worst_p = m_ranks.iloc[-1]
        
        st.subheader(f"🎯 Strategic Sourcing: {sel_hist_comm}")
        scol1, scol2 = st.columns(2)
        with scol1:
            st.markdown(f"""
                <div class="strategy-card best-buy">
                    <div style="font-size: 14px; opacity: 0.9;">CHEAPEST MARKET (BEST TO BUY)</div>
                    <div style="font-size: 24px; font-weight: bold; margin: 5px 0;">{best_m}</div>
                    <div style="font-size: 20px;">₦{best_p:,.2f} <small>(Avg/Kg)</small></div>
                </div>
            """, unsafe_allow_html=True)
        with scol2:
            st.markdown(f"""
                <div class="strategy-card worst-buy">
                    <div style="font-size: 14px; opacity: 0.9;">HIGHEST PRICE MARKET (AVOID)</div>
                    <div style="font-size: 24px; font-weight: bold; margin: 5px 0;">{worst_m}</div>
                    <div style="font-size: 20px;">₦{worst_p:,.2f} <small>(Avg/Kg)</small></div>
                </div>
            """, unsafe_allow_html=True)

        # AI MARKET ADVISOR INTEGRATION
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Market Advisor")
        
        volatility = ((max_p - min_p) / min_p) * 100 if min_p > 0 else 0
        annual_avg = df_hist[df_hist["commodity"] == sel_hist_comm][target_col].mean()
        
        if volatility > 20:
            advice = f"🚨 **High Volatility Warning:** {sel_hist_comm} Kasuwa internal prices are fluctuating significantly ({volatility:.1f}%). Avoid spot-buying; look for long-term fixed contracts in {best_m}."
            bg_adv = "#FFF4E5"
        elif avg_p < annual_avg:
            advice = f"✅ **Optimal Buy Window:** Kasuwa internal prices for {sel_hist_comm} in {sel_hist_month} are {((annual_avg-avg_p)/annual_avg)*100:.1f}% below the annual average. Strong window for inventory stocking."
            bg_adv = "#E8F5E9"
        else:
            advice = f"ℹ️ **Market Stability:** {sel_hist_comm} is showing stable Kasuwa internal price action. Proceed with standard procurement volumes, prioritizing {best_m} for the best margins."
            bg_adv = "#E3F2FD"

        st.markdown(f"""
            <div class="advisor-container" style="background-color: {bg_adv};">
                <p style="color: #1F2937; font-size: 16px; margin: 0; line-height: 1.6;">
                    <b>Strategic Insight for {sel_hist_comm}:</b><br>{advice}
                </p>
            </div>
        """, unsafe_allow_html=True)

else:
    st.info("No Kasuwa internal price data available for this month.")

# =====================================================
# 6. PRICE GAP VISUALIZER (TABLE ONLY)
# =====================================================
st.markdown("---")

if not report_data.empty:
    # Determine if we use price_per_kg or fallback to price
    target_val = "price_per_kg" if "price_per_kg" in report_data.columns else "price"
    
    # Calculate aggregation
    gap_df = report_data.groupby('commodity').agg(
        min_price=(target_val, 'min'),
        max_price=(target_val, 'max'),
        avg_price=(target_val, 'mean')
    ).reset_index()

    # Helper function to find markets
    def get_market(row, type='min'):
        target = row['min_price'] if type == 'min' else row['max_price']
        match = report_data[(report_data['commodity'] == row['commodity']) & (report_data[target_val] == target)]
        return match['Market'].iloc[0] if not match.empty else "Unknown"

    # Add descriptive columns
    gap_df['Cheapest Market'] = gap_df.apply(lambda r: get_market(r, 'min'), axis=1)
    gap_df['Most Expensive Market'] = gap_df.apply(lambda r: get_market(r, 'max'), axis=1)
    
    # Sort by Commodity name
    gap_df = gap_df.sort_values('commodity')

    # Display only the subheader and the table
    st.subheader(f"Detailed Gap Analysis: {sel_hist_month}")
    
    st.dataframe(
        gap_df.style.format({
            'min_price': '₦{:,.2f}', 
            'max_price': '₦{:,.2f}', 
            'avg_price': '₦{:,.2f}'
        }),
        use_container_width=True, 
        hide_index=True,
        column_config={
            "commodity": "Commodity",
            "min_price": "Min Price",
            "max_price": "Max Price",
            "avg_price": "Avg Price",
            "Cheapest Market": "Cheapest Source",
            "Most Expensive Market": "Top Selling Market"
        }
    )
else:
    st.warning(f"No data available for gap analysis in {sel_hist_month}.")

# =====================================================
# 8. MARKET & PRICE COMPARISON
# =====================================================
st.markdown("---")
st.header("⚖️ Market & Price Comparison")

if not df_hist.empty:
    df_hist["norm_comm"] = df_hist["commodity"]
    if not df_live.empty:
        df_live["norm_comm"] = df_live["Commodity"]

    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        all_hist_commodities = sorted(df_hist["norm_comm"].unique())
        selected_comp_comm = st.selectbox("Select Commodity from Kasuwa internal price", all_hist_commodities)

    with col_comp2:
        hist_markets = sorted(df_hist[df_hist["norm_comm"] == selected_comp_comm]["Market"].unique())
        sel_m_hist = st.selectbox("Select Kasuwa internal price Market", hist_markets)

    # Internal Price (already in KG)
    target_val_hist = "price_per_kg" if "price_per_kg" in df_hist.columns else "price"
    hist_val = df_hist[(df_hist["norm_comm"] == selected_comp_comm) & 
                        (df_hist["Market"] == sel_m_hist)][target_val_hist].mean()

    live_match = pd.DataFrame()
    if not df_live.empty:
        live_match = df_live[df_live["norm_comm"] == selected_comp_comm]

    if not live_match.empty:
        live_markets = sorted(live_match["Location"].unique())
        sel_m_live = st.selectbox("Select Other sources Market to Compare", live_markets)
        
        # --- CONVERSION LOGIC ---
        # Get the mean price per bag and divide by 100 to get price per KG
        live_val_bag = live_match[live_match["Location"] == sel_m_live]["Price"].mean()
        live_val_kg = live_val_bag / 100 
        
        # Calculate comparison using the converted KG value
        diff = live_val_kg - hist_val
        perc_change = (diff / hist_val) * 100 if hist_val != 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Kasuwa internal: {sel_m_hist}", f"₦{hist_val:,.2f}")
        m2.metric(f"Other sources (KG): {sel_m_live}", f"₦{live_val_kg:,.2f}", f"{perc_change:+.1f}%")
        
        comp_chart_df = pd.DataFrame({
            "Source": [f"Kasuwa internal ({sel_m_hist})", f"Other sources ({sel_m_live})"],
            "Price per KG": [hist_val, live_val_kg]
        })
        
        fig_comp = px.bar(
            comp_chart_df, 
            x="Source", 
            y="Price per KG", 
            color="Source", 
            color_discrete_sequence=[ACCENT_COLOR, PRIMARY_COLOR], 
            text_auto='.2f' # Changed to .2f for precision in KG prices
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning(f"No other sources price data found for '{selected_comp_comm}'. Showing Kasuwa internal price value only.")
        st.metric(f"Kasuwa internal Average ({sel_m_hist})", f"₦{hist_val:,.2f}")

else:
    st.error("Kasuwa internal price data file is missing or empty.")

# =====================================================
# 7. OTHER SOURCES DATA TABLE
# =====================================================
st.markdown("---")
st.header("🌐 Other sources Commodity Prices")

if not df_live.empty:
    search_query = st.text_input("🔍 Search table (Filter by Date, Commodity, or Market)", placeholder="Enter keyword...")
    display_df = df_live.copy()
    
    # 1. CLEAN DATA TYPES: Ensure Price is strictly numeric so formatting works
    if 'Price' in display_df.columns:
        display_df['Price'] = pd.to_numeric(display_df['Price'], errors='coerce')

    # Apply Sidebar Filters
    if sel_live_comm != "All" and 'Commodity' in display_df.columns: 
        display_df = display_df[display_df['Commodity'] == sel_live_comm]
    
    if sel_live_market != "All" and 'Location' in display_df.columns: 
        display_df = display_df[display_df['Location'] == sel_live_market]
            
    if sel_live_month != "All" and 'Month' in display_df.columns:
        display_df = display_df[display_df['Month'] == sel_live_month]
    
    # Apply Text Search Filter
    if search_query:
        mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        display_df = display_df[mask]

    # Columns to hide from users
    cols_to_drop = ['Month', 'source', 'scraped_at', 'norm_comm']
    final_display = display_df.drop(columns=cols_to_drop, errors='ignore')

    # 2. RENDER TABLE WITH ROBUST FORMATTING
    st.dataframe(
        final_display, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, h:mm a"),
            # Simplified format to ensure the JS renderer doesn't break
            "Price": st.column_config.NumberColumn("Price (₦)", format="₦%d") 
        }
    )
else:
    st.info("Other sources data table is currently empty or format is unrecognized.")



































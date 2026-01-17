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
# 2. PDF GENERATOR FUNCTION
# =====================================================
def generate_pdf_report(month_name, report_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], textColor=colors.HexColor(PRIMARY_COLOR), spaceAfter=12)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Heading2'], textColor=colors.black, spaceBefore=10)
    body_style = styles['Normal']
    
    elements = []
    elements.append(Paragraph(f"Agriarche Market Intelligence Report", title_style))
    elements.append(Paragraph(f"Analysis Month: {month_name}", styles['Heading3']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    elements.append(Spacer(1, 20))

    summary_table_data = [["Commodity", "Avg Price (N)", "High (N)", "Low (N)"]]

    for comm in sorted(report_df["commodity"].unique()):
        comm_df = report_df[report_df["commodity"] == comm]
        avg_c = comm_df["price"].mean()
        high_c = comm_df["price"].max()
        low_c = comm_df["price"].min()
        market_stats = comm_df.groupby("Market")["price"].mean()
        top_m = market_stats.idxmax()
        bot_m = market_stats.idxmin()
        vol = ((high_c - low_c) / low_c) * 100 if low_c != 0 else 0

        elements.append(Paragraph(f"Commodity: {comm}", sub_style))
        text = (f"In {month_name}, the average price for {comm} was <b>N{avg_c:,.0f}</b>. "
                f"The market showed a volatility spread of {vol:.1f}% between the low of N{low_c:,.0f} "
                f"and a high of N{high_c:,.0f}. {top_m} was the highest priced market, while "
                f"{bot_m} recorded the lowest average prices.")
        elements.append(Paragraph(text, body_style))
        elements.append(Spacer(1, 15))

        summary_table_data.append([comm, f"{avg_c:,.0f}", f"{high_c:,.0f}", f"{low_c:,.0f}"])

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Monthly Price Summary Table", sub_style))
    elements.append(Spacer(1, 10))

    t = Table(summary_table_data, colWidths=[160, 110, 110, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PRIMARY_COLOR)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# =====================================================
# 3. DATA LOADERS
# =====================================================
@st.cache_data
def load_historical_data():
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
            df["commodity"] = df[comm_col].astype(str).str.strip()
            df["Market"] = df[market_col].astype(str).str.strip() if market_col else "Unknown"
                
            df = df.dropna(subset=["ds", "price", "commodity"])
            df["year"] = df["ds"].dt.year
            df["month_name"] = df["ds"].dt.month_name()
            df["day"] = df["ds"].dt.day
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_live_excel_data():
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
            return ldf
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# =====================================================
# 4. INTERFACE EXECUTION
# =====================================================
df_hist = load_historical_data()
df_live = load_live_excel_data()

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)

st.markdown("<h1 style='text-align:center;'>Commodity Pricing Intelligence Dashboard</h1>", unsafe_allow_html=True)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Market Filters")
months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

if not df_hist.empty:
    st.sidebar.subheader("📊 Historical Analysis")
    sel_hist_comm = st.sidebar.selectbox("Select Commodity", sorted(df_hist["commodity"].unique()))
    hist_market_list = ["All Markets"] + sorted(df_hist["Market"].unique().tolist())
    sel_hist_market = st.sidebar.selectbox("Select Historical Market", hist_market_list)
    sel_hist_month = st.sidebar.selectbox("Select Month", months_list, index=0)
    years_avail = sorted(df_hist["year"].unique())
    compare_years = st.sidebar.multiselect("Compare Years", years_avail, default=years_avail)
else:
    # Fallback if historical data fails
    sel_hist_month = "January"
    sel_hist_comm = "None"

st.sidebar.markdown("---")

# SAFETY WRAPPER FOR LIVE FILTERS
if not df_live.empty:
    st.sidebar.subheader("🌐 Live Market Controls")
    
    live_comm_list = ["All"]
    if 'Commodity' in df_live.columns:
        live_comm_list += sorted(df_live['Commodity'].dropna().unique().tolist())
    sel_live_comm = st.sidebar.selectbox("Filter Live Commodity", live_comm_list)

    live_market_list = ["All"]
    if 'Location' in df_live.columns:
        live_market_list += sorted(df_live['Location'].dropna().unique().tolist())
    sel_live_market = st.sidebar.selectbox("Filter Live Market", live_market_list)
    
    sel_live_month = st.sidebar.selectbox("Filter Live Month", ["All"] + months_list)
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
    dfc_grouped = dfc.groupby(["year", "day"], as_index=False)["price"].mean()

    title_suffix = f"in {sel_hist_month}"
    if sel_hist_market != "All Markets": title_suffix += f" ({sel_hist_market})"
    st.subheader(f"Price Trend: {sel_hist_comm} {title_suffix}")

    if not dfc_grouped.empty:
        fig = px.line(dfc_grouped, x="day", y="price", color="year", markers=True,
                      text=dfc_grouped["price"].apply(lambda x: f"<b>{x/1000:.1f}k</b>"),
                      color_discrete_map={"2024": PRIMARY_COLOR, "2025": ACCENT_COLOR, "2026": "#E67E22"},
                      labels={"day": "Day of Month", "price": "Price (₦)"})
        
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
                title=dict(text="<b>Price (₦)</b>", font=dict(size=16, color="black")),
                tickfont=dict(size=14, color="black", family="Arial Black"), 
                showline=True, linecolor="black", linewidth=3, gridcolor="#eeeeee"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        avg_p = dfc["price"].mean()
        max_p = dfc["price"].max()
        min_p = dfc["price"].min()

        st.markdown(f"""
            <div class='metric-container'>
                <div class='metric-card'><div class='metric-label'>Average Price</div><div class='metric-value'>₦{avg_p:,.0f}</div></div>
                <div class='metric-card'><div class='metric-label'>Highest Price</div><div class='metric-value'>₦{max_p:,.0f}</div></div>
                <div class='metric-card'><div class='metric-label'>Lowest Price</div><div class='metric-value'>₦{min_p:,.0f}</div></div>
            </div>
        """, unsafe_allow_html=True)

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
        m_ranks = strategy_df.groupby("Market")["price"].mean().sort_values()
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
                    <div style="font-size: 20px;">₦{best_p:,.0f} <small>(Avg)</small></div>
                </div>
            """, unsafe_allow_html=True)
        with scol2:
            st.markdown(f"""
                <div class="strategy-card worst-buy">
                    <div style="font-size: 14px; opacity: 0.9;">HIGHEST PRICE MARKET (AVOID)</div>
                    <div style="font-size: 24px; font-weight: bold; margin: 5px 0;">{worst_m}</div>
                    <div style="font-size: 20px;">₦{worst_p:,.0f} <small>(Avg)</small></div>
                </div>
            """, unsafe_allow_html=True)

        # AI MARKET ADVISOR INTEGRATION
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("  Market Advisor")
        
        volatility = ((max_p - min_p) / min_p) * 100 if min_p > 0 else 0
        annual_avg = df_hist[df_hist["commodity"] == sel_hist_comm]["price"].mean()
        
        if volatility > 20:
            advice = f"🚨 **High Volatility Warning:** {sel_hist_comm} prices are fluctuating significantly ({volatility:.1f}%). Avoid spot-buying; look for long-term fixed contracts in {best_m}."
            bg_adv = "#FFF4E5"
        elif avg_p < annual_avg:
            advice = f"✅ **Optimal Buy Window:** Prices for {sel_hist_comm} in {sel_hist_month} are {((annual_avg-avg_p)/annual_avg)*100:.1f}% below the annual average. Strong window for inventory stocking."
            bg_adv = "#E8F5E9"
        else:
            advice = f"ℹ️ **Market Stability:** {sel_hist_comm} is showing stable price action. Proceed with standard procurement volumes, prioritizing {best_m} for the best margins."
            bg_adv = "#E3F2FD"

        st.markdown(f"""
            <div class="advisor-container" style="background-color: {bg_adv};">
                <p style="color: #1F2937; font-size: 16px; margin: 0; line-height: 1.6;">
                    <b>Strategic Insight for {sel_hist_comm}:</b><br>{advice}
                </p>
            </div>
        """, unsafe_allow_html=True)

else:
    st.info("No historical data available for this month.")

# =====================================================
# 6. PRICE GAP VISUALIZER (AUTO-ANIMATED ON LOAD)
# =====================================================
st.markdown("---")
st.header(f"⚡ Price Gap Visualizer: {sel_hist_month}")
if not report_data.empty:
    st.info(f"This section identifies market arbitrage opportunities for {sel_hist_month}.")
    
    # 1. Prepare data
    gap_df = report_data.groupby('commodity').agg(
        min_price=('price', 'min'),
        max_price=('price', 'max'),
        avg_price=('price', 'mean')
    ).reset_index()

    def get_market(row, type='min'):
        target = row['min_price'] if type == 'min' else row['max_price']
        match = report_data[(report_data['commodity'] == row['commodity']) & (report_data['price'] == target)]
        return match['Market'].iloc[0] if not match.empty else "Unknown"

    gap_df['Cheapest Market'] = gap_df.apply(lambda r: get_market(r, 'min'), axis=1)
    gap_df['Most Expensive Market'] = gap_df.apply(lambda r: get_market(r, 'max'), axis=1)
    gap_df['Price Gap (₦)'] = gap_df['max_price'] - gap_df['min_price']
    gap_df['Opportunity %'] = (gap_df['Price Gap (₦)'] / gap_df['min_price']) * 100
    
    plot_df = gap_df.sort_values('Opportunity %', ascending=False)

    # 2. Setup Frames for Animation (Start = 0, End = Actual)
    frames = [
        dict(data=[dict(type='bar', y=[0] * len(plot_df))], name='start'),
        dict(data=[dict(type='bar', y=plot_df['Price Gap (₦)'])], name='end')
    ]

    # 3. Create the Base Figure
    fig_gap = px.bar(
        plot_df,
        x='commodity', 
        y='Price Gap (₦)',
        color='Opportunity %',
        text_auto='.2s',
        title=f"Market Price Spread (Gap) for {sel_hist_month}",
        color_continuous_scale='Greens',
        range_y=[0, plot_df['Price Gap (₦)'].max() * 1.2] 
    )

    # 4. FORCE AUTO-PLAY & HIDE CONTROLS
    fig_gap.update_layout(
        xaxis={'categoryorder':'total descending'},
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            visible=False,
            buttons=[dict(
                label="Play",
                method="animate",
                args=[None, dict(frame=dict(duration=1500, redraw=True), fromcurrent=True, mode='immediate')]
            )]
        )]
    )

    fig_gap.frames = [
        dict(data=[dict(y=[0] * len(plot_df))], name='start'),
        dict(data=[dict(y=plot_df['Price Gap (₦)'])], name='end')
    ]

    fig_gap.update_layout(sliders=[dict(visible=False)])

    st.plotly_chart(fig_gap, use_container_width=True)

    # Detailed Table
    st.subheader("Detailed Gap Analysis")
    st.dataframe(
        gap_df.sort_values('Opportunity %', ascending=False).style.format({
            'min_price': '₦{:,.0f}', 'max_price': '₦{:,.0f}', 
            'Price Gap (₦)': '₦{:,.0f}', 'Opportunity %': '{:.1f}%'
        }),
        use_container_width=True, hide_index=True
    )
else:
    st.warning("No data available to calculate price gaps.")

# =====================================================
# 7. LIVE DATA TABLE
# =====================================================
st.markdown("---")
st.header("🌐 Real-time Commodity Prices")
if not df_live.empty:
    search_query = st.text_input("🔍 Search table (Filter by Date, Commodity, Market, or Source)", placeholder="Enter keyword...")
    display_df = df_live.copy()
    
    if sel_live_comm != "All": 
        if 'Commodity' in display_df.columns:
            display_df = display_df[display_df['Commodity'] == sel_live_comm]
    
    if sel_live_market != "All": 
        if 'Location' in display_df.columns:
            display_df = display_df[display_df['Location'] == sel_live_market]
            
    if sel_live_month != "All" and 'Month' in display_df.columns:
        display_df = display_df[display_df['Month'] == sel_live_month]
    
    if search_query:
        mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        display_df = display_df[mask]

    st.dataframe(
        display_df.drop(columns=['Month'], errors='ignore'), 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("Live data table is currently empty or format is unrecognized.")


































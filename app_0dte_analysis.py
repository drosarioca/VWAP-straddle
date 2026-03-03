"""
app_0dte_analysis.py
=====================
Streamlit dashboard — Nifty 0 DTE Expiry Day Deep Analysis
Run: streamlit run app_0dte_analysis.py
"""

import os
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty 0 DTE Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background: #0d1117; }
.stMetric { background: #161b22; border-radius:10px; padding:12px; }
.stMetricLabel { font-size:12px; color:#8b949e; }
.stMetricValue { font-size:28px; font-weight:700; color:#e6edf3; }
.stMetricDelta { font-size:13px; }
h1,h2,h3 { color:#e6edf3; }
.section-header {
    background: linear-gradient(90deg,#1f6feb,#3fb950);
    -webkit-background-clip: text; -webkit-text-fill-color:transparent;
    font-size:22px; font-weight:700; margin-bottom:8px;
}
</style>
""", unsafe_allow_html=True)

CHART_BG = "#0d1117"
GRID_COL = "#21262d"
TEXT_COL = "#c9d1d9"
ACCENT   = "#1f6feb"
GREEN    = "#3fb950"
RED      = "#f85149"
YELLOW   = "#d29922"

PLOTLY_BASE = dict(
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
    font_color=TEXT_COL,
    xaxis=dict(gridcolor=GRID_COL, showgrid=True),
    yaxis=dict(gridcolor=GRID_COL, showgrid=True),
    margin=dict(l=40, r=20, t=40, b=40),
)


# ── Data loading (cached) ─────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading expiry day data…")
def load_data(years_tuple):
    from nifty_0dte_analysis import run_analysis
    years = list(years_tuple) if years_tuple else None
    results = run_analysis(years=years, save_excel=True)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR filters
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚙️ Filters")

all_years = list(range(2021, 2026))
sel_years = st.sidebar.multiselect("Years", all_years, default=all_years)
years_tuple = tuple(sorted(sel_years)) if sel_years else tuple(all_years)

results = load_data(years_tuple)
df      = results["raw_df"].copy()
kpis    = results["kpis"]

# Spot-only filtered df
spot = df[df["spot_open"].notna()].copy()

# Additional sidebar filters
min_range = st.sidebar.slider("Min day range %", 0.0, 3.0, 0.0, 0.05)
max_range = st.sidebar.slider("Max day range %", 0.1, 5.0, 5.0, 0.1)
spot = spot[(spot["day_range_pct"] >= min_range) & (spot["day_range_pct"] <= max_range)]

st.sidebar.markdown(f"**{len(spot)} expiry days** in filter")
st.sidebar.markdown("---")
st.sidebar.markdown("📁 Data from `icharts_download/` + `nifty_spot_data/`")


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📌 Overview",
    "📈 Intraday Pattern",
    "💸 Straddle Decay",
    "🕐 Hourly Heatmap",
    "📊 Distribution",
    "📆 Year Comparison",
    "🔍 Raw Data",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown('<div class="section-header">Expiry Day Dashboard — Overview</div>', unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Expiry Days", len(spot))
    c2.metric("% Up Days",   f"{kpis['pct_up_days']:.1f}%",
              delta=f"{kpis['pct_up_days']-50:.1f}% vs coin flip")
    c3.metric("Avg Range",   f"{kpis['avg_range_pct']:.2f}%")
    c4.metric("Median Range",f"{kpis['median_range_pct']:.2f}%")
    c5.metric("Avg OC Move", f"{kpis['avg_oc_move_pct']:.2f}%")

    if "avg_straddle_decay_pct" in kpis:
        c6,c7,c8,_,_ = st.columns(5)
        c6.metric("Avg Straddle Decay", f"{kpis['avg_straddle_decay_pct']:.1f}%")
        c7.metric("Days Straddle Decayed", f"{kpis.get('pct_straddle_decayed',0):.0f}%")
        c8.metric("Days w/ Straddle Data", kpis.get("days_with_straddle_data","N/A"))

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Direction Breakdown")
        dir_counts = spot["direction"].value_counts().reset_index()
        dir_counts.columns = ["Direction","Count"]
        fig = px.pie(dir_counts, names="Direction", values="Count",
                     color="Direction",
                     color_discrete_map={"UP": GREEN, "DOWN": RED},
                     hole=0.4)
        fig.update_layout(**PLOTLY_BASE, showlegend=True, height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Daily Range % – Rolling (30-day avg)")
        spot_sorted = spot.sort_values("date").copy()
        spot_sorted["roll_avg"] = spot_sorted["day_range_pct"].rolling(30).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=spot_sorted["date"], y=spot_sorted["day_range_pct"],
            mode="markers", marker=dict(color=ACCENT, size=4, opacity=0.5), name="Daily Range %"
        ))
        fig.add_trace(go.Scatter(
            x=spot_sorted["date"], y=spot_sorted["roll_avg"],
            mode="lines", line=dict(color=YELLOW, width=2), name="30-day avg"
        ))
        fig.update_layout(**PLOTLY_BASE, height=300,
                          legend=dict(orientation="h", yanchor="bottom", y=1))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Weekday Statistics")
    wk = results["weekday"].reset_index()
    wk.columns = [c.replace("_"," ").title() for c in wk.columns]
    st.dataframe(wk.style.format({
        "Avg Range Pct": "{:.3f}%",
        "Avg Oc Pct":    "{:.3f}%",
        "Pct Up":        "{:.1f}%",
    }), use_container_width=True, hide_index=True)

    hl = results["hl_timing"]
    st.markdown(f"""
**High/Low Timing:**  
🔺 High forms **before** Low on **{hl['pct_high_before_low']}%** of expiry days  
🔻 Low forms **before** High on **{hl['pct_low_before_high']}%** of expiry days
""")
    # High/Low by hour bar chart
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Bar(
            x=[f"{h}:00" for h in sorted(hl["high_by_hour"].keys())],
            y=[hl["high_by_hour"][h] for h in sorted(hl["high_by_hour"].keys())],
            marker_color=GREEN, name="High of Day"
        ))
        fig.update_layout(**PLOTLY_BASE, title="🔺 High-of-Day hour distribution",
                          height=280)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure(go.Bar(
            x=[f"{h}:00" for h in sorted(hl["low_by_hour"].keys())],
            y=[hl["low_by_hour"][h] for h in sorted(hl["low_by_hour"].keys())],
            marker_color=RED, name="Low of Day"
        ))
        fig.update_layout(**PLOTLY_BASE, title="🔻 Low-of-Day hour distribution",
                          height=280)
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — INTRADAY PATTERN
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown('<div class="section-header">Composite Intraday Pattern on Expiry Days</div>', unsafe_allow_html=True)
    st.caption("Average % move from open at each hour — all expiry days combined")

    path = results["intraday_path"].reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=path["time"], y=path["avg_pct_from_open"],
        mode="lines+markers",
        line=dict(color=ACCENT, width=3),
        marker=dict(size=8),
        name="Avg % from open",
    ))
    # Confidence band ±1 std
    upper = path["avg_pct_from_open"] + path["std_pct_from_open"]
    lower = path["avg_pct_from_open"] - path["std_pct_from_open"]
    fig.add_traces([
        go.Scatter(x=path["time"], y=upper, mode="lines",
                   line=dict(width=0), showlegend=False),
        go.Scatter(x=path["time"], y=lower, mode="lines",
                   line=dict(width=0), fill="tonexty",
                   fillcolor="rgba(31,111,235,0.2)", name="±1 Std Dev"),
    ])
    fig.add_hline(y=0, line_dash="dash", line_color=GRID_COL)
    fig.update_layout(**PLOTLY_BASE, height=420,
                      title="Composite Expiry Day Price Path",
                      yaxis_title="% from Open",
                      xaxis_title="Time of Day")
    st.plotly_chart(fig, use_container_width=True)

    # Split UP vs DOWN days
    spot_copy = spot.copy()
    time_cols  = ["spot_0915","spot_1000","spot_1100","spot_1200",
                  "spot_1300","spot_1400","spot_1500","spot_1529"]
    time_labels = ["09:15","10:00","11:00","12:00","13:00","14:00","15:00","15:29"]

    up_days   = spot_copy[spot_copy["direction"] == "UP"]
    dn_days   = spot_copy[spot_copy["direction"] == "DOWN"]

    fig2 = go.Figure()
    for days, col, name in [(up_days, GREEN, "UP Days"), (dn_days, RED, "DOWN Days")]:
        avgs = [days[tc].mean() for tc in time_cols]
        fig2.add_trace(go.Scatter(
            x=time_labels, y=avgs, mode="lines+markers",
            line=dict(color=col, width=2.5),
            marker=dict(size=7), name=name,
        ))
    fig2.add_hline(y=0, line_dash="dash", line_color=GRID_COL)
    fig2.update_layout(**PLOTLY_BASE, height=380,
                       title="Intraday Path — UP Days vs DOWN Days",
                       yaxis_title="% from Open", xaxis_title="Time of Day")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("##### Intraday Path Statistics Table")
    st.dataframe(path.style.format({
        "avg_pct_from_open":    "{:.3f}%",
        "median_pct_from_open": "{:.3f}%",
        "std_pct_from_open":    "{:.3f}%",
        "pct_positive":         "{:.1f}%",
        "pct_negative":         "{:.1f}%",
    }), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — STRADDLE DECAY
# ─────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown('<div class="section-header">ATM Straddle Decay Curve on Expiry Day</div>', unsafe_allow_html=True)

    decay = results["straddle_decay"].reset_index()
    strad_df = df[df["straddle_open"].notna()].copy()

    if decay.empty:
        st.warning("No straddle data found. Ensure icharts_download/ has data for the selected years.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            avg_decay = kpis.get('avg_straddle_decay_pct', 'N/A')
            st.metric("Avg Straddle Decay (Open→Close)", f"{avg_decay:.1f}%" if isinstance(avg_decay, float) else avg_decay)
        with col2:
            st.metric("Days Straddle Decayed", f"{kpis.get('pct_straddle_decayed',0):.0f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=decay["time"], y=decay["avg_pct_remaining"],
            mode="lines+markers",
            line=dict(color=YELLOW, width=3),
            marker=dict(size=8),
            name="Avg % Remaining",
        ))
        fig.add_trace(go.Scatter(
            x=decay["time"], y=decay["median_pct_remaining"],
            mode="lines+markers",
            line=dict(color=ACCENT, width=2, dash="dot"),
            marker=dict(size=6),
            name="Median % Remaining",
        ))
        fig.add_hline(y=100, line_dash="dash", line_color=GRID_COL, annotation_text="Open value")
        fig.update_layout(**PLOTLY_BASE, height=420,
                          title="ATM Straddle Value — % of Opening Price Remaining",
                          yaxis_title="% of Straddle Open Remaining",
                          xaxis_title="Time of Day")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Straddle Open vs Close Scatter")
        fig2 = px.scatter(
            strad_df, x="straddle_open", y="straddle_close",
            color="year", hover_data=["date","atm_strike","day_range_pct"],
            labels={"straddle_open":"Straddle Open (pts)","straddle_close":"Straddle Close (pts)"},
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig2.add_shape(type="line",
                       x0=strad_df["straddle_open"].min(), y0=strad_df["straddle_open"].min(),
                       x1=strad_df["straddle_open"].max(), y1=strad_df["straddle_open"].max(),
                       line=dict(color=GRID_COL, dash="dash"), name="No decay line")
        fig2.update_layout(**PLOTLY_BASE, height=400)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### Decay Stats Table")
        st.dataframe(decay, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — HOURLY RETURN HEATMAP  (Year × Time Slot)
# ─────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown('<div class="section-header">Intraday Hour-Slot Heatmap — Year vs Time Band</div>', unsafe_allow_html=True)
    st.caption(
        "Each cell = average metric for that 1-hour band across all expiry days in that year. "
        "Rows = time slots, Columns = years."
    )

    # ── Define the 6 hour slots using the :15-boundary snapshots ──────────────
    PERIOD_SLOTS = [
        ("9:15-10:15",  "spot_0915", "spot_1015"),
        ("10:15-11:15", "spot_1015", "spot_1115"),
        ("11:15-12:15", "spot_1115", "spot_1215"),
        ("12:15-13:15", "spot_1215", "spot_1315"),
        ("13:15-14:15", "spot_1315", "spot_1415"),
        ("14:15-15:15", "spot_1415", "spot_1515"),
    ]

    # ── Metric selector ────────────────────────────────────────────────────────
    hm_metric = st.radio(
        "Metric",
        ["Avg % Move (signed)", "Avg Absolute Range %", "% Positive Periods"],
        horizontal=True,
    )

    # ── Build period columns from snapshot differences ─────────────────────────
    spot_hm = spot.copy()
    pivot_rows = {}

    for label, s_col, e_col in PERIOD_SLOTS:
        if s_col not in spot_hm.columns or e_col not in spot_hm.columns:
            continue
        move = spot_hm[e_col] - spot_hm[s_col]   # % change during this slot
        spot_hm[f"__period_{label}"] = move

        if hm_metric == "Avg % Move (signed)":
            pivot_rows[label] = spot_hm.groupby("year")[f"__period_{label}"].mean()
        elif hm_metric == "Avg Absolute Range %":
            pivot_rows[label] = spot_hm.groupby("year")[f"__period_{label}"].apply(
                lambda x: x.abs().mean()
            )
        else:  # % Positive
            pivot_rows[label] = spot_hm.groupby("year")[f"__period_{label}"].apply(
                lambda x: (x > 0).mean() * 100
            )

    if not pivot_rows:
        st.warning("No :15-boundary data found. The cache may be stale — clear it with the button below and reload.")
        if st.button("Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()
    else:
        piv_hm = pd.DataFrame(pivot_rows).T.round(3)
        # Ensure year columns are sorted
        piv_hm = piv_hm.reindex(sorted(piv_hm.columns), axis=1)

        # Color scale: diverging RdBu for signed, sequential for others
        cscale = "RdBu" if hm_metric == "Avg % Move (signed)" else "RdYlGn"
        reverse = (hm_metric == "Avg % Move (signed)")  # red=negative, blue=positive
        if reverse:
            cscale = "RdBu"   # imshow uses blue=high natively, suits positive=blue

        # Annotate cells with formatted text
        suffix = "%" if hm_metric == "% Positive Periods" else "%"
        annot  = piv_hm.applymap(lambda v: f"{v:+.2f}%" if pd.notna(v) else "")

        fig_hm = px.imshow(
            piv_hm,
            color_continuous_scale=cscale,
            aspect="auto",
            text_auto=False,
            labels={"x": "Year", "y": "Time Slot", "color": hm_metric},
        )
        # Add custom text annotations manually so we can format them
        for i, row_label in enumerate(piv_hm.index):
            for j, col_label in enumerate(piv_hm.columns):
                val = piv_hm.loc[row_label, col_label]
                if pd.notna(val):
                    fig_hm.add_annotation(
                        x=j, y=i,
                        text=f"{val:+.2f}%" if hm_metric == "Avg % Move (signed)" else f"{val:.2f}%",
                        showarrow=False,
                        font=dict(size=13, color="white"),
                        xref="x", yref="y",
                    )

        fig_hm.update_layout(
            **PLOTLY_BASE,
            height=480,
            title=f"{hm_metric} — Time Slot x Year Heatmap",
        )
        fig_hm.update_xaxes(
            tickmode="array",
            tickvals=list(range(len(piv_hm.columns))),
            ticktext=[str(c) for c in piv_hm.columns],
            gridcolor=GRID_COL,
        )
        fig_hm.update_yaxes(
            tickmode="array",
            tickvals=list(range(len(piv_hm.index))),
            ticktext=list(piv_hm.index),
            gridcolor=GRID_COL,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

        st.markdown("##### Detail Table")
        fmt = "{:+.3f}%" if hm_metric == "Avg % Move (signed)" else "{:.3f}%"
        st.dataframe(
            piv_hm.style.format(fmt).background_gradient(
                cmap="RdBu" if hm_metric == "Avg % Move (signed)" else "RdYlGn",
                axis=None
            ),
            use_container_width=True,
        )

        # ── Cache stale warning if :15 columns missing ────────────────────────
        if "spot_1015" not in spot.columns:
            st.info("The cached data was built before :15-boundary columns were added. "
                    "Please clear the Streamlit cache and reload to see this heatmap.")
            if st.button("Clear Cache & Reload"):
                st.cache_data.clear()
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — DISTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown('<div class="section-header">Distribution Analysis</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Daily Range % Distribution")
        fig = px.histogram(spot, x="day_range_pct", nbins=50,
                           color_discrete_sequence=[ACCENT],
                           labels={"day_range_pct":"Day Range %"})
        fig.update_layout(**PLOTLY_BASE, height=350)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Range Buckets")
        rng = results["range_distribution"].reset_index()
        rng.columns = ["Bucket","Count","Pct %"]
        st.dataframe(rng.style.format({"Pct %":"{:.1f}%"}),
                     use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### Open-to-Close Move % Distribution")
        fig2 = px.histogram(spot, x="oc_move_pct", nbins=50,
                            color_discrete_sequence=[YELLOW],
                            labels={"oc_move_pct":"OC Move %"})
        fig2.add_vline(x=0, line_dash="dash", line_color="white")
        fig2.update_layout(**PLOTLY_BASE, height=350)
        st.plotly_chart(fig2, use_container_width=True)

        # Box plot by year
        st.markdown("##### Range % Box Plot by Year")
        fig3 = px.box(spot, x="year", y="day_range_pct",
                      color="year",
                      color_discrete_sequence=px.colors.qualitative.Bold,
                      labels={"day_range_pct":"Day Range %","year":"Year"})
        fig3.update_layout(**PLOTLY_BASE, height=300, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # Percentiles table
    st.markdown("##### Day Range % Percentiles")
    ptiles = spot["day_range_pct"].describe(percentiles=[0.1,0.25,0.5,0.75,0.9]).round(3)
    st.dataframe(ptiles.rename("Range %").to_frame().T, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — YEAR COMPARISON
# ─────────────────────────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown('<div class="section-header">Year-over-Year Comparison</div>', unsafe_allow_html=True)

    yearly = results["yearly"].reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yearly["year"],y=yearly["avg_range_pct"],
                             marker_color=ACCENT,name="Avg Range %"))
        fig.update_layout(**PLOTLY_BASE,height=320,
                          title="Avg Daily Range % by Year",
                          yaxis_title="Range %")
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=yearly["year"],y=yearly["pct_up"],
                              marker_color=[GREEN if v >= 50 else RED for v in yearly["pct_up"]],
                              name="% Up Days"))
        fig2.add_hline(y=50,line_dash="dash",line_color=GRID_COL)
        fig2.update_layout(**PLOTLY_BASE,height=320,
                           title="% Up Days by Year",
                           yaxis_title="% Up Days")
        st.plotly_chart(fig2,use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=yearly["year"],y=yearly["avg_oc_pct"],
                              marker_color=[GREEN if v>=0 else RED for v in yearly["avg_oc_pct"]],
                              name="Avg OC %"))
        fig3.add_hline(y=0,line_dash="dash",line_color=GRID_COL)
        fig3.update_layout(**PLOTLY_BASE,height=320,
                           title="Avg Open-to-Close % by Year",
                           yaxis_title="OC Move %")
        st.plotly_chart(fig3,use_container_width=True)

    with col4:
        if "avg_straddle_decay" in yearly.columns:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(x=yearly["year"],y=yearly["avg_straddle_decay"],
                                  marker_color=YELLOW,name="Avg Straddle Decay %"))
            fig4.update_layout(**PLOTLY_BASE,height=320,
                               title="Avg Straddle Decay % by Year",
                               yaxis_title="Decay %")
            st.plotly_chart(fig4,use_container_width=True)

    st.markdown("##### Year-over-Year Full Table")
    yearly_disp = yearly.copy()
    yearly_disp.columns = [c.replace("_"," ").title() for c in yearly_disp.columns]
    st.dataframe(yearly_disp.style.format(precision=2), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — RAW DATA
# ─────────────────────────────────────────────────────────────────────────────
with tabs[6]:
    st.markdown('<div class="section-header">Raw Expiry Day Data</div>', unsafe_allow_html=True)

    display_cols = ["date","year","month_name","weekday","atm_strike",
                    "spot_open","spot_close","spot_high","spot_low",
                    "day_range_pts","day_range_pct","oc_move_pct","direction",
                    "straddle_open","straddle_close","straddle_decay_pts","straddle_decay_pct",
                    "high_time","low_time"]
    display_cols = [c for c in display_cols if c in spot.columns]

    search = st.text_input("🔍 Search date (YYYY-MM-DD)")
    view = spot[display_cols].copy()
    if search:
        view = view[view["date"].astype(str).str.contains(search)]

    st.dataframe(
        view.sort_values("date", ascending=False).style.applymap(
            lambda v: "color:#3fb950" if v == "UP" else ("color:#f85149" if v == "DOWN" else ""),
            subset=["direction"] if "direction" in view.columns else []
        ).format({
            "day_range_pct":      "{:.3f}%",
            "oc_move_pct":        "{:.3f}%",
            "straddle_decay_pct": "{:.2f}%",
        }),
        use_container_width=True,
        height=600,
    )

    csv = view.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download as CSV", csv,
                       "nifty_0dte_expiry_data.csv", "text/csv")

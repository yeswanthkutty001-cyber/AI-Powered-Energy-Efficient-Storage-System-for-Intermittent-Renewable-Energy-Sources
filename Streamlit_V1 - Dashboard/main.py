import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import streamlit.components.v1 as components

# ======================================================
# PAGE CONFIG
# ======================================================
from Background import BackgroundCSSGenerator
st.set_page_config(
    page_title="Teacher Performance Tracker",
    page_icon="📊",  # You can replace this with an emoji or a URL to an image
    layout="wide"
)
img1_path = r"200w.gif"

background_generator = BackgroundCSSGenerator(img1_path)
page_bg_img = background_generator.generate_background_css()
st.markdown(page_bg_img, unsafe_allow_html=True)
# Dummy user credentials
st.markdown("""
<style>
.metric-card {
    padding: 12px;
    border-radius: 14px;
    background: rgba(240,240,240,0.5);
}
.control-box {
    padding: 16px;
    border-radius: 16px;
    background: linear-gradient(145deg, #f7f9fc, #eef1f6);
}
</style>
""", unsafe_allow_html=True)

np.random.seed(42)

BATTERY_ID = "BAT-AADHAAR-IND-00042"
N_CELLS_SERIES = 3

# ======================================================
# SOC / SOH ESTIMATION
# ======================================================

def calculate_soc(voltage, v_min=3.0, v_max=4.2):
    soc = (voltage - v_min) / (v_max - v_min) * 100
    return float(np.clip(soc, 0, 100))


def calculate_soh(voltage, avg_voltage, temperature):
    delta_t = max(0, temperature - 25)
    delta_v = abs(voltage - avg_voltage)
    soh = 100 - (0.3 * delta_t) - (80 * delta_v)
    return float(np.clip(soh, 80, 100))


def classify_severity(fault):
    if fault["THERMAL"]:
        return "CRITICAL"
    if fault["OV"] or fault["UV"]:
        return "WARNING"
    return "NORMAL"

def auto_refresh(seconds=1):
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()

    if time.time() - st.session_state.last_refresh > seconds:
        st.session_state.last_refresh = time.time()
        st.rerun()


# ======================================================
# MOCK BMS DATA
# ======================================================

def generate_cell_data():
    cells = []
    series_voltages = np.random.normal(3.80, 0.02, N_CELLS_SERIES)
    temperature = np.random.normal(39.5, 1.0)
    avg_voltage = np.mean(series_voltages)

    for i, v in enumerate(series_voltages):
        soc = calculate_soc(v)
        soh = calculate_soh(v, avg_voltage, temperature)

        fault = {
            "OV": v > 4.2,
            "UV": v < 3.0,
            "THERMAL": temperature > 45
        }

        cells.append({
            "series_id": f"S{i+1}",
            "voltage": round(v, 3),
            "temperature": round(temperature, 1),
            "SOC": round(soc, 1),
            "SOH": round(soh, 1),
            "hotspot_prob": round(np.clip((temperature - 30) * 3, 0, 100), 1),
            "fault": fault,
            "severity": classify_severity(fault)
        })

    return cells


def generate_timeseries(days=3):
    time_index = pd.date_range(
        datetime.now() - timedelta(days=days),
        periods=days * 24,
        freq="H"
    )

    voltage = np.linspace(3.95, 3.70, len(time_index)) + np.random.normal(0, 0.02, len(time_index))
    temperature = np.random.normal(39, 1.5, len(time_index))

    soc = [calculate_soc(v) for v in voltage]
    avg_v = np.mean(voltage)
    soh = [calculate_soh(v, avg_v, t) for v, t in zip(voltage, temperature)]

    return pd.DataFrame({
        "time": time_index,
        "voltage": voltage,
        "temperature": temperature,
        "SOC": soc,
        "SOH": soh
    })

# ======================================================
# SENSOR + GRID LOGIC (PHYSICALLY CONSISTENT)
# ======================================================

def mock_sensor_data():
    return {
        "S1": np.random.normal(38, 1),
        "S2": np.random.normal(39, 1),
        "S3": np.random.normal(40, 1),
        "S4": np.random.normal(39.5, 1)
    }


def mock_cell_grid_from_sensors(sensors):
    """
    Generate 3x3 grid from sensor values
    Force ONE cell to be a hotspot (demo purpose)
    """
    base = list(sensors.values())
    grid = []

    for i in range(3):
        row = []
        for j in range(3):
            temp = np.random.normal(base[i % len(base)], 0.6)
            row.append({
                "state": "O",
                "temp": round(temp, 1)
            })
        grid.append(row)

    # 🔴 FORCE ONE CELL TO BE HOT (example: middle cell)
    grid[1][1]["state"] = "X"
    grid[1][1]["temp"] = 45.8   # clearly above threshold

    return grid


def render_cell_grid(grid):
    html = "<table style='border-collapse: collapse; margin:auto;'>"
    for row in grid:
        html += "<tr>"
        for cell in row:
            color = "#2ecc71" if cell["state"] == "O" else "#e74c3c"
            html += f"""
            <td style="
                width:70px;
                height:70px;
                text-align:center;
                border:2px solid black;
                background:{color};
                color:white;
                font-size:16px;
                font-weight:bold;">
                {cell['state']}<br>{cell['temp']}°C
            </td>
            """
        html += "</tr>"
    html += "</table>"
    return html

# ======================================================
# GLOBAL STATE
# ======================================================

cells = generate_cell_data()
ts_data = generate_timeseries()

pack_soc = round(np.mean([c["SOC"] for c in cells]), 1)
pack_soh = round(min([c["SOH"] for c in cells]), 1)
pack_temp = round(np.mean([c["temperature"] for c in cells]), 1)

critical_cells = [c for c in cells if c["severity"] == "CRITICAL"]
warning_cells = [c for c in cells if c["severity"] == "WARNING"]

# ======================================================
# HEADER
# ======================================================

st.title("🔋 AI-Powered Energy-Efficient Storage System")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Battery Aadhaar", BATTERY_ID)
c2.metric("SOC (%)", pack_soc)
c3.metric("SOH (%)", pack_soh)

system_state = "NORMAL"
if critical_cells:
    system_state = "CRITICAL"
elif warning_cells:
    system_state = "WARNING"

c4.metric("System Status", system_state)

# ======================================================
# TABS
# ======================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Cell Safety",
    "📉 Degradation & AI",
    "🧬 Digital Twin",
    "⚡ Grid Dispatch"
])

# ======================================================
# TAB 1 — LIVE THERMAL MATRIX
# ======================================================
with tab1:
    st.subheader("🔍 Live Thermal Safety Monitoring (Cell Matrix View)")

    # ---- Sensor placeholders ----
    cols = st.columns(4)
    s1 = cols[0].empty()
    s2 = cols[1].empty()
    s3 = cols[2].empty()
    s4 = cols[3].empty()

    sensors = mock_sensor_data()
    grid = mock_cell_grid_from_sensors(sensors)

    s1.metric("🌡️ Sensor 1", f"{sensors['S1']:.2f} °C")
    s2.metric("🌡️ Sensor 2", f"{sensors['S2']:.2f} °C")
    s3.metric("🌡️ Sensor 3", f"{sensors['S3']:.2f} °C")
    s4.metric("🌡️ Sensor 4", f"{sensors['S4']:.2f} °C")

    st.divider()

    # ---- HTML GRID (correct rendering) ----
    components.html(render_cell_grid(grid), height=260)

    hot_cells = sum(cell["state"] == "X" for row in grid for cell in row)

    if hot_cells >= 2:
        st.error("🔥 Multiple hotspots detected — protection recommended")
    elif hot_cells == 1:
        st.warning("⚠️ Localized hotspot detected")
    else:
        st.success("All cells operating within safe thermal limits")

    st.caption(
        "Grid shows inferred parallel-cell temperatures using copper busbar thermal gradients."
    )

    # ---- Auto refresh (version-safe) ----
    auto_refresh(seconds=1)

# ======================================================
# TAB 2 — DEGRADATION
# ======================================================

with tab2:
    st.subheader("📉 Degradation, RUL & Grid-Aware Analytics")

    st.markdown(
        "This section provides advanced degradation analytics, remaining useful life (RUL) prediction, "
        "and the impact of grid operating stress on battery health."
    )

    # =====================================================
    # CONSTANTS (INDUSTRY REFERENCES)
    # =====================================================
    V_MIN, V_MAX = 3.0, 4.2
    T_MAX = 45
    SOH_EOL = 80          # End of Life threshold
    NOMINAL_CYCLES = 2000 # Typical Li-ion cycle life

    # =====================================================
    # BASIC TREND CHARTS (WITH LIMITS)
    # =====================================================
    fig_v = px.line(ts_data, x="time", y="voltage",
                    title="🔌 Cell Voltage Trend with Safe Operating Window")
    fig_v.add_hrect(y0=V_MIN, y1=V_MAX,
                    fillcolor="green", opacity=0.12, line_width=0)

    fig_t = px.line(ts_data, x="time", y="temperature",
                    title="🌡️ Thermal Profile & Risk Zone")
    fig_t.add_hrect(y0=T_MAX, y1=60,
                    fillcolor="red", opacity=0.15, line_width=0)

    fig_soc = px.line(ts_data, x="time", y="SOC",
                      title="🔋 State of Charge (SOC) Trend")

    fig_soh = px.line(ts_data, x="time", y="SOH",
                      title="🧬 SOH Degradation Trend")
    fig_soh.add_hline(y=SOH_EOL, line_dash="dash",
                      line_color="red",
                      annotation_text="End of Life (80%)")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_v, use_container_width=True)
    with col2:
        st.plotly_chart(fig_t, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(fig_soc, use_container_width=True)
    with col4:
        st.plotly_chart(fig_soh, use_container_width=True)

    st.divider()

    # =====================================================
    # 📊 CYCLE COUNT vs SOH (KEY INDUSTRY GRAPH)
    # =====================================================
    st.markdown("### 📊 Cycle Count vs State of Health (SOH)")

    cycles = np.linspace(0, NOMINAL_CYCLES, 50)
    soh_curve = 100 - (cycles / NOMINAL_CYCLES) * (100 - SOH_EOL)

    df_cycles = pd.DataFrame({
        "Cycle Count": cycles,
        "SOH (%)": soh_curve
    })

    fig_cycles = px.line(
        df_cycles,
        x="Cycle Count",
        y="SOH (%)",
        title="Battery Aging Curve (Cycle Life Model)"
    )

    fig_cycles.add_hline(
        y=SOH_EOL,
        line_dash="dash",
        line_color="red",
        annotation_text="End of Life"
    )

    st.plotly_chart(fig_cycles, use_container_width=True)

    st.caption(
        "SOH degradation modeled using a standard linear cycle-life approximation for Li-ion cells."
    )

    st.divider()

    # =====================================================
    # 🔮 REMAINING USEFUL LIFE (RUL) PREDICTION
    # =====================================================
    st.markdown("### 🔮 Remaining Useful Life (RUL) Prediction")

    current_soh = pack_soh
    used_fraction = (100 - current_soh) / (100 - SOH_EOL)
    estimated_cycles_used = used_fraction * NOMINAL_CYCLES
    remaining_cycles = max(NOMINAL_CYCLES - estimated_cycles_used, 0)

    st.metric(
        label="Estimated Remaining Cycles",
        value=f"{int(remaining_cycles)} cycles"
    )

    st.progress(min(estimated_cycles_used / NOMINAL_CYCLES, 1.0))

    st.caption(
        "RUL estimated using SOH-based degradation trajectory relative to end-of-life threshold."
    )

    st.divider()

    # =====================================================
    # ⚡ GRID-AWARE DEGRADATION ANALYTICS
    # =====================================================
    st.markdown("### ⚡ Grid-Aware Degradation Analytics")

    # Simulated grid stress factor
    grid_stress = np.random.choice(["Low", "Medium", "High"], p=[0.4, 0.4, 0.2])

    stress_factor = {
        "Low": 0.8,
        "Medium": 1.0,
        "High": 1.3
    }[grid_stress]

    adjusted_rul = remaining_cycles / stress_factor

    st.write({
        "Grid Stress Level": grid_stress,
        "Stress Multiplier": stress_factor,
        "Adjusted Remaining Cycles": int(adjusted_rul)
    })

    fig_grid = px.bar(
        pd.DataFrame({
            "Scenario": ["Normal Usage", "Grid-Stressed Usage"],
            "Remaining Cycles": [remaining_cycles, adjusted_rul]
        }),
        x="Scenario",
        y="Remaining Cycles",
        title="Impact of Grid Stress on Battery Lifetime"
    )

    st.plotly_chart(fig_grid, use_container_width=True)

    st.divider()

    # =====================================================
    # 🧠 AI INTERPRETATION (FINAL WOW)
    # =====================================================
    st.markdown("### 🧠 AI Health Interpretation")

    if grid_stress == "High" and current_soh < 85:
        st.error(
            "🔥 High grid stress combined with reduced SOH detected. "
            "Battery lifetime is significantly impacted. Load derating or grid-support reduction is advised."
        )
    elif grid_stress == "High":
        st.warning(
            "⚠️ High grid stress detected. Long-term operation under these conditions "
            "may accelerate degradation."
        )
    else:
        st.success(
            "✅ Battery operating within acceptable health and grid stress limits. "
            "No immediate degradation risk identified."
        )

# ======================================================
# TAB 3 — DIGITAL TWIN
# ======================================================

with tab3:
    st.subheader("🧬 Battery Digital Twin")

    st.caption(
        "A real-time virtual representation of the physical battery asset, "
        "combining identity, health, risk, and lifecycle intelligence."
    )

    st.divider()

    # =====================================================
    # 🔹 TOP: BATTERY IDENTITY (EXECUTIVE CARD)
    # =====================================================
    st.markdown("### 🔐 Battery Aadhaar")

    id_col1, id_col2, id_col3 = st.columns([2, 1, 1])

    with id_col1:
        st.markdown(f"""
        **Battery ID**  
        `{BATTERY_ID}`  

        **Chemistry**  
        Li-ion (NMC 18650)  

        **Configuration**  
        3s3p • 18 Ah • 216 Wh
        """)

    with id_col2:
        st.metric("Manufactured", "Jan 2026")
        st.metric("Batch", "NMC-IND-24A")

    with id_col3:
        st.metric("Warranty", "5 Years")
        st.metric("Asset Status", "Active 🟢")

    st.divider()

    # =====================================================
    # 🔹 LIVE HEALTH GAUGES (VERY IMPORTANT)
    # =====================================================
    st.markdown("### ⚙️ Live Health Overview")

    h1, h2, h3, h4 = st.columns(4)

    h1.metric("SOC", f"{pack_soc} %")
    h2.metric("SOH", f"{pack_soh} %")
    h3.metric("Avg Temperature", f"{pack_temp} °C")
    h4.metric("Thermal Margin", f"{round(45 - pack_temp, 1)} °C")

    st.divider()

    # =====================================================
    # 🔹 RISK INTELLIGENCE (THIS IS ENTERPRISE LEVEL)
    # =====================================================
    st.markdown("### ⚠️ Battery Risk Intelligence")

    thermal_risk = np.clip((pack_temp - 30) * 3, 0, 100)
    aging_risk = np.clip((100 - pack_soh) * 1.2, 0, 100)
    soc_risk = np.clip(abs(pack_soc - 50) * 0.6, 0, 100)

    overall_risk = int(
        0.45 * thermal_risk +
        0.40 * aging_risk +
        0.15 * soc_risk
    )

    r1, r2 = st.columns([3, 2])

    with r1:
        st.markdown("**Overall Battery Risk Index**")
        st.progress(overall_risk / 100)

        if overall_risk > 70:
            st.error("High Risk — Immediate action required")
        elif overall_risk > 40:
            st.warning("Moderate Risk — Monitor closely")
        else:
            st.success("Low Risk — Normal operation")

    with r2:
        st.markdown("**Risk Breakdown**")
        st.write("🔥 Thermal Stress")
        st.progress(thermal_risk / 100)
        st.write("🧬 Aging Stress")
        st.progress(aging_risk / 100)
        st.write("⚡ SOC Stress")
        st.progress(soc_risk / 100)

    st.divider()

    # =====================================================
    # 🔹 LIFECYCLE TIMELINE (STORYTELLING)
    # =====================================================
    st.markdown("### 🕒 Lifecycle Timeline")

    timeline = [
        ("Jan 2026", "Commissioned into service"),
        ("Mar 2026", "Stable operation phase"),
        ("Jun 2026", "Minor voltage imbalance corrected"),
        ("Aug 2026", "Thermal peak event recorded"),
        ("Oct 2026", "AI health model recalibrated"),
        ("Future", "Predicted mid-life phase"),
        ("EOL", "End of Life at SOH = 80%")
    ]

    for t, e in timeline:
        st.markdown(f"**{t}** — {e}")

    st.divider()

    # =====================================================
    # 🔹 DIGITAL TWIN ADVISORY (CEO-LEVEL)
    # =====================================================
    st.markdown("### 🧠 Digital Twin Advisory")

    if overall_risk > 70:
        st.error(
            "🚨 Battery health risk is high. "
            "Recommended actions: derate power output, limit grid support, "
            "schedule thermal inspection."
        )
    elif overall_risk > 40:
        st.warning(
            "⚠️ Battery operating under moderate stress. "
            "Continue operation with enhanced monitoring."
        )
    else:
        st.success(
            "✅ Battery operating in optimal conditions. "
            "Approved for full grid participation and charge–discharge cycles."
        )

    st.caption(
        "The Digital Twin continuously synchronizes physical data with predictive models "
        "to enable safe, reliable, and scalable energy storage operations."
    )


# ======================================================
# TAB 4 — GRID DISPATCH
# ======================================================
with tab4:
    st.subheader("⚡ Energy Orchestration Control Console")

    st.caption(
        "Real-time decision engine balancing battery longevity, renewable priority, "
        "grid economics, and carbon impact."
    )

    # ===============================
    # SYSTEM CONTEXT
    # ===============================
    solar_available = np.random.choice([True, False], p=[0.6, 0.4])
    grid_price_signal = np.random.choice(["Low", "Medium", "High"], p=[0.4, 0.4, 0.2])
    load_demand_kw = round(np.random.uniform(1.8, 3.2), 2)
    grid_carbon_intensity = np.random.choice(["Low", "Medium", "High"], p=[0.3, 0.5, 0.2])

    st.markdown("### 🌐 System Context")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Load Demand", f"{load_demand_kw} kW")
    c2.metric("Solar", "Available ☀️" if solar_available else "Unavailable")
    c3.metric("Grid Price", grid_price_signal)
    c4.metric("Grid Carbon", grid_carbon_intensity)

    st.divider()

    # ===============================
    # DISPATCH SCORING
    # ===============================
    battery_score = (
        0.5 * (pack_soh / 100) +
        0.3 * (1 - max(pack_temp - 30, 0) / 20) +
        0.2 * (pack_soc / 100)
    )

    solar_score = 1.0 if solar_available else 0.0

    grid_score = {
        "Low": 0.9,
        "Medium": 0.6,
        "High": 0.3
    }[grid_price_signal]

    scores = {
        "Solar": solar_score,
        "Battery": battery_score,
        "Grid": grid_score
    }

    total = sum(scores.values()) + 1e-6
    contributions = {k: round(v / total * 100, 1) for k, v in scores.items()}

    # ===============================
    # DISPATCH DECISION
    # ===============================
    st.markdown("### 🧠 Dispatch Decision")

    if pack_temp > 42 or pack_soh < 85:
        st.error("Battery Protection Mode")
        rationale = "Thermal or aging risk detected → battery usage limited"
    elif solar_available:
        st.success("Renewable Priority Mode")
        rationale = "Solar prioritized to reduce degradation and emissions"
    else:
        st.warning("Grid Support Mode")
        rationale = "Battery + grid supporting load"

    st.info(f"**Decision Rationale:** {rationale}")

    st.divider()

    # ===============================
    # ENERGY FLOW (VISUAL RAILS)
    # ===============================
    st.markdown("### 🔄 Energy Flow Allocation")

    for src, pct in contributions.items():
        icon = "☀️" if src == "Solar" else "🔋" if src == "Battery" else "⚡"
        st.markdown(f"**{icon} {src}**")
        st.progress(pct / 100)
        st.caption(f"{pct}% contribution")

    st.divider()

    # ===============================
    # CARBON & LIFETIME AWARENESS
    # ===============================
    st.markdown("### 🌱 Sustainability & Lifetime Impact")

    if grid_carbon_intensity == "High" and solar_available:
        st.success("Low-carbon dispatch achieved using renewables")
    elif grid_carbon_intensity == "High":
        st.warning("High-carbon grid detected → consider load shifting")
    else:
        st.success("Carbon impact within acceptable limits")

    if pack_soh < 90:
        st.warning("Battery aging considered → conservative dispatch applied")

    st.divider()

    # ===============================
    # OPERATOR READINESS
    # ===============================
    st.markdown("### 🧑‍✈️ Operator Readiness")

    st.checkbox("Enable Manual Override", value=False)
    st.caption(
        "System is designed for autonomous operation but allows "
        "human-in-the-loop control when required."
    )
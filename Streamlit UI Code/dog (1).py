import streamlit as st
import serial
import time

# --- Serial Setup ---
ser = serial.Serial('COM9', 9600, timeout=1)
time.sleep(2)

# --- Page Setup ---
st.set_page_config(page_title="🔥 Real-time Temperature Grid", layout="centered")
st.title("🔥 Real-time Temperature Grid (3x3)")
st.markdown("Monitor **4 sensors** mapped into a 3×3 fault detection grid.")

# --- Sensor placeholders ---
col1, col2 = st.columns(2)
with col1:
    s1_placeholder = st.empty()
    s2_placeholder = st.empty()
with col2:
    s3_placeholder = st.empty()
    s4_placeholder = st.empty()

# --- Grid placeholder ---
st.subheader("🟩 Fault Detection Grid (O = Normal, X = Fault)")
grid_placeholder = st.empty()

# --- Parsing Functions ---
def parse_temperatures(line: str):
    """Parse sensor line like 'S1:25.30 S2:30.50 S3:28.90 S4:40.10'"""
    try:
        parts = line.strip().split()
        values = {}
        for p in parts:
            if ":" in p:
                k, v = p.split(":")
                values[k] = float(v)
        return values if len(values) == 4 else None
    except:
        return None

def parse_grid(line: str):
    """Parse grid line like 'GRID:O,O,X;O,O,O;X,O,X'"""
    try:
        grid_str = line.split("GRID:")[-1]
        rows = grid_str.split(";")
        return [r.split(",") for r in rows]
    except:
        return None

# --- Main Loop ---
while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode("utf-8", errors="ignore").strip()

        # Handle sensor values
        if line.startswith("S1:"):
            vals = parse_temperatures(line)
            if vals:
                s1_placeholder.metric("🌡️ Sensor 1", f"{vals['S1']:.2f} °C")
                s2_placeholder.metric("🌡️ Sensor 2", f"{vals['S2']:.2f} °C")
                s3_placeholder.metric("🌡️ Sensor 3", f"{vals['S3']:.2f} °C")
                s4_placeholder.metric("🌡️ Sensor 4", f"{vals['S4']:.2f} °C")

        # Handle grid
        elif line.startswith("GRID:"):
            grid = parse_grid(line)
            if grid:
                grid_html = "<table style='border-collapse: collapse; margin:auto;'>"
                for r in grid:
                    grid_html += "<tr>"
                    for c in r:
                        color = "#2ecc71" if c == "O" else "#e74c3c"
                        grid_html += f"<td style='width:60px;height:60px;text-align:center;border:2px solid black;background:{color};color:white;font-size:20px;font-weight:bold;'>{c}</td>"
                    grid_html += "</tr>"
                grid_html += "</table>"

                grid_placeholder.markdown(grid_html, unsafe_allow_html=True)

    time.sleep(0.2)

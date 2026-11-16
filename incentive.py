import streamlit as st
import pandas as pd
import math

# --- 1. APP CONFIG & A5 PRINT CSS ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")

st.markdown("""
<style>
@media print {
    @page {
        size: A5;
        margin: 6mm;
    }
    /* Hide sidebar, buttons, and input editors when printing */
    section[data-testid="stSidebar"],
    .stButton,
    div[data-testid="stDataEditor"],
    .no-print {
        display: none !important;
    }
    /* Compact single A5 page sizing */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        max-width: 100% !important;
    }
    body {
        font-size: 8px !important;
        color: #000 !important;
    }
    table {
        font-size: 7px !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("👤 Single Operator Multi-Mold Productivity & Bonus Calculator")

# --- 2. SIDEBAR: ALLOWANCES & PARAMETERS ---
with st.sidebar:
    st.header("⚙️ Industrial Engineering Factors")
    fatigue_pct = st.number_input("Fatigue Allowance (%)", value=8.0, step=0.5)
    personal_pct = st.number_input("Personal Needs Allowance (%)", value=6.0, step=0.5)
    total_allowance_pct = fatigue_pct + personal_pct
    total_allowance_decimal = total_allowance_pct / 100.0
    st.caption(f"Total F&P Allowance Deduction: **{total_allowance_pct:.1f}%**")
    
    st.divider()
    st.header("🚶 Physical Constraints")
    walk_time = st.number_input("Walk/Transition Time per Mold Station (s)", value=3.0, step=0.5)
    parts_per_cycle = st.number_input("Parts Produced per Cycle/Mold", value=2, step=1)
    shift_hours = st.number_input("Shift Duration (Hours)", value=8.0, step=0.5)

# --- 3. MOLD / MATERIAL DATA INPUTS ---
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.subheader("📦 Operator Mold Assignment Data")
st.info("First rows can be set as **Empty / Balance Molds** (active for walking circuit and transition time, but zero production).")
st.markdown('</div>', unsafe_allow_html=True)

default_molds = [
    {'id': 'Empty Station / Buffer 1', 'units': 1, 'p': 0, 'is_empty': True},
    {'id': 'Mold Type A', 'units': 2, 'p': 180, 'l': 12, 'is_empty': False},
    {'id': 'Mold Type B', 'units': 1, 'p': 240, 'l': 15, 'is_empty': False},
]
for i in range(ord('C'), ord('R')):
    default_molds.append({'id': f'Mold Type {chr(i)}', 'units': 0, 'p': 0, 'l': 0, 'is_empty': False})

edited_molds = st.data_editor(
    default_molds,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "id": st.column_config.TextColumn("Station / Mold ID", required=True),
        "units": st.column_config.NumberColumn("Number of Units", min_value=0, step=1, format="%d"),
        "p": st.column_config.NumberColumn("Press / Cure Time (s)", min_value=0.0, step=1.0),
        "l": st.column_config.NumberColumn("Load / Service Time (s)", min_value=0.0, step=1.0),
        "is_empty": st.column_config.CheckboxColumn("Empty Mold (Walk-only)", default=False)
    }
)

# Unpack active molds and stations
all_circuit_stations = []
active_mold_summary = []

for m in edited_molds:
    try:
        qty = int(m.get('units', 0) or 0)
        press_time = float(m.get('p', 0) or 0)
        load_time = float(m.get('l', 0) or 0)
        mold_name = str(m.get('id', 'Unknown'))
        is_empty = bool(m.get('is_empty', False))
        
        if qty > 0:
            if is_empty:
                # Empty molds contribute to walking circuit time and station count, but have 0 load/press
                active_mold_summary.append({
                    'Mold Type': f"{mold_name} [EMPTY]",
                    'Units': qty,
                    'Press (s)': 0,
                    'Load (s)': 0,
                    'Min Cycle (s)': 0
                })
                for i in range(qty):
                    all_circuit_stations.append({
                        'id': f"{mold_name} (#{i+1} [EMPTY])",
                        'p': 0,
                        'l': 0,
                        'is_empty': True
                    })
            elif press_time > 0:
                active_mold_summary.append({
                    'Mold Type': mold_name,
                    'Units': qty,
                    'Press (s)': press_time,
                    'Load (s)': load_time,
                    'Min Cycle (s)': press_time + load_time
                })
                for i in range(qty):
                    all_circuit_stations.append({
                        'id': f"{mold_name} (#{i+1})",
                        'p': press_time,
                        'l': load_time,
                        'is_empty': False
                    })
    except Exception:
        continue

# --- 4. EXECUTION BUTTON ---
run_calc = st.button('🚀 Calculate Operator Productivity & Incentive KPIs')

if run_calc:
    if not all_circuit_stations:
        st.error("⚠️ **No valid stations found!** Please ensure at least one station/mold has units > 0.")
    else:
        try:
            num_stations = len(all_circuit_stations)
            
            total_walking_in_circuit = num_stations * walk_time
            total_loading_in_circuit = sum(m['l'] for m in all_circuit_stations)
            net_active_work = total_walking_in_circuit + total_loading_in_circuit
            
            max_machine_constraint = max([m['p'] + m['l'] for m in all_circuit_stations]) if all_circuit_stations else 0
            base_circuit_time = max(net_active_work, max_machine_constraint)
            operator_active_utilization = (net_active_work / base_circuit_time) * 100 if base_circuit_time > 0 else 0
            
            total_raw_baseline_hourly_output = 0
            total_absolute_max_hourly_output = 0
            
            for m in all_circuit_stations:
                if m['is_empty']:
                    continue
                machine_min_cycle = m['p'] + m['l']
                max_mold_hourly_out = (3600 / machine_min_cycle) * parts_per_cycle if machine_min_cycle > 0 else 0
                total_absolute_max_hourly_output += max_mold_hourly_out
                
                if base_circuit_time > 0:
                    circuits_needed = math.ceil(machine_min_cycle / base_circuit_time)
                    actual_visit_interval = circuits_needed * base_circuit_time
                else:
                    actual_visit_interval = machine_min_cycle
                
                mold_baseline_hourly_out = (3600 / actual_visit_interval) * parts_per_cycle if actual_visit

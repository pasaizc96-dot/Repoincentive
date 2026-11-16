import streamlit as st
import pandas as pd
import math

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")
st.title("👤 Single Operator Multi-Mold Productivity & Bonus Calculator")

# --- 2. SIDEBAR: ALLOWANCES & PARAMETERS ---
with st.sidebar:
    st.header("⚙️ Industrial Engineering Factors")
    
    # Allowances
    fatigue_pct = st.number_input("Fatigue Allowance (%)", value=8.0, step=0.5)
    personal_pct = st.number_input("Personal Needs Allowance (%)", value=6.0, step=0.5)
    total_allowance_multiplier = 1.0 + ((fatigue_pct + personal_pct) / 100.0)
    st.caption(f"Total F&P Allowance Multiplier: **{total_allowance_multiplier:.3f}x**")
    
    st.divider()
    st.header("🚶 Physical Constraints")
    walk_time = st.number_input("Walk/Transition Time per Mold Station (s)", value=3.0, step=0.5)
    parts_per_cycle = st.number_input("Parts Produced per Cycle/Mold", value=2, step=1)
    shift_hours = st.number_input("Shift Duration (Hours)", value=8.0, step=0.5)

# --- 3. MOLD / MATERIAL DATA INPUTS ---
st.subheader("📦 Operator Mold Assignment Data")
st.info("Enter your mold types, the **number of units** active for each type, and their Press (P) and Load (L) times.")

default_molds = [
    {'id': 'Mold Type A', 'units': 2, 'p': 180, 'l': 12},
    {'id': 'Mold Type B', 'units': 1, 'p': 240, 'l': 15},
    {'id': 'Mold Type C', 'units': 0, 'p': 300, 'l': 20},
    {'id': 'Mold Type D', 'units': 0, 'p': 0, 'l': 0},
    {'id': 'Mold Type E', 'units': 0, 'p': 0, 'l': 0},
]

edited_molds = st.data_editor(
    default_molds,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": "Mold ID / Type",
        "units": "Number of Units",
        "p": "Press / Cure Time (s)",
        "l": "Load / Service Time (s)"
    }
)

# Unpack multiple units into individual stations for circuit simulation
active_molds = []
for m in edited_molds:
    qty = int(m.get('units', 0))
    press_time = m.get('p', 0)
    if qty > 0 and press_time > 0:
        for i in range(qty):
            active_molds.append({
                'id': f"{m['id']} (#{i+1})",
                'base_id': m['id'],
                'p': press_time,
                'l': m.get('l', 0)
            })

# --- 4. CORE CALCULATIONS ---
if st.button("🚀 Calculate Operator Productivity & Incentive KPIs"):
    if not active_molds:
        st.warning("Please add at least one mold with units > 0 and a valid Press time.")
    else:
        num_molds = len(active_molds)
        
        # 1. Active work per complete operator circuit (visiting every individual mold station once)
        total_walking_in_circuit = num_molds * walk_time
        total_loading_in_circuit = sum(m['l'] for m in active_molds)
        net_active_work = total_walking_in_circuit + total_loading_in_circuit
        
        # 2. Maximum machine constraint in the circuit
        max_machine_constraint = max([m['p'] + m['l'] for m in active_molds])
        
        # Operator baseline cycle time for the circuit (pacing)
        base_circuit_time = max(net_active_work, max_machine_constraint)
        
        # Apply F&P Allowances to total operator time required per circuit
        adjusted_circuit_time = base_circuit_time * total_allowance_multiplier
        
        # 3. Output Calculations per mold station within the adjusted circuit framework
        mold_breakdown = []
        total_hourly_output = 0
        
        for m in active_molds:
            machine_min_cycle = m['p'] + m['l']
            # How many circuits must pass before this specific mold station is serviced again?
            circuits_needed = math.ceil(machine_min_cycle / adjusted_circuit_time)
            actual_visit_interval = circuits_needed * adjusted_circuit_time
            
            # Hourly output for this mold station
            mold_hourly_out = (3600 / actual_visit_interval) * parts_per_cycle
            total_hourly_output += mold_hourly_out
            
            # Machine utilization percentage
            m_util = (machine_min_cycle / actual_visit_interval) * 100
            
            mold_breakdown.append({
                'Station ID': m['id'],
                'Press Time (s)': m['p'],
                'Load Time (s)': m['l'],
                'Circuits per Visit': circuits_needed,
                'Visit Interval (s)': round(actual_visit_interval, 1),
                'Machine Utilization (%)': round(m_util, 1),
                'Output (Parts/Hr)': round(mold_hourly_out, 1)
            })
            
        # Operator Utilization (How busy the operator is including allowances vs total time)
        operator_utilization = (net_active_work / adjusted_circuit_time) * 100

        # --- 5. RESULTS DISPLAY ---
        st.success("Calculations Complete!")
        
        # Top-level KPI Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Output (Parts/Hour)", f"{total_hourly_output:.1f}")
        col2.metric("Shift Output ({0} hrs)".format(int(shift_hours)), f"{total_hourly_output * shift_hours:,.0f} Parts")
        col3.metric("Operator Workload / Util", f"{operator_utilization:.1f}%", help="Includes F&P allowances")
        col4.metric("Circuit Cycle Time", f"{adjusted_circuit_time:.1f} s")

        st.divider()

        # --- 6. BONUS TIER KPIS (110%, 120%, 130%, 140%) ---
        st.subheader("🎯 Incentive Bonus Target Thresholds")
        st.caption("Target output brackets required for operator incentive pay tiers based on baseline standard performance.")

        tier_cols = st.columns(4)
        tiers = [
            ("110% Tier", 1.10),
            ("120% Tier", 1.20),
            ("130% Tier", 1.30),
            ("140% Tier", 1.40)
        ]

        for i, (tier_name, multiplier) in enumerate(tiers):
            tier_hourly = total_hourly_output * multiplier
            tier_shift = tier_hourly * shift_hours
            with tier_cols[i]:
                st.metric(
                    label=tier_name,
                    value=f"{tier_hourly:.1f} PPH",
                    delta=f"{tier_shift:,.0f} parts/shift"
                )

        st.divider()

        # --- 7. DETAILED MOLD BREAKDOWN TABLE ---
        st.subheader("📋 Individual Mold Station Performance Breakdown")
        df_molds = pd.DataFrame(mold_breakdown)
        st.dataframe(df_molds, use_container_width=True)
        
        # Shift breakdown summary table
        st.subheader("⏱️ Shift Summary & Workload Breakdown")
        summary_data = {
            "Metric Description": [
                "Total Active Mold Stations in Circuit",
                "Net Active Work per Circuit (Walk + Load)",
                "Allowance Multiplier (Fatigue + Personal)",
                "Total Adjusted Circuit Time",
                "Operator Direct Working Time (%)",
                "Operator Allowance / Recovery Time (%)"
            ],
            "Value": [
                f"{num_molds} stations",
                f"{net_active_work:.1f} seconds",
                f"{total_allowance

import streamlit as st
import pandas as pd
import math

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")
st.title("👤 Single Operator Multi-Mold Productivity & Bonus Calculator")

# --- 2. SIDEBAR: ALLOWANCES & PARAMETERS ---
with st.sidebar:
    st.header("⚙️ Industrial Engineering Factors")
    
    # Allowances used to adjust baseline standard
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
        "id": st.column_config.TextColumn("Mold ID / Type", required=True),
        "units": st.column_config.NumberColumn("Number of Units", min_value=0, step=1, format="%d"),
        "p": st.column_config.NumberColumn("Press / Cure Time (s)", min_value=0.0, step=1.0),
        "l": st.column_config.NumberColumn("Load / Service Time (s)", min_value=0.0, step=1.0)
    }
)

# Unpack multiple units into individual stations for circuit simulation safely
active_molds = []
for m in edited_molds:
    try:
        qty = int(m.get('units', 0) or 0)
        press_time = float(m.get('p', 0) or 0)
        load_time = float(m.get('l', 0) or 0)
        mold_name = str(m.get('id', 'Unknown'))
        
        if qty > 0 and press_time > 0:
            for i in range(qty):
                active_molds.append({
                    'id': f"{mold_name} (#{i+1})",
                    'base_id': mold_name,
                    'p': press_time,
                    'l': load_time
                })
    except Exception as e:
        continue

# --- 4. EXECUTION BUTTON ---
run_calc = st.button('🚀 Calculate Operator Productivity & Incentive KPIs')

if run_calc:
    if not active_molds:
        st.error("⚠️ **No valid active molds found!** Please ensure at least one mold has 'Number of Units' > 0 and a 'Press / Cure Time' greater than 0.")
    else:
        try:
            num_molds = len(active_molds)
            
            # 1. Active work per complete operator circuit (visiting every individual mold station once)
            total_walking_in_circuit = num_molds * walk_time
            total_loading_in_circuit = sum(m['l'] for m in active_molds)
            net_active_work = total_walking_in_circuit + total_loading_in_circuit
            
            # 2. Maximum machine constraint in the circuit
            max_machine_constraint = max([m['p'] + m['l'] for m in active_molds])
            
            # Operator baseline cycle time for the circuit (pacing)
            base_circuit_time = max(net_active_work, max_machine_constraint)
            
            # Operator active workload percentage
            operator_active_utilization = (net_active_work / base_circuit_time) * 100 if base_circuit_time > 0 else 0
            
            # 3. Output Calculations per mold station
            mold_breakdown = []
            total_raw_baseline_hourly_output = 0
            total_absolute_max_hourly_output = 0
            
            for m in active_molds:
                machine_min_cycle = m['p'] + m['l']
                
                # ABSOLUTE THEORETICAL MAX (Machine Capped with 0 operator wait time)
                max_mold_hourly_out = (3600 / machine_min_cycle) * parts_per_cycle if machine_min_cycle > 0 else 0
                total_absolute_max_hourly_output += max_mold_hourly_out
                
                # ACTUAL BASELINE OUTPUT (Limited by operator circuit interval)
                if base_circuit_time > 0:
                    circuits_needed = math.ceil(machine_min_cycle / base_circuit_time)
                    actual_visit_interval = circuits_needed * base_circuit_time
                else:
                    circuits_needed = 1
                    actual_visit_interval = machine_min_cycle
                
                mold_baseline_hourly_out = (3600 / actual_visit_interval) * parts_per_cycle if actual_visit_interval > 0 else 0
                total_raw_baseline_hourly_output += mold_baseline_hourly_out
                
                # Machine utilization relative to operator circuit visit interval
                m_util = (machine_min_cycle / actual_visit_interval) * 100 if actual_visit_interval > 0 else 0
                max_possible_efficiency_pct = (mold_baseline_hourly_out / max_mold_hourly_out) * 100 if max_mold_hourly_out > 0 else 0
                
                mold_breakdown.append({
                    'Station ID': m['id'],
                    'Press (s)': m['p'],
                    'Load (s)': m['l'],
                    'Min Cycle (s)': machine_min_cycle,
                    'Visit Interval (s)': round(actual_visit_interval, 1),
                    'Machine Util (%)': round(m_util, 1),
                    'Baseline PPH': round(mold_baseline_hourly_out, 1),
                    'Absolute Max PPH': round(max_mold_hourly_out, 1),
                    'Efficiency vs Cap (%)': round(max_possible_efficiency_pct, 1)
                })
                
            # Allowance-Adjusted Baseline (100% Standard = Raw Baseline minus Allowance %)
            adjusted_baseline_hourly_output = total_raw_baseline_hourly_output * (1.0 - total_allowance_decimal)
                
            if total_absolute_max_hourly_output > 0:
                overall_efficiency_ratio = (total_raw_baseline_hourly_output / total_absolute_max_hourly_output) * 100
            else:
                overall_efficiency_ratio = 0

            # --- 5. RESULTS DISPLAY ---
            st.success("Calculations Complete!")
            
            # --- SECTION 1: PURE TECHNICAL BASELINE ---
            st.subheader("📊 Section 1: Pure Technical Baseline (Unadjusted)")
            st.caption("Core engineering metrics assuming 100% steady-state work with no allowances applied.")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Pure Raw Baseline PPH", f"{total_raw_baseline_hourly_output:.1f}", help="Actual expected hourly output based purely on circuit pacing")
            col2.metric("Absolute Machine Max PPH", f"{total_absolute_max_hourly_output:.1f}", help="Hard physical ceiling if machines never waited for operator")
            col3.metric("Operator Active Workload", f"{operator_active_utilization:.1f}%", help="Pure active work time vs circuit time")
            col4.metric("Circuit Balance Ratio", f"{overall_efficiency_ratio:.1f}%", delta="Machine Constrained" if overall_efficiency_ratio < 100 else "Fully Balanced", delta_color="inverse")

            st.divider()

            # --- SECTION 2: ALLOWANCE-ADJUSTED INCENTIVE TARGETS ---
            st.subheader("🎯 Section 2: Allowance-Adjusted Incentive Targets (100% to

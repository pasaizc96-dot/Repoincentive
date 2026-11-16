import streamlit as st
import pandas as pd
import math

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")
st.title("👤 Single Operator Multi-Mold Productivity & Incentive Planner")

# --- 2. SIDEBAR: ALLOWANCES & PARAMETERS ---
with st.sidebar:
    st.header("⚙️ Industrial Engineering Factors")
    
    # Allowances
    fatigue_pct = st.number_input("Fatigue Allowance (%)", value=8.0, step=0.5)
    personal_pct = st.number_input("Personal Needs Allowance (%)", value=6.0, step=0.5)
    total_allowance_multiplier = 1.0 + ((fatigue_pct + personal_pct) / 100.0)
    st.caption(f"F&P Allowance Factor: **{total_allowance_multiplier:.3f}x** (Standard Time / Normal Time)")
    
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

# Unpack multiple units into individual stations safely
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
    except Exception:
        continue

# --- 4. EXECUTION BUTTON ---
run_calc = st.button('🚀 Calculate Operator Productivity & Incentive KPIs')

if run_calc:
    if not active_molds:
        st.error("⚠️ **No valid active molds found!** Please ensure at least one mold has 'Number of Units' > 0 and a 'Press / Cure Time' greater than 0.")
    else:
        try:
            num_molds = len(active_molds)
            
            # 1. Normal Time Calculations (Pure Active Work & Machine Constraints)
            net_normal_walk = num_molds * walk_time
            net_normal_load = sum(m['l'] for m in active_molds)
            normal_active_work = net_normal_walk + net_normal_load
            
            max_machine_constraint = max([m['p'] + m['l'] for m in active_molds])
            
            # Base Normal Circuit Pacing Time
            base_normal_circuit_time = max(normal_active_work, max_machine_constraint)
            
            # Standard Circuit Time (Normal Time * Allowance Multiplier)
            standard_circuit_time = base_normal_circuit_time * total_allowance_multiplier
            
            # 2. Output Calculations per mold station using Standard Circuit Time pacing
            mold_breakdown = []
            total_baseline_hourly_output = 0
            total_absolute_max_hourly_output = 0
            
            for m in active_molds:
                machine_min_cycle = m['p'] + m['l']
                
                # Absolute Theoretical Max (Machine Capped with 0 operator wait time)
                max_mold_hourly_out = (3600 / machine_min_cycle) * parts_per_cycle if machine_min_cycle > 0 else 0
                total_absolute_max_hourly_output += max_mold_hourly_out
                
                # Actual Baseline Output (Paced by Standard Circuit Time)
                if standard_circuit_time > 0:
                    circuits_needed = math.ceil(machine_min_cycle / standard_circuit_time)
                    actual_visit_interval = circuits_needed * standard_circuit_time
                else:
                    circuits_needed = 1
                    actual_visit_interval = machine_min_cycle
                
                mold_baseline_hourly_out = (3600 / actual_visit_interval) * parts_per_cycle if actual_visit_interval > 0 else 0
                total_baseline_hourly_output += mold_baseline_hourly_out
                
                # Machine utilization & maximum achievable efficiency cap
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
                    'Max Achievable Cap (%)': round(max_possible_efficiency_pct, 1)
                })
                
            # Operator Performance Index (Standard Time allowance scaling)
            operator_standard_performance_pct = total_allowance_multiplier * 100
            
            if total_absolute_max_hourly_output > 0:
                overall_max_efficiency_cap = (total_baseline_hourly_output / total_absolute_max_hourly_output) * 100
            else:
                overall_max_efficiency_cap = 0

            # --- 5. RESULTS DISPLAY ---
            st.success("Calculations Complete!")
            
            # Top-level KPI Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Baseline Output (Parts/Hour)", f"{total_baseline_hourly_output:.1f}")
            col2.metric("Absolute Machine Max PPH", f"{total_absolute_max_hourly_output:.1f}", help="Hard physical limit if machines never waited for operator")
            col3.metric("Operator Standard Pace Index", f"{operator_standard_performance_pct:.1f}%", help="Standard performance rating including F&P allowance buffer")
            col4.metric("Baseline vs Machine Cap", f"{overall_max_efficiency_cap:.1f}%", delta="Machine Constrained" if overall_max_efficiency_cap < 100 else "Fully Balanced", delta_color="inverse")

            st.divider()

            # --- 6. BONUS TIER KPIS VS REALITY VALIDATION ---
            st.subheader("🎯 Incentive Bonus Target Thresholds vs. Machine Limits")
            st.caption("Validating target output brackets against the absolute machine-capped physical threshold.")

            tier_cols = st.columns(4)
            tiers = [
                ("110% Target", 1.10),
                ("120% Target", 1.20),
                ("130% Target", 1.30),
                ("140% Target", 1.40)
            ]

            for i, (tier_name, multiplier) in enumerate(tiers):
                target_hourly = total_baseline_hourly_output * multiplier
                is_physically_impossible = target_hourly > total_absolute_max_hourly_output
                
                with tier_cols[i]:
                    if is_physically_impossible:
                        st.metric(
                            label=tier_name,
                            value=f"{target_hourly:.1f} PPH",
                            delta="❌ Not Achievable (Machine Capped)",
                            delta_color="inverse"
                        )
                    else:
                        st.metric(
                            label=tier_name,
                            value=f"{target_hourly:.1f} PPH",
                            delta="✅ Achievable",
                            delta_color="normal"
                        )

            st

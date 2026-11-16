import streamlit as st
import pandas as pd
import math

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")
st.title("👤 Single Operator Multi-Mold Productivity & Bonus Calculator")

# --- 2. SIDEBAR: ALLOWANCES & PARAMETERS ---
with st.sidebar:
    st.header("⚙️ Industrial Engineering Factors")
    
    # Allowances applied as an earned incentive multiplier
    fatigue_pct = st.number_input("Fatigue Allowance (%)", value=8.0, step=0.5)
    personal_pct = st.number_input("Personal Needs Allowance (%)", value=6.0, step=0.5)
    total_allowance_multiplier = 1.0 + ((fatigue_pct + personal_pct) / 100.0)
    st.caption(f"F&P Allowance Multiplier: **{total_allowance_multiplier:.3f}x**")
    
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
            
            # Operator active utilization percentage
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
                
                mold_raw_baseline_out = (3600 / actual_visit_interval) * parts_per_cycle if actual_visit_interval > 0 else 0
                total_raw_baseline_hourly_output += mold_raw_baseline_out
                
                # Machine utilization relative to operator circuit visit interval
                m_util = (machine_min_cycle / actual_visit_interval) * 100 if actual_visit_interval > 0 else 0
                max_possible_efficiency_pct = (mold_raw_baseline_out / max_mold_hourly_out) * 100 if max_mold_hourly_out > 0 else 0
                
                mold_breakdown.append({
                    'Station ID': m['id'],
                    'Press (s)': m['p'],
                    'Load (s)': m['l'],
                    'Min Cycle (s)': machine_min_cycle,
                    'Visit Interval (s)': round(actual_visit_interval, 1),
                    'Machine Util (%)': round(m_util, 1),
                    'Raw Baseline PPH': round(mold_raw_baseline_out, 1),
                    'Absolute Max PPH': round(max_mold_hourly_out, 1),
                    'Efficiency vs Cap (%)': round(max_possible_efficiency_pct, 1)
                })
                
            if total_absolute_max_hourly_output > 0:
                overall_efficiency_ratio = (total_raw_baseline_hourly_output / total_absolute_max_hourly_output) * 100
            else:
                overall_efficiency_ratio = 0

            # Calculate Allowance-Adjusted (Earned) Baseline Output
            total_earned_baseline_output = total_raw_baseline_hourly_output * total_allowance_multiplier

            # --- 5. RESULTS DISPLAY ---
            st.success("Calculations Complete!")
            
            # Top-level KPI Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Earned Baseline (100% + F&P)", f"{total_earned_baseline_output:.1f} PPH", help="Baseline output scaled with Fatigue & Personal allowance multiplier")
            col2.metric("Raw Standard Baseline", f"{total_raw_baseline_hourly_output:.1f} PPH", help="Pure physical circuit baseline output without allowance inflation")
            col3.metric("Absolute Machine Max PPH", f"{total_absolute_max_hourly_output:.1f}", help="Hard physical ceiling if machines never waited for operator")
            col4.metric("Circuit Balance Ratio", f"{overall_efficiency_ratio:.1f}%", delta="Machine Constrained" if overall_efficiency_ratio < 100 else "Fully Balanced", delta_color="inverse")

            st.divider()

            # --- 6. BONUS TIER KPIS VS REALITY VALIDATION ---
            st.subheader("🎯 Incentive Bonus Target Thresholds vs. Machine Limits")
            st.caption("Validating allowance-adjusted target output brackets against the absolute machine-capped physical threshold.")

            tier_cols = st.columns(4)
            tiers = [
                ("110% Target", 1.10),
                ("120% Target", 1.20),
                ("130% Target", 1.30),
                ("140% Target", 1.40)
            ]

            for i, (tier_name, multiplier) in enumerate(tiers):
                # Targets are calculated based on the Earned Allowance Baseline
                target_hourly = total_earned_baseline_output * multiplier
                
                # Check if target exceeds absolute machine capacity limit
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

            st.divider()

            # --- 7. DETAILED MOLD BREAKDOWN TABLE ---
            st.subheader("📋 Individual Mold Station Performance & Ceiling Breakdown")
            df_molds = pd.DataFrame(mold_breakdown)
            st.dataframe(df_molds, use_container_width=True)
            
            # Shift breakdown summary table
            st.subheader("⏱️ Shift Summary & Workload Breakdown")
            summary_data = {
                "Metric Description": [
                    "Total Active Mold Stations in Circuit",
                    "Net Active Work per Circuit (Walk + Load)",
                    "Base Circuit Cycle Time",
                    "Operator Active Workload (%)",
                    "Raw Standard Baseline Output (PPH)",
                    "F&P Allowance Multiplier",
                    "Earned Baseline Output (100% Adjusted)",
                    "Absolute Machine Capacity Ceiling (PPH)"
                ],
                "Value": [
                    f"{num_molds} stations",
                    f"{net_active_work:.1f} seconds",
                    f"{base_circuit_time:.1f} seconds",
                    f"{operator_active_utilization:.1f}%",
                    f"{total_raw_baseline_hourly_output:.1f} PPH",
                    f"{total_allowance_multiplier:.3f}x ({fatigue_pct + personal_pct}% total)",
                    f"{total_earned_baseline_output:.1f} PPH",
                    f"{total_absolute_max_hourly_output:.1f} PPH"
                ]
            }
            st.table(pd.DataFrame(summary_data))
            
        except Exception as e:
            st.error(f"⚠️ Calculation error encountered: {e}")

import streamlit as st
import pandas as pd
import math
from datetime import date

# --- 1. APP CONFIG & PRINT CSS ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")

st.markdown("""
<style>
@media print {
    /* Hide sidebar, buttons, and input editors when printing */
    section[data-testid="stSidebar"],
    .stButton,
    div[data-testid="stDataEditor"],
    .no-print {
        display: none !important;
    }
    /* Optimize page margins and font readability for small/single sheet */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
    }
    body {
        font-size: 12px !important;
        color: #000 !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("👤 Single Operator Multi-Mold Productivity & Bonus Calculator")

# --- 2. SIDEBAR: ALLOWANCES, PARAMETERS & OPERATOR INFO ---
with st.sidebar:
    st.header("🪪 Operator Sign-Off Info")
    operator_name = st.text_input("Operator Name / ID", value="OP-001")
    shift_date = st.date_input("Shift Date", value=date.today())

    st.divider()
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
st.info("Enter your mold types, the **number of units** active for each type, and their Press (P) and Load (L) times.")
st.markdown('</div>', unsafe_allow_html=True)

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

# Unpack multiple units into individual stations & keep clean summary list of active mold types
active_molds = []
active_mold_summary = []

for m in edited_molds:
    try:
        qty = int(m.get('units', 0) or 0)
        press_time = float(m.get('p', 0) or 0)
        load_time = float(m.get('l', 0) or 0)
        mold_name = str(m.get('id', 'Unknown'))
        
        if qty > 0 and press_time > 0:
            active_mold_summary.append({
                'Mold Type': mold_name,
                'Units': qty,
                'Press (s)': press_time,
                'Load (s)': load_time,
                'Min Cycle (s)': press_time + load_time
            })
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
            
            # 1. Active work per complete operator circuit
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
                
                # ABSOLUTE THEORETICAL MAX
                max_mold_hourly_out = (3600 / machine_min_cycle) * parts_per_cycle if machine_min_cycle > 0 else 0
                total_absolute_max_hourly_output += max_mold_hourly_out
                
                # ACTUAL BASELINE OUTPUT
                if base_circuit_time > 0:
                    circuits_needed = math.ceil(machine_min_cycle / base_circuit_time)
                    actual_visit_interval = circuits_needed * base_circuit_time
                else:
                    circuits_needed = 1
                    actual_visit_interval = machine_min_cycle
                
                mold_baseline_hourly_out = (3600 / actual_visit_interval) * parts_per_cycle if actual_visit_interval > 0 else 0
                total_raw_baseline_hourly_output += mold_baseline_hourly_out
                
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

            # --- 5. RESULTS DISPLAY (SCREEN VIEW) ---
            st.markdown('<div class="no-print">', unsafe_allow_html=True)
            st.success("Calculations Complete!")
            
            # SECTION 1: PURE TECHNICAL BASELINE
            st.subheader("📊 Section 1: Pure Technical Baseline (Unadjusted)")
            st.caption("Core engineering metrics assuming 100% steady-state work with no allowances applied.")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Pure Raw Baseline PPH", f"{total_raw_baseline_hourly_output:.1f}")
            col2.metric("Absolute Machine Max PPH", f"{total_absolute_max_hourly_output:.1f}")
            col3.metric("Operator Active Workload", f"{operator_active_utilization:.1f}%")
            col4.metric("Circuit Balance Ratio", f"{overall_efficiency_ratio:.1f}%", delta="Machine Constrained" if overall_efficiency_ratio < 100 else "Fully Balanced", delta_color="inverse")

            st.divider()

            # SECTION 2: ALLOWANCE-ADJUSTED INCENTIVE TARGETS
            st.subheader("🎯 Section 2: Allowance-Adjusted Incentive Targets (100% to 140%)")
            st.caption(f"Incentive targets starting from the adjusted 100% standard (Raw Baseline minus {total_allowance_pct:.1f}% F&P allowance).")

            tier_cols = st.columns(5)
            tiers = [
                ("100% Standard", 1.00),
                ("110% Target", 1.10),
                ("120% Target", 1.20),
                ("130% Target", 1.30),
                ("140% Target", 1.40)
            ]

            for i, (tier_name, multiplier) in enumerate(tiers):
                target_hourly = adjusted_baseline_hourly_output * multiplier
                is_physically_impossible = target_hourly > total_absolute_max_hourly_output
                
                with tier_cols[i]:
                    if is_physically_impossible:
                        st.metric(label=tier_name, value=f"{target_hourly:.1f} PPH", delta="❌ Machine Capped", delta_color="inverse")
                    else:
                        st.metric(label=tier_name, value=f"{target_hourly:.1f} PPH", delta="✅ Achievable", delta_color="normal")

            st.divider()

            # DETAILED MOLD BREAKDOWN TABLE
            st.subheader("📋 Individual Mold Station Performance & Ceiling Breakdown")
            st.dataframe(pd.DataFrame(mold_breakdown), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # --- 6. PRINTABLE OPERATOR SIGN-OFF SHEET ---
            st.divider()
            st.subheader("🖨️ Operator Production & Incentive Target Sheet (Print Ready)")
            st.caption("Press **Ctrl + P** (or **Cmd + P**) to print this compact sign-off sheet.")

            with st.container(border=True):
                # Header Metadata
                st.markdown(f"### 📋 Daily Operator Production & Incentive Standard")
                h_col1, h_col2, h_col3 = st.columns(3)
                h_col1.markdown(f"**Operator ID / Name:** {operator_name}")
                h_col2.markdown(f"**Date:** {shift_date.strftime('%Y-%m-%d')}")
                h_col3.markdown(f"**Shift Hours:** {shift_hours:.1f} hrs")

                p_col1, p_col2, p_col3 = st.columns(3)
                p_col1.markdown(f"**Active Stations:** {num_molds} molds")
                p_col2.markdown(f"**Walk Time / Parts per Cycle:** {walk_time:.1f}s / {parts_per_cycle} pcs")
                p_col3.markdown(f"**F&P Allowance:** {total_allowance_pct:.1f}% (Fatigue {fatigue_pct:.1f}% + Personal {personal_pct:.1f}%)")

                st.markdown("---")

                # Compact Two-Column Layout for Sheet Readability
                left_sheet, right_sheet = st.columns([1, 1.3])

                with left_sheet:
                    st.markdown("**1. Assigned Molds & Cycle Inputs**")
                    df_summary_molds = pd.DataFrame(active_mold_summary)
                    st.table(df_summary_molds)

                    st.markdown("**2. Technical Baseline Reference**")
                    tech_ref_df = pd.DataFrame({
                        "Parameter": [
                            "Pure Technical Baseline (0% Allow.)",
                            "Absolute Machine Max Limit",
                            "Operator Active Workload"
                        ],
                        "Per Hour": [
                            f"{total_raw_baseline_hourly_output:.1f} PPH",
                            f"{total_absolute_max_hourly_output:.1f} PPH",
                            f"{operator_active_utilization:.1f}%"
                        ],
                        f"Per Shift ({shift_hours:.1f}h)": [
                            f"{total_raw_baseline_hourly_output * shift_hours:.0f} pcs",
                            f"{total_absolute_max_hourly_output * shift_hours:.0f} pcs",
                            "-"
                        ]
                    })
                    st.table(tech_ref_df)

                with right_sheet:
                    st.markdown(f"**3. Allowance-Adjusted Targets (-{total_allowance_pct:.1f}% F&P)**")
                    target_rows = []
                    for tier_name, mult in tiers:
                        pph = adjusted_baseline_hourly_output * mult
                        daily_pcs = pph * shift_hours
                        status = "Machine Capped" if pph > total_absolute_max_hourly_output else "Achievable"
                        target_rows.append({
                            "Incentive Tier": tier_name,
                            "Target / Hour": f"{pph:.1f} PPH",
                            f"Target / Shift ({shift_hours:.1f}h)": f"{daily_pcs:.0f} pcs",
                            "Feasibility": status
                        })
                    st.table(pd.DataFrame(target_rows))

                st.markdown("---")
                
                # Sign-Off Footer
                sig1, sig2 = st.columns(2)
                with sig1:
                    st.markdown("**Operator Acknowledgment:**")
                    st.markdown("<br>Signature: ___________________________ &nbsp;&nbsp; Date: ____________", unsafe_allow_html=True)
                with sig2:
                    st.markdown("**Supervisor / IE Approval:**")
                    st.markdown("<br>Signature: ___________________________ &nbsp;&nbsp; Date: ____________", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ Calculation error encountered: {e}")

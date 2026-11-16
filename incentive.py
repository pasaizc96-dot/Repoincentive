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
        margin: 8mm;
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
        font-size: 9px !important;
        color: #000 !important;
    }
    table {
        font-size: 8px !important;
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

# --- 3. MOLD / MATERIAL DATA INPUTS (20 ROWS DEFAULT) ---
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.subheader("📦 Operator Mold Assignment Data")
st.info("Enter your mold types, the **number of units** active for each type, and their Press (P) and Load (L) times (up to 20 types).")
st.markdown('</div>', unsafe_allow_html=True)

default_molds = [
    {'id': 'Mold Type A', 'units': 2, 'p': 180, 'l': 12},
    {'id': 'Mold Type B', 'units': 1, 'p': 240, 'l': 15},
]
for i in range(ord('C'), ord('U')):
    default_molds.append({'id': f'Mold Type {chr(i)}', 'units': 0, 'p': 0, 'l': 0})

edited_molds = st.data_editor(
    default_molds,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "id": st.column_config.TextColumn("Mold ID / Type", required=True),
        "units": st.column_config.NumberColumn("Number of Units", min_value=0, step=1, format="%d"),
        "p": st.column_config.NumberColumn("Press / Cure Time (s)", min_value=0.0, step=1.0),
        "l": st.column_config.NumberColumn("Load / Service Time (s)", min_value=0.0, step=1.0)
    }
)

# Unpack active molds
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
            
            total_walking_in_circuit = num_molds * walk_time
            total_loading_in_circuit = sum(m['l'] for m in active_molds)
            net_active_work = total_walking_in_circuit + total_loading_in_circuit
            
            max_machine_constraint = max([m['p'] + m['l'] for m in active_molds])
            base_circuit_time = max(net_active_work, max_machine_constraint)
            operator_active_utilization = (net_active_work / base_circuit_time) * 100 if base_circuit_time > 0 else 0
            
            mold_breakdown = []
            total_raw_baseline_hourly_output = 0
            total_absolute_max_hourly_output = 0
            
            for m in active_molds:
                machine_min_cycle = m['p'] + m['l']
                max_mold_hourly_out = (3600 / machine_min_cycle) * parts_per_cycle if machine_min_cycle > 0 else 0
                total_absolute_max_hourly_output += max_mold_hourly_out
                
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
                
            adjusted_baseline_hourly_output = total_raw_baseline_hourly_output * (1.0 - total_allowance_decimal)
            overall_efficiency_ratio = (total_raw_baseline_hourly_output / total_absolute_max_hourly_output * 100) if total_absolute_max_hourly_output > 0 else 0

            # --- 5. SCREEN DISPLAY ---
            st.markdown('<div class="no-print">', unsafe_allow_html=True)
            st.success("Calculations Complete!")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Pure Raw Baseline PPH", f"{total_raw_baseline_hourly_output:.1f}")
            col2.metric("Absolute Machine Max PPH", f"{total_absolute_max_hourly_output:.1f}")
            col3.metric("Operator Active Workload", f"{operator_active_utilization:.1f}%")
            col4.metric("Circuit Balance Ratio", f"{overall_efficiency_ratio:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)

            # --- 6. COMPACT A5 PRINTABLE SIGN-OFF SHEET ---
            st.divider()
            st.subheader("🖨️ A5 Printable Operator Sign-Off Sheet")
            st.caption("Press **Ctrl + P** (or **Cmd + P**) and set paper size to **A5** to print.")

            with st.container(border=True):
                st.markdown("### 👤 Operator Production & Incentive Objectives")
                
                # Header Information
                h_col1, h_col2, h_col3 = st.columns(3)
                h_col1.markdown("**Operator:** __________________")
                h_col2.markdown("**Date:** ____________")
                h_col3.markdown(f"**Shift:** {shift_hours:.1f} Hrs")

                p_col1, p_col2 = st.columns(2)
                p_col1.markdown(f"**Walk Time:** {walk_time:.1f}s | **Parts/Cycle:** {parts_per_cycle}")
                p_col2.markdown(f"**F&P Deduction:** {total_allowance_pct:.1f}%")

                st.markdown("---")

                # 100% - 140% Objectives Table
                st.markdown("**1. Incentive Objectives (100% - 140%)**")
                target_rows = []
                tiers = [
                    ("100% Standard", 1.00),
                    ("110% Target", 1.10),
                    ("120% Target", 1.20),
                    ("130% Target", 1.30),
                    ("140% Target", 1.40)
                ]
                for tier_name, mult in tiers:
                    pph = adjusted_baseline_hourly_output * mult
                    daily_pcs = pph * shift_hours
                    status = "Not Achievable" if pph > total_absolute_max_hourly_output else "Achievable"
                    target_rows.append({
                        "Objective Tier": tier_name,
                        "Hourly (PPH)": f"{pph:.1f}",
                        f"Shift Total ({shift_hours}h)": f"{daily_pcs:.0f}",
                        "Status": status
                    })
                st.table(pd.DataFrame(target_rows))

                # Assigned Molds Table (Padded to 8 rows max for consistent A5 sizing)
                st.markdown("**2. Assigned Molds**")
                padded_molds = active_mold_summary.copy()
                while len(padded_molds) < 8:
                    padded_molds.append({'Mold Type': '---', 'Units': '', 'Press (s)': '', 'Load (s)': '', 'Min Cycle (s)': ''})
                st.table(pd.DataFrame(padded_molds[:8]))

                # Operator Feedback Blank Rows
                st.markdown("**3. Operator Feedback & Downtime Notes:**")
                st.markdown("• _________________________________________________________________________________")
                st.markdown("• _________________________________________________________________________________")

                st.markdown("---")
                
                # Sign-Off Footer
                sig1, sig2 = st.columns(2)
                with sig1:
                    st.markdown("**Operator Signature:**")
                    st.markdown("___________________________ &nbsp;&nbsp; Date: _________", unsafe_allow_html=True)
                with sig2:
                    st.markdown("**Supervisor / IE Signature:**")
                    st.markdown("___________________________ &nbsp;&nbsp; Date: _________", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ Calculation error encountered: {e}")

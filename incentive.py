import streamlit as st
import pandas as pd
import math
import io
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# --- 1. APP CONFIG & A5 PRINT CSS ---
st.set_page_config(page_title="Single Operator Mold Productivity & Incentive Planner", layout="wide")

st.markdown("""
<style>
@media print {
    @page {
        size: A5;
        margin: 8mm;
    }
    section[data-testid="stSidebar"],
    .stButton,
    .stDownloadButton,
    div[data-testid="stDataEditor"],
    .no-print {
        display: none !important;
    }
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
st.info("Enter your mold types, the **number of units** active for each type, and their Press (P) and Load (L) times (up to 20 types). Calculations update automatically.")
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

# --- HELPER: EXCEL GENERATOR ---
def generate_a5_excel(target_rows, padded_molds, shift_hours, walk_time, parts_per_cycle, total_allowance_pct):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        wb = writer.book
        ws = wb.create_sheet("A5_SignOff_Sheet")
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

        # Page setup for A5 Portrait, Fit to 1x1 page
        ws.page_setup.paperSize = ws.PAPERSIZE_A5
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.page_margins.left = 0.25
        ws.page_margins.right = 0.25
        ws.page_margins.top = 0.25
        ws.page_margins.bottom = 0.25

        # Styling definitions
        title_font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        sub_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        bold_font = Font(name="Calibri", size=9, bold=True)
        reg_font = Font(name="Calibri", size=9)
        thin_side = Side(border_style="thin", color="808080")
        border_all = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")

        # Title Banner
        ws.merge_cells("A1:E1")
        ws["A1"] = "OPERATOR PRODUCTION & INCENTIVE TARGET SHEET"
        ws["A1"].font = title_font
        ws["A1"].fill = header_fill
        ws["A1"].alignment = center_align
        ws.row_dimensions[1].height = 22

        # Header Metadata (Blank Operator & Date for handwritten fill)
        ws.merge_cells("A2:B2")
        ws["A2"] = "Operator Name/ID: ______________________"
        ws["C2"] = "Date: ______________"
        ws.merge_cells("D2:E2")
        ws["D2"] = f"Shift Duration: {shift_hours:.1f} Hrs"

        ws.merge_cells("A3:B3")
        ws["A3"] = f"Walk Time: {walk_time:.1f}s | Parts/Cycle: {parts_per_cycle}"
        ws.merge_cells("C3:E3")
        ws["C3"] = f"F&P Allowance Deduction: {total_allowance_pct:.1f}%"

        for r in [2, 3]:
            ws.row_dimensions[r].height = 18
            for c in range(1, 6):
                cell = ws.cell(row=r, column=c)
                cell.font = bold_font
                cell.alignment = left_align
                cell.border = border_all

        # Section 1: Incentive Objectives (100% - 140%)
        ws.merge_cells("A5:E5")
        ws["A5"] = "1. INCENTIVE OBJECTIVES (ALLOWANCE-ADJUSTED)"
        ws["A5"].font = bold_font
        ws["A5"].fill = sub_fill
        ws["A5"].alignment = left_align
        ws.row_dimensions[5].height = 18

        obj_headers = ["Objective Tier", "Hourly (PPH)", f"Shift Total ({shift_hours:.1f}h)", "Status", "Notes"]
        ws.row_dimensions[6].height = 18
        for idx, text in enumerate(obj_headers, 1):
            c = ws.cell(row=6, column=idx, value=text)
            c.font = bold_font
            c.fill = sub_fill
            c.alignment = center_align
            c.border = border_all

        for i, row_data in enumerate(target_rows, start=7):
            ws.row_dimensions[i].height = 17
            vals = [row_data["Objective Tier"], row_data["Hourly (PPH)"], row_data[f"Shift Total ({shift_hours:.1f}h)"], row_data["Status"], ""]
            for c_idx, val in enumerate(vals, 1):
                cell = ws.cell(row=i, column=c_idx, value=val)
                cell.font = reg_font
                cell.border = border_all
                cell.alignment = center_align if c_idx in [2, 3, 4] else left_align
                if c_idx == 4:
                    cell.font = Font(name="Calibri", size=9, bold=True, color="006100" if val == "Achievable" else "9C0006")

        # Section 2: Assigned Molds (Fixed 8 rows)
        ws.merge_cells("A13:E13")
        ws["A13"] = "2. ASSIGNED MOLDS & CYCLE PARAMETERS"
        ws["A13"].font = bold_font
        ws["A13"].fill = sub_fill
        ws["A13"].alignment = left_align
        ws.row_dimensions[13].height = 18

        mold_headers = ["Mold Type", "Units", "Press (s)", "Load (s)", "Min Cycle (s)"]
        ws.row_dimensions[14].height = 18
        for idx, text in enumerate(mold_headers, 1):
            c = ws.cell(row=14, column=idx, value=text)
            c.font = bold_font
            c.fill = sub_fill
            c.alignment = center_align
            c.border = border_all

        for i, m_row in enumerate(padded_molds[:8], start=15):
            ws.row_dimensions[i].height = 17
            vals = [m_row["Mold Type"], m_row["Units"], m_row["Press (s)"], m_row["Load (s)"], m_row["Min Cycle (s)"]]
            for c_idx, val in enumerate(vals, 1):
                cell = ws.cell(row=i, column=c_idx, value=val)
                cell.font = reg_font
                cell.border = border_all
                cell.alignment = left_align if c_idx == 1 else center_align

        # Section 3: Operator Feedback Blank Rows
        ws.merge_cells("A24:E24")
        ws["A24"] = "3. OPERATOR FEEDBACK / DOWNTIME & ISSUE LOG"
        ws["A24"].font = bold_font
        ws["A24"].fill = sub_fill
        ws["A24"].alignment = left_align
        ws.row_dimensions[24].height = 18

        for r in range(25, 28):
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
            ws.row_dimensions[r].height = 20
            for c in range(1, 6):
                ws.cell(row=r, column=c).border = border_all

        # Section 4: Signatures
        ws.merge_cells("A29:B29")
        ws["A29"] = "Operator Signature: ________________________"
        ws["C29"] = "Date: __________"
        ws.merge_cells("D29:E29")
        ws["D29"] = "Supervisor / IE: ________________________"
        ws.row_dimensions[29].height = 24
        for c in range(1, 6):
            cell = ws.cell(row=29, column=c)
            cell.font = bold_font
            cell.alignment = left_align

        # Set optimized column widths for A5 Portrait
        col_widths = {1: 22, 2: 13, 3: 15, 4: 15, 5: 14}
        for col_idx, width in col_widths.items():
            ws.column_dimensions[chr(64 + col_idx)].width = width

    output.seek(0)
    return output.getvalue()

# --- 4. CALCULATION & REPORT RENDER ---
if not active_molds:
    st.warning("⚠️ **No valid active molds found!** Please ensure at least one mold has 'Number of Units' > 0 and a 'Press / Cure Time' greater than 0.")
else:
    try:
        num_molds = len(active_molds)
        
        total_walking_in_circuit = num_molds * walk_time
        total_loading_in_circuit = sum(m['l'] for m in active_molds)
        net_active_work = total_walking_in_circuit + total_loading_in_circuit
        
        max_machine_constraint = max([m['p'] + m['l'] for m in active_molds])
        base_circuit_time = max(net_active_work, max_machine_constraint)
        operator_active_utilization = (net_active_work / base_circuit_time) * 100 if base_circuit_time > 0 else 0
        
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
            
        adjusted_baseline_hourly_output = total_raw_baseline_hourly_output * (1.0 - total_allowance_decimal)
        overall_efficiency_ratio = (total_raw_baseline_hourly_output / total_absolute_max_hourly_output * 100) if total_absolute_max_hourly_output > 0 else 0

        # --- SCREEN METRIC DISPLAY ---
        st.markdown('<div class="no-print">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pure Raw Baseline PPH", f"{total_raw_baseline_hourly_output:.1f}")
        col2.metric("Absolute Machine Max PPH", f"{total_absolute_max_hourly_output:.1f}")
        col3.metric("Operator Active Workload", f"{operator_active_utilization:.1f}%")
        col4.metric("Circuit Balance Ratio", f"{overall_efficiency_ratio:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)

        # Prepare structured tables for both Screen & Excel
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

        padded_molds = active_mold_summary.copy()
        while len(padded_molds) < 8:
            padded_molds.append({'Mold Type': '', 'Units': '', 'Press (s)': '', 'Load (s)': '', 'Min Cycle (s)': ''})

        # --- EXCEL DOWNLOAD BUTTON ---
        excel_bytes = generate_a5_excel(
            target_rows=target_rows,
            padded_molds=padded_molds,
            shift_hours=shift_hours,
            walk_time=walk_time,
            parts_per_cycle=parts_per_cycle,
            total_allowance_pct=total_allowance_pct
        )
        st.download_button(
            label="📥 Download Formatted A5 Excel Sign-Off Sheet (.xlsx)",
            data=excel_bytes,
            file_name="Operator_Incentive_A5_SignOff.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- COMPACT A5 PRINTABLE PREVIEW ---
        st.divider()
        st.subheader("🖨️ A5 Printable Operator Sign-Off Preview")
        st.caption("Download the Excel file above for native A5 grid printing, or press **Ctrl + P** directly here.")

        with st.container(border=True):
            st.markdown("### 👤 Operator Production & Incentive Objectives")
            
            h_col1, h_col2, h_col3 = st.columns(3)
            h_col1.markdown("**Operator:** __________________")
            h_col2.markdown("**Date:** ____________")
            h_col3.markdown(f"**Shift:** {shift_hours:.1f} Hrs")

            p_col1, p_col2 = st.columns(2)
            p_col1.markdown(f"**Walk Time:** {walk_time:.1f}s | **Parts/Cycle:** {parts_per_cycle}")
            p_col2.markdown(f"**F&P Deduction:** {total_allowance_pct:.1f}%")

            st.markdown("---")
            st.markdown("**1. Incentive Objectives (100% - 140%)**")
            st.table(pd.DataFrame(target_rows))

            st.markdown("**2. Assigned Molds**")
            display_molds = [
                {k: ('---' if k == 'Mold Type' and v == '' else v) for k, v in row.items()}
                for row in padded_molds[:8]
            ]
            st.table(pd.DataFrame(display_molds))

            st.markdown("**3. Operator Feedback & Downtime Notes:**")
            st.markdown("• _________________________________________________________________________________")
            st.markdown("• _________________________________________________________________________________")
            st.markdown("• _________________________________________________________________________________")

            st.markdown("---")
            sig1, sig2 = st.columns(2)
            with sig1:
                st.markdown("**Operator Signature:**")
                st.markdown("___________________________ &nbsp;&nbsp; Date: _________", unsafe_allow_html=True)
            with sig2:
                st.markdown("**Supervisor / IE Signature:**")
                st.markdown("___________________________ &nbsp;&nbsp; Date: _________", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ Calculation error encountered: {e}")

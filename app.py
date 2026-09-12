"""Boiler Efficiency Calculator — Streamlit app.

A mobile-friendly reimplementation of the BOILERE1-based boiler efficiency
calculator (originally boiler_eff.html). All engineering math lives in
boiler_calc.py and matches the original tool's results exactly.
"""
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from boiler_calc import compute, COMPONENT_NAMES

st.set_page_config(
    page_title="Boiler Efficiency Calculator",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Mobile-friendly styling: bigger touch targets, tighter spacing ---
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 760px; }
    div.stButton > button, div.stDownloadButton > button {
        width: 100%; padding: 0.75rem 1rem; font-weight: 600; font-size: 1.05rem;
        border-radius: 0.6rem;
    }
    div.stNumberInput input, div.stTextInput input { font-size: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 Boiler Efficiency Calculator")
st.caption("Based on the BOILERE1 program. Enter a test run's data below.")


def num_input(label, key, value, step=0.01, fmt="%.2f", help=None):
    return st.number_input(label, value=float(value), step=step, format=fmt, key=key, help=help)


with st.form("boiler_form"):
    with st.expander("General Information", expanded=True):
        factory_name = st.text_input("Factory Name", value="ST. MARY")
        boiler_id = st.text_input("Boiler Identification", value="EXAMPLE")
        date_str = st.text_input("Date", value=datetime.now().strftime("%m/%d/%Y"))
        run_number = st.text_input("Run Number", value="1")
        comments = st.text_input("Comments", value="")

    with st.expander("Fuel & Combustion", expanded=True):
        moisture_bagasse = num_input("Moisture % Bagasse", "moisture_bagasse", 48.00)
        ash_bagasse = num_input("Ash % Bagasse", "ash_bagasse", 4.00)
        oxygen_dry_flue = num_input("% Oxygen in Dry Flue Gases", "oxygen_dry_flue", 9.00)
        co_ppm = num_input("PPM CO in Dry Flue Gases", "co_ppm", 100.00)
        nox_ppm = num_input("PPM NOx in Dry Flue Gases (as NO)", "nox_ppm", 100.00)
        so2_ppm = num_input("PPM SO2 in Dry Flue Gases", "so2_ppm", 0.00)
        voc_ppm = num_input("PPM VOC in Dry Flue Gases", "voc_ppm", 0.00)

    with st.expander("Steam & Water Conditions", expanded=True):
        steam_flow = num_input("Steam Flow from Boiler (lb/hr)", "steam_flow", 100000.00, step=100.0)
        steam_pressure = num_input("Steam Pressure at Boiler (PSIG)", "steam_pressure", 225.00)
        steam_superheat = num_input("Steam Superheat (deg. F)", "steam_superheat", 0.00)
        live_steam_enthalpy = num_input(
            "Live Steam Enthalpy (Btu/lb)", "live_steam_enthalpy", 1200.90,
            help="Set to 0 to have enthalpy estimated from pressure and superheat instead.",
        )
        feed_water_temp = num_input("Boiler Feed Water Temp (deg. F)", "feed_water_temp", 250.00)
        assumed_losses = num_input("Assumed Heat Losses from Boiler (1-3%)", "assumed_losses", 3.00)

    with st.expander("Air & Air Preheater", expanded=True):
        inlet_air_temp = num_input("Inlet Air Temp to APH (deg. F)", "inlet_air_temp", 80.00)
        relative_humidity = num_input("Inlet Air Humidity to APH (%)", "relative_humidity", 80.00)
        preheated_air_temp = num_input("Preheated Air Temp out of APH (deg. F)", "preheated_air_temp", 450.00)
        flue_gas_temp_out_aph = num_input("Flue Gas Temp out of APH (deg. F)", "flue_gas_temp_out_aph", 425.00)
        aph_surface = num_input("APH Heating Surface (sq. ft.)", "aph_surface", 15000.00, step=100.0)
        aph_gas_flow_area = num_input("APH Gas Flow Cross Section (sq. ft.)", "aph_gas_flow_area", 40.00)

    submitted = st.form_submit_button("Calculate Boiler Efficiency", type="primary")


def stack_gas_df(matrix, dry_pct=True):
    rows = []
    for i in range(9):
        row = {
            "Component": COMPONENT_NAMES[i],
            "Lbs.": matrix[i][0],
            "Lb. Moles": matrix[i][1],
            "Molal Cp (Btu/lb mol-F)": matrix[i][2] if i < 8 else None,
            "Temp Diff (F)": matrix[i][3] if i < 8 else None,
            "Heat Content (Btu)": matrix[i][4],
            "Wet Gas Vol %": matrix[i][6],
            "Dry Gas Vol %": matrix[i][7] if (i < 5 or i == 8) else None,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_excel(inputs_display, pg2_items, emissions_rows, df_daf, df_actual, meta):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        meta_rows = [
            ["Factory Name", meta["factory_name"]],
            ["Boiler Number", meta["boiler_id"]],
            ["Date", meta["date"]],
            ["Run Number", meta["run_number"]],
            ["Comments", meta["comments"]],
        ]
        pd.DataFrame(meta_rows).to_excel(writer, sheet_name="Input Data", header=False, index=False, startrow=0)
        pd.DataFrame(inputs_display, columns=["Parameter", "Value", "Unit"]).to_excel(
            writer, sheet_name="Input Data", index=False, startrow=len(meta_rows) + 2
        )
        df_daf.to_excel(writer, sheet_name="Stack Gas (DAF Basis)", index=False)
        pd.DataFrame(pg2_items, columns=["Parameter", "Value", "Unit"]).to_excel(
            writer, sheet_name="Efficiency & Flows", index=False
        )
        pd.DataFrame(emissions_rows, columns=["Boiler Emissions", "lbs/hour", "lbs/ton bagasse fired", "lb/MM Btu"]).to_excel(
            writer, sheet_name="Emissions", index=False
        )
        df_actual.to_excel(writer, sheet_name="Stack Gas (Actual Burned)", index=False)
    output.seek(0)
    return output


def build_text_report(meta, inputs_display, df_daf, pg2_items, emissions_rows, df_actual):
    lines = []
    lines.append("BOILER EFFICIENCY CALCULATION".center(80))
    lines.append("")
    lines.append(meta["factory_name"].center(80))
    lines.append("")
    lines.append(f"Boiler Number: {meta['boiler_id']}")
    lines.append(f"Date:          {meta['date']}")
    lines.append(f"Run Number:    {meta['run_number']}")
    lines.append("")
    lines.append("Input Data (Basis: 100 lbs Dry Ash-Free Bagasse)")
    lines.append("-" * 60)
    for label, value, unit in inputs_display:
        val_str = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
        lines.append(f"{label:<58} {val_str:>12} {unit}")
    lines.append("")
    lines.append(f"Comments: {meta['comments']}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("STACK GAS ANALYSIS (Basis: 100 lb Dry Ash-Free Bagasse)")
    lines.append("=" * 80)
    lines.append(df_daf.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    lines.append("")
    lines.append("=" * 80)
    lines.append("EFFICIENCY, TEMPERATURES, FLOWS")
    lines.append("=" * 80)
    for label, value, unit in pg2_items:
        val_str = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
        lines.append(f"{label:<70} {val_str:>16} {unit}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("BOILER EMISSIONS")
    lines.append("=" * 80)
    header = f"{'Pollutant':<39} {'lbs/hour':>14} {'lbs/ton bagasse':>18} {'lb/MMBtu':>12}"
    lines.append(header)
    for name, v1, v2, v3 in emissions_rows:
        lines.append(f"{name:<39} {v1:>14,.6f} {v2:>18,.6f} {v3:>12,.6f}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("STACK GAS ANALYSIS (Basis: Actual Bagasse Burned)")
    lines.append("=" * 80)
    lines.append(df_actual.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return "\n".join(lines)


if submitted:
    inputs = dict(
        moisture_bagasse=moisture_bagasse, ash_bagasse=ash_bagasse,
        oxygen_dry_flue=oxygen_dry_flue, co_ppm=co_ppm, nox_ppm=nox_ppm,
        so2_ppm=so2_ppm, voc_ppm=voc_ppm, steam_flow=steam_flow,
        steam_pressure=steam_pressure, steam_superheat=steam_superheat,
        live_steam_enthalpy=live_steam_enthalpy, feed_water_temp=feed_water_temp,
        assumed_losses=assumed_losses, inlet_air_temp=inlet_air_temp,
        relative_humidity=relative_humidity, preheated_air_temp=preheated_air_temp,
        flue_gas_temp_out_aph=flue_gas_temp_out_aph, aph_surface=aph_surface,
        aph_gas_flow_area=aph_gas_flow_area,
    )

    results, errors = compute(inputs)
    st.session_state["calc_results"] = results
    st.session_state["calc_errors"] = errors

if "calc_results" in st.session_state:
    results = st.session_state["calc_results"]
    errors = st.session_state["calc_errors"]

    if results is None:
        for e in errors:
            st.error(e)
    else:
        for e in errors:
            st.warning(e)

        st.success("Calculation complete.")

        st.subheader("Key Results")
        c1, c2 = st.columns(2)
        c1.metric("Actual Boiler Efficiency", f"{results['actual_boiler_eff_used']:.2f} %")
        c2.metric("Theoretical Max Efficiency", f"{results['E_theoretical_max_boiler_eff']:.2f} %")
        c1.metric("Excess Air", f"{results['E1_excess_air_percent']:.2f} %")
        c2.metric("Bagasse Burned (as fired)", f"{results['S9_lbs_as_fired_bagasse_required']:,.0f} lb/hr")
        c1.metric("Heat Input", f"{results['heat_input_mmbtu_hr']:,.2f} MMBtu/hr")
        c2.metric("Boiler Outlet Temp", f"{results['T3_calc_boiler_outlet_temp']:.0f} °F")

        # --- Build shared data for tables/exports ---
        inputs_display = [
            ("Moisture % Bagasse", moisture_bagasse, ""),
            ("Ash % Bagasse", ash_bagasse, ""),
            ("Inlet Ambient Air Temp to Air Preheater, deg. F", inlet_air_temp, ""),
            ("Inlet Relative Humidity in Air to Air Preheater", relative_humidity, ""),
            ("Preheated Air Temp Leaving Air Preheater, deg. F", preheated_air_temp, ""),
            ("Flue Gas Temp Out of Air Preheater, deg. F", flue_gas_temp_out_aph, ""),
            ("% Oxygen in Dry Flue Gases", oxygen_dry_flue, ""),
            ("PPM Carbon Monoxide in Dry Flue Gases", co_ppm, ""),
            ("PPM Nitric Oxide in Dry Flue Gases", nox_ppm, ""),
            ("PPM Sulfur Dioxide in Dry Flue Gases", so2_ppm, ""),
            ("PPM Volatile Organic Compounds in Dry Flue Gases", voc_ppm, ""),
            ("Steam Flow from Boiler, lb/hr", steam_flow, ""),
            ("Boiler Pressure, PSIG", steam_pressure, ""),
            ("Steam Superheat, deg. F", steam_superheat, ""),
            ("Live Steam Enthalpy, Btu/lb", live_steam_enthalpy, ""),
            ("Boiler Feed Water Temperature, deg. F", feed_water_temp, ""),
            ("Air Preheater Heating Surface, sq. ft.", aph_surface, ""),
            ("Assumed Heat Losses from Boiler (1-3%)", assumed_losses, ""),
            ("Air Preheater Flue Gas Flow Area, sq. ft.", aph_gas_flow_area, ""),
        ]

        pg2_items = [
            ("Excess Air, %", results["E1_excess_air_percent"], ""),
            ("Theoretical Maximum Boiler Efficiency, %", results["E_theoretical_max_boiler_eff"], ""),
            ("Heat Losses Assumed in Boiler, %", assumed_losses, ""),
            ("Actual Boiler Efficiency Used, %", results["actual_boiler_eff_used"], ""),
            ("Theoretical Maximum Furnace Temperature, deg. F", results["T5_theoretical_max_furnace_temp"], ""),
            ("Calculated Boiler Outlet Temperature, deg. F", results["T3_calc_boiler_outlet_temp"], ""),
            ("Bagasse Burned (as fired), lb/hr", results["S9_lbs_as_fired_bagasse_required"], ""),
            ("Gross Calorific Value of Bagasse, Btu/lb", results["gross_cal_val_as_fired"], ""),
            ("Heat Transferred to Steam/lb bagasse burned, Btu", results["S8_heat_transferred_to_steam_per_lb_wet_bagasse"], ""),
            ("Heat Supplied by Boiler, Btu/lb steam", results["heat_supplied_per_lb_steam"], ""),
            ("Heat Input, Btu/hr", results["S10_heat_input_as_fired_btu_hr"], ""),
            ("Lbs Steam Produced per Lb Bagasse (as fired)", results["lbs_steam_per_lb_bagasse_fired"], ""),
            ("Combustion Air, lb/hr", results["combustion_air_total_lb_hr"], ""),
            ("Volume of Combustion Air, SCFM", results["V1_vol_comb_air_SCFM"], ""),
            ("Volume of Combustion Air to Air Preheater, ACFM", results["V0_vol_comb_air_to_APH_ACFM"], ""),
            ("Volume of Combustion Air Out of Air Preheater, ACFM", results["V2_vol_comb_air_out_APH_ACFM"], ""),
            ("Weight of Flue Gases, lb/hr", results["weight_flue_gases_total_lb_hr"], ""),
            ("Volume of Flue Gases, SCFM", results["V5_vol_flue_gas_SCFM"], ""),
            ("Volume of Flue Gases, DSCFM", results["V5_vol_flue_gas_DSCFM"], ""),
            ("Volume of Flue Gases (Boiler Outlet), ACFM", results["V3_vol_flue_gas_boiler_outlet_ACFM"], ""),
            ("Volume of Flue Gases (Air Heater Outlet), ACFM", results["V4_vol_flue_gas_APH_outlet_ACFM"], ""),
            ("Flue Gas Velocity at Air Heater Inlet, Ft/Sec", results["flue_gas_velocity_AH_inlet_ft_sec"], ""),
            ("Flue Gas Velocity at Air Heater Outlet, Ft/Sec", results["flue_gas_velocity_AH_outlet_ft_sec"], ""),
            ("Average Flue Gas Velocity Through Air Heater, Ft/Sec", results["avg_flue_gas_velocity_AH_ft_sec"], ""),
            ("Overall Heat Transfer Coeff. in Air Preheater, Btu/hr/ft2/F", results["U_ohtc_aph"], ""),
        ]

        emissions_rows = [
            ("Carbon Monoxide", results["emissions_co_lb_hr"], results["emissions_co_lb_ton"], results["emissions_co_lb_mmbtu"]),
            ("Nitrogen Oxides (as NO2)", results["emissions_nox_as_no2_lb_hr"], results["emissions_nox_lb_ton"], results["emissions_nox_lb_mmbtu"]),
            ("Sulfur Dioxide", results["emissions_so2_lb_hr"], results["emissions_so2_lb_ton"], results["emissions_so2_lb_mmbtu"]),
            ("Volatile Organic Compounds (as C3H8)", results["emissions_voc_as_c3h8_lb_hr"], results["emissions_voc_lb_ton"], results["emissions_voc_lb_mmbtu"]),
        ]

        df_daf = stack_gas_df(results["P_analysis"])
        df_actual = stack_gas_df(results["Z_actual_analysis"])

        tab1, tab2, tab3, tab4 = st.tabs(["Efficiency & Flows", "Emissions", "Stack Gas (DAF)", "Stack Gas (Actual)"])

        with tab1:
            st.dataframe(
                pd.DataFrame(pg2_items, columns=["Parameter", "Value", "Unit"]).drop(columns=["Unit"]),
                hide_index=True, width='stretch',
                column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
            )

        with tab2:
            st.dataframe(
                pd.DataFrame(emissions_rows, columns=["Pollutant", "lb/hr", "lb/ton bagasse", "lb/MMBtu"]),
                hide_index=True, width='stretch',
            )

        with tab3:
            st.caption("Basis: 100 lb Dry Ash-Free Bagasse")
            st.dataframe(df_daf, hide_index=True, width='stretch')

        with tab4:
            st.caption("Basis: Actual Bagasse Burned")
            st.dataframe(df_actual, hide_index=True, width='stretch')

        meta = dict(factory_name=factory_name, boiler_id=boiler_id, date=date_str,
                    run_number=run_number, comments=comments)

        st.subheader("Download Report")
        d1, d2 = st.columns(2)

        excel_bytes = build_excel(inputs_display, pg2_items, emissions_rows, df_daf, df_actual, meta)
        d1.download_button(
            "⬇️ Excel Report",
            data=excel_bytes,
            file_name=f"{boiler_id or 'Boiler'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )

        text_report = build_text_report(meta, inputs_display, df_daf, pg2_items, emissions_rows, df_actual)
        d2.download_button(
            "⬇️ Text Report",
            data=text_report,
            file_name=f"{boiler_id or 'Boiler'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            width='stretch',
        )

        with st.expander("Full Printout (classic format)"):
            st.code(text_report, language=None)

st.divider()
st.caption("© Boiler Efficiency Calculator — based on the BOILERE1 Program.")

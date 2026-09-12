"""Core calculation engine for the Boiler Efficiency Calculator.

This is a line-for-line Python port of the BOILERE1-derived JavaScript
calculation found in boiler_eff.html, so that results match exactly.
"""
import math

D1 = 48.205  # Carbon %
D2 = 6.667   # Hydrogen %
D3 = 45.128  # Oxygen %
D4 = 8350.0  # Heating value

COMPONENT_NAMES = [
    "Carbon Dioxide", "Carbon Monoxide", "Nitric Oxide", "Oxygen", "Nitrogen",
    "Water of Combustion", "Water in Bagasse", "Water in Air", "Total",
]


class CalculationError(Exception):
    pass


def molal_specific_heat(T, b0, b1, b2, b3, b4):
    return b0 + b1 * T + b2 * T ** 2 + b3 * T ** 3 + b4 * T ** 4


def invert_3x3(m):
    det = (m[0][0] * (m[1][1] * m[2][2] - m[2][1] * m[1][2])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    if abs(det) < 1e-9:
        return None
    inv_det = 1.0 / det
    return [
        [(m[1][1] * m[2][2] - m[2][1] * m[1][2]) * inv_det,
         (m[0][2] * m[2][1] - m[0][1] * m[2][2]) * inv_det,
         (m[0][1] * m[1][2] - m[0][2] * m[1][1]) * inv_det],
        [(m[1][2] * m[2][0] - m[1][0] * m[2][2]) * inv_det,
         (m[0][0] * m[2][2] - m[0][2] * m[2][0]) * inv_det,
         (m[1][0] * m[0][2] - m[0][0] * m[1][2]) * inv_det],
        [(m[1][0] * m[2][1] - m[2][0] * m[1][1]) * inv_det,
         (m[2][0] * m[0][1] - m[0][0] * m[2][1]) * inv_det,
         (m[0][0] * m[1][1] - m[1][0] * m[0][1]) * inv_det],
    ]


def mat_vec(m, v):
    result = [0.0, 0.0, 0.0]
    for i in range(3):
        for j in range(3):
            result[i] += m[i][j] * v[j]
    return result


def compute(inputs):
    """Run the full boiler efficiency calculation.

    `inputs` is a dict with the numeric fields used by the original app.
    Returns (results_dict, errors_list). If errors_list is non-empty,
    results_dict may be None or partial.
    """
    errors = []

    S1 = inputs["steam_flow"]
    S2 = inputs["steam_pressure"]
    S3 = inputs["steam_superheat"]
    R5_live_steam_enthalpy = inputs["live_steam_enthalpy"]
    S4_feed_water_temp = inputs["feed_water_temp"]
    S5_aph_surface = inputs["aph_surface"]
    S6_assumed_losses = inputs["assumed_losses"]
    M_moisture_bagasse = inputs["moisture_bagasse"]
    A_ash_bagasse = inputs["ash_bagasse"]
    T1_inlet_air_temp = inputs["inlet_air_temp"]
    H_relative_humidity = inputs["relative_humidity"]
    T2_preheated_air_temp = inputs["preheated_air_temp"]
    T4_flue_gas_temp_out_aph = inputs["flue_gas_temp_out_aph"]
    P_oxygen_dry_flue = inputs["oxygen_dry_flue"]
    Q1_co_ppm = inputs["co_ppm"]
    R1_nox_ppm = inputs["nox_ppm"]
    R2_so2_ppm = inputs["so2_ppm"]
    W2_voc_ppm = inputs["voc_ppm"]
    A1_aph_gas_flow_area = inputs["aph_gas_flow_area"]

    if T1_inlet_air_temp > 200:
        errors.append("Inlet air temperature above 200 deg. F (out of range).")
        return None, errors

    S7_live_steam_enthalpy_calc = R5_live_steam_enthalpy
    Q_co_fraction = Q1_co_ppm / 10000.0
    R_no_fraction = R1_nox_ppm / 10000.0

    Z1 = P_oxygen_dry_flue * 0.232 / 100 / 32 + P_oxygen_dry_flue * 0.768 / 100 / 28 - 0.232 / 32
    Z2 = -P_oxygen_dry_flue / 12 / 100 + 16 * P_oxygen_dry_flue / 12 / 32 / 100 + 1 / 12 - 16 / (12 * 32)
    Z3 = -16 * P_oxygen_dry_flue / 100 / 14 / 32 + P_oxygen_dry_flue / 14 / 100 - P_oxygen_dry_flue / 28 / 100 + 16 / (14 * 32)
    Z4 = Q_co_fraction * 0.232 / 100 / 32 + Q_co_fraction * 0.768 / 100 / 28
    Z5 = -Q_co_fraction / 12 / 100 + 16 * Q_co_fraction / 100 / 12 / 32 + 1 / 12
    Z6 = -16 * Q_co_fraction / 14 / 32 / 100 + Q_co_fraction / 14 / 100 - Q_co_fraction / 28 / 100
    Z7 = R_no_fraction * 0.232 / 100 / 32 + 0.768 * R_no_fraction / 28 / 100
    Z8 = -R_no_fraction / 100 / 12 + R_no_fraction * 16 / 100 / 12 / 32
    Z9 = -R_no_fraction * 16 / 100 / 14 / 32 + R_no_fraction / 100 / 14 - R_no_fraction / 28 / 100 - 1 / 14

    Y1 = (-P_oxygen_dry_flue * D1 / 100 / 12 + D3 * (1 - P_oxygen_dry_flue / 100) / 32
          + D1 * 16 * (P_oxygen_dry_flue / 100 - 1) / 12 / 32
          + D2 * 16 * (P_oxygen_dry_flue / 100 - 1) / 2 / 32)
    Y2 = (-Q_co_fraction * D1 / 100 / 12 - Q_co_fraction * D3 / 100 / 32
          + Q_co_fraction * D1 * 16 / 100 / 12 / 32
          + Q_co_fraction * D2 * 16 / 100 / 2 / 32 + D1 / 12)
    Y3 = (-R_no_fraction * D1 / 100 / 12 - R_no_fraction * D3 / 100 / 32
          + R_no_fraction * D1 * 16 / 100 / 12 / 32
          + R_no_fraction * D2 * 16 / 100 / 2 / 32)

    C_matrix = [[Z1, Z2, Z3], [Z4, Z5, Z6], [Z7, Z8, Z9]]
    B_vector = [Y1, Y2, Y3]

    inv_C = invert_3x3(C_matrix)
    if inv_C is None:
        errors.append("Matrix is singular, cannot solve simultaneous equations. "
                       "Check input values (especially O2, CO, NOx).")
        return None, errors

    X_solution = mat_vec(inv_C, B_vector)
    X_lbs_dry_air, Y_lbs_C_to_CO2, Z_lbs_N2_to_NO = X_solution

    O2_in_dry_air = X_lbs_dry_air * 0.232
    N2_in_dry_air = X_lbs_dry_air * 0.768

    P1_CO2 = Y_lbs_C_to_CO2 * 44 / 12
    P2_CO = (D1 - Y_lbs_C_to_CO2) * 28 / 12
    P3_NO = Z_lbs_N2_to_NO * 30 / 14
    P4_O2 = (O2_in_dry_air + D3 - Y_lbs_C_to_CO2 * 32 / 12
             - (D1 - Y_lbs_C_to_CO2) * 16 / 12 - Z_lbs_N2_to_NO * 16 / 14 - D2 * 16 / 2)
    P5_N2 = N2_in_dry_air - Z_lbs_N2_to_NO
    P6_H2O_combustion = D2 * 18 / 2

    bagasse_denom = 100 - A_ash_bagasse - M_moisture_bagasse
    if abs(bagasse_denom) < 1e-6:
        errors.append("Sum of Ash and Moisture % Bagasse cannot be 100%.")
        return None, errors
    B_total_bagasse_for_100_DAF = 100 * 100 / bagasse_denom
    P7_H2O_in_bagasse = B_total_bagasse_for_100_DAF * M_moisture_bagasse / 100

    if T1_inlet_air_temp <= 90:
        H1 = (0.000874666561 + 0.000020125603 * T1_inlet_air_temp
              + 2.55146562e-6 * T1_inlet_air_temp ** 2
              - 2.40747862e-8 * T1_inlet_air_temp ** 3
              + 3.86800701e-10 * T1_inlet_air_temp ** 4)
    elif T1_inlet_air_temp <= 130:
        H1 = (-0.208469990707 + 0.0068386665 * T1_inlet_air_temp
              - 0.000075049999 * T1_inlet_air_temp ** 2
              + 3.18333331e-7 * T1_inlet_air_temp ** 3)
    else:
        H1 = (-904.841207678 + 29.27295 * T1_inlet_air_temp
              - 0.3775272 * T1_inlet_air_temp ** 2
              + 0.002426797 * T1_inlet_air_temp ** 3
              - 0.000007777666 * T1_inlet_air_temp ** 4
              + 9.94852000e-9 * T1_inlet_air_temp ** 5)
    H2_actual_water_per_lb_dry_air = H1 * H_relative_humidity / 100
    P8_H2O_in_air = X_lbs_dry_air * H2_actual_water_per_lb_dry_air

    heat_loss_incomplete_comb_CO = (D1 - Y_lbs_C_to_CO2) * 10135.1
    water_vapor_heat_term = (P6_H2O_combustion + P7_H2O_in_bagasse) * (1070.9 - (T1_inlet_air_temp - 40) * 0.5675)
    C_heat_released = 100 * D4 - heat_loss_incomplete_comb_CO - water_vapor_heat_term

    # P_analysis: 9 rows x 8 cols. cols: 0 lbs,1 lbmoles,2 Cp,3 dT,4 heat,5 MW,6 wet%,7 dry%
    P = [[0.0] * 8 for _ in range(9)]
    P[0][0], P[1][0], P[2][0] = P1_CO2, P2_CO, P3_NO
    P[3][0], P[4][0], P[5][0] = P4_O2, P5_N2, P6_H2O_combustion
    P[6][0], P[7][0] = P7_H2O_in_bagasse, P8_H2O_in_air
    P[0][5], P[1][5], P[2][5] = 44.0, 28.0, 30.0
    P[3][5], P[4][5], P[5][5] = 32.0, 28.0, 18.0
    P[6][5], P[7][5] = 18.0, 18.0
    for i in range(8):
        if P[i][5] != 0:
            P[i][1] = P[i][0] / P[i][5]

    total_dry_moles_for_ppm_calc = sum(P[i][1] for i in range(5)) or 1e-9

    R3_SO2_moles = R2_so2_ppm * total_dry_moles_for_ppm_calc / 1000000.0
    R4_SO2_lbs = R3_SO2_moles * 64.0
    W3_VOC_moles = W2_voc_ppm * total_dry_moles_for_ppm_calc / 1000000.0
    W4_VOC_lbs_as_CH4 = W3_VOC_moles * 16.0

    temp_diff_P = T4_flue_gas_temp_out_aph - T1_inlet_air_temp
    for i in range(8):
        P[i][3] = temp_diff_P
    T_cp_P = T4_flue_gas_temp_out_aph
    P[0][2] = molal_specific_heat(T_cp_P, 8.662768808515, 0.0029821577147, -9.16288392e-7, 1.66998526e-10, -1.32316049e-14)
    P[1][2] = molal_specific_heat(T_cp_P, 6.951182636762, 0.0000808081517, 3.01692378e-7, -1.05930043e-10, 1.09966077e-14)
    P[2][2] = molal_specific_heat(T_cp_P, 7.122349487607, 0.0000939566571, 3.04296002e-7, -1.10185684e-10, 1.16096792e-14)
    P[3][2] = molal_specific_heat(T_cp_P, 6.955593537838, 0.0006110843706, 1.97256425e-8, -4.42793203e-11, 6.33390329e-15)
    P[4][2] = molal_specific_heat(T_cp_P, 6.955458834414, 0.0000017042737, 3.19710501e-7, -1.04701709e-10, 1.04940056e-14)
    cp_h2o_p = molal_specific_heat(T_cp_P, 7.993663783892, 0.000300684918, 4.04862076e-7, -1.30505019e-10, 1.29129087e-14)
    for i in (5, 6, 7):
        P[i][2] = cp_h2o_p
    for i in range(8):
        P[i][4] = P[i][1] * P[i][2] * P[i][3]
    for j in (0, 1, 4):
        P[8][j] = sum(P[i][j] for i in range(8))

    total_lb_moles_wet_P = P[8][1]
    total_lb_moles_dry_P = sum(P[i][1] for i in range(5))

    if total_lb_moles_wet_P > 1e-9:
        for i in range(8):
            P[i][6] = (P[i][1] / total_lb_moles_wet_P) * 100
    if total_lb_moles_dry_P > 1e-9:
        for i in range(5):
            P[i][7] = (P[i][1] / total_lb_moles_dry_P) * 100
    P[8][6] = sum(P[i][6] for i in range(8))
    P[8][7] = sum(P[i][7] for i in range(5))

    E_theoretical_max_boiler_eff = 0 if abs(100 * D4) < 1e-9 else (C_heat_released - P[8][4]) / (100 * D4) * 100
    G_theoretical_dry_air = (D1 * 32 / 12 + D2 * 16 / 2 - D3) / 0.232
    E1_excess_air_percent = 0 if abs(G_theoretical_dry_air) < 1e-9 else (X_lbs_dry_air - G_theoretical_dry_air) / G_theoretical_dry_air * 100

    # Q_air_analysis: 4 rows x 6 cols (N2, O2, H2O, Total)
    Q = [[0.0] * 6 for _ in range(4)]
    Q[0][0], Q[1][0], Q[2][0] = N2_in_dry_air, O2_in_dry_air, P8_H2O_in_air
    Q[0][5], Q[1][5], Q[2][5] = 28.0, 32.0, 18.0
    for i in range(3):
        if Q[i][5] != 0:
            Q[i][1] = Q[i][0] / Q[i][5]
    T_cp_Q = T2_preheated_air_temp
    Q[0][2] = molal_specific_heat(T_cp_Q, 6.955458834414, 0.0000017042737, 3.19710501e-7, -1.04701709e-10, 1.04940056e-14)
    Q[1][2] = molal_specific_heat(T_cp_Q, 6.955593537838, 0.0006110843706, 1.97256425e-8, -4.42793203e-11, 6.33390329e-15)
    Q[2][2] = molal_specific_heat(T_cp_Q, 7.993663783892, 0.000300684918, 4.04862076e-7, -1.30505019e-10, 1.29129087e-14)
    temp_diff_Q = T2_preheated_air_temp - T1_inlet_air_temp
    for i in range(3):
        Q[i][3] = temp_diff_Q
    for i in range(3):
        Q[i][4] = Q[i][1] * Q[i][2] * Q[i][3]
    for j in (0, 1, 4):
        Q[3][j] = sum(Q[i][j] for i in range(3))

    # Trial and error search for T3 (boiler outlet) and T5 (theoretical max furnace temp)
    R = [[0.0] * 6 for _ in range(9)]
    for i in range(8):
        R[i][0], R[i][1] = P[i][0], P[i][1]

    T_iter = T4_flue_gas_temp_out_aph - 0.5
    T3_found = False
    T3_calc_boiler_outlet_temp = 0.0
    T5_theoretical_max_furnace_temp = 0.0
    max_iterations = 10000
    current_iteration = 0

    while current_iteration < max_iterations:
        T_iter += 0.5
        current_iteration += 1
        R[0][2] = molal_specific_heat(T_iter, 8.662768808515, 0.0029821577147, -9.16288392e-7, 1.66998526e-10, -1.32316049e-14)
        R[1][2] = molal_specific_heat(T_iter, 6.951182636762, 0.0000808081517, 3.01692378e-7, -1.05930043e-10, 1.09966077e-14)
        R[2][2] = molal_specific_heat(T_iter, 7.122349487607, 0.0000939566571, 3.04296002e-7, -1.10185684e-10, 1.16096792e-14)
        R[3][2] = molal_specific_heat(T_iter, 6.955593537838, 0.0006110843706, 1.97256425e-8, -4.42793203e-11, 6.33390329e-15)
        R[4][2] = molal_specific_heat(T_iter, 6.955458834414, 0.0000017042737, 3.19710501e-7, -1.04701709e-10, 1.04940056e-14)
        cp_h2o_r = molal_specific_heat(T_iter, 7.993663783892, 0.000300684918, 4.04862076e-7, -1.30505019e-10, 1.29129087e-14)
        for i in (5, 6, 7):
            R[i][2] = cp_h2o_r
        temp_diff_R = T_iter - T1_inlet_air_temp
        for i in range(8):
            R[i][3] = temp_diff_R
        for i in range(8):
            R[i][4] = R[i][1] * R[i][2] * R[i][3]
        R[8][4] = sum(R[i][4] for i in range(8))

        if not T3_found and R[8][4] >= (P[8][4] + Q[3][4]):
            T3_calc_boiler_outlet_temp = T_iter
            T3_found = True
        if R[8][4] >= (C_heat_released + Q[3][4]):
            T5_theoretical_max_furnace_temp = T_iter
            if T3_found:
                break
        if T_iter > 4500:
            errors.append("Warning: T3/T5 iteration exceeded 4500F.")
            if not T3_found:
                T3_calc_boiler_outlet_temp = T_iter
            if T5_theoretical_max_furnace_temp == 0:
                T5_theoretical_max_furnace_temp = T_iter
            break
    else:
        errors.append("Warning: Max iterations for T3/T5.")
        if not T3_found:
            T3_calc_boiler_outlet_temp = T_iter
        if T5_theoretical_max_furnace_temp == 0:
            T5_theoretical_max_furnace_temp = T_iter

    if R5_live_steam_enthalpy > 0:
        h_feedwater = S4_feed_water_temp - 32.0
        S7_heat_to_steam_btu_hr = S1 * (S7_live_steam_enthalpy_calc - h_feedwater)
    else:
        h_steam_calc = (1158.13 + 0.5439531818 * S2 - 0.003075257085 * S2 ** 2
                         + 9.66408644e-6 * S2 ** 3 - 1.54910405e-8 * S2 ** 4
                         + 9.71608424e-12 * S2 ** 5 + 0.5 * S3)
        h_feedwater = S4_feed_water_temp - 32.0
        S7_heat_to_steam_btu_hr = S1 * (h_steam_calc - h_feedwater)

    W_lbs_wet_bagasse_for_100_DAF = B_total_bagasse_for_100_DAF
    actual_boiler_eff_used = E_theoretical_max_boiler_eff - S6_assumed_losses
    S8_heat_transferred_to_steam_per_lb_wet_bagasse = (
        0 if abs(W_lbs_wet_bagasse_for_100_DAF) < 1e-9
        else D4 * 100.0 / W_lbs_wet_bagasse_for_100_DAF * (actual_boiler_eff_used / 100.0)
    )
    S9_lbs_as_fired_bagasse_required = (
        0 if abs(S8_heat_transferred_to_steam_per_lb_wet_bagasse) < 1e-9
        else S7_heat_to_steam_btu_hr / S8_heat_transferred_to_steam_per_lb_wet_bagasse
    )
    gross_cal_val_as_fired = D4 * ((100.0 - (M_moisture_bagasse + A_ash_bagasse)) / 100.0)
    S10_heat_input_as_fired_btu_hr = S9_lbs_as_fired_bagasse_required * gross_cal_val_as_fired
    F1_factor_actual_to_basis_bagasse_wt = (
        0 if abs(W_lbs_wet_bagasse_for_100_DAF) < 1e-9
        else S9_lbs_as_fired_bagasse_required / W_lbs_wet_bagasse_for_100_DAF
    )

    V1_vol_comb_air_SCFM = Q[3][1] * F1_factor_actual_to_basis_bagasse_wt * 385.5 / 60.0
    V0_vol_comb_air_to_APH_ACFM = V1_vol_comb_air_SCFM * (460 + T1_inlet_air_temp) / (460 + 68)
    V2_vol_comb_air_out_APH_ACFM = V1_vol_comb_air_SCFM * (460 + T2_preheated_air_temp) / (460 + 68)
    V5_vol_flue_gas_SCFM = P[8][1] * F1_factor_actual_to_basis_bagasse_wt * 385.5 / 60.0
    dry_gas_mole_fraction = total_lb_moles_dry_P / total_lb_moles_wet_P if total_lb_moles_wet_P > 1e-9 else 0
    V5_vol_flue_gas_DSCFM = V5_vol_flue_gas_SCFM * dry_gas_mole_fraction
    V3_vol_flue_gas_boiler_outlet_ACFM = V5_vol_flue_gas_SCFM * (460 + T3_calc_boiler_outlet_temp) / (460 + 68)
    V4_vol_flue_gas_APH_outlet_ACFM = V5_vol_flue_gas_SCFM * (460 + T4_flue_gas_temp_out_aph) / (460 + 68)

    Q_aph_total_btu_hr = F1_factor_actual_to_basis_bagasse_wt * Q[3][4]
    delta_T_hot_end = T3_calc_boiler_outlet_temp - T2_preheated_air_temp
    delta_T_cold_end = T4_flue_gas_temp_out_aph - T1_inlet_air_temp
    U_ohtc_aph = 0.0
    if S5_aph_surface > 1e-9:
        if abs(delta_T_hot_end - delta_T_cold_end) < 1e-6:
            if delta_T_hot_end > 1e-6:
                lmtd = delta_T_hot_end
                if abs(S5_aph_surface * lmtd) > 1e-9:
                    U_ohtc_aph = Q_aph_total_btu_hr / (S5_aph_surface * lmtd)
        elif delta_T_hot_end > 1e-6 and delta_T_cold_end > 1e-6 and (delta_T_hot_end / delta_T_cold_end) > 0:
            lmtd = (delta_T_hot_end - delta_T_cold_end) / math.log(delta_T_hot_end / delta_T_cold_end)
            if abs(S5_aph_surface * lmtd) > 1e-9:
                U_ohtc_aph = Q_aph_total_btu_hr / (S5_aph_surface * lmtd)

    emissions_co_lb_hr = P[1][0] * F1_factor_actual_to_basis_bagasse_wt
    emissions_nox_as_no2_lb_hr = P[2][0] * F1_factor_actual_to_basis_bagasse_wt * (46.0 / 30.0)
    emissions_so2_lb_hr = R4_SO2_lbs * F1_factor_actual_to_basis_bagasse_wt
    emissions_voc_as_c3h8_lb_hr = W4_VOC_lbs_as_CH4 * F1_factor_actual_to_basis_bagasse_wt * (44.0 / 16.0)
    tons_bagasse_fired_hr = S9_lbs_as_fired_bagasse_required / 2000.0 if S9_lbs_as_fired_bagasse_required > 1e-9 else 0
    emissions_co_lb_ton = emissions_co_lb_hr / tons_bagasse_fired_hr if tons_bagasse_fired_hr > 1e-9 else 0
    emissions_nox_lb_ton = emissions_nox_as_no2_lb_hr / tons_bagasse_fired_hr if tons_bagasse_fired_hr > 1e-9 else 0
    emissions_so2_lb_ton = emissions_so2_lb_hr / tons_bagasse_fired_hr if tons_bagasse_fired_hr > 1e-9 else 0
    emissions_voc_lb_ton = emissions_voc_as_c3h8_lb_hr / tons_bagasse_fired_hr if tons_bagasse_fired_hr > 1e-9 else 0
    heat_input_mmbtu_hr = S10_heat_input_as_fired_btu_hr / 1000000.0
    emissions_co_lb_mmbtu = emissions_co_lb_hr / heat_input_mmbtu_hr if heat_input_mmbtu_hr > 1e-9 else 0
    emissions_nox_lb_mmbtu = emissions_nox_as_no2_lb_hr / heat_input_mmbtu_hr if heat_input_mmbtu_hr > 1e-9 else 0
    emissions_so2_lb_mmbtu = emissions_so2_lb_hr / heat_input_mmbtu_hr if heat_input_mmbtu_hr > 1e-9 else 0
    emissions_voc_lb_mmbtu = emissions_voc_as_c3h8_lb_hr / heat_input_mmbtu_hr if heat_input_mmbtu_hr > 1e-9 else 0

    Z = [row[:] for row in P]
    for i in range(9):
        Z[i][0] = P[i][0] * F1_factor_actual_to_basis_bagasse_wt
        Z[i][1] = P[i][1] * F1_factor_actual_to_basis_bagasse_wt
        Z[i][4] = P[i][4] * F1_factor_actual_to_basis_bagasse_wt

    combustion_air_total_lb_hr = Q[3][0] * F1_factor_actual_to_basis_bagasse_wt
    weight_flue_gases_total_lb_hr = P[8][0] * F1_factor_actual_to_basis_bagasse_wt
    heat_supplied_per_lb_steam = S7_heat_to_steam_btu_hr / S1 if abs(S1) > 1e-9 else 0
    lbs_steam_per_lb_bagasse_fired = S1 / S9_lbs_as_fired_bagasse_required if abs(S9_lbs_as_fired_bagasse_required) > 1e-9 else 0
    flue_gas_velocity_AH_inlet_ft_sec = V3_vol_flue_gas_boiler_outlet_ACFM / 60.0 / A1_aph_gas_flow_area if abs(A1_aph_gas_flow_area) > 1e-9 else 0
    flue_gas_velocity_AH_outlet_ft_sec = V4_vol_flue_gas_APH_outlet_ACFM / 60.0 / A1_aph_gas_flow_area if abs(A1_aph_gas_flow_area) > 1e-9 else 0
    avg_flue_gas_velocity_AH_ft_sec = ((V3_vol_flue_gas_boiler_outlet_ACFM + V4_vol_flue_gas_APH_outlet_ACFM) / 2.0 / 60.0 / A1_aph_gas_flow_area) if abs(A1_aph_gas_flow_area) > 1e-9 else 0

    results = {
        "X_lbs_dry_air": X_lbs_dry_air,
        "P_analysis": P,
        "Q_air_analysis": Q,
        "Z_actual_analysis": Z,
        "E_theoretical_max_boiler_eff": E_theoretical_max_boiler_eff,
        "E1_excess_air_percent": E1_excess_air_percent,
        "actual_boiler_eff_used": actual_boiler_eff_used,
        "T3_calc_boiler_outlet_temp": T3_calc_boiler_outlet_temp,
        "T5_theoretical_max_furnace_temp": T5_theoretical_max_furnace_temp,
        "S9_lbs_as_fired_bagasse_required": S9_lbs_as_fired_bagasse_required,
        "gross_cal_val_as_fired": gross_cal_val_as_fired,
        "S8_heat_transferred_to_steam_per_lb_wet_bagasse": S8_heat_transferred_to_steam_per_lb_wet_bagasse,
        "heat_supplied_per_lb_steam": heat_supplied_per_lb_steam,
        "S10_heat_input_as_fired_btu_hr": S10_heat_input_as_fired_btu_hr,
        "lbs_steam_per_lb_bagasse_fired": lbs_steam_per_lb_bagasse_fired,
        "combustion_air_total_lb_hr": combustion_air_total_lb_hr,
        "V1_vol_comb_air_SCFM": V1_vol_comb_air_SCFM,
        "V0_vol_comb_air_to_APH_ACFM": V0_vol_comb_air_to_APH_ACFM,
        "V2_vol_comb_air_out_APH_ACFM": V2_vol_comb_air_out_APH_ACFM,
        "weight_flue_gases_total_lb_hr": weight_flue_gases_total_lb_hr,
        "V5_vol_flue_gas_SCFM": V5_vol_flue_gas_SCFM,
        "V5_vol_flue_gas_DSCFM": V5_vol_flue_gas_DSCFM,
        "V3_vol_flue_gas_boiler_outlet_ACFM": V3_vol_flue_gas_boiler_outlet_ACFM,
        "V4_vol_flue_gas_APH_outlet_ACFM": V4_vol_flue_gas_APH_outlet_ACFM,
        "flue_gas_velocity_AH_inlet_ft_sec": flue_gas_velocity_AH_inlet_ft_sec,
        "flue_gas_velocity_AH_outlet_ft_sec": flue_gas_velocity_AH_outlet_ft_sec,
        "avg_flue_gas_velocity_AH_ft_sec": avg_flue_gas_velocity_AH_ft_sec,
        "U_ohtc_aph": U_ohtc_aph,
        "emissions_co_lb_hr": emissions_co_lb_hr,
        "emissions_co_lb_ton": emissions_co_lb_ton,
        "emissions_co_lb_mmbtu": emissions_co_lb_mmbtu,
        "emissions_nox_as_no2_lb_hr": emissions_nox_as_no2_lb_hr,
        "emissions_nox_lb_ton": emissions_nox_lb_ton,
        "emissions_nox_lb_mmbtu": emissions_nox_lb_mmbtu,
        "emissions_so2_lb_hr": emissions_so2_lb_hr,
        "emissions_so2_lb_ton": emissions_so2_lb_ton,
        "emissions_so2_lb_mmbtu": emissions_so2_lb_mmbtu,
        "emissions_voc_as_c3h8_lb_hr": emissions_voc_as_c3h8_lb_hr,
        "emissions_voc_lb_ton": emissions_voc_lb_ton,
        "emissions_voc_lb_mmbtu": emissions_voc_lb_mmbtu,
        "heat_input_mmbtu_hr": heat_input_mmbtu_hr,
    }
    return results, errors

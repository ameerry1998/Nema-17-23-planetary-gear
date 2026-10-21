"""Codex (secondary agent, 2026-10-21): steady brake loads and uncertainty, never synthetic test results."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent


def torque_interval(tight_N, slack_N, arm_tight_mm, arm_slack_mm, force_error_N, arm_error_mm):
    if tight_N < slack_N or slack_N < 0 or force_error_N < 0 or arm_error_mm < 0:
        raise ValueError('Use nonnegative tensions/errors with the tight side identified')
    if min(arm_tight_mm, arm_slack_mm) <= arm_error_mm:
        raise ValueError('Moment arms must remain positive within uncertainty')
    nominal = (tight_N * arm_tight_mm - slack_N * arm_slack_mm) / 1000
    low = ((tight_N - force_error_N) * (arm_tight_mm - arm_error_mm) - (slack_N + force_error_N) * (arm_slack_mm + arm_error_mm)) / 1000
    high = ((tight_N + force_error_N) * (arm_tight_mm + arm_error_mm) - max(0, slack_N - force_error_N) * (arm_slack_mm - arm_error_mm)) / 1000
    return dict(nominal_Nm=nominal, lower_Nm=low, upper_Nm=high,
                scope='Conservative independent force/arm error bounds; no gauge bandwidth or alignment validation')


def rotor_positions(c):
    hub_end = c['hub_start_z_mm'] + c['hub_body_length_mm']
    face = hub_end + c['plate_hub_boss_length_mm']
    rim = face - c['drum_depth_assumed_mm']
    return dict(hub_end_mm=hub_end, plate_back_mm=face, drum_rear_rim_mm=rim,
                rear_guide_start_mm=rim - c['rear_guide_thickness_mm'],
                standoff_length_mm=c['drum_depth_assumed_mm'] - c['drum_face_thickness_assumed_mm'],
                rope_plane_mm=(rim + face - c['drum_face_thickness_assumed_mm']) / 2)


def report(c):
    p = rotor_positions(c)
    r = (c['drum_od_mm'] + c['rope_diameter_assumed_mm']) / 2000
    w = math.tau * c['target_speed_rpm'] / 60
    near, far = c['bearing_centers_z_mm']
    if far <= near or p['rope_plane_mm'] <= far or r <= 0:
        raise ValueError('Expected an overhung brake beyond two separated output bearings')
    force = c['total_tension_limit_N']
    moment = force * (p['rope_plane_mm'] - far)
    d = c['shaft_equivalent_diameter_mm']
    sigma = 32 * moment / (math.pi * d ** 3)
    tau = 16 * c['peak_torque_Nm'] * 1000 / (math.pi * d ** 3)
    peak_force = c['example_slack_tension_N'] + c['peak_torque_Nm'] / r
    if peak_force > c['individual_tension_limit_N'] or peak_force + c['example_slack_tension_N'] > force:
        raise ValueError('Example tension pair exceeds the provisional fixture limits')
    load_far = force * (p['rope_plane_mm'] - near) / (far - near)
    heat_cap = c['drum_mass_assumed_kg'] * c['steel_specific_heat_assumed_J_kgK']
    if heat_cap <= 0:
        raise ValueError('Positive drum mass and heat capacity required')
    return dict(status='CALCULATED CANDIDATE ONLY; NO MEASURED LOAD OR THERMAL DATA',
        positions=p, effective_radius_assumed_mm=r * 1000,
        running_brake_power_W=c['running_torque_Nm'] * w,
        peak_brake_power_W=c['peak_torque_Nm'] * w,
        example_peak_tight_N=peak_force, example_peak_slack_N=c['example_slack_tension_N'],
        example_required_friction_coefficient_for_180deg_wrap=math.log(peak_force / c['example_slack_tension_N']) / math.pi,
        example_peak_measurement_bounds=torque_interval(peak_force, c['example_slack_tension_N'], r * 1000, r * 1000, .5, 1),
        radial_screen=dict(total_rope_force_N=force, outer_bearing_reaction_N=load_far,
            inner_bearing_opposing_reaction_N=load_far - force,
            bearing_static_catalog_rating_N=c['bearing_static_rating_N'],
            bearing_limit_scope='Catalog rating only. Printed cap stiffness, fit, bearing load sharing, shock and fatigue are not established.',
            shaft_bending_MPa=sigma, shaft_torsion_MPa=tau,
            shaft_von_mises_MPa=math.sqrt(sigma ** 2 + 3 * tau ** 2),
            shaft_limit_scope='11 mm equivalent solid round; no groove, shoulder, concentration or material allowable'),
        thermal_screen=dict(assumed_heat_capacity_J_K=heat_cap,
            running_10s_bulk_rise_C=c['running_torque_Nm'] * w * c['initial_test_duration_s'] / heat_cap,
            running_60s_bulk_rise_C=c['running_torque_Nm'] * w * 60 / heat_cap,
            scope='Uniform adiabatic bulk estimate with assumed mass/cp. Not a contact-temperature bound or permission to run; measure mass and temperatures.'),
        unfinished=['Actual drum dimensions/mass and hub fit', 'Powered casing mounts and rope anchors',
                    'Guard and released-load behavior', 'Rope grade/strength/termination',
                    'Calibrated force gauges and simultaneous capture', 'RPM and temperature sensing',
                    'Static rotor retention/load and subsequent powered validation'])


if __name__ == '__main__':
    result = report(json.loads((ROOT / 'brake-rotor.json').read_text()))
    (ROOT / 'brake-load-report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['running_brake_power_W', 'peak_brake_power_W', 'radial_screen', 'thermal_screen']}, indent=2))

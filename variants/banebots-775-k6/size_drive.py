"""Codex (secondary agent, 2026-10-21): traceable D1 sizing screens, not a gear rating."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent


def geometry(stage, cfg):
    m, ns, np = stage['module_mm'], stage['sun_teeth'], stage['planet_teeth']
    nr = ns + 2 * np
    orbit = m * (ns + np) / 2
    ring_root_radius = m * (nr + 2.5) / 2 + cfg['geometry']['extra_root_clearance_mm']
    backing = min(cfg['geometry']['housing_od_mm'] / 2, cfg['geometry']['tie_rod_radius_mm'] - cfg['geometry']['tie_rod_hole_mm'] / 2) - ring_root_radius
    return dict(ring_teeth=nr, ratio=1 + nr / ns, orbit_mm=orbit,
                sun_pitch_mm=m * ns, planet_pitch_mm=m * np,
                ring_pitch_mm=m * nr,
                planet_root_web_mm=(m * (np - 2.5) - 2 * cfg['geometry']['extra_root_clearance_mm'] - cfg['geometry']['planet_bearing_od_mm'] - cfg['geometry']['bearing_fit_allowance_mm']) / 2,
                planet_neighbor_gap_mm=2 * orbit * math.sin(math.pi / stage['planets']) - m * (np + 2),
                equally_spaced_assembly=(nr + ns) % stage['planets'] == 0,
                minimum_ring_backing_at_tie_hole_mm=backing,
                ring_backing_over_whole_tooth_height=backing / (2.25 * m + cfg['geometry']['extra_root_clearance_mm']))


def evaluate(cfg):
    g = cfg['geometry']
    spacer_swept_d = g['planet_spacer_od_mm'] + g['planet_spacer_id_mm'] - g['planet_bearing_id_mm']
    assert g['planet_spacer_id_mm'] > g['planet_bearing_id_mm']
    assert spacer_swept_d < g['planet_shaft_abutment_max_mm'], 'Planet spacer can touch bearing shield'
    assert g['planet_through_bore_mm'] <= g['planet_housing_abutment_max_mm']
    assert g['planet_through_bore_mm'] > spacer_swept_d
    assert cfg['geometry']['pressure_angle_deg'] == 20, 'Lewis factor currently supports 20-degree teeth only'
    assert cfg['targets']['running_nm'] > 0 and cfg['targets']['brief_peak_nm'] >= cfg['targets']['running_nm']
    assert cfg['targets']['output_rpm'] > 0 and cfg['motor']['supply_v'] > 0
    assert all(0 < s['efficiency_assumed'] <= 1 for s in cfg['stages'])
    motor = cfg['motor']
    stall = motor['stall_oz_in'] * 0.00706155183333
    ratios = [geometry(s, cfg)['ratio'] for s in cfg['stages']]
    ratio = math.prod(ratios)
    eta = math.prod(s['efficiency_assumed'] for s in cfg['stages'])
    report = {'revision': cfg['revision'], 'status': cfg['status'], 'overall_ratio': ratio,
              'assumed_overall_efficiency': eta, 'motor_stall_nm_at_18v': stall,
              'material': cfg['material'], 'cases': {}, 'stages': [],
              'not_established': ['Actual K6 torque and duty', 'Printed fatigue allowable', 'Dynamic factor at high input speed', 'Internal-ring root and rim stress', 'Contact fatigue and wear', 'Temperature equilibrium', 'Actual unequal planet load sharing', 'Physical fits and shaft alignment', 'Motor cooling and current-limit calibration']}
    for label, torque in [('running', cfg['targets']['running_nm']), ('peak', cfg['targets']['brief_peak_nm'])]:
        tm = torque / (ratio * eta)
        rpm = cfg['targets']['output_rpm'] * ratio
        v_required = motor['nominal_v'] * (rpm / motor['no_load_rpm'] + tm / stall)
        current = motor['no_load_a'] + (motor['stall_a'] - motor['no_load_a']) * tm / stall
        report['cases'][label] = dict(output_nm=torque, output_rpm=cfg['targets']['output_rpm'],
            output_mechanical_w=torque * cfg['targets']['output_rpm'] * math.tau / 60,
            motor_nm=tm, motor_rpm=rpm, estimated_motor_a=current,
            estimated_average_motor_v=v_required,
            estimated_pwm_duty=v_required / motor['supply_v'],
            estimated_motor_electrical_w=v_required * current,
            motor_model_note='Linear interpolation from manufacturer no-load/stall data; ignores PWM ripple and temperature. No-load current at reduced voltage is unmeasured.')
    for i, s in enumerate(cfg['stages']):
        g = geometry(s, cfg)
        remaining = math.prod(ratios[i:]) * math.prod(x['efficiency_assumed'] for x in cfg['stages'][i:])
        sun_rpm = cfg['targets']['output_rpm'] * math.prod(ratios[i:])
        carrier_rpm = sun_rpm / g['ratio']
        phase_relative_rpm = sun_rpm - carrier_rpm
        row = dict(name=s['name'], **g, module_mm=s['module_mm'], width_mm=s['width_mm'],
                   planets=s['planets'], input_rpm=sun_rpm, carrier_rpm=carrier_rpm,
                   pitch_speed_in_carrier_frame_m_s=math.pi * g['sun_pitch_mm'] / 1000 * phase_relative_rpm / 60,
                   planet_bearing_relative_rpm=phase_relative_rpm * s['sun_teeth'] / s['planet_teeth'], cases={})
        pa = math.radians(cfg['geometry']['pressure_angle_deg'])
        rs, rp = g['sun_pitch_mm'] / 2, g['planet_pitch_mm'] / 2
        path = math.sqrt((rs + s['module_mm']) ** 2 - (rs * math.cos(pa)) ** 2) + math.sqrt((rp + s['module_mm']) ** 2 - (rp * math.cos(pa)) ** 2) - (rs + rp) * math.sin(pa)
        row['external_transverse_contact_ratio_standard_geometry'] = path / (math.pi * s['module_mm'] * math.cos(pa))
        row['minimum_20deg_unshifted_sun_teeth_screen'] = 2 / math.sin(pa) ** 2
        for label, torque in [('running', cfg['targets']['running_nm']), ('peak', cfg['targets']['brief_peak_nm'])]:
            ts = torque / remaining
            ft = ts / (g['sun_pitch_mm'] / 2000) / s['planets']
            factored = ft * cfg['factors']['planet_load_sharing'] * cfg['factors']['dynamic']
            y_s = 0.484 - 2.87 / s['sun_teeth']
            y_p = 0.484 - 2.87 / s['planet_teeth']
            sigma_s = factored / (s['width_mm'] * s['module_mm'] * y_s)
            sigma_p = factored / (s['width_mm'] * s['module_mm'] * y_p)
            normal = factored / math.cos(math.radians(cfg['geometry']['pressure_angle_deg']))
            rho_s = g['sun_pitch_mm'] / 2 * math.sin(math.radians(20))
            rho_p = g['planet_pitch_mm'] / 2 * math.sin(math.radians(20))
            equivalent_r = 1 / (1 / rho_s + 1 / rho_p)
            equivalent_e = cfg['material']['elastic_modulus_mpa'] / (2 * (1 - cfg['material']['poisson_ratio'] ** 2))
            hertz = math.sqrt(normal * equivalent_e / (math.pi * s['width_mm'] * equivalent_r))
            pin_load = 2 * factored
            pin_span = s['carrier_gap_mm'] + cfg['geometry']['carrier_plate_mm']
            pin_moment = pin_load * pin_span / 4
            pin_stress = 32 * pin_moment / (math.pi * 5 ** 3)
            row['cases'][label] = dict(sun_input_nm=ts, nominal_tangential_force_per_planet_n=ft,
                factored_tangential_force_n=factored,
                sun_lewis_screen_mpa=sigma_s, planet_lewis_screen_mpa=sigma_p,
                below_assumed_bending_screen=max(sigma_s, sigma_p) <= cfg['material']['screening_bending_mpa'],
                external_mesh_hertz_pitch_point_screen_mpa=hertz,
                pin_load_upper_screen_n=pin_load, pin_bending_screen_mpa=pin_stress,
                pin_deflection_screen_mm=pin_load * pin_span ** 3 / (48 * 200000 * math.pi * 5 ** 4 / 64),
                carrier_pin_bearing_pressure_screen_mpa=pin_load / (2 * 5 * cfg['geometry']['carrier_plate_mm']))
        assert g['equally_spaced_assembly'] and g['planet_neighbor_gap_mm'] > 0
        assert g['planet_root_web_mm'] >= 2
        assert g['ring_backing_over_whole_tooth_height'] >= 1.2, 'Thin ring ligament at tie hole needs redesign/analysis'
        assert abs(s['shoulder_length_mm'] - (2 * cfg['geometry']['carrier_plate_mm'] + s['carrier_gap_mm'])) < 1e-9
        report['stages'].append(row)
    report['output_shaft'] = {'profile': '12 mm REX, conservatively screened as 11 mm solid round',
        'peak_torsional_shear_mpa': 16 * cfg['targets']['brief_peak_nm'] * 1000 / (math.pi * 11 ** 3),
        'note': 'No alloy-specific strength rating or stress-concentration factor yet. Avoid retaining-ring grooves in loaded spans.'}
    report['ratio_comparison_at_target_rpm'] = []
    for r in [80, 100, 125]:
        torque = cfg['targets']['brief_peak_nm'] / (r * eta)
        volts = motor['nominal_v'] * (cfg['targets']['output_rpm'] * r / motor['no_load_rpm'] + torque / stall)
        report['ratio_comparison_at_target_rpm'].append(dict(ratio=r, assumed_efficiency=eta,
            estimated_required_motor_v_at_peak=volts, fits_average_voltage_model=volts <= motor['supply_v'],
            note='Same assumed efficiency for comparison only; alternative ratios need their own geometry/load analysis'))
    report['calculation_limits'] = 'Lewis approximation assumes a conventional 20-degree full-depth tooth. cq_gears uses an approximated root arc; local root FEA/testing remains necessary. Factors and 8 MPa threshold are judgments, not ISO/AGMA validation. Hertz is an elastic pitch-point estimate, not a polymer wear-life prediction. Planet pins use a conservative central point load with simply supported ends. Reverse bending of planet teeth is not separately life-rated.'
    return report


if __name__ == '__main__':
    cfg = json.loads((ROOT / 'drive.json').read_text())
    report = evaluate(cfg)
    (ROOT / 'sizing-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Ratio:', report['overall_ratio'], 'assumed efficiency:', report['assumed_overall_efficiency'])
    for s in report['stages']:
        print(s['name'], 'peak tooth screen MPa:', round(s['cases']['peak']['sun_lewis_screen_mpa'], 3), 'root web mm:', round(s['planet_root_web_mm'], 3))

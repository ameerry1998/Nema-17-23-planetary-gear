"""Codex (secondary agent, 2026-10-21): orbiting mass and conservative pin bending from current CAD volumes."""
from pathlib import Path
import hashlib
import json
import math
from size_drive import evaluate

ROOT = Path(__file__).resolve().parent
DEPENDENCIES = ['drive.json', 'dynamic-inputs.json', 'sizing-report.json',
                'drive-candidate/validation-all.json', 'size_drive.py', 'dynamic_review.py']


def orbital_force(mass_g, radius_mm, rpm):
    if not all(math.isfinite(x) and x >= 0 for x in [mass_g, radius_mm, rpm]):
        raise ValueError('Mass, radius and RPM must be finite and nonnegative')
    return mass_g / 1000 * radius_mm / 1000 * (math.tau * rpm / 60) ** 2


def beam_bounds(force_N, start_mm, end_mm, left_mm, right_mm):
    """Codex (secondary agent, 2026-10-21): superposition bound over all point-load locations in a part's axial extent."""
    if force_N < 0 or not all(math.isfinite(x) for x in [force_N, start_mm, end_mm, left_mm, right_mm]):
        raise ValueError('Finite nonnegative force required')
    if end_mm < start_mm or right_mm <= left_mm:
        raise ValueError('Ordered extent and separated supports required')
    span = right_mm - left_mm
    levers = [max(0, left_mm - start_mm), max(0, end_mm - right_mm)]
    a, b = max(left_mm, start_mm), min(right_mm, end_mm)
    if a <= b:
        x = min(max((left_mm + right_mm) / 2, a), b)
        levers.append((x - left_mm) * (right_mm - x) / span)
    return dict(moment_bound_Nmm=force_N * max(levers),
                left_reaction_bound_N=force_N * max(abs(right_mm-start_mm), abs(right_mm-end_mm)) / span,
                right_reaction_bound_N=force_N * max(abs(start_mm-left_mm), abs(end_mm-left_mm)) / span)


def component_masses(c, s, validation, d):
    g, pin = c['geometry'], c['geometry']['planet_pin']
    plate, gap, width = g['carrier_plate_mm'], s['carrier_gap_mm'], s['width_mm']
    gear_z = plate + (gap - width) / 2
    pin_z = s['pin_head_recess_mm']
    pin_end = pin_z + s['shoulder_length_mm']
    steel = d['steel_density_assumed_g_cm3'] / 1000
    brass = d['brass_density_assumed_g_cm3'] / 1000
    rows = []
    def add(name, mass, lo, hi, evidence):
        if mass < 0 or hi < lo:
            raise ValueError('Invalid component mass/extent')
        rows.append(dict(component=name, nominal_mass_g=mass, z_min_mm=lo, z_max_mm=hi, evidence=evidence))
    v = validation['parts'][s['name']+'-planet']['volume_mm3']
    add('printed planet', v / 1000 * d['pccf_density_g_cm3'], gear_z, gear_z+width, 'Current validated STL solid volume times published filament density')
    for lo in [gear_z, gear_z + width - g['planet_bearing_width_mm']]:
        add('695ZZ1 bearing', d['bearing_mass_g'], lo, lo + g['planet_bearing_width_mm'], 'Manufacturer approximate mass')
    for part, lo, hi in [('planet-inner-spacer',gear_z+4,gear_z+width-4),
                         ('planet-end-spacer',plate,gear_z),('planet-end-spacer',gear_z+width,plate+gap)]:
        v = validation['parts'][s['name']+'-'+part]['volume_mm3']
        add(part, v*brass, lo, hi, 'Current spacer CAD volume times assumed brass density')
    add('pin shoulder', math.pi*pin['diameter_max_mm']**2/4*(s['shoulder_length_mm']+pin['shoulder_length_plus_mm'])*steel,
        pin_z, pin_end+pin['shoulder_length_plus_mm'], 'Solid cylindrical mass envelope')
    add('pin head', math.pi*pin['head_diameter_mm']**2/4*pin['head_height_mm']*steel,
        pin_z-pin['head_height_mm'],pin_z,'Socket/reliefs ignored in mass envelope')
    add('pin threaded end',math.pi*pin['thread_diameter_mm']**2/4*pin['thread_length_mm']*steel,
        pin_end,pin_end+pin['thread_length_mm']+pin['shoulder_length_plus_mm'],'Full major-diameter cylinder; thread grooves ignored')
    add('pin stop washer',math.pi*(pin['washer_od_mm']**2-pin['washer_id_mm']**2)/4*pin['washer_thickness_mm']*steel,
        pin_end,pin_end+pin['washer_thickness_mm']+pin['shoulder_length_plus_mm'],'Nominal annular envelope')
    nut_area = math.sqrt(3)/2*pin['nut_af_mm']**2
    add('pin nut',nut_area*pin['nut_height_mm']*steel,pin_end+pin['washer_thickness_mm'],
        pin_end+pin['washer_thickness_mm']+pin['nut_height_mm']+pin['shoulder_length_plus_mm'],'Full hex prism; thread bore and chamfers ignored in mass envelope')
    if s['pin_upper_shim_mm']:
        add('external S1 shim',math.pi*(pin['upper_shim_od_mm']**2-pin['upper_shim_id_mm']**2)/4*s['pin_upper_shim_mm']*steel,
            plate+gap+plate,pin_end,'Nominal steel annulus outside the carrier')
    return rows


def review(c, validation, sizing, d):
    if d['mass_multiplier_assumed'] < 1 or any(d[k] <= 0 for k in ['pccf_density_g_cm3','bearing_mass_g','steel_density_assumed_g_cm3','brass_density_assumed_g_cm3']):
        raise ValueError('Positive mass inputs and multiplier >=1 required')
    result = dict(status='CALCULATED ORBITAL-LOAD SCREEN; PHYSICAL VALIDATION PENDING',physical_testing='NOT PERFORMED',stages=[])
    free_motor_rpm = c['motor']['no_load_rpm'] * c['motor']['supply_v'] / c['motor']['nominal_v']
    free_output_rpm = free_motor_rpm / sizing['overall_ratio']
    for s, base in zip(c['stages'], sizing['stages']):
        assert s['name'] == base['name']
        parts = component_masses(c,s,validation,d)
        total_mass = sum(x['nominal_mass_g'] for x in parts)
        plate = c['geometry']['carrier_plate_mm']
        left = (s['pin_head_recess_mm'] + plate)/2
        right = plate+s['carrier_gap_mm']+plate/2
        row = dict(stage=s['name'], components=parts, nominal_orbiting_mass_per_pin_g=total_mass,
                   assumed_mass_multiplier=d['mass_multiplier_assumed'], support_centers_mm=[left,right], cases={})
        for label, speed_scale, torque_case in [('running',1,'running'),('peak',1,'peak'),('estimated_no_load',free_output_rpm/c['targets']['output_rpm'],None)]:
            rpm = base['carrier_rpm'] * speed_scale
            tangential = base['cases'][torque_case]['pin_load_upper_screen_n'] if torque_case else 0
            mesh_bound = tangential / math.cos(math.radians(c['geometry']['pressure_angle_deg']))
            mesh_z = plate+s['carrier_gap_mm']/2
            bound = beam_bounds(mesh_bound,mesh_z,mesh_z,left,right)
            centrifugal = gravity = 0
            for part in parts:
                mass = part['nominal_mass_g'] * d['mass_multiplier_assumed']
                cf = orbital_force(mass,base['orbit_mm'],rpm)
                gf = mass/1000*d['gravity_m_s2']
                centrifugal += cf; gravity += gf
                bb = beam_bounds(cf+gf,part['z_min_mm'],part['z_max_mm'],left,right)
                for k in bound:
                    bound[k] += bb[k]
            sigma = 32*bound['moment_bound_Nmm']/(math.pi*c['geometry']['planet_pin']['diameter_min_mm']**3)
            pressure_left = bound['left_reaction_bound_N']/(c['geometry']['planet_pin']['diameter_min_mm']*(plate-s['pin_head_recess_mm']))
            pressure_right = bound['right_reaction_bound_N']/(c['geometry']['planet_pin']['diameter_min_mm']*plate)
            row['cases'][label] = dict(output_rpm=c['targets']['output_rpm']*speed_scale, carrier_rpm=rpm,
                planet_bearing_relative_rpm=base['planet_bearing_relative_rpm']*speed_scale,
                mesh_normal_force_sum_bound_N=mesh_bound, centrifugal_force_allowance_N=centrifugal,
                gravity_force_allowance_N=gravity, combined_transverse_force_sum_bound_N=mesh_bound+centrifugal+gravity,
                **bound,pin_bending_bound_MPa=sigma, carrier_pin_pressure_bound_MPa=max(pressure_left,pressure_right),
                single_planet_imbalance_example_N=orbital_force(d['imbalance_example_g'],base['orbit_mm'],rpm),
                case_limit='No-load case excludes unknown frictional torque; estimated speed is not a verified maximum' if not torque_case else 'Mesh load already includes assumed unequal-sharing and dynamic factors; this adds conservative normal-force, mass and gravity bounds')
        result['stages'].append(row)
    result['method'] = 'Mass from current CAD volumes and manufacturer/assumed densities. Bound two mesh normal forces by tangential-force sum/cos(pressure angle), without assuming radial cancellation. Add centrifugal and gravity magnitudes conservatively. For each component, bound simply supported beam moments/reactions over its entire axial extent, including overhanging head/nut. Sum independent bounds; these extrema need not occur together.'
    result['limits'] = ['Mass multiplier and support locations are assumptions, not proven worst cases',
        'No bearing life, fit, rotating-outer-ring suitability or fatigue qualification',
        'No input-coupler balance or high-speed rating', 'No motor rotor inertia, acceleration-ramp or jam-shock model',
        'No printed carrier flexure, notch stresses, pin fatigue, internal-ring load or thermal validation',
        'Assembly matching and bearing/pin clearances must be measured; mass matching is not a substitute for vibration testing',
        'This supplements the tangential-only pin screen in sizing-report.json; it does not revise tooth-strength evidence']
    return result


def generate():
    c=json.loads((ROOT/'drive.json').read_text())
    v=json.loads((ROOT/'drive-candidate/validation-all.json').read_text())
    assert v['status'].startswith('DIGITAL STAGE CHECKS PASSED')
    for name, expected in v['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, f'Stale CAD source: {name}'
    for name,data in v['parts'].items():
        assert hashlib.sha256((ROOT/'drive-candidate'/(name+'.stl')).read_bytes()).hexdigest()==data['stl_sha256']
    sizing=json.loads((ROOT/'sizing-report.json').read_text())
    assert sizing == evaluate(c), 'Sizing report must match the current drive configuration'
    r=review(c,v,sizing,json.loads((ROOT/'dynamic-inputs.json').read_text()))
    r['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in DEPENDENCIES}
    return r


if __name__=='__main__':
    report=generate()
    (ROOT/'dynamic-report.json').write_text(json.dumps(report,indent=2)+'\n')
    for row in report['stages']:
        p=row['cases']['peak']
        print(row['stage'],'nominal orbiting mass g:',round(row['nominal_orbiting_mass_per_pin_g'],3),
              'peak centrifugal allowance N:',round(p['centrifugal_force_allowance_N'],3),
              'pin bending bound MPa:',round(p['pin_bending_bound_MPa'],3))

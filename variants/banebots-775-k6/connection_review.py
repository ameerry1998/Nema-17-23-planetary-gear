"""Codex (secondary agent, 2026-10-21): expose connection pressure and heat assumptions."""
import copy
import json
import math
from pathlib import Path
from size_drive import evaluate

ROOT = Path(__file__).resolve().parent


def flat_contact(torque_nm, length_mm, half_flat_mm, faces=3):
    assert torque_nm >= 0 and length_mm > 0 and half_flat_mm > 0 and faces > 0
    return 2 * torque_nm * 1000 / (faces * length_mm * half_flat_mm ** 2)


def review(c):
    r = evaluate(c)
    contacts = []
    for stage in r['stages']:
        s = next(x for x in c['stages'] if x['name'] == stage['name'])
        length = s['width_mm'] - s['sun_retention_counterbore_mm']
        contacts.append(dict(part=stage['name'] + ' sun / 8 REX shaft', engagement_mm=length,
            torque_nm=stage['cases']['peak']['sun_input_nm'],
            idealized_average_contact_mpa=flat_contact(stage['cases']['peak']['sun_input_nm'], length, math.sqrt(4 ** 2 - 3.5 ** 2))))
    contacts.append(dict(part='S1 printed carrier / 8 REX shaft', engagement_mm=9,
        torque_nm=r['stages'][1]['cases']['peak']['sun_input_nm'],
        idealized_average_contact_mpa=flat_contact(r['stages'][1]['cases']['peak']['sun_input_nm'], 9, math.sqrt(4 ** 2 - 3.5 ** 2))))
    peak = c['targets']['brief_peak_nm']
    contacts.extend([
        dict(part='Printed attachment / 12 REX shaft', engagement_mm=c['interface']['shaft_engagement_mm'], torque_nm=peak,
            idealized_average_contact_mpa=flat_contact(peak, c['interface']['shaft_engagement_mm'], math.sqrt(6 ** 2 - 5.5 ** 2))),
        dict(part='Printed attachment / K6 6.35 mm hex', engagement_mm=c['interface']['adapter_hex_depth_mm'], torque_nm=peak,
            idealized_average_contact_mpa=flat_contact(peak, c['interface']['adapter_hex_depth_mm'], 6.35 / (2 * math.sqrt(3))))])
    thermal = []
    for case, point in r['cases'].items():
        power = point['output_mechanical_w'] / r['assumed_overall_efficiency']
        loss = []
        for s in c['stages']:
            loss.append(dict(stage=s['name'], loss_w=power * (1 - s['efficiency_assumed'])))
            power *= s['efficiency_assumed']
        thermal.append(dict(case=case, stage_losses=loss, total_gearbox_loss_w=sum(x['loss_w'] for x in loss),
            note='Assumed efficiencies; not measured heating or a prediction of local tooth temperature.'))
    candidate = copy.deepcopy(c)
    candidate['stages'][2].update(sun_teeth=20, planet_teeth=20, planets=5, module_mm=1.25,
        width_mm=17, carrier_gap_mm=18, shoulder_length_mm=30)
    alternate = evaluate(candidate)['stages'][2]
    return dict(physical_tests=0,
        method='Idealized uniform pressure on the leading half of three flat faces: T = 3*p*L*a^2/2. This is not Hertz contact, an exact local stress solution, or a validated contact pattern. Clipped REX half-flat a is sqrt(R^2-(AF/2)^2). Real corner contact and uneven sharing can increase stress.',
        contacts=contacts,
        interpretation='No PCCF compressive-creep/fatigue allowable is established. Do not compare these pressures directly with tensile yield as a pass/fail criterion. The roughly 66 MPa K6 socket estimate makes the all-printed socket a poor untested primary torque path. Develop a retained steel-socket cassette instead.',
        hub_bolt_screen=dict(final_torque_nm=peak, bolt_circle_radius_mm=math.sqrt(8 ** 2 + 8 ** 2),
            four_bolt_force_n=peak * 1000 / (4 * math.sqrt(8 ** 2 + 8 ** 2)),
            factored_printed_hole_bearing_mpa=peak * 1000 * 2.5 / (4 * math.sqrt(8 ** 2 + 8 ** 2) * 4 * 4),
            note='Four M4 bolts, 6 mm plate minus 2 mm countersink, assumed 2.5 load factor. Ignores preload, countersink wedging, local splitting, plate flexibility and actual sharing. No strength acceptance inferred.'),
        heating=thermal,
        compact_candidate=dict(sun_teeth=20, planet_teeth=20, planets=5, module_mm=1.25, width_mm=17,
            peak_tooth_screen_mpa=alternate['cases']['peak']['sun_lewis_screen_mpa'],
            result='Not adopted: exceeds the existing 8 MPa screening assumption; posts also need relocation. Avoid shrinking a part solely to reduce package length.'))


if __name__ == '__main__':
    c = json.loads((ROOT / 'drive.json').read_text())
    result = review(c)
    (ROOT / 'connection-review.json').write_text(json.dumps(result, indent=2) + '\n')
    for row in result['contacts']:
        print(row['part'], round(row['idealized_average_contact_mpa'], 2), 'MPa idealized contact')

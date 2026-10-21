"""Codex (secondary agent, 2026-10-21): assemble D1 cartridges with retained bearings and casing.

Purchased-part solids are simplified clearance envelopes, not manufacturing CAD.
Axial fit, insert selection and motor-face assumptions still need confirmation.
"""
from pathlib import Path
import hashlib
import json
import math
import cadquery as cq
import build_drive as B

ROOT = Path(__file__).resolve().parent
C = B.CFG
A = C['assembly']
G = C['geometry']
STAGES = ROOT / 'drive-candidate'
OUT = ROOT / 'drive-assembly'
OUT.mkdir(exist_ok=True)
B.OUT = OUT
B.REPORT = {'status': 'BUILDING', 'purpose': C['status'], 'parts': {}, 'placements': [], 'interferences': [],
            'physical_testing': 'NOT PERFORMED', 'limitations': ['Motor face spacing remains assumed', 'Shaft endplay and clamp retention untested', 'Bearing/insert fits untested', 'Simplified purchased-part envelopes', 'No arm, grinder clamp or load fixture yet'],
            'source_sha256': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in ('drive.json', 'build_drive.py', 'assemble_drive.py')}}
REPORT = B.REPORT
ITEMS = []


def add(name, shape, category, z=0, color=None):
    s = shape.translate((0, 0, z))
    ITEMS.append({'name': name, 'shape': s, 'category': category, 'color': color or '#9eaaaf'})
    return s


def tie_holes(shape, height):
    for x, y in B.polar(G['tie_rod_radius_mm'], 6, math.pi / 6):
        shape = shape.cut(B.cylinder(G['tie_rod_hole_mm'], height + 2, -1, x, y))
    return shape


def shell(name, z0, z1):
    assert z1 > z0
    part = tie_holes(B.ring_solid(G['housing_od_mm'], A['housing_bore_mm'], z1 - z0), z1 - z0)
    B.save(name, part, note='Fixed casing spacer; six M4 tie rods clamp the complete stack')
    add(name, part, 'fixed', z0, '#84939c')


def retainer(name, bearing_od, z, inverted=False):
    small = bearing_od == 16
    aperture, body_d, radius = (14, 19, 11.5) if small else (25.8, 31, 18.5)
    part = B.ring_solid(body_d, aperture, 2)
    for x, y in B.polar(radius, 3, math.pi / 3):
        part = part.fuse(B.cylinder(7, 2, 0, x, y))
        part = part.cut(B.cylinder(2.3, 4, -1, x, y))
    part = B.save(name, part.clean(), note='Three M2 x 6 screws into ruthex RX-M2x4 brass inserts; print-fit coupon required')
    add(name, part, 'fixed', z - 2 if inverted else z, '#84939c')


def cap(name, z, output=False):
    h = A['output_cap_mm'] if output else A['interstage_cap_mm']
    id_, od, width, aperture = (12, 28, 8, 25.8) if output else (8, 16, 5, 14)
    part = B.ring_solid(G['housing_od_mm'], aperture, h)
    seats = [0, h - width] if output else [h - width]
    for seat in seats:
        part = part.cut(B.cylinder(od + G['bearing_fit_allowance_mm'], width + 0.01, seat))
    radius = 18.5 if output else 11.5
    insert_zs = [0, h - 5] if output else [h - 5]
    for hole_z in insert_zs:
        for x, y in B.polar(radius, 3, math.pi / 3):
            part = part.cut(B.cylinder(3.2, 5.01, hole_z, x, y))
    part = B.save(name, tie_holes(part, h), note='Bearing shoulders and separate retainers capture outer races; nominal pockets need fit coupons')
    add(name, part, 'fixed', z, '#84939c')
    for i, seat in enumerate(seats):
        add(f'{name}-bearing-{i}', B.bearing(id_, od, width), 'bearing', z + seat)
    retainer(name + '-retainer-top', od, z + h)
    if output:
        retainer(name + '-retainer-bottom', od, z, inverted=True)
    return z + h


def load_part(stage, part):
    return cq.importers.importStep(str(STAGES / f'{stage}-{part}.step')).val()


def stage_positions():
    bases = [0.0]
    for i in range(2):
        s, nxt = C['stages'][i], C['stages'][i + 1]
        start = bases[i] + G['carrier_plate_mm'] + s['carrier_gap_mm'] + A['output_shaft_start_in_carrier_mm']
        next_tip_local = G['carrier_plate_mm'] + (nxt['carrier_gap_mm'] + nxt['width_mm']) / 2 - nxt['sun_retention_counterbore_mm']
        bases.append(start + A['interstage_shaft_lengths_mm'][i] - next_tip_local)
    return bases


def stage(s, base, index):
    name, plate, gap, width = s['name'], G['carrier_plate_mm'], s['carrier_gap_mm'], s['width_mm']
    geom = B.geometry(s, C)
    gear_z = base + plate + (gap - width) / 2
    upper_z = base + plate + gap
    add(name + '-lower', load_part(name, 'carrier-lower'), 'rotating', base, '#ded5c1')
    add(name + '-upper', load_part(name, 'carrier-upper'), 'rotating', upper_z, '#ded5c1')
    if name in ('S2', 'S3'):
        hub = cq.Workplane('XY').box(24, 29.94, 8, centered=(True, True, False)).val().translate((0, -2.97, 0)) if name == 'S3' else B.cylinder(32, 8)
        hub = hub.fuse(B.cylinder(14, 2, -2)).cut(B.rex_profile(s['output_rex_mm'], 12, z=-3))
        for x in [-8, 8]:
            for y in [-8, 8]:
                hub = hub.cut(B.cylinder(4, 10, -1, x, y))
                screw = B.cylinder(4, 8, 2, x, y).fuse(cq.Solid.makeCone(4, 2, 2, cq.Vector(x, y, 0)))
                add(f'{name}-metal-hub-bolt-{x}-{y}', screw, 'fastener', upper_z)
        add(name + '-metal-hub-REFERENCE', hub, 'rotating', upper_z + plate)
    add(name + '-ring', load_part(name, 'fixed-ring'), 'fixed', gear_z, '#84939c')
    add(name + '-sun', load_part(name, 'sun'), 'rotating', gear_z, '#dca749')
    add(name + '-carrier-journal', B.bearing(8, 16, 5), 'bearing', base + 1)
    for i, (x, y) in enumerate(B.polar(geom['orbit_mm'], s['planets'])):
        add(f'{name}-planet-{i}', load_part(name, 'planet').translate((x, y, 0)), 'rotating', gear_z, '#69a79a')
        for j, zz in enumerate([gear_z, gear_z + width - 4]):
            add(f'{name}-planet-{i}-bearing-{j}', B.bearing(5, 13, 4).translate((x, y, 0)), 'bearing', zz)
        add(f'{name}-planet-{i}-inner-spacer', load_part(name, 'planet-inner-spacer').translate((x, y, 0)), 'rotating', gear_z + 4)
        for j, zz in enumerate([base + plate, gear_z + width]):
            add(f'{name}-planet-{i}-end-spacer-{j}', load_part(name, 'planet-end-spacer').translate((x, y, 0)), 'rotating', zz)
        pin = B.cylinder(5, s['shoulder_length_mm']).fuse(B.cylinder(9, 5, -5)).fuse(B.cylinder(4, 6, s['shoulder_length_mm']))
        add(f'{name}-pin-{i}', pin.translate((x, y, 0)), 'fastener', base)
        nut = B.hex_prism(7, 4).cut(B.cylinder(4, 6, -1))
        add(f'{name}-pin-nut-{i}', nut.translate((x, y, 0)), 'fastener', upper_z + plate)
    for i, (x, y) in enumerate(B.polar(geom['orbit_mm'], s['planets'], math.pi / s['planets'])):
        length = s['shoulder_length_mm'] + 5
        bolt = B.cylinder(3, length, -length).fuse(B.cylinder(5.5, 3))
        add(f'{name}-post-screw-{i}', bolt.translate((x, y, 0)), 'fastener', upper_z + plate)
    out_start = upper_z + A['output_shaft_start_in_carrier_mm']
    out_length = A['interstage_shaft_lengths_mm'][index] if index < 2 else A['output_shaft_length_mm']
    add(name + '-output-shaft-REFERENCE', B.rex_profile(s['output_rex_mm'], out_length), 'shaft', out_start)
    REPORT['placements'].append(dict(stage=name, lower_carrier_z_mm=base, gear_z_mm=gear_z,
        upper_carrier_z_mm=upper_z, boss_end_mm=upper_z + plate + 8,
        output_shaft_start_mm=out_start, output_shaft_length_mm=out_length,
        output_shaft_tip_mm=out_start + out_length))
    return gear_z, gear_z + width, upper_z + plate + 8


def shaft_spacer(name, id_, od, z0, z1):
    assert z1 > z0
    part = B.ring_solid(od, id_ + .15, z1 - z0)
    B.save(name, part, material='Steel or aluminum precision tube; STL is a FIT SAMPLE ONLY',
           note='Deburr ends square. Select metal shims for 0.1 to 0.3 mm measured endplay; do not preload bearing balls through mis-sized spacers.')
    add(name, part, 'shaft', z0)


def retain_shafts():
    for i, p in enumerate(REPORT['placements']):
        s = C['stages'][i]
        base, g0 = p['lower_carrier_z_mm'], p['gear_z_mm']
        previous_end = A['input_cap_z_mm'] + A['interstage_cap_mm'] if i == 0 else REPORT['placements'][i - 1]['boss_end_mm'] + .5 + A['interstage_cap_mm']
        shaft_spacer(s['name'] + '-input-long-spacer', 8, 10, previous_end, base + 1)
        shaft_spacer(s['name'] + '-input-short-spacer', 8, 10, base + 6, g0)
        seat = g0 + s['width_mm'] - s['sun_retention_counterbore_mm']
        washer = B.ring_solid(10, 4.3, .8)
        screw = B.cylinder(4, 8, -8).fuse(B.cylinder(7, 4))
        add(s['name'] + '-sun-retaining-washer', washer, 'fastener', seat)
        add(s['name'] + '-sun-retaining-screw', screw, 'fastener', seat + .8)
        boss_end = p['boss_end_mm']
        shaft_spacer(s['name'] + '-output-inner-spacer', s['output_rex_mm'], 10 if i < 2 else 15,
                     boss_end, boss_end + (1.5 if i < 2 else 2.5))
    shaft_spacer('input-coupler-bearing-spacer', 8, 10, -13.5, A['input_cap_z_mm'] + 1)
    top = REPORT['envelope']['case_end_mm']
    shaft_spacer('output-bearing-separator', 12, 15, top - 16, top - 8)
    shaft_spacer('output-collar-spacer', 12, 15, top, top + 2.5)
    collar = B.cylinder(26, 10).cut(B.rex_profile(12, 12, z=-1))
    add('output-metal-clamping-collar-REFERENCE', collar, 'shaft', top + 2.5)
    REPORT['axial_retention'] = 'S1 printed keyed hub with captive M3 radial retention screw; S2/S3 metal clamping hubs; steel end washers/screws, metal spacers and output collar. 0.1 to 0.3 mm endplay must be shimmed physically. Axial pull/slip tests pending.'


def motor_interface():
    z, h = A['motor_face_z_mm'], A['motor_plate_mm']
    plate = B.ring_solid(G['housing_od_mm'], A['motor_collar_clearance_mm'], h)
    for x in [-A['motor_hole_spacing_assumed_mm'] / 2, A['motor_hole_spacing_assumed_mm'] / 2]:
        slot = cq.Workplane('XY').center(x, 0).slot2D(7.4, 4.4, 0).extrude(h + 2).val().translate((0, 0, -1))
        plate = plate.cut(slot)
        bolt = B.cylinder(4, h + 2.5, -2.5, x, 0).fuse(B.cylinder(7, 4, h, x, 0))
        add('motor-mount-bolt-' + str(x), bolt, 'fixed', z)
    for angle in [60, 120, 240, 300]:
        a = math.radians(angle)
        plate = plate.cut(B.cylinder(5, h + 2, -1, 16.5 * math.cos(a), 16.5 * math.sin(a)))
    plate = B.save('motor-face-plate', tie_holes(plate, h), note='M4 slots cover 26 to 32 mm pitch. 18.2 mm collar clearance and 2.5 mm modeled screw engagement are assumptions. Fit the unpowered motor before release.')
    add('motor-face-plate', plate, 'fixed', z)
    shell('motor-coupler-guard', z + h, A['input_cap_z_mm'])
    coupler = B.cylinder(A['input_coupler_od_mm'], A['input_coupler_length_mm'])
    coupler = coupler.cut(B.cylinder(5, 9.525 + 1, -1)).cut(B.cylinder(8, 10.525, 9.525))
    add('625228-metal-coupler-REFERENCE', coupler, 'shaft', -32.55)
    add('motor-body-REFERENCE', B.cylinder(A['motor_body_od_mm'], A['motor_body_length_mm']), 'reference', z - A['motor_body_length_mm'], '#59616a')
    add('motor-shaft-REFERENCE', B.cylinder(5, A['motor_shaft_protrusion_published_mm']), 'shaft', z)
    REPORT['motor_connection'] = dict(coupler='ServoCity 625228, simplified envelope from manufacturer STEP',
        motor_shaft_overlap_mm=6.62, input_shaft_overlap_mm=8,
        face_pitch_status='Assumed 29 mm; slotted 26 to 32 mm adjustment',
        shaft_protrusion_status='7.62 mm published, reference face needs physical check',
        speed_rating='Not published by supplier; guarded speed/vibration/retention test required')


def adapter():
    it = C['interface']; h = it['adapter_length_mm']
    part = B.cylinder(it['adapter_body_od_mm'], h)
    lug = cq.Workplane('XY').box(10, 18, 16, centered=(False, True, False)).val().translate((9, 0, 0))
    part = part.fuse(lug)
    part = part.cut(B.rex_profile(12, it['adapter_rex_socket_depth_mm'] + .1, G['rex_fit_allowance_mm'], -.1))
    socket = B.hex_prism(it['adapter_grinder_hex_af_mm'] + it['adapter_hex_allowance_mm'], it['adapter_hex_depth_mm'] + .1, h - it['adapter_hex_depth_mm'])
    part = part.cut(socket)
    slit = cq.Workplane('XY').box(24, 1, 16.1, centered=(False, True, False)).val().translate((0, 0, -.1))
    part = part.cut(slit)
    for zz in [4, 12]:
        hole = B.cylinder(3.4, 30, -15).rotate((0, 0, 0), (1, 0, 0), 90).translate((13, 0, zz))
        nut = B.hex_prism(5.7, 3).rotate((0, 0, 0), (1, 0, 0), 90).translate((13, 9.1, zz))
        part = part.cut(hole).cut(nut)
    part = B.save('adapter-12REX-to-quarter-inch-hex-FIT-AND-LOAD-TEST', part.clean(),
        note='Separate split-clamp adapter, two M3 x 25 screws/nuts. K6 socket engagement and strength unverified; test against steel hex coupon before putting on grinder.')
    tip = REPORT['envelope']['output_tip_mm']
    add('removable-grinder-adapter', part, 'shaft', tip - it['shaft_engagement_mm'], '#ce8f52')
    REPORT['output_interface'] = dict(profile=it['output_profile'], engagement_mm=it['shaft_engagement_mm'],
        axial_socket_bottom_clearance_mm=it['adapter_rex_socket_depth_mm'] - it['shaft_engagement_mm'],
        minimum_removal_travel_mm=it['shaft_engagement_mm'] + 2,
        grinder_hex_status='6.35 mm nominal published; protrusion and clearance unverified',
        adapter_test_status='No physical torque or retention tests')


def collision_checks():
    for fixed in [x for x in ITEMS if x['category'] == 'fixed']:
        fb = fixed['shape'].BoundingBox()
        for moving in [x for x in ITEMS if x['category'] in ('rotating', 'shaft', 'fastener')]:
            mb = moving['shape'].BoundingBox()
            if min(fb.zmax, mb.zmax) - max(fb.zmin, mb.zmin) <= 0.00001:
                continue
            v = fixed['shape'].intersect(moving['shape']).Volume()
            if v > 0.001:
                REPORT['interferences'].append({'fixed': fixed['name'], 'moving': moving['name'], 'volume_mm3': v})
    assert not REPORT['interferences'], REPORT['interferences']


def main():
    validation = json.loads((STAGES / 'validation-all.json').read_text())
    assert validation['status'].startswith('DIGITAL STAGE CHECKS PASSED'), 'Stage build incomplete'
    for filename, expected in validation['source_sha256'].items():
        assert expected == hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(), f'Regenerate cartridges after changes to {filename}'
    for name, data in validation['parts'].items():
        assert hashlib.sha256((STAGES / (name + '.step')).read_bytes()).hexdigest() == data['step_sha256'], name
    REPORT['cartridge_validation_sha256'] = hashlib.sha256((STAGES / 'validation-all.json').read_bytes()).hexdigest()
    bases = stage_positions()
    top = cap('input-bearing-cap', A['input_cap_z_mm'])
    for i, (s, base) in enumerate(zip(C['stages'], bases)):
        g0, g1, boss_end = stage(s, base, i)
        shell(s['name'] + '-case-lower', top, g0)
        cap_bottom = boss_end + (2.5 if i == 2 else 0.5)
        shell(s['name'] + '-case-upper', g1, cap_bottom)
        top = cap(s['name'] + '-output-cap', cap_bottom, output=i == 2)
    first = C['stages'][0]
    input_tip = G['carrier_plate_mm'] + (first['carrier_gap_mm'] + first['width_mm']) / 2
    add('input-shaft-REFERENCE', B.rex_profile(8, A['input_shaft_length_mm']), 'shaft', input_tip - A['input_shaft_length_mm'])
    REPORT['envelope'] = {'case_od_mm': G['housing_od_mm'], 'case_length_mm': top - A['input_cap_z_mm'], 'case_start_mm': A['input_cap_z_mm'], 'case_end_mm': top, 'output_tip_mm': REPORT['placements'][-1]['output_shaft_tip_mm']}
    retain_shafts()
    motor_interface()
    adapter()
    collision_checks()
    assy = cq.Assembly(name='D1-gearbox-candidate')
    for item in ITEMS:
        assy.add(item['shape'], name=item['name'], color=cq.Color(item['color']))
    assy.save(str(OUT / 'D1-gearbox-REFERENCE.step'))
    REPORT['status'] = 'MODELED FIXED/MOVING INTERFERENCE CHECK PASSED; EXPERIMENTAL BUILD CANDIDATE, PHYSICAL FIT AND LOAD TESTS REQUIRED'


if __name__ == '__main__':
    report = OUT / 'assembly-validation.json'
    report.write_text(json.dumps(REPORT, indent=2) + '\n')
    try:
        main()
    except Exception as exc:
        REPORT['status'] = 'FAILED'
        REPORT['error'] = str(exc)
        raise
    finally:
        report.write_text(json.dumps(REPORT, indent=2) + '\n')

"""Codex (secondary agent, 2026-10-21): export a motor-removed, hand-loaded fixture candidate."""
import hashlib
import json
import math
from pathlib import Path
import cadquery as cq
import build_drive as B
from fixture_math import dimensions, screen

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT / 'static-fixture.json').read_text())
D = json.loads((ROOT / 'drive.json').read_text())
OUT = ROOT / 'static-fixture'
OUT.mkdir(exist_ok=True)
SOURCES = ['static-fixture.json', 'fixture_math.py', 'build_static_fixture.py', 'build_drive.py', 'drive.json',
           'drive-assembly/assembly-validation.json', 'drive-assembly/input-bearing-cap.step',
           'drive-assembly/S3-output-cap.step']
B.OUT = OUT
B.REPORT = {'status': 'BUILDING', 'parts': {}, 'physical_testing': 'NOT PERFORMED',
            'source_sha256': {}, 'limitations': C['limits']}
R = B.REPORT


def box(w, h, depth, y=0, z=0):
    return cq.Workplane('XY').box(w, h, depth, centered=(True, True, False)).val().translate((0, y, z))


def main():
    d1 = json.loads((ROOT / 'drive-assembly/assembly-validation.json').read_text())
    assert d1['status'].startswith('MODELED FIXED/MOVING INTERFERENCE CHECK PASSED')
    for name, value in d1['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value, name
    R['source_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    dims = dimensions(C, D)
    g, a = D['geometry'], D['assembly']
    t, front = C['plate_thickness_mm'], C['plate_front_z_mm']
    back = front - t
    foot_bottom, foot_top = C['foot_bottom_y_mm'], C['foot_top_y_mm']
    plate = B.cylinder(g['housing_od_mm'], t).fuse(box(C['foot_width_mm'], foot_top - foot_bottom, t, (foot_bottom + foot_top) / 2))
    plate = plate.cut(B.cylinder(8.5, t + 2, -1))
    plate = plate.cut(B.cylinder(C['hub_pilot_od_mm'] + C['hub_pilot_clearance_mm'], C['hub_pilot_length_mm'] + .2, t - C['hub_pilot_length_mm'] - .1))
    ties = B.polar(g['tie_rod_radius_mm'], 6, math.pi / 6)
    for x, y in ties:
        plate = plate.cut(B.cylinder(g['tie_rod_hole_mm'], t + 2, -1, x, y))
    for x in [-C['hub_mount_xy_mm'], C['hub_mount_xy_mm']]:
        for y in [-C['hub_mount_xy_mm'], C['hub_mount_xy_mm']]:
            plate = plate.cut(B.cylinder(4.4, t + 2, -1, x, y))
            plate = plate.cut(B.cylinder(C['hub_screw_head_recess_diameter_mm'], C['hub_screw_head_recess_depth_mm'] + .1, -.1, x, y))
    B.save('TF1-vise-plate-MOTOR-REMOVED-ONLY', plate.clean(), note='Print broad back face on bed. Clamp only the bottom 20 mm rectangular foot in soft vise jaws; rear support required. No motor may be installed.')
    spacer = B.ring_solid(C['standoff_od_mm'], g['tie_rod_hole_mm'], dims['standoff_length_mm'])
    B.save('TF1-tie-rod-standoff-STATIC-ONLY', spacer, quantity=6, note='Six printed static-fixture spacers. Tighten tie rods evenly only enough to close gaps, without crushing plastic.')
    h = C['cradle_top_y_mm'] - foot_bottom
    cradle = box(C['cradle_width_mm'], h, C['cradle_depth_mm'], (foot_bottom + C['cradle_top_y_mm']) / 2)
    cradle = cradle.cut(B.cylinder(g['housing_od_mm'] + C['cradle_diametral_clearance_mm'], C['cradle_depth_mm'] + 2, -1))
    for x in [-C['cradle_bolt_x_mm'], C['cradle_bolt_x_mm']]:
        hole = B.cylinder(C['cradle_bolt_diameter_mm'], h + 2).rotate((0, 0, 0), (1, 0, 0), -90)
        cradle = cradle.cut(hole.translate((x, foot_bottom - 1, C['cradle_depth_mm'] / 2)))
    B.save('TF1-rear-cradle-STATIC-ONLY', cradle.clean(), note='Print broad end face on bed; semicircular saddle opens upward in use. Shim to actual vise height, clamp to bench and support S3 output cap. No powered-brake rating.')
    hub = B.cylinder(C['hub_od_mm'], C['hub_length_mm'], front)
    hub = hub.fuse(B.cylinder(C['hub_pilot_od_mm'], C['hub_pilot_length_mm'], front - C['hub_pilot_length_mm']))
    hub = hub.cut(B.rex_profile(8, C['hub_length_mm'] + C['hub_pilot_length_mm'] + 2, z=front - C['hub_pilot_length_mm'] - 1))
    screws = []
    for x in [-C['hub_mount_xy_mm'], C['hub_mount_xy_mm']]:
        for y in [-C['hub_mount_xy_mm'], C['hub_mount_xy_mm']]:
            hub = hub.cut(B.cylinder(4, C['hub_length_mm'] + 2, front - 1, x, y))
            z = back + C['hub_screw_head_recess_depth_mm']
            screws.append((f'hub-screw-{x}-{y}', B.cylinder(4, C['hub_screw_length_mm'], z, x, y).fuse(B.cylinder(7, 4, z - 4, x, y))))
    cap = cq.importers.importStep(str(ROOT / 'drive-assembly/input-bearing-cap.step')).val().translate((0, 0, a['input_cap_z_mm']))
    output_cap = cq.importers.importStep(str(ROOT / 'drive-assembly/S3-output-cap.step')).val().translate((0, 0, d1['envelope']['case_end_mm'] - a['output_cap_mm']))
    input_shaft = B.rex_profile(8, a['input_shaft_length_mm'], z=dims['input_shaft_start_mm'])
    input_spacer = B.ring_solid(10, 8.15, 2.5, -13.5)
    printed = [('vise-plate', plate.translate((0, 0, back))), ('rear-cradle', cradle.translate((0, 0, C['cradle_z_mm'])))]
    printed.extend((f'standoff-{i}', spacer.translate((x, y, front))) for i, (x, y) in enumerate(ties))
    hardware = [('locking-hub-REFERENCE', hub), ('input-shaft-REFERENCE', input_shaft), ('input-spacer-REFERENCE', input_spacer), *screws]
    cases = [('existing-input-cap', cap), ('existing-output-cap', output_cap)]
    collisions = []
    for name, part in printed:
        for label, other in [*hardware, *cases]:
            volume = part.intersect(other).Volume()
            if volume > .001:
                collisions.append(dict(a=name, b=label, volume_mm3=volume))
    for name, part in hardware:
        for label, other in cases:
            volume = part.intersect(other).Volume()
            if volume > .001:
                collisions.append(dict(a=name, b=label, volume_mm3=volume))
    for i, (name, part) in enumerate(hardware):
        for label, other in hardware[i + 1:]:
            volume = part.intersect(other).Volume()
            if volume > .001:
                collisions.append(dict(a=name, b=label, volume_mm3=volume))
    R['interferences'] = collisions
    assert not collisions, collisions
    jaw_top = C['vise_jaw_top_y_max_mm']
    assert jaw_top - foot_bottom >= 20
    assert jaw_top < -g['tie_rod_radius_mm'] - 4
    body = B.ring_solid(g['housing_od_mm'], 20, d1['envelope']['case_length_mm'], d1['envelope']['case_start_mm'])
    output_shaft = B.rex_profile(12, a['output_shaft_length_mm'], z=d1['envelope']['output_tip_mm'] - a['output_shaft_length_mm'])
    reference = [*printed, *hardware, ('gearbox-OUTER-ENVELOPE-ONLY', body), ('output-shaft-REFERENCE', output_shaft)]
    assembly = cq.Assembly(name='TF1-STATIC-ONLY-MOTOR-REMOVED')
    for name, shape in reference:
        color = '#62a59a' if any(name == n for n, _ in printed) else '#939da4'
        assembly.add(shape, name=name, color=cq.Color(color))
    assembly.save(str(OUT / 'TF1-STATIC-REFERENCE.step'))
    render(plate, reference)
    R.update(status='DIGITAL STATIC-FIXTURE CLEARANCE CHECK PASSED; PHYSICAL VALIDATION REQUIRED',
             dimensions=dims, static_screen=screen(C, D),
             material=C['material'], maximum_planned_load_Nm=C['maximum_planned_output_torque_Nm'],
             conditions='Motor, motor coupler, guard and motor plate removed; original input spacer retained; additional hub fixes input to vise plate; rear cradle shimmed and clamped',
             fit_scope='Valid single solids, watertight meshes, nominal printed/metal and actual cap clearance. Purchased hub shape is simplified; actual clamp-bolt access and vise/bench fit unverified.',
             direct_output_test='Use an indicating torque tool with an 11 mm six-point socket directly on exposed output shaft. Load opposite the intended powered output direction, observed from the same end. The grinder attachment is tested separately.')


def render(plate, reference):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LightSource
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(13, 7), facecolor='#f6f4ed')
    groups = [[('Printed input-lock plate', plate)], reference]
    for index, group in enumerate(groups):
        ax = fig.add_subplot(1, 2, index + 1, projection='3d')
        ax.set_facecolor('#f6f4ed')
        elev, azim = (75, -90) if index == 0 else (20, -65)
        ev, az = math.radians(elev), math.radians(azim)
        view = np.array([math.cos(ev) * math.cos(az), math.cos(ev) * math.sin(az), math.sin(ev)])
        points = []
        for name, shape in group:
            vertices, faces = shape.tessellate(.4)
            v = np.array([p.toTuple() for p in vertices])
            if index == 1:
                v = v[:, [2, 0, 1]]
            points.append(v)
            is_print = name in ['Printed input-lock plate', 'vise-plate', 'rear-cradle'] or name.startswith('standoff')
            triangles = v[np.array(faces)]
            normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
            triangles = triangles[normals @ view > 0]
            ax.add_collection3d(Poly3DCollection(triangles, facecolors='#62a59a' if is_print else '#a3abb0', linewidths=0, antialiaseds=False, alpha=1, shade=True, lightsource=LightSource(azdeg=225, altdeg=45)))
        points = np.concatenate(points)
        lo, hi = points.min(axis=0), points.max(axis=0)
        span = hi - lo
        for setter, low, high in zip([ax.set_xlim, ax.set_ylim, ax.set_zlim], lo, hi):
            setter(low - 6, high + 6)
        ax.set_box_aspect(span + 12)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title('Print the plate flat' if index == 0 else 'Static setup, motor removed', fontsize=15)
    fig.suptitle('TF1: hold the input, apply measured torque at the output', fontsize=18, y=.96)
    fig.text(.5, .055, 'Teal: printed fixture. Gray: bought input hub/shafts and gearbox envelope.\nBench vise, shims and torque tool omitted. CAD candidate only; no physical test passed.', ha='center', fontsize=11)
    fig.subplots_adjust(left=.02, right=.98, bottom=.12, top=.86)
    fig.savefig(OUT / 'TF1-static-test-setup.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    (OUT / 'validation.json').write_text(json.dumps(R, indent=2) + '\n')
    try:
        main()
    except Exception as exc:
        R.update(status='FAILED DIGITAL FIXTURE CHECK', failure=str(exc))
        raise
    finally:
        (OUT / 'validation.json').write_text(json.dumps(R, indent=2) + '\n')

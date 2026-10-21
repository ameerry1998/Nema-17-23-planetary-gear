"""Codex (secondary agent, 2026-10-21): load-sized stage cartridges for fit/load-fixture development.

These exports are engineering candidates. Assembly geometry is exported by
assemble_drive.py; no physical fit, load, temperature or wear test has passed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import time

import cadquery as cq
import numpy as np
import trimesh
from cq_gears import PlanetaryGearset
from size_drive import geometry, evaluate

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / 'drive.json').read_text())
OUT = ROOT / 'drive-candidate'
OUT.mkdir(exist_ok=True)
G = CFG['geometry']
REPORT = {'status': 'BUILDING', 'purpose': CFG['status'], 'parts': {}, 'stages': {},
          'physical_testing': 'NOT PERFORMED', 'source_sha256': {}}
for filename in ('drive.json', 'build_drive.py', 'size_drive.py'):
    REPORT['source_sha256'][filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()


def cylinder(d, h, z=0, x=0, y=0):
    return cq.Workplane('XY').workplane(offset=z).center(x, y).circle(d / 2).extrude(h).val()


def hex_prism(af, h, z=0):
    return cq.Workplane('XY').workplane(offset=z).polygon(6, af / math.cos(math.pi / 6)).extrude(h).val()


def rex_profile(d, h, clearance=0, z=0):
    return hex_prism(d - 1 + clearance, h, z).rotate((0, 0, 0), (0, 0, 1), 30).intersect(cylinder(d + clearance, h, z))


def ring_solid(od, id, h, z=0):
    return cylinder(od, h, z).cut(cylinder(id, h + 2, z - 1))


def save(name, solid, quantity=1, material=None, note='Engineering candidate'):
    material = material or CFG['material']['name']
    assert solid.isValid(), f'Invalid solid: {name}'
    assert len(solid.Solids()) == 1, f'Disconnected CAD: {name}'
    step, stl = OUT / (name + '.step'), OUT / (name + '.stl')
    cq.exporters.export(solid, str(step))
    cq.exporters.export(solid, str(stl), tolerance=0.02, angularTolerance=0.08)
    mesh = trimesh.load_mesh(str(stl))
    assert mesh.is_watertight and mesh.is_volume and len(mesh.split()) == 1, f'Invalid mesh: {name}'
    REPORT['parts'][name] = dict(cad_valid=True, mesh_watertight=True, quantity=quantity,
        material=material, note=note, volume_mm3=float(mesh.volume), dimensions_mm=mesh.extents.tolist(),
        step_sha256=hashlib.sha256(step.read_bytes()).hexdigest(), stl_sha256=hashlib.sha256(stl.read_bytes()).hexdigest())
    print('Exported', name, flush=True)
    return solid


def polar(radius, count, phase=0):
    return [(radius * math.cos(math.tau * i / count + phase), radius * math.sin(math.tau * i / count + phase)) for i in range(count)]


def bearing(id, od, width, z=0):
    return ring_solid(od, id, width, z)


def make_stage(s):
    name, b, gap, count = s['name'], s['width_mm'], s['carrier_gap_mm'], s['planets']
    info = geometry(s, CFG)
    ns, np_, nr = s['sun_teeth'], s['planet_teeth'], info['ring_teeth']
    orbit = info['orbit_mm']
    plate = G['carrier_plate_mm']
    side_gap = (gap - b) / 2
    planet_positions = polar(orbit, count)
    post_positions = polar(orbit, count, math.pi / count)
    gear_z = plate + side_gap
    upper_z = plate + gap
    sets = PlanetaryGearset(module=s['module_mm'], sun_teeth_number=ns,
        planet_teeth_number=np_, width=b, rim_width=5, n_planets=count,
        pressure_angle=G['pressure_angle_deg'], backlash=G['backlash_parameter'],
        clearance=G['extra_root_clearance_mm'])
    raw_sun = sets.sun.build().rotate((0, 0, 0), (0, 0, 1), 180 / ns)
    sun = raw_sun.cut(rex_profile(8, b + 2, G['rex_fit_allowance_mm'], -1))
    if s['sun_retention_counterbore_mm']:
        sun = sun.cut(cylinder(10.5, s['sun_retention_counterbore_mm'] + 0.1, b - s['sun_retention_counterbore_mm']))
    sun = save(name + '-sun', sun, note='8 mm REX bore; M4 shaft-end washer retention. S1 has no counterbore to preserve its small root web; axial stack not yet finalized')
    planet_phase = 180 / np_ if np_ % 2 else 0
    ring_phase = 180 / nr if np_ % 2 else 0
    raw_planet = sets.planet.build().rotate((0, 0, 0), (0, 0, 1), planet_phase)
    planet = raw_planet.cut(cylinder(G['planet_through_bore_mm'], b + 2, -1))
    for z in (-0.1, b - 4):
        planet = planet.cut(cylinder(13 + G['bearing_fit_allowance_mm'], 4.1, z))
    planet = save(name + '-planet', planet, count, note='Two 695ZZ 5 x 13 x 4 mm bearings per planet; outer-race pocket fit must be checked')
    raw_ring = sets.ring.build().rotate((0, 0, 0), (0, 0, 1), ring_phase)
    annulus = ring_solid(G['housing_od_mm'], 2 * sets.ring.rim_r - 1, b)
    ring = raw_ring.fuse(annulus).clean()
    for x, y in polar(G['tie_rod_radius_mm'], 6, math.pi / 6):
        ring = ring.cut(cylinder(G['tie_rod_hole_mm'], b + 2, -1, x, y))
    ring = save(name + '-fixed-ring', ring, note=f"Fixed ring with six M4 clearance holes on {2 * G['tie_rod_radius_mm']} mm pitch circle")
    carrier_radius = orbit + 6.5
    lower = cylinder(2 * carrier_radius, plate)
    lower = lower.cut(cylinder(G['carrier_journal_abutment_hole_mm'], plate + 2, -1))
    lower = lower.cut(cylinder(16 + G['bearing_fit_allowance_mm'], 5.1, plate - 5))
    for x, y in post_positions:
        lower = lower.fuse(cylinder(7, gap, plate, x, y))
        lower = lower.cut(cylinder(3.4, plate + gap + 2, -1, x, y))
        lower = lower.cut(hex_prism(5.7, 2.8, -0.1).translate((x, y, 0)))
    for x, y in planet_positions:
        lower = lower.cut(cylinder(G['pin_hole_mm'], plate + 2, -1, x, y))
    lower = save(name + '-carrier-lower', lower.clean(), note='Lower plate, M3 spacer posts and 688ZZ carrier journal; use metal 5 mm shoulder pins')
    shaft_d = s['output_rex_mm']
    metal_hub = name in ('S2', 'S3')
    boss_d = 20 if shaft_d == 8 else 26
    upper = cylinder(2 * carrier_radius, plate)
    if not metal_hub:
        upper = upper.fuse(cylinder(boss_d, 8, plate))
        upper = upper.cut(rex_profile(shaft_d, plate + 10, G['rex_fit_allowance_mm'], -1))
    else:
        upper = upper.cut(cylinder(14.2, plate + 2, -1))
        for x in [-8, 8]:
            for y in [-8, 8]:
                upper = upper.cut(cylinder(4.4, plate + 2, -1, x, y))
                upper = upper.cut(cq.Solid.makeCone(4.2, 2.2, 2, cq.Vector(x, y, 0)))
    upper = upper.cut(cylinder(14.2, 5, -0.1))
    for x, y in planet_positions:
        upper = upper.cut(cylinder(G['pin_hole_mm'], plate + 2, -1, x, y))
    for x, y in post_positions:
        upper = upper.cut(cylinder(3.4, plate + 2, -1, x, y))
    radial_hole = cylinder(3.4, boss_d, 0).rotate((0, 0, 0), (0, 1, 0), 90).translate((0, 0, plate + 4))
    nut = hex_prism(5.7, 2.6).rotate((0, 0, 0), (0, 1, 0), 90).translate((boss_d / 2 - 4.0, 0, plate + 4))
    nut_access = cq.Workplane('XY').box(2.6, 6, 5, centered=(False, True, False)).val().translate((boss_d / 2 - 4, 0, plate + 4))
    if not metal_hub:
        upper = upper.cut(radial_hole).cut(nut).cut(nut_access)
    hub_sku = '1309-0016-4008' if name == 'S2' else '1301-0016-4012'
    upper = save(name + '-carrier-upper', upper.clean(), note=f'Four M4 x 10 countersunk bolts on 16 mm square and 14.2 mm through pilot for metal goBILDA {hub_sku} hub' if metal_hub else f'{shaft_d} mm REX positive-drive bore; radial captive M3 nut/set screw for axial retention; needs hub slip/endplay test')
    spacer = ring_solid(G['planet_spacer_od_mm'], G['planet_spacer_id_mm'], b - 8)
    spacer = save(name + '-planet-inner-spacer', spacer, count, material='K&S 9824 brass tube; STL is a FIT SAMPLE ONLY', note='6 mm OD clears selected NSK 695 inner-race abutment limit. Square ends and actual cut length need physical fit check.')
    end_spacer = ring_solid(G['planet_spacer_od_mm'], G['planet_spacer_id_mm'], side_gap)
    end_spacer = save(name + '-planet-end-spacer', end_spacer, count * 2, material='K&S 9824 brass tube or equivalent precision shim; STL is a FIT SAMPLE ONLY', note='Nominal axial stack only; select shims after checking free rotation and actual bearing widths')
    solids = [('ring', ring.translate((0, 0, gear_z))), ('sun', sun.translate((0, 0, gear_z))),
              ('lower', lower), ('upper', upper.translate((0, 0, upper_z)))]
    for i, (x, y) in enumerate(planet_positions):
        solids.append((f'planet-{i}', planet.translate((x, y, gear_z))))
        for z in (gear_z, gear_z + b - 4):
            solids.append((f'bearing-{i}-{z}', bearing(5, 13, 4, z).translate((x, y, 0))))
        solids.append((f'inner-spacer-{i}', spacer.translate((x, y, gear_z + 4))))
        for z in (plate, gear_z + b):
            solids.append((f'end-spacer-{i}-{z}', end_spacer.translate((x, y, z))))
        solids.append((f'pin-{i}', cylinder(5, s['shoulder_length_mm'], 0, x, y)))
    solids.append(('carrier-journal', bearing(8, 16, 5, plate - 5)))
    assembly = cq.Assembly(name=name)
    for label, solid in solids:
        color = cq.Color('#a3aeb5') if any(k in label for k in ('bearing', 'pin', 'spacer')) else cq.Color('#d7a74c') if label == 'sun' else cq.Color('#6fa89c') if label.startswith('planet') else cq.Color('#7f8a9c') if label == 'ring' else cq.Color('#ddd7cb')
        assembly.add(solid, name=label.replace('.', '_'), color=color)
    assembly.save(str(OUT / (name + '-cartridge-REFERENCE.step')))
    basic = {'module_mm': s['module_mm'], 'gear_width_mm': b, 'carrier_gap_mm': gap,
             'shoulder_length_mm': s['shoulder_length_mm'], 'gear_z_mm': gear_z,
             'upper_carrier_z_mm': upper_z, 'cartridge_height_excluding_fastener_heads_mm': upper_z + plate + 8,
             'housing_od_mm': G['housing_od_mm'], 'gear_ratio': info['ratio'],
             'planet_root_web_mm': info['planet_root_web_mm'], 'interference_samples': []}
    cycle = 360 / nr
    for theta in np.linspace(0, cycle, 13):
        sun_at = sun.rotate((0, 0, 0), (0, 0, 1), info['ratio'] * theta)
        planet_angle = (1 - (info['ratio'] - 1) * ns / np_) * theta
        p_at = planet.rotate((0, 0, 0), (0, 0, 1), planet_angle)
        a = math.radians(theta)
        p_at = p_at.translate((orbit * math.cos(a), orbit * math.sin(a), 0))
        values = [sun_at.intersect(p_at).Volume(), raw_ring.intersect(p_at).Volume()]
        basic['interference_samples'].append({'carrier_deg': float(theta), 'sun_planet_mm3': float(values[0]), 'ring_planet_mm3': float(values[1])})
    REPORT['stages'][name] = basic
    assert max(max(x['sun_planet_mm3'], x['ring_planet_mm3']) for x in basic['interference_samples']) < 0.001, name
    for x, y in planet_positions:
        positioned = planet.translate((x, y, gear_z))
        assert positioned.intersect(sun.translate((0, 0, gear_z))).Volume() < 0.001, f'{name}: incorrectly clocked planet'
        assert positioned.intersect(ring.translate((0, 0, gear_z))).Volume() < 0.001, f'{name}: planet/ring phase'
        assert positioned.intersect(lower).Volume() < 0.001, f'{name}: planet/post collision'
        assert positioned.intersect(upper.translate((0, 0, upper_z))).Volume() < 0.001, name
    assert lower.intersect(ring.translate((0, 0, gear_z))).Volume() < 0.001, name
    assert upper.translate((0, 0, upper_z)).intersect(ring.translate((0, 0, gear_z))).Volume() < 0.001, name
    basic['checks'] = '13 phase samples for one representative sun/planet and ring/planet mesh, plus all planets at initial phase and carrier/gear clearances. Equal-spacing assembly condition also checked. Full assembly is checked separately.'
    REPORT['stages'][name] = basic
    print('Checked stage:', name, flush=True)
    return solids


def render_stage(solids, name):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(10, 8), facecolor='#f8f5ee')
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('#f8f5ee')
    triangles, colors = [], []
    for label, solid in solids:
        if label == 'upper' or label == 'ring':
            continue
        vertices, faces = solid.tessellate(0.12)
        v = np.array([x.toTuple() for x in vertices]); f = np.array(faces)
        color = '#d6a34b' if label == 'sun' else '#699f94' if label.startswith('planet') else '#b3bdc2' if any(x in label for x in ('pin', 'bearing')) else '#d5cebd'
        triangles.append(v[f])
        colors.extend([color] * len(f))
    ax.add_collection3d(Poly3DCollection(np.concatenate(triangles), facecolors=colors, linewidths=0, shade=True, alpha=1))
    ax.set(xlim=(-40, 40), ylim=(-40, 40), zlim=(0, 45))
    ax.set_box_aspect((80, 80, 45)); ax.view_init(55, -65); ax.set_axis_off()
    fig.suptitle(f'{name}: load-sized candidate cartridge', fontsize=18)
    fig.text(.5, .08, 'Upper carrier and fixed ring hidden to show the bearing-supported planets.', ha='center', fontsize=11)
    fig.text(.5, .04, 'Engineering candidate. Physical strength, fit and wear are not yet tested.', ha='center', fontsize=11, color='#8a493a')
    fig.savefig(OUT / (name + '-internal-preview.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['S1', 'S2', 'S3'])
    args = parser.parse_args()
    report_path = OUT / ('validation-' + (args.stage or 'all') + '.json')
    report_path.write_text(json.dumps(REPORT, indent=2) + '\n')
    started = time.time()
    try:
        evaluate(CFG)
        for stage in CFG['stages']:
            if args.stage and stage['name'] != args.stage:
                continue
            solids = make_stage(stage)
            render_stage(solids, stage['name'])
        REPORT['status'] = 'DIGITAL STAGE CHECKS PASSED; NOT A COMPLETE OR PHYSICALLY VALIDATED DRIVE'
    except Exception as exc:
        REPORT['status'] = 'FAILED'
        REPORT['error'] = str(exc)
        raise
    finally:
        REPORT['elapsed_seconds'] = time.time() - started
        report_path.write_text(json.dumps(REPORT, indent=2) + '\n')

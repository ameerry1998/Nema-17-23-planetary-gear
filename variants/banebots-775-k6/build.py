"""Codex (secondary agent, 2026-10-21): unpowered K6 fit prototypes.

Generate engineering solids with the Apache-2.0 cq_gears library. This is an
independent parametric prototype, not a modification of Omar Salem's Fusion
files. No component here is released for motor-powered use.
"""
from pathlib import Path
import json
import math
import argparse
import cadquery as cq
import numpy as np
import trimesh
from cq_gears import PlanetaryGearset

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text())
OUT = ROOT / 'fit-tests'
CAD = ROOT / 'cad'
OUT.mkdir(exist_ok=True)
CAD.mkdir(exist_ok=True)
REPORT = {'purpose': P['status'], 'parts': {}, 'load_validation': 'NOT PERFORMED'}


def save_part(name, shape, folder=OUT):
    if isinstance(shape, cq.Workplane):
        shape = shape.val()
    assert shape.isValid(), f'Invalid CAD solid: {name}'
    assert len(shape.Solids()) == 1, f'Expected a single solid: {name}'
    cq.exporters.export(shape, str(folder / (name + '.step')))
    cq.exporters.export(shape, str(folder / (name + '.stl')), tolerance=0.015, angularTolerance=0.08)
    mesh = trimesh.load_mesh(folder / (name + '.stl'))
    assert mesh.is_watertight and mesh.is_volume, f'Invalid printable mesh: {name}'
    assert len(mesh.split()) == 1, f'Disconnected mesh: {name}'
    REPORT['parts'][name] = {'cad_valid': True, 'mesh_watertight': True,
                            'volume_mm3': float(mesh.volume),
                            'dimensions_mm': mesh.extents.tolist()}
    print('Exported and checked:', name, flush=True)
    return shape


def make_gauges():
    for d in (5.0, 5.1, 5.2, 5.3):
        shape = cq.Workplane('XY').circle(6).circle(d/2).extrude(3)
        save_part(f'shaft-fit-{d:.1f}mm-NO-POWER', shape)
    plate = cq.Workplane('XY').circle(25).circle(10.5).extrude(2)
    for sign in (-1, 1):
        cut = (cq.Workplane('XY').center(sign*P['motor_hole_spacing_mm_assumed']/2, 0)
               .slot2D(7.4, 4.4, 0).extrude(2))
        plate = plate.cut(cut)
    save_part('motor-face-slotted-TEMPLATE-NO-POWER', plate)
    for d in (11.0, 11.1, 11.2):
        shape = cq.Workplane('XY').circle(9).circle(d/2).extrude(5)
        save_part(f'bearing-seat-{d:.1f}mm-NO-POWER', shape)


def make_gears():
    ring_z = P['sun_teeth'] + 2*P['planet_teeth']
    ratio = 1 + ring_z / P['sun_teeth']
    orbit = P['module_mm']*(P['sun_teeth']+P['planet_teeth'])/2
    assert (ring_z + P['sun_teeth']) % P['planets'] == 0
    assert 2*orbit*math.sin(math.pi/P['planets']) > P['module_mm']*(P['planet_teeth']+2)
    REPORT['gearing'] = {'sun_teeth': P['sun_teeth'], 'planet_teeth': P['planet_teeth'],
                         'ring_teeth': ring_z, 'ratio_per_stage': ratio,
                         'proposed_total_ratio': ratio**P['stages_proposed'],
                         'planet_center_radius_mm': orbit,
                         'equally_spaced_planets_assembly_condition': True,
                         'motor_no_load_output_estimate_at_12V_rpm': 19500*(12/18)/(ratio**P['stages_proposed']),
                         'speed_note': 'Voltage-scaled estimate only; not a measured loaded speed.'}
    gs = PlanetaryGearset(module=P['module_mm'], sun_teeth_number=P['sun_teeth'],
                          planet_teeth_number=P['planet_teeth'], width=P['coupon_width_mm'],
                          rim_width=P['ring_rim_mm'], n_planets=P['planets'],
                          pressure_angle=P['pressure_angle_deg'],
                          backlash=P['cq_gears_backlash_parameter'],
                          clearance=P['tip_root_extra_clearance_mm'])
    sun = save_part('sun-18T-HAND-TEST', gs.sun.build(bore_d=P['sun_test_bore_mm']))
    planet = save_part('planet-27T-HAND-TEST-print-three', gs.planet.build(bore_d=P['planet_test_bore_mm']))
    ring = save_part('ring-72T-HAND-TEST', gs.ring.build())
    carrier = cq.Workplane('XY').circle(21).circle(2.6).extrude(2)
    for i in range(P['planets']):
        a = 2*math.pi*i/P['planets']
        x, y = orbit*math.cos(a), orbit*math.sin(a)
        pin = cq.Workplane('XY').workplane(offset=2).center(x,y).circle(P['printed_fixture_pin_mm']/2).extrude(3.5)
        carrier = carrier.union(pin)
    save_part('carrier-HAND-TEST-ONLY', carrier)
    stand = cq.Workplane('XY').circle(36).extrude(2)
    stand = stand.union(cq.Workplane('XY').workplane(offset=2).circle(2.4).extrude(6))
    stand = stand.union(cq.Workplane('XY').workplane(offset=2).circle(36).circle(27).extrude(2.2))
    stand = stand.union(cq.Workplane('XY').workplane(offset=4.2).circle(36).circle(gs.ring.rim_r+0.2).extrude(1))
    save_part('stand-HAND-TEST-ONLY', stand)
    assembled = [ring.rotate((0,0,0),(0,0,1),180/ring_z),
                 sun.rotate((0,0,0),(0,0,1),180/P['sun_teeth'])]
    for i in range(P['planets']):
        a = 2*math.pi*i/P['planets']
        assembled.append(planet.rotate((0,0,0),(0,0,1),180/P['planet_teeth']).translate((orbit*math.cos(a),orbit*math.sin(a),0)))
    intersections = []
    for i in range(len(assembled)):
        for j in range(i+1,len(assembled)):
            v=assembled[i].intersect(assembled[j]).Volume()
            intersections.append(float(v))
    REPORT['initial_gear_intersection_max_mm3'] = max(intersections)
    assert max(intersections) < 0.001, intersections
    sampled = []
    for theta in np.linspace(0, 5, 11):
        a = math.radians(theta)
        s = sun.rotate((0,0,0),(0,0,1),180/P['sun_teeth'] + ratio*theta)
        pg = planet.rotate((0,0,0),(0,0,1),180/P['planet_teeth'] + (1-(ratio-1)*P['sun_teeth']/P['planet_teeth'])*theta)
        pg = pg.translate((orbit*math.cos(a),orbit*math.sin(a),0))
        sampled.extend([float(s.intersect(pg).Volume()),float(assembled[0].intersect(pg).Volume())])
    REPORT['sampled_motion_intersection_max_mm3'] = max(sampled)
    REPORT['sampled_motion_note'] = '11 positions over one 5-degree carrier tooth-mesh cycle. Ideal CAD only; not physical running clearance or durability.'
    assert max(sampled) < 0.001, sampled
    comp = cq.Compound.makeCompound(assembled)
    cq.exporters.export(comp,str(CAD/'single-stage-mesh-REFERENCE.step'))
    rendered = [assembled[0].translate((0,0,4.2))] + [s.translate((0,0,4.3)) for s in assembled[1:]]
    rendered += [carrier.val().translate((0,0,2.1)),stand.val()]
    cq.exporters.export(cq.Compound.makeCompound(rendered),str(CAD/'hand-test-assembly-REFERENCE.step'))
    vertices = []
    for s in rendered:
        verts, faces = s.tessellate(0.05)
        vertices.append((np.array([v.toTuple() for v in verts]),np.array(faces)))
    render_preview(vertices)


def render_preview(meshes):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    colors = ['#556575','#e1a542','#8baca4','#8baca4','#8baca4','#c7c3b8','#e5e1d8']
    fig = plt.figure(figsize=(10,7),facecolor='#faf8f2')
    ax = fig.add_subplot(111,projection='3d')
    ax.set_facecolor('#faf8f2')
    faces = np.concatenate([v[f] for v,f in meshes])
    face_colors = np.concatenate([np.tile(matplotlib.colors.to_rgba(color),(len(f),1)) for (_,f),color in zip(meshes,colors)])
    ax.add_collection3d(Poly3DCollection(faces,facecolors=face_colors,linewidths=0,alpha=1,shade=False,antialiased=False))
    ax.set_xlim(-38,38); ax.set_ylim(-38,38); ax.set_zlim(0,15)
    ax.set_box_aspect((76,76,15)); ax.view_init(90,-90); ax.set_axis_off()
    fig.suptitle('K6 / BaneBots 775: first gear-mesh test',fontsize=19,y=.95)
    fig.text(.5,.12,'18-tooth sun  /  27-tooth planets  /  72-tooth ring',ha='center',fontsize=12)
    fig.text(.5,.07,'5:1 per stage. Hand-turn only. This is not a powered gearbox.',ha='center',fontsize=11,color='#824a36')
    fig.savefig(ROOT/'gear-mesh-preview.png',dpi=170,bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--gauges-only',action='store_true')
    opts=args.parse_args()
    make_gauges()
    if not opts.gauges_only:
        make_gears()
    (ROOT/'validation.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('Finished. Physical fit, motion through full cycle, strength, heat and wear remain untested.',flush=True)

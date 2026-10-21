"""Codex (secondary agent, 2026-10-21): printed split cassette around a stock-steel torque path."""
import hashlib
import json
from pathlib import Path
import cadquery as cq
import build_drive as B

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT / 'socket-adapter.json').read_text())
OUT = ROOT / 'socket-adapter'
OUT.mkdir(exist_ok=True)
B.OUT = OUT
B.REPORT = {'status': 'BUILDING', 'parts': {}, 'physical_testing': 'NOT PERFORMED',
            'source_sha256': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in ['socket-adapter.json', 'build_socket_adapter.py', 'build_drive.py', 'drive.json', 'drive-assembly/assembly-validation.json', 'drive-assembly/S3-output-cap-retainer-top.step']},
            'limitations': C['unverified']}
R = B.REPORT


def square(width, height, z=0):
    return cq.Workplane('XY').rect(width, width).extrude(height).val().translate((0, 0, z))


def bore_x(shape, y, z, diameter, x0=-25, length=50):
    hole = B.cylinder(diameter, length).rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y, z))
    return shape.cut(hole)


def main():
    h = C['length_mm']; gap = C['split_gap_mm']; clearance = C['socket_diametral_clearance_mm']
    d1 = json.loads((ROOT / 'drive-assembly/assembly-validation.json').read_text())
    assert d1['status'].startswith('MODELED FIXED/MOVING INTERFERENCE CHECK PASSED')
    assert d1['source_sha256']['drive.json'] == hashlib.sha256((ROOT / 'drive.json').read_bytes()).hexdigest()
    case_end = d1['envelope']['case_end_mm']
    assert abs(C['case_z_on_D1_mm'] + C['input_socket_z_mm'] + C['input_shaft_engagement_mm'] - d1['envelope']['output_tip_mm']) < .001
    assert abs(C['required_D1_collar_spacer_length_mm'] - (C['case_z_on_D1_mm'] + C['collar_z_mm'] - case_end)) < .001
    assert C['output_socket_z_mm'] - (C['input_socket_z_mm'] + C['input_socket_length_mm']) == C['square_bridge_length_mm'] - 2 * C['square_engagement_mm']
    assert C['square_engagement_mm'] <= C['square_bore_depth_assumed_mm']
    assert C['input_shaft_engagement_mm'] < C['input_socket_hex_depth_mm']
    body = B.cylinder(C['body_od_mm'], h)
    body = body.cut(B.cylinder(8, h + 2, -1))
    body = body.cut(B.cylinder(16, C['collar_z_mm'] + .1, -.1))
    body = body.cut(B.cylinder(C['collar_od_mm'] + C['collar_clearance_mm'], C['collar_length_mm'] + .4, C['collar_z_mm'] - .2))
    body = body.cut(B.cylinder(12.5, C['input_socket_z_mm'], 0))
    for prefix in ['input', 'output']:
        body = body.cut(B.cylinder(C[prefix + '_socket_max_od_mm'] + clearance,
                                  C[prefix + '_socket_length_mm'] + .4, C[prefix + '_socket_z_mm'] - .2))
    body = body.cut(B.cylinder(10, C['output_socket_z_mm'] - C['input_socket_z_mm'] - C['input_socket_length_mm'], C['input_socket_z_mm'] + C['input_socket_length_mm']))
    for z in [7, 55]:
        for y in [-18, 18]:
            lug = cq.Workplane('XY').box(20, 8, 8).val().translate((0, y, z))
            body = body.fuse(lug)
            body = bore_x(body, y, z, 3.4)
            body = bore_x(body, y, z, 6.2, -25, 15)
            nut = B.hex_prism(5.7, 25).rotate((0, 0, 0), (0, 1, 0), 90).translate((7, y, z))
            body = body.cut(nut)
    body = body.clean()
    halves = []
    for name, sign in [('left', -1), ('right', 1)]:
        clip = cq.Workplane('XY').box(50, 100, h + 20).val().translate((sign * (25 + gap / 2), 0, h / 2))
        half = body.intersect(clip).clean()
        halves.append((name, half))
        printed = half.rotate((0, 0, 0), (0, 1, 0), -90 if sign > 0 else 90)
        printed = printed.translate((0, 0, -printed.BoundingBox().zmin))
        B.save('SA1-cassette-' + name, printed, material=C['material'], note='Print split face down. Contains ordinary steel sockets; do not power before fit/retention tests. The stored STEP/STL is in print orientation.')
    reference = []
    for prefix in ['input', 'output']:
        z, length, od, af, depth = [C[prefix + suffix] for suffix in ['_socket_z_mm', '_socket_length_mm', '_socket_max_od_mm', '_socket_hex_mm', '_socket_hex_depth_mm']]
        socket = B.cylinder(od, length, z)
        hex_z = z - .1 if prefix == 'input' else z + length - depth
        sq_z = z + length - C['square_bore_depth_assumed_mm'] if prefix == 'input' else z - .1
        hex_bore = B.hex_prism(af + .1, depth + .1, hex_z).rotate((0, 0, 0), (0, 0, 1), 30)
        socket = socket.cut(hex_bore).cut(square(6.45, C['square_bore_depth_assumed_mm'] + .1, sq_z))
        reference.append((prefix + '-steel-socket-envelope', socket))
    bridge_z = C['input_socket_z_mm'] + C['input_socket_length_mm'] - C['square_engagement_mm']
    reference.append(('steel-square-bridge-envelope', square(6.35, C['square_bridge_length_mm'], bridge_z)))
    reference.append(('existing-metal-collar-envelope', B.ring_solid(C['collar_od_mm'], 12, C['collar_length_mm'], C['collar_z_mm'])))
    shaft_tip_local = C['input_socket_z_mm'] + C['input_shaft_engagement_mm']
    reference.append(('12REX-output-shaft-envelope', B.rex_profile(12, shaft_tip_local + 2, z=-2)))
    interference = []
    for name, half in halves:
        for label, part in reference:
            volume = half.intersect(part).Volume()
            if volume > .001:
                interference.append(dict(printed=name, metal=label, volume_mm3=volume))
    for i, (name, part) in enumerate(reference):
        for label, other in reference[i + 1:]:
            volume = part.intersect(other).Volume()
            if volume > .001:
                interference.append(dict(metal_a=name, metal_b=label, volume_mm3=volume))
    retainer = cq.importers.importStep(str(ROOT / 'drive-assembly/S3-output-cap-retainer-top.step')).val().translate((0, 0, case_end - C['case_z_on_D1_mm']))
    for x, y in B.polar(18.5, 3, 3.141592653589793 / 3):
        retainer = retainer.fuse(B.cylinder(4, 2, case_end + 2 - C['case_z_on_D1_mm'], x, y))
    for name, half in halves:
        volume = half.intersect(retainer).Volume()
        if volume > .001:
            interference.append(dict(printed=name, fixed='D1 output retainer with M2 head envelopes', volume_mm3=volume))
    assert not interference, interference
    assy = cq.Assembly(name='SA1-socket-cassette-fit-candidate')
    for name, half in halves:
        assy.add(half, name=name, color=cq.Color('#5d9e94'))
    for name, part in reference:
        assy.add(part, name=name, color=cq.Color('#aab2b7'))
    assy.save(str(OUT / 'SA1-REFERENCE.step'))
    render(halves, reference)
    B.save('SA1-output-collar-spacer-FIT-SAMPLE', B.ring_solid(15, 12.15, C['required_D1_collar_spacer_length_mm']), material='Precision metal spacer; STL is a fit sample only')
    R.update(status='DIGITAL SOCKET-CASE CLEARANCE CHECK PASSED; PHYSICAL FIT AND LOAD TESTS REQUIRED',
        case_to_simplified_hardware_intersections=interference,
        input_shaft_tip_local_mm=shaft_tip_local,
        retainer_with_screw_head_clearance_mm=C['case_z_on_D1_mm'] - (case_end + 4),
        attachment_end_on_D1_mm=C['case_z_on_D1_mm'] + h,
        torque_path='12 REX shaft -> 11 mm steel socket -> steel male-square bridge -> 6.35 mm steel socket -> grinder hex. Printed split case locates and retains this chain; the socket bridge needs its own load verification.',
        physical_test_next='Check actual socket/bridge dimensions and hand fit before printing both case halves. No metal parts need printing.')


def render(halves, reference):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 8), facecolor='#f6f4ed')
    groups = [[(n, s.translate((-18 if n == 'left' else 18, 0, 0))) for n, s in halves], reference]
    for index, parts in enumerate(groups):
        ax = fig.add_subplot(1, 2, index + 1, projection='3d')
        ax.set_facecolor('#f6f4ed')
        triangles, colors = [], []
        for name, solid in parts:
            vertices, faces = solid.tessellate(.15)
            v = np.array([a.toTuple() for a in vertices])
            triangles.append(v[np.array(faces)])
            color = '#5d9e94' if index == 0 else '#bca363' if 'bridge' in name else '#9ea9b0'
            colors.extend([color] * len(faces))
        ax.add_collection3d(Poly3DCollection(np.concatenate(triangles), facecolors=colors, linewidths=0, shade=True))
        ax.set(xlim=(-40, 40), ylim=(-28, 28), zlim=(-3, 70))
        ax.set_box_aspect((80, 56, 73)); ax.view_init(20, -55); ax.set_axis_off()
        ax.set_title('PRINT: two CF-plastic case halves' if index == 0 else 'BUY: steel sockets + square bridge', fontsize=14)
    fig.suptitle('SA1 interchangeable grinder attachment', fontsize=20, y=.96)
    fig.text(.5, .10, 'The case holds the parts together. The steel chain transmits the grinding torque.', ha='center', fontsize=13)
    fig.text(.5, .06, 'CAD candidate with simplified hardware. Physical fit, retention and load tests are pending.', ha='center', fontsize=11, color='#8a493a')
    fig.savefig(OUT / 'SA1-printed-and-bought.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    report = OUT / 'validation.json'
    report.write_text(json.dumps(R, indent=2) + '\n')
    try:
        main()
    except Exception as exc:
        R.update(status='FAILED', error=str(exc))
        raise
    finally:
        report.write_text(json.dumps(R, indent=2) + '\n')

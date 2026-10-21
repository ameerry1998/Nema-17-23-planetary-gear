"""Codex (secondary agent, 2026-10-21): static fixture estimates and instrument-error handling."""
import math


def lever_torque(force_kgf, radius_mm, angle_deg=90):
    if force_kgf < 0 or radius_mm <= 0 or not 0 < angle_deg <= 180:
        raise ValueError('Use positive radius, nonnegative force and a valid force/lever angle')
    return force_kgf * 9.80665 * radius_mm / 1000 * math.sin(math.radians(angle_deg))


def limited_reading(limit_Nm, relative_error, absolute_error_Nm=0):
    if limit_Nm <= 0 or not 0 <= relative_error < 1 or not 0 <= absolute_error_Nm < limit_Nm:
        raise ValueError('Specify a positive limit and the instrument accuracy, not its resolution')
    return (limit_Nm - absolute_error_Nm) / (1 + relative_error)


def dimensions(config, drive):
    a = drive['assembly']
    first = drive['stages'][0]
    shaft_tip = drive['geometry']['carrier_plate_mm'] + (first['carrier_gap_mm'] + first['width_mm']) / 2 - first['sun_retention_counterbore_mm']
    shaft_start = shaft_tip - a['input_shaft_length_mm']
    front = config['plate_front_z_mm']
    hub_end = front + config['hub_length_mm']
    overlap = hub_end - max(front, shaft_start)
    endplay = -13.5 - hub_end
    engagement = config['hub_screw_length_mm'] - (config['plate_thickness_mm'] - config['hub_screw_head_recess_depth_mm'])
    if not 6 <= overlap <= config['hub_length_mm']:
        raise ValueError('Input shaft has insufficient engagement in the locking hub')
    if not .1 <= endplay <= .3:
        raise ValueError('Locking hub must leave 0.1 to 0.3 mm nominal input-spacer endplay')
    if not 6 <= engagement <= config['hub_length_mm']:
        raise ValueError('Hub screws need 6 mm engagement without protruding')
    standoff = a['input_cap_z_mm'] - front
    if standoff <= 0:
        raise ValueError('Fixture plate must be behind the input cap')
    return dict(input_shaft_start_mm=shaft_start, hub_end_mm=hub_end,
                hub_shaft_overlap_mm=overlap, nominal_input_endplay_mm=endplay,
                hub_screw_engagement_mm=engagement, standoff_length_mm=standoff)


def screen(config, drive):
    t = config['maximum_planned_output_torque_Nm'] * 1000
    radius = drive['geometry']['tie_rod_radius_mm']
    plate = config['plate_thickness_mm']
    factor = 2
    force = t / (6 * radius)
    return dict(
        assumed_peak_output_Nm=t / 1000,
        ideal_input_reaction_Nm=t / 1000 / math.prod(1 + (s['sun_teeth'] + 2 * s['planet_teeth']) / s['sun_teeth'] for s in drive['stages']),
        tie_rod_equal_share_tangential_force_N=force,
        tie_rod_assumed_unequal_share_factor=factor,
        plate_hole_projected_bearing_pressure_MPa=force * factor / (4 * plate),
        scope='Static equilibrium and projected pressure only; no measured friction, clamping, plate bending, printed allowable or fixture rating',
        example_5Nm_limit_with_4percent_reading_accuracy_Nm=limited_reading(5, .04),
        example_2kgf_at_100mm_perpendicular_Nm=lever_torque(2, 100))

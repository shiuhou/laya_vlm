"""Offline initial-depth points versus returned-pose nominal gripper sweeps."""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

from .records import code_identity, file_hash, load_records
from .robot_only_geometry import forward, quaternion_matrix
from .sensor_gripper_proximity import proxy_distance

ROOT = Path(__file__).resolve().parents[2]
RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
PROTOCOL = ROOT / 'docs/research/task2_observed_surface_sweep_protocol.md'
SOURCES = {
    'task2-box-point-boundary-run-01/episodes.jsonl': 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771',
    'interaction-observability-paired-01/close/0000.npz': '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969',
    'task2-box-support-run-02/sensor-representation.json': 'be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead',
    'robot-geometry-observability-03/robot-calibration.json': '11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa',
    'robot-geometry-observability-03/static-setup.json': 'cd500c2464cd9692796e89ce5a9ce1485576d8ba8c17398a490b89f8f2be2bab',
}
HELPERS = {'robot_only_geometry.py': 'c8563e80070a7081a43c9d92d1f6f86446732c77964c2c55665ab76bd32d147c',
           'sensor_gripper_proximity.py': '4f52b9e168cdb802daca4eea1bd26115750957430e1e5e1fe89ec47fba233db6'}
MOVES = {'MV_FWD': [.01, 0., 0.], 'MV_BACK': [-.01, 0., 0.],
         'MV_LEFT': [0., .01, 0.], 'MV_RIGHT': [0., -.01, 0.],
         'MV_UP': [0., 0., .01], 'MV_DOWN': [0., 0., -.01], 'STOP': [0., 0., 0.]}
GEOMS = ['gripper0_hand_collision', 'gripper0_finger1_collision', 'gripper0_finger1_pad_collision',
         'gripper0_finger2_collision', 'gripper0_finger2_pad_collision']
OWN_KEYS = {'robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos'}


def write(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def support(depth, k, transform, bounds):
    """Exact row-major arithmetic from task2_box_support.sensor_representation."""
    selected = np.zeros(depth.shape, bool)
    x1, y1, x2, y2 = bounds
    selected[y1:y2, x1:x2] = True
    selected &= np.isfinite(depth) & (depth >= .01) & (depth <= 5.)
    ys, xs = np.nonzero(selected)
    z = depth[ys, xs].astype(np.float64)
    camera = np.column_stack(((xs+.5-k[0, 2])*z/k[0, 0], (ys+.5-k[1, 2])*z/k[1, 1], z))
    world = camera @ transform[:3, :3].T + transform[:3, 3]
    return [{'pixel_xy': [int(x), int(y)], 'depth_m': float(depth[y, x]), 'position_world_m': p.tolist()}
            for x, y, p in zip(xs, ys, world)]


def subtree(calibration):
    """Keep fixed own hand root and its descendants; discard all arm/base data."""
    selected = []
    names = set()
    for body in calibration['bodies']:
        if body['name'] == 'robot0_right_hand':
            item = deepcopy(body)
            if item['joints']:
                raise ValueError('Fixed own hand root required')
            item.update(parent=None, position_parent_m=[0., 0., 0.], quaternion_parent_wxyz=[1., 0., 0., 0.])
            selected.append(item)
            names.add(body['name'])
        elif body['parent'] in names:
            selected.append(deepcopy(body))
            names.add(body['name'])
    if [g['name'] for g in calibration['geometries']] != GEOMS:
        raise ValueError('All five sealed gripper proxies required in calibration order')
    sites = [s for s in calibration['sites'] if s['name'] == 'gripper0_grip_site']
    result = {'version': calibration['version'], 'bodies': selected, 'sites': deepcopy(sites),
              'geometries': deepcopy(calibration['geometries'])}
    if len(sites) != 1 or any(x['body'] not in names for x in sites + result['geometries']):
        raise ValueError('Self-contained gripper subtree required')
    return result


def own_packet(observations):
    return {k: observations[k] for k in sorted(OWN_KEYS)}


def place(calibration, packet):
    if set(packet) != OWN_KEYS:
        raise ValueError('Only returned own position, body quaternion and signed jaws admitted')
    p, q, jaws = (np.asarray(packet[k], float) for k in ('robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos'))
    if p.shape != (3,) or q.shape != (4,) or jaws.shape != (2,) or not all(np.isfinite(v).all() for v in (p, q, jaws)):
        raise ValueError('Finite returned own packet required')
    local = forward(calibration, dict(zip(('gripper0_finger_joint1', 'gripper0_finger_joint2'), jaws)))
    site = local['sites']['gripper0_grip_site']
    mount = np.asarray(site['rotation_world'])
    body_rotation = quaternion_matrix(q[[3, 0, 1, 2]])
    site_rotation = body_rotation @ mount
    origin = np.asarray(site['position_world_m'])
    vertices = {name: ((np.asarray(g['vertices_world_m'])-origin) @ mount) @ site_rotation.T+p
                for name, g in local['geometries'].items()}
    return vertices, {'body_to_site_position_m': origin.tolist(), 'body_to_site_rotation': mount.tolist(),
                      'returned_site_rotation_world': site_rotation.tolist()}


def distances(points, geometries, delta):
    """Per-proxy solids only; gaps remain gaps in the min/OR union."""
    result = {}
    for mode in ('current', 'endpoint', 'sweep'):
        columns = []
        for vertices in geometries.values():
            if mode == 'endpoint':
                vertices = vertices + delta
            elif mode == 'sweep' and np.any(delta):
                vertices = np.concatenate((vertices, vertices+delta))
            columns.append(proxy_distance(points, vertices))
        result[mode] = {'distance': np.column_stack([c[0] for c in columns]),
                        'closest': np.stack([c[1] for c in columns], axis=1),
                        'inside': np.column_stack([c[2] for c in columns])}
    return result


def summarize(arrays, indices, support_rows, names):
    result = {}
    for label, columns in [(name, [i]) for i, name in enumerate(names)] + [('union', list(range(len(names))))]:
        if not len(indices):
            result[label] = {'point_count': 0, 'minimum_m': None, 'contained_point_count': 0,
                             'nearest': None, 'exact_minimizer_count': 0}
            continue
        selected = arrays['distance'][np.ix_(indices, columns)]
        row, col = np.unravel_index(np.argmin(selected), selected.shape)
        point, proxy = int(indices[row]), columns[col]
        minimum = float(selected[row, col])
        result[label] = {'point_count': len(indices), 'minimum_m': minimum,
            'contained_point_count': int(arrays['inside'][np.ix_(indices, columns)].any(axis=1).sum()),
            'exact_minimizer_count': int(np.count_nonzero(selected == minimum)),
            'nearest': {**support_rows[point], 'full_support_index': point, 'proxy': names[proxy],
                        'closest_solid_point_world_m': arrays['closest'][point, proxy].tolist(),
                        'inside': bool(arrays['inside'][point, proxy])}}
    return result


def compute(request, output):
    if set(request) != {'calibration', 'own_packets', 'full_support', 'inner_indices'} or set(request['own_packets']) != {'sample0', 'sample1'}:
        raise ValueError('Sanitized fixed two-sample schema required')
    if request['calibration'] != subtree(request['calibration']):
        raise ValueError('Only normalized own-gripper calibration subtree admitted')
    output = Path(output)
    output.mkdir(exist_ok=False)
    full = request['full_support']
    if any(set(r) != {'pixel_xy', 'depth_m', 'position_world_m'} for r in full):
        raise ValueError('Only observed support fields admitted')
    points = np.asarray([r['position_world_m'] for r in full], float).reshape(-1, 3)
    if not np.isfinite(points).all():
        raise ValueError('Finite support points required')
    groups = {'inner': np.asarray(request['inner_indices'], int), 'full': np.arange(len(full))}
    if len(set(groups['inner'])) != len(groups['inner']) or np.any(groups['inner'] < 0) or np.any(groups['inner'] >= len(full)):
        raise ValueError('Inner support must be a subset of full support')
    result = {'candidate_order': list(MOVES), 'geometry_order': GEOMS, 'samples': {}}
    for label, packet in request['own_packets'].items():
        geometries, mount = place(request['calibration'], packet)
        sample = {'mount': mount, 'proxy_vertices_world_m': {k: v.tolist() for k, v in geometries.items()}, 'candidates': {}}
        for token, delta in MOVES.items():
            measured = distances(points, geometries, np.asarray(delta))
            arrays = {mode+'_'+key: value for mode, values in measured.items() for key, value in values.items()}
            artifact = label+'-'+token+'.npz'
            np.savez_compressed(output / artifact, **arrays)
            sample['candidates'][token] = {'nominal_delta_m': delta, 'artifact': artifact,
                'artifact_sha256': file_hash(output / artifact),
                'supports': {group: {mode: summarize(values, indices, full, GEOMS) for mode, values in measured.items()}
                             for group, indices in groups.items()}}
        result['samples'][label] = sample
    write(output / 'features.json', result)


def compatibility(calibration):
    """Present-time XML subtree/box checks only; no compiler or scene construction."""
    import scipy
    package = Path(importlib.util.find_spec('robosuite').origin).parent
    xml_path = package / 'models/assets/grippers/panda_gripper.xml'
    xml = ET.parse(xml_path).getroot()
    def values(node, name, default):
        return np.fromstring(node.get(name, default), sep=' ')
    bodies = {b['name']: b for b in calibration['bodies']}
    checked = []
    for node in xml.findall('.//body'):
        name = 'gripper0_'+node.attrib['name']
        saved = bodies[name]
        if not np.allclose(values(node, 'pos', '0 0 0'), saved['position_parent_m'], rtol=0, atol=1e-12) or not np.allclose(
                quaternion_matrix(values(node, 'quat', '1 0 0 0')), quaternion_matrix(saved['quaternion_parent_wxyz']), rtol=0, atol=1e-12):
            raise ValueError('Current static body mismatch: '+name)
        for joint, saved_joint in zip(node.findall('joint'), saved['joints']):
            if ('gripper0_'+joint.attrib['name'] != saved_joint['name'] or joint.attrib['type'] != saved_joint['kind']
                    or not np.array_equal(values(joint, 'axis', '0 0 1'), saved_joint['axis_body'])
                    or not np.array_equal(values(joint, 'pos', '0 0 0'), saved_joint['anchor_body_m'])
                    or float(joint.get('ref', '0')) != saved_joint['qpos_reference']):
                raise ValueError('Current static signed-jaw mapping mismatch')
        if len(node.findall('joint')) != len(saved['joints']):
            raise ValueError('Current static joint count mismatch')
        checked.append(name)
    for geom in calibration['geometries']:
        name = geom['name'].removeprefix('gripper0_')
        node = xml.find('.//geom[@name="'+name+'"]')
        if node is None:
            raise ValueError('Missing current gripper geometry')
        if node.attrib['type'] == 'box':
            if not np.array_equal(np.max(np.abs(geom['vertices_local_m']), axis=0), values(node, 'size', '')) or not np.allclose(
                    geom['position_body_m'], values(node, 'pos', '0 0 0'), rtol=0, atol=1e-12) or not np.allclose(
                    quaternion_matrix(geom['quaternion_body_wxyz']), quaternion_matrix(values(node, 'quat', '1 0 0 0')), rtol=0, atol=1e-12):
                raise ValueError('Current exact pad box mismatch')
    site = next(s for s in calibration['sites'] if s['name'] == 'gripper0_grip_site')
    node = xml.find('.//site[@name="grip_site"]')
    if site['body'] != 'gripper0_eef' or not np.array_equal(site['position_body_m'], values(node, 'pos', '0 0 0')) or not np.allclose(
            quaternion_matrix(site['quaternion_body_wxyz']), quaternion_matrix(values(node, 'quat', '1 0 0 0')), rtol=0, atol=1e-12):
        raise ValueError('Current grip-site local mount mismatch')
    paths = [xml_path, package/'models/grippers/panda_gripper.py', package/'models/robots/manipulators/panda_robot.py',
             Path('/home/junhongli/projects/LIBERO/libero/libero/envs/env_wrapper.py'), Path('/home/junhongli/projects/jev-libero/src/jev_libero/world.py')]
    paths += [xml_path.parent / x.attrib['file'] for x in xml.findall('asset/mesh') if x.attrib['name'] in ('hand', 'finger')]
    if 'return "PandaGripper"' not in paths[2].read_text() or 'robots=["Panda"]' not in paths[3].read_text() or 'gripper_types="default"' not in paths[3].read_text():
        raise ValueError('Inspected current Panda/default-gripper source differs')
    return {'current_source_sha256': {str(p): file_hash(p) for p in paths}, 'checked_static_bodies': checked,
            'current_body_joint_pad_checks_passed': True, 'historical_asset_byte_identity_proven': False,
            'compiled_mesh_vertices_reexported_or_compared_to_current_STL': False,
            'scope': 'conditional sealed convex calibration; present-time compatibility only',
            'numpy_version': np.__version__, 'scipy_version': scipy.__version__}


def prepare():
    for name, expected in SOURCES.items():
        if file_hash(RAW / name) != expected:
            raise ValueError('Sealed source mismatch: '+name)
    for name, expected in HELPERS.items():
        if file_hash(Path(__file__).with_name(name)) != expected:
            raise ValueError('Existing pure helper changed')
    records, errors = load_records(RAW / 'task2-box-point-boundary-run-01/episodes.jsonl')
    if errors:
        raise ValueError('Journal chain mismatch')
    calibration = json.loads((RAW / 'robot-geometry-observability-03/robot-calibration.json').read_text())
    sensor = json.loads((RAW / 'task2-box-support-run-02/sensor-representation.json').read_text())
    if sensor['box_xyxy'] != [208, 156, 228, 223] or sensor['crop_xyxy'] != [212, 169, 224, 210]:
        raise ValueError('Frozen support bounds changed')
    with np.load(RAW / 'interaction-observability-paired-01/close/0000.npz', allow_pickle=False) as frame:
        args = [frame[k] for k in ('depth_m', 'intrinsics', 'camera_to_world')]
        inner, full = [support(*args, bounds) for bounds in (sensor['crop_xyxy'], sensor['box_xyxy'])]
        if inner != [{k: row[k] for k in ('pixel_xy', 'depth_m', 'position_world_m')} for row in sensor['support_G']]:
            raise ValueError('Original inner G arithmetic/order differs')
    index = {tuple(row['pixel_xy']): i for i, row in enumerate(full)}
    indices = [index[tuple(row['pixel_xy'])] for row in inner]
    if [full[i] for i in indices] != inner:
        raise ValueError('Inner G not exact subset of full support')
    packets, selections = {}, {}
    for label, step in (('sample0', 21), ('sample1', 22)):
        selected = [r for r in records if r['kind'] == 'control_started' and r['data']['step'] == step and r['data']['control'] == 0]
        if len(selected) != 1:
            raise ValueError('Selected own packet missing/ambiguous')
        row = selected[0]
        packets[label] = own_packet(row['data']['previous_returned_own_observations'])
        selections[label] = {'step': step, 'record_id': row['record_id'], 'field': 'previous_returned_own_observations',
                             'read_boundary_time_s': row['data']['state_before'][0],
                             'initial_support_age_at_read_boundary_s': row['data']['state_before'][0]-.5,
                             'exact_observation_sample_time_s': None}
    request = {'calibration': subtree(calibration), 'own_packets': packets, 'full_support': full, 'inner_indices': indices}
    receipt = {'source_sha256': SOURCES, 'helper_sha256': HELPERS, 'selections': selections,
               'exact_inner_G_equality': True, 'inner_points': len(inner), 'full_points': len(full),
               'compatibility': compatibility(calibration), 'own_geometry_or_proximity_features_computed': False}
    return request, receipt, records


def run(output, review):
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('Clean reviewed freeze required')
    if identity['commit'] not in Path(review).read_text() or 'PASS' not in Path(review).read_text():
        raise ValueError('Prospective PASS naming exact freeze required')
    request, receipt, records = prepare()
    output = Path(output)
    output.mkdir(exist_ok=False)
    write(output / 'request.json', request)
    write(output / 'admission.json', receipt)
    write(output / 'manifest.json', {'code': identity, 'review_sha256': file_hash(review),
                                   'protocol_sha256': file_hash(PROTOCOL), 'request_sha256': file_hash(output/'request.json')})
    (output / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (output / 'review.txt').write_bytes(Path(review).read_bytes())
    subprocess.run([sys.executable, '-m', __package__+'.task2_observed_surface_sweep', '--worker',
                    '--input', str(output/'request.json'), '--output', str(output/'features')], check=True)
    write(output / 'feature-seal.json', {str(p.relative_to(output)): file_hash(p) for p in sorted((output/'features').iterdir())})
    # Evaluation occurs after the complete numerical artifact seal; no worker feedback.
    initial = next(r['data'] for r in records if r['kind'] == 'initial_frame_gate')
    robot = set(initial['groups_evaluator_only']['robot'])
    evaluator = {}
    for step in (21, 22):
        selected = next(r['data']['selected'] for r in records if r['kind'] == 'decision' and r['data']['step'] == step)
        contacts = [{'stage': r['kind'], 'record_id': r['record_id'],
                     **{k: r['data'][k] for k in ('step', 'control', 'index', 'time_s')}, 'contact': c}
                    for r in records if r['kind'] in ('native_before', 'native_after') and r['data']['step'] == step
                    for c in r['data']['contacts'] if robot.intersection(c['geom_ids'])]
        evaluator[str(step)] = {'executed': selected, 'raw_robot_contacts': contacts,
                                'unexecuted_outcomes': {token: None for token in MOVES if token != selected}}
    write(output / 'evaluator-after-seal.json', evaluator)
    print(json.dumps({'status': 'complete', 'samples': 2, 'candidates_per_sample': 7,
                      'proxies': 5, 'inner_points': receipt['inner_points'], 'full_points': receipt['full_points']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--input')
    parser.add_argument('--output', required=True)
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.worker:
        compute(json.loads(Path(args.input).read_text()), args.output)
    elif args.preflight:
        _, receipt, _ = prepare()
        write(args.output, {'code': code_identity(), **receipt})
        print(json.dumps({'status': 'pass', 'inner_points': receipt['inner_points'], 'full_points': receipt['full_points'], 'own_geometry_or_proximity_features_computed': False}))
    else:
        run(args.output, args.review)

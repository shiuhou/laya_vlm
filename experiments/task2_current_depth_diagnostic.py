"""Stored full-depth versus existing silhouette subset, with fixed fresh goals."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy
from scipy.spatial import ConvexHull

HELPER_ROOT = Path('/home/junhongli/projects/laya-render-measurement-semantics')
HELPERS = {
    'embodied_runtime/experiments/sensor_gripper_proximity.py': '4f52b9e168cdb802daca4eea1bd26115750957430e1e5e1fe89ec47fba233db6',
    'embodied_runtime/experiments/robot_only_geometry.py': 'c8563e80070a7081a43c9d92d1f6f86446732c77964c2c55665ab76bd32d147c',
    'embodied_runtime/decision_interface.py': '92c87afe4b28e90bc50ec25293bb09ca6a93c8d52b598ae465e36d4d54f4c917',
    'embodied_runtime/runtime_core.py': '04be07b6be4d287d9b93e6376fb837cfa1a914eb0f81d9d2cf90b7c7f16763c7',
}
RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
ORDER = ('present-postevent', 'away-postevent')
MOVES = {'MV_FWD': [.01, 0., 0.], 'MV_BACK': [-.01, 0., 0.],
         'MV_LEFT': [0., .01, 0.], 'MV_RIGHT': [0., -.01, 0.],
         'MV_UP': [0., 0., .01], 'MV_DOWN': [0., 0., -.01], 'STOP': [0., 0., 0.]}
GEOMS = ['gripper0_hand_collision', 'gripper0_finger1_collision', 'gripper0_finger1_pad_collision',
         'gripper0_finger2_collision', 'gripper0_finger2_pad_collision']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


for name, digest in HELPERS.items():
    require(sha(HELPER_ROOT / name) == digest, 'changed pure helper ' + name)
sys.path.insert(0, str(HELPER_ROOT))
from embodied_runtime.decision_interface import (CandidateEffectBundle, CanonicalDecisionInput,  # noqa: E402
    CanonicalDecisionState, geometric_effects)
from embodied_runtime.runtime_core import Candidate  # noqa: E402
from embodied_runtime.experiments.sensor_gripper_proximity import (  # noqa: E402
    NUMERIC_TOLERANCE, projected_proxy_mask, proxy_distance)


def containment(points, vertices):
    """The unchanged proxy_distance halfspace test, without unused distances."""
    inside = np.ones(len(points), bool)
    for equation in ConvexHull(vertices).equations:
        inside &= np.einsum('...i,...i->...', points, equation[:3]) + equation[3] <= NUMERIC_TOLERANCE
    return inside


def restore_view(value):
    return CanonicalDecisionInput(CanonicalDecisionState.from_dict(value['state']),
        tuple(Candidate(**item) for item in value['candidates']), CandidateEffectBundle(**value['effects']),
        tuple(value['history']), value['diagnostic_only'])


def selected(view, excluded):
    candidates = tuple(c for c in view.candidates if c.token not in excluded)
    return replace(view, candidates=candidates, effects=geometric_effects(view.state, candidates)).rule_token()


def self_test():
    vertices = np.array([[x, y, z] for x in (-1., 1.) for y in (-1., 1.) for z in (-1., 1.)])
    points = np.array([[0., 0., 0.], [1., 0., 0.], [1.1, 0., 0.], [1., 1., 1.], [-2., 1., 1.]])
    for shift in (np.zeros(3), np.array([.04, -.12, .33])):
        actual = containment(points + shift, vertices + shift)
        require(np.array_equal(actual, proxy_distance(points + shift, vertices + shift)[2]), 'halfspace parity')
        require(actual.tolist() == [True, True, False, True, False], 'closed-solid membership')
    print('Containment parity: 10 synthetic point/solid cases passed.')


def compute(decisions_path, decisions_sha, output):
    require(sha(decisions_path) == decisions_sha, 'sealed decision source changed')
    output = Path(output)
    output.mkdir(exist_ok=False)
    packet = read(decisions_path)
    rows = [row for row in packet['records'] if row['arm'] == 'fresh']
    require([row['case_id'] for row in rows] == list(ORDER), 'fixed two fresh records')
    preflight_path = RAW / 'task2-closed-empty-slow-point-preflight-01.json'
    require(sha(preflight_path) == '35ff93678d77b147bf1f5e0f4767de9ea2e62d915e2f2db3526eeeece2ce1903', 'slow input binding')
    preflight = read(preflight_path)
    own_rows, summaries = [], []
    request = {'decision_source': str(decisions_path), 'decision_sha256': decisions_sha,
        'preflight_sha256': sha(preflight_path), 'helper_sha256': HELPERS,
        'script_sha256': sha(__file__), 'protocol_sha256': sha(Path(__file__).resolve().parents[1] / 'docs/research/task2_current_depth_diagnostic.md'),
        'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1], text=True).strip(),
        'conditions': list(ORDER), 'candidate_order': list(MOVES), 'depth_range_m': [.01, 5.],
        'versions': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__},
        'tolerance': NUMERIC_TOLERANCE, 'mask': 'unchanged five collision-proxy projected silhouette union',
        'goal': 'fixed current slow POINT per frame', 'new_model_physics_render_FK_calls': 0}
    write(output / 'request.json', request)
    for index, row in enumerate(rows):
        name = row['case_id']
        source = preflight['source']['images'][index]
        require(row['source'] == source and row['generation_mode'] == 'slow'
                and row['syntax_status'] == 'admitted_rgb_point' and row['nonadmission'] is None, 'bound admitted fresh goal')
        view = restore_view(row['canonical'])
        require([c.token for c in view.candidates] == list(MOVES) and view.rule_token() == row['unguarded_token'], 'unchanged original nominal rule')
        original_excluded = {token for token, details in row['all_seven_candidates'].items() if details['excluded']}
        require(selected(view, original_excluded) == row['guarded_token'], 'reproduce saved stale-guard choice')
        vertices = row['selection']['current_proxy_vertices_world_m']
        require(list(vertices) == GEOMS, 'five separate placed own proxies')
        own_rows.append(row['own'])
        path = Path(preflight['source']['source_root']) / source['directory'] / source['artifact']
        require(sha(path) == source['artifact_sha256'], 'same-frame depth source')
        with np.load(path, allow_pickle=False) as archive:
            depth, k, transform = (archive[key] for key in ('depth_m', 'intrinsics', 'camera_to_world'))
        valid = np.isfinite(depth) & (depth >= .01) & (depth <= 5.)
        ys, xs = np.nonzero(valid)
        z = depth[ys, xs].astype(np.float64)
        camera = np.column_stack(((xs + .5 - k[0, 2]) * z / k[0, 0],
                                  (ys + .5 - k[1, 2]) * z / k[1, 1], z))
        points = camera @ transform[:3, :3].T + transform[:3, 3]
        masks = np.stack([projected_proxy_mask(vertices[geom], k, transform, depth.shape)[0] for geom in GEOMS], axis=-1)
        subset = ~masks.any(axis=-1)[ys, xs]
        inside = np.stack([np.column_stack([containment(points, np.asarray(vertices[geom]) + delta) for geom in GEOMS])
                           for delta in map(np.asarray, MOVES.values())])
        np.savez_compressed(output / (name + '-arrays.npz'), pixel_xy=np.column_stack((xs, ys)), depth_m=z,
            points_world_m=points, endpoint_inside=inside, projected_proxy_masks=masks, outside_silhouette=subset)
        current_union = inside[-1].any(axis=-1)
        groups = []
        for label, keep in (('all_valid_depth', np.ones(len(points), bool)), ('outside_partial_gripper_silhouette', subset)):
            candidates = {}
            for ordinal, (token, delta) in enumerate(MOVES.items()):
                members = inside[ordinal] & keep[:, None]
                union = members.any(axis=-1)
                indices = np.flatnonzero(union)
                candidates[token] = {'delta_m': delta, 'contained_point_count': int(union.sum()),
                    'excluded': token != 'STOP' and bool(union.any()),
                    'witness_pixel_xy': np.column_stack((xs[indices], ys[indices])).tolist(),
                    'per_proxy_count': {geom: int(members[:, i].sum()) for i, geom in enumerate(GEOMS)},
                    'already_current_contained_count': int((union & current_union).sum()),
                    'new_endpoint_contained_count': int((union & ~current_union).sum()),
                    'nominal_tcp_to_P_m': row['all_seven_candidates'][token]['nominal_tcp_to_P_m']}
            excluded = {token for token, details in candidates.items() if details['excluded']}
            groups.append({'representation': label, 'support_count': int(keep.sum()),
                'support_status': 'observed_unknown_ownership' if keep.any() else 'unknown_empty_support',
                'selected_token': selected(view, excluded) if keep.any() else None,
                'all_seven_candidates': candidates})
        summaries.append({'case_id': name, 'source': source, 'point_world_m': row['point_world_m'],
            'own': row['own'], 'current_proxy_vertices_world_m': vertices,
            'unguarded_token': row['unguarded_token'], 'stale_guard_token': row['guarded_token'],
            'valid_depth_count': int(valid.sum()), 'excluded_silhouette_count': int((~subset).sum()), 'groups': groups})
    require(own_rows[0] == own_rows[1], 'paired returned own state differs')
    result = {'status': 'completed', 'conditions': summaries, 'fresh_goals_fixed': True, 'nominal_choices': 4,
        'new_model_physics_render_FK_calls': 0, 'executed_actions': 0,
        'ownership': 'unknown for both representations', 'safety_or_clearance_established': False}
    write(output / 'features.json', result)
    write(output / 'feature-seal.json', {path.name: sha(path) for path in sorted(output.iterdir())})
    print(json.dumps({'status': 'completed', 'feature_seal_sha256': sha(output / 'feature-seal.json'),
        'conditions': [{**{key: row[key] for key in ('case_id', 'unguarded_token', 'stale_guard_token')},
            'groups': [{key: group[key] for key in ('representation', 'support_count', 'selected_token')} for group in row['groups']]}
            for row in summaries]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--decisions-sha256')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        require(args.decisions is not None and args.decisions_sha256 and args.output is not None, 'three source/output arguments required')
        compute(args.decisions, args.decisions_sha256, args.output)

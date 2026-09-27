"""Inspect completed paired approach evidence at three fixed boundaries only."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from PIL import Image

from ..runtime_core import _sha256_json
from .records import file_hash
from .proprio_frame_consistency import static_mount
from .task2_point_jaw_geometry import returned_packet_relation

RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
ROOT = Path(__file__).resolve().parents[2]
SOURCE_HASHES = {
    'interaction-observability-paired-01/close/0000.npz': '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969',
    'robot-geometry-observability-03/robot-calibration.json': '11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa',
    'task2-point-region-control-run-01/whole/sensor-result.json': '87fb2c2b9587ae1cd08f85d4bf331288c20b4b50b65aa6f0132b78294eb3cef5',
    'task2-point-region-control-run-01/neck/sensor-result.json': 'fd6edea327618a8bb86a52dafe48fe2d857a2e71fa7677bdcadb89d65657fd0d',
}
HELPERS = {'task2_point_jaw_geometry.py': '71a1d2c0bbf444f6f418ca2fec3a873e697da692def18cbb8cf4b9df0777bbd2',
           'proprio_frame_consistency.py': '3661e810a9ffb90c00b0c83a8db79559b940bf421fcf3cb2720e8caa43021e20'}


def read(path):
    return json.loads(Path(path).read_text())


def journal(directory, expected, require_initial=True):
    if file_hash(directory/'episodes.jsonl') != expected:
        raise ValueError('Completed journal hash differs')
    kept, signatures, previous, kind = defaultdict(list), {}, None, None
    for index, line in enumerate((directory/'episodes.jsonl').open('rb')):
        row = json.loads(line)
        if (not line.endswith(b'\n') or row['seq'] != index or row['previous_record_id'] != previous
                or row['record_id'] != _sha256_json({key: value for key, value in row.items() if key != 'record_id'})):
            raise ValueError('Journal chain invalid')
        previous, kind, data = row['record_id'], row['kind'], row['data']
        if kind in ('control_started', 'control_completed', 'native_before', 'native_after'):
            key = (kind, data['step'], data.get('control'), data.get('index'))
            if key in signatures:
                raise ValueError('Duplicate physical evidence key')
            signatures[key] = _sha256_json(data)
        if kind in ('initial_frame_gate', 'vision_capture', 'decision', 'action_completed', 'endpoint', 'termination', 'failure'):
            kept[kind].append(row)
    if (kept['failure'] or kind != 'termination' or len(kept['termination']) != 1
            or (require_initial and len(kept['initial_frame_gate']) != 1)):
        raise ValueError('Normally closed collection required; preserve partial evidence separately')
    kept['signatures'] = signatures
    return kept


def first_comparable_divergence(decisions):
    for first, second in zip(*decisions):
        if first['data']['step'] != second['data']['step']:
            raise ValueError('Comparable decision indices differ')
        if first['data']['selected'] != second['data']['selected']:
            return first['data']['step']
    return None


def exact_capture(captures, sequence, sim_time):
    rows = [row for row in captures if row['data']['capture_seq'] == sequence]
    if len(rows) != 1 or rows[0]['data']['capture_sim_time'] != sim_time:
        raise ValueError('Exact recorded capture sequence/time required')
    return rows[0]


def boundary(records, step=None, terminal=False):
    initial = records['initial_frame_gate'][0]
    endpoints = records['endpoint']
    if terminal and endpoints:
        own_row = endpoints[-1]
    elif not terminal and step:
        selected = [row for row in endpoints if row['data']['step'] == step-1]
        if len(selected) != 1:
            raise ValueError('Unique preceding completed endpoint required')
        own_row = selected[0]
    else:
        own_row = initial
    if own_row is initial:
        time = initial['data']['fresh_capture_sim_time_s']
        capture = exact_capture(records['vision_capture'], 1, time)
        own, field = own_row['data']['initial_own_observations'], 'initial_own_observations'
    else:
        actions = [row for row in records['action_completed'] if row['data']['step'] == own_row['data']['step']]
        if len(actions) != 1:
            raise ValueError('Completed endpoint action missing')
        time = actions[0]['data']['result']['execution_after']['sim_time']
        capture = exact_capture(records['vision_capture'], own_row['data']['capture_seq'], time)
        own, field = own_row['data']['own_observations'], 'own_observations'
    if step is not None and not terminal:
        decision = next(row for row in records['decision'] if row['data']['step'] == step)
        if decision['data']['canonical']['state']['meta']['asof_sim_time'] != time:
            raise ValueError('Pre-decision capture time differs')
    return {'own_record_id': own_row['record_id'], 'own_record_field': field, 'own_packet': own,
            'capture': capture, 'boundary_time_s': time, 'exact_own_sample_time_s': None}


def frame_arrays(directory, capture):
    path = directory/capture['data']['artifact']
    if file_hash(path) != capture['data']['artifact_sha256']:
        raise ValueError('Actual stored frame hash differs')
    with np.load(path, allow_pickle=False) as frame:
        return {key: frame[key].copy() for key in ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')}


def interpret(pair, hashes, output):
    pair, output = Path(pair), Path(output)
    for name, digest in SOURCE_HASHES.items():
        if file_hash(RAW/name) != digest:
            raise ValueError('Fixed source changed: '+name)
    for name, digest in HELPERS.items():
        if file_hash(Path(__file__).parent/name) != digest:
            raise ValueError('Existing own-pad helper changed')
    batch = read(pair/'request.json')
    batch_records = journal(pair, hashes['pair'], require_initial=False)
    if batch_records['termination'][0]['data']['reason'] != 'both_fixed_conditions_and_replays_complete':
        raise ValueError('Wait for both conditions and replays to finish')
    conditions = ('whole', 'neck')
    runs = [journal(pair/name, hashes[name]) for name in conditions]
    replay_hashes = {}
    for name in conditions:
        replay_path = pair/(name+'-replay')/'result.json'
        if read(replay_path)['status'] != 'passed':
            raise ValueError('Both archived verification replays must pass')
        replay_hashes[name] = file_hash(replay_path)
    divergence = first_comparable_divergence([run['decision'] for run in runs])
    prefix_steps = divergence if divergence is not None else min(len(run['action_completed']) for run in runs)
    signatures = [{key: value for key, value in run['signatures'].items() if key[1] < prefix_steps} for run in runs]
    prefix_equal = signatures[0] == signatures[1]
    own_initial_equal = runs[0]['initial_frame_gate'][0]['data']['initial_own_observations'] == runs[1]['initial_frame_gate'][0]['data']['initial_own_observations']
    prefix_captures_equal = True
    for index in range(prefix_steps+1):
        frames = [frame_arrays(pair/name, run['vision_capture'][index]) for name, run in zip(conditions, runs)]
        prefix_captures_equal &= all(frames[0][key].shape == frames[1][key].shape and frames[0][key].dtype == frames[1][key].dtype
                                     and frames[0][key].tobytes() == frames[1][key].tobytes() for key in frames[0])
    calibration = read(RAW/'robot-geometry-observability-03/robot-calibration.json')
    _, mount, _ = static_mount(calibration)
    output.mkdir(parents=True, exist_ok=False)
    panels, reports = [], []
    exclusions = []
    for name, run in zip(conditions, runs):
        sensor = read(RAW/'task2-point-region-control-run-01'/name/'sensor-result.json')
        point = sensor['point']['position_world_m']
        if run['initial_frame_gate'][0]['data']['cached_point']['position_world_m'] != point:
            raise ValueError('Collection changed the fixed native POINT')
        snapshots, panel_row = [], []
        choices = [('initial', boundary(run, step=0)),
                   ('pre_first_divergence', None if divergence is None else boundary(run, step=divergence)),
                   ('terminal', boundary(run, terminal=True))]
        for label, selected in choices:
            if selected is None:
                panel_row.append(None)
                continue
            frame = frame_arrays(pair/name, selected['capture'])
            prefix = name+'_'+label
            Image.fromarray(frame['rgb']).save(output/(prefix+'_rgb.png'))
            if not np.array_equal(np.asarray(Image.open(output/(prefix+'_rgb.png'))), frame['rgb']):
                raise ValueError('Unmarked source RGB changed')
            relation = returned_packet_relation(point, selected['own_packet'], mount)
            snapshots.append({'label': label, **selected, 'point_world_m': point, 'existing_point_jaw_relation': relation,
                'unmarked_rgb_artifact': prefix+'_rgb.png',
                'rgbd_source_artifact': str(pair/name/selected['capture']['data']['artifact'])})
            panel_row.append((frame['rgb'], selected['capture']['data'], label))
        selected_decision = None if divergence is None else next(row for row in run['decision'] if row['data']['step'] == divergence)
        if selected_decision is not None:
            candidates = selected_decision['data']['experiment_selection']['all_seven_candidates']
            exclusions.append({token: {key: value for key, value in details.items() if key != 'nominal_tcp_to_P_m'} for token, details in candidates.items()})
        reports.append({'condition': name, 'journal_sha256': hashes[name], 'replay_sha256': replay_hashes[name],
            'fixed_point_source': sensor['point'], 'termination': run['termination'][0],
            'action_tokens': [row['data']['token'] for row in run['action_completed']],
            'decisions': [row['data'] for row in run['decision']], 'first_cross_arm_divergence_decision': selected_decision,
            'snapshots': snapshots})
        panels.append(panel_row)
    result = {'pair': str(pair), 'journal_sha256': hashes, 'request_sha256': file_hash(pair/'request.json'),
        'batch_request': batch, 'source_sha256': SOURCE_HASHES, 'existing_helper_sha256': HELPERS,
        'first_comparable_selected_token_divergence_step': divergence, 'comparable_physical_prefix_actions': prefix_steps,
        'initial_own_packets_equal': own_initial_equal, 'physical_prefix_control_native_data_equal': prefix_equal,
        'physical_prefix_all_capture_arrays_equal': bool(prefix_captures_equal),
        'first_divergence_exclusions_equal': None if not exclusions else exclusions[0] == exclusions[1],
        'conditions': reports, 'new_model_physics_render_calls': 0,
        'visual_inspection': 'pending independent opening of actual images',
        'limits': ['STOP executes no hold and does not establish a stable pose',
                   'cached point-to-pad-prism algebra is not current visual identity, extent, fit or a grasp',
                   'endpoint guard is not swept clearance; contact evidence remains a separate full native audit',
                   'if the common physical-prefix checks fail, the token difference is not an isolated goal-only causal comparison']}
    with (output/'interpretation.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(12, 8.6))
    for row, name in enumerate(conditions):
        for column, item in enumerate(panels[row]):
            ax = axes[row, column]
            if item is None:
                ax.text(.5, .5, 'No comparable token divergence', ha='center', va='center', transform=ax.transAxes)
            else:
                rgb, capture, label = item
                ax.imshow(rgb)
                ax.set_title(f'{name}: {label}\ncapture {capture["capture_seq"]}, boundary {capture["capture_sim_time"]:.3f} s', fontsize=9)
            ax.set_axis_off()
    fig.suptitle('Actual stored RGB: fixed whole/neck approach pair\nInitial, before first differing token, terminal; no grasp or stable-pose claim', fontsize=12)
    fig.tight_layout()
    fig.savefig(output/'actual_rgb_boundaries.png', dpi=160)
    plt.close(fig)
    print(json.dumps({'first_divergence_step': divergence, 'prefix_actions': prefix_steps,
                      'physical_prefix_equal': prefix_equal, 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair', required=True)
    parser.add_argument('--output', required=True)
    for name in ('pair', 'whole', 'neck'):
        parser.add_argument('--'+name+'-sha256', required=True)
    args = parser.parse_args()
    interpret(args.pair, {name: getattr(args, name+'_sha256') for name in ('pair', 'whole', 'neck')}, args.output)

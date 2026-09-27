"""Post-event fixed-region RGB motion; run only with a reviewed new-source binding."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path

import numpy as np

from . import point_temporal_probe as lk
from . import task2_point_anchor_image_motion as motion
from .records import RunRecorder, code_identity, file_hash, jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'docs/research/task2_closed_empty_image_motion_assay.md'
OUTPUT = motion.prior.base.RAW/'task2-closed-empty-image-motion-run-01'
ROLES = ('present', 'away')
COUNT = 25
SEEDS = [[x, y] for y in range(169, 210) for x in range(212, 224)]
ENDPOINTS = {'postevent_preclose': 0, 'close1': 8, 'close2_prelift': 16, 'postlift': 24}
HELPERS = ((lk, '86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36'),
           (motion, '3f3822e3609ccb3a1647d53e1d5b8143f04deb8c07b759d9d14919576672e19b'),
           (motion.pixel_footprint, '5559a4ee170e50f45295252b3db2b08553b3ba0a2b886e8bbe6cdbc50b15da8c'))
OWN_KEYS = {'robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos', 'robot0_gripper_qvel'}
SENSOR_KEYS = set(motion.FRAME_KEYS) | {'capture_sim_time', 'own_observations',
    'render_preserves_state_and_caches', 'own_packet_status', 'capture_record_id', 'scene_boundary'}


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(jsonable(value), stream, indent=2, allow_nan=False)
        stream.write('\n')


def relative(root, name):
    path = Path(name)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('relative source path required')
    resolved = (Path(root)/path).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError('source path escapes its bound directory')
    return resolved


def selected_manifest(rows, condition):
    """Select by declared sensor stream only; never decode journal/evaluator data."""
    if any(set(row)-SENSOR_KEYS for row in rows):
        raise ValueError('unregistered sensor manifest fields')
    prefix = [('reset', -1, None, 'primary', 1)] + [('approach', i, 7, 'primary', i+2) for i in range(29)]
    if (len(rows) != 56 or [r['capture_id'] for r in rows] != list(range(56))
            or len({r['artifact'] for r in rows}) != 56
            or [tuple(r[k] for k in ('phase', 'after_step', 'control', 'source_capture_stream', 'source_capture_seq'))
                for r in rows[:30]] != prefix
            or any((r['condition'], r['anchor'], r['arm']) != (condition, 'neck', 'close') for r in rows)):
        raise ValueError('complete ordered 56-row source manifest required')
    scenes = [r for r in rows if r['source_capture_stream'] == 'scene']
    if ([r['phase'] for r in scenes] != ['scene_before', 'scene_after']
            or [r['source_capture_seq'] for r in scenes] != [1, 2]
            or [r['scene_boundary'] for r in scenes] != ['before', 'after']
            or scenes[0]['capture_read_sim_time_s'] != scenes[1]['capture_read_sim_time_s']):
        raise ValueError('one ordered same-time before/after scene boundary required')
    selected = [r for r in rows if r['source_capture_stream'] == 'auxiliary'
                or (r['source_capture_stream'] == 'scene' and r['phase'] == 'scene_after')]
    if len(selected) != COUNT:
        raise ValueError('all 25 post-event and control captures required')
    seen, previous = set(), None
    for i, row in enumerate(selected):
        if (row['condition'], row['anchor'], row['arm']) != (condition, 'neck', 'close'):
            raise ValueError('fixed neck closed-jaw source identity differs')
        if i == 0:
            expected = ('scene_after', 29, None, 'scene')
            own_source = {'journal': 'episodes.jsonl', 'kind': 'scene_boundary', 'boundary': 'after', 'step': 29}
            tcp_field = 'scene_boundary.own_observations.robot0_eef_pos'
        else:
            action, control = divmod(i-1, 8)
            expected = (('close_or_hold', 'additional_close', 'lift')[action], 29+action, control, 'auxiliary')
            own_source = {'journal': 'episodes.jsonl', 'kind': 'control_completed', 'step': 29+action, 'control': control}
            tcp_field = 'control_completed.returned_own_observations.robot0_eef_pos'
            if row['source_capture_seq'] != i:
                raise ValueError('all ordered auxiliary source sequences 1..24 required')
        if tuple(row[k] for k in ('phase', 'after_step', 'control', 'source_capture_stream')) != expected:
            raise ValueError('post-event suffix order or control boundary differs')
        if row['own_source'] != own_source:
            raise ValueError('exact saved own-packet boundary binding required')
        if row['artifact'] in seen:
            raise ValueError('unique capture artifacts required')
        seen.add(row['artifact'])
        time = row['capture_read_sim_time_s']
        if (not np.isfinite(time) or time < 0 or time != row['capture_sim_time']
                or (previous is not None and time <= previous)):
            raise ValueError('strictly increasing post-event read times required')
        previous = time
        if row['cached_geometry_sample_time_s'] is not None or row['exact_observation_sample_time_s'] is not None:
            raise ValueError('exact observation/cache sample times remain unknown')
        if row['render_preserves_state_and_caches'] is not True:
            raise ValueError('individual capture read-only guard required')
        own, tcp = row['own_observations'], row['own_tcp_world_m']
        if own is None:
            if any(row[k] is not None for k in ('own_tcp_world_m', 'tcp_read_sim_time_s', 'tcp_source_field')):
                raise ValueError('missing own observation must remain explicit')
        elif (set(own) != OWN_KEYS or tcp != own['robot0_eef_pos']
                or row['tcp_source_field'] != tcp_field
                or row['tcp_read_sim_time_s'] is None
                or not np.isfinite(row['tcp_read_sim_time_s'])
                or not 0 <= row['tcp_read_sim_time_s'] <= time):
            raise ValueError('saved TCP must match its own observation and read time')
    return deepcopy(selected)


def load_cell(directory, specification):
    directory = Path(directory)
    hashes = specification['sha256']
    if set(hashes) != {'sensor-captures.json', 'sensor-seal.json'}:
        raise ValueError('exact manifest and sensor-seal hashes required')
    for name, digest in hashes.items():
        if file_hash(directory/name) != digest:
            raise ValueError('bound source file changed: '+name)
    rows = json.loads((directory/'sensor-captures.json').read_text())
    seal = json.loads((directory/'sensor-seal.json').read_text())
    expected = {'sensor-captures.json': hashes['sensor-captures.json']}
    expected['own-controls.json'] = file_hash(directory/'own-controls.json')
    expected.update({r['artifact']: r['artifact_sha256'] for r in rows})
    if (seal['sha256'] != expected or seal['journal_parse_errors'] or seal['holding'] is not None
            or file_hash(directory/'episodes.jsonl') != seal['journal_sha256_linkage_only']):
        raise ValueError('complete bound sensor seal and journal linkage required')
    selected = selected_manifest(rows, specification['condition'])
    frames = []
    for row in selected:
        path = relative(directory, row['artifact'])
        if file_hash(path) != row['artifact_sha256']:
            raise ValueError('bound sensor archive changed')
        with np.load(path, allow_pickle=False) as archive:
            frame = {key: archive[key].copy() for key in ('rgb', 'intrinsics', 'camera_to_world')}
        if (frame['rgb'].dtype != np.uint8 or frame['rgb'].shape != (384, 384, 3)
                or frame['intrinsics'].shape != (3, 3) or frame['camera_to_world'].shape != (4, 4)
                or not np.isfinite(frame['intrinsics']).all() or not np.isfinite(frame['camera_to_world']).all()):
            raise ValueError('fixed native RGB and saved calibration schema required')
        frames.append(frame)
    return {'frames': frames, 'meta': selected,
            'source_journal_sha256_linkage_only': seal['journal_sha256_linkage_only']}


def load_inputs(binding_path):
    binding = json.loads(Path(binding_path).read_text())
    if (binding['schema'] != 'task2-closed-empty-image-motion-binding-v1'
            or binding['source_admitted'] is not True or set(binding['cells']) != set(ROLES)):
        raise ValueError('complete admitted two-cell binding required')
    for module, digest in HELPERS:
        if file_hash(module.__file__) != digest:
            raise ValueError('unchanged helper source required')
    source = Path(binding['source_root'])
    if not source.is_absolute() or file_hash(source/'episodes.jsonl') != binding['matrix_journal_sha256']:
        raise ValueError('complete source matrix journal linkage required')
    # These files can contain mechanical evidence: hash only, never parse them.
    for key in ('source_admission', 'source_review'):
        receipt = binding[key]
        if file_hash(receipt['path']) != receipt['sha256']:
            raise ValueError('independent source-admission linkage changed')
    directories = [relative(source, binding['cells'][role]['directory']) for role in ROLES]
    if any(binding['cells'][r]['condition'] != 'neck-'+r or binding['cells'][r]['directory'] != 'neck-'+r for r in ROLES):
        raise ValueError('exact neck-present and neck-away source cells required')
    packets = {role: load_cell(directory, binding['cells'][role]) for role, directory in zip(ROLES, directories)}
    return packets, {'binding_sha256': file_hash(binding_path), 'binding': binding,
        'captures': {role: packet['meta'] for role, packet in packets.items()},
        'reference': 0, 'seed_count': 492, 'frames_per_cell': COUNT, 'tracks': 984, 'rows': 24600,
        'measured_scene_depth_read': False, 'evaluator_read': False, 'through_event_tracking': False}


def iter_tracks(packet, cv2):
    frames, metadata = packet['frames'], packet['meta']
    if len(frames) != COUNT or len(metadata) != COUNT or cv2.__version__ != lk.CV2_VERSION:
        raise ValueError('fixed complete suffix and OpenCV version required')
    projections = [motion.project_own_tcp(row['own_tcp_world_m'], frame)
                   for row, frame in zip(metadata, frames, strict=True)]
    rgbs = np.stack([frame['rgb'] for frame in frames])
    for seed_id, seed in enumerate(SEEDS):
        tracked = lk.track_lk(rgbs, seed, cv2)
        if (len(tracked) != COUNT or [r['frame'] for r in tracked] != list(range(COUNT))
                or any(set(r) != set(motion.NATIVE_KEYS) for r in tracked)
                or tracked[0]['status'] != 'seeded' or tracked[0]['point_pixel_index_xy'] != seed):
            raise ValueError('complete native rows and fresh numerical seed required')
        rows = []
        for i, (native, saved) in enumerate(zip(tracked, metadata, strict=True)):
            meta = {key: deepcopy(saved[key]) for key in motion.FRAME_KEYS if key != 'capture_id'}
            # Invalid own XYZ remains a B-only null with raw evidence in the bound manifest.
            if projections[i]['status'] in ('missing_own_tcp', 'nonfinite_or_invalid_own_tcp'):
                meta['own_tcp_world_m'] = None
            rows.append({**native, **meta, 'capture_id': i, 'seed_id': seed_id, 'seed_pixel_index_xy': seed})
        yield motion.enrich_track(rows, projections, 0)


def summarize(tracks):
    summaries = motion.summarize(tracks, COUNT, 0)
    for i, row in enumerate(summaries):
        row.update(native_failure_count=sum(t[i]['status'] == 'native_failure' for t in tracks),
                   unknown_after_failure_count=sum(t[i]['status'] == 'unknown_after_native_failure' for t in tracks))
    return summaries


def preflight(binding_path, output):
    import cv2
    identity, runtime = code_identity(), motion.prior.environment(cv2)
    if identity['dirty_status']:
        raise ValueError('clean committed extraction freeze required')
    _, admission = load_inputs(binding_path)
    write_json(output, {'status': 'pass', 'code': identity, 'environment': runtime,
        'protocol_sha256': file_hash(PROTOCOL), 'admission': admission,
        'LK_projection_displacement_computed': False, 'model_physics_render_calls': 0})


def run(binding_path, preflight_path, review_path, output):
    import cv2
    identity, runtime = code_identity(), motion.prior.environment(cv2)
    preflight = json.loads(Path(preflight_path).read_text())
    review = json.loads(Path(review_path).read_text())
    if (identity['dirty_status'] or preflight['code'] != identity or preflight['status'] != 'pass'
            or preflight['environment'] != runtime or preflight['protocol_sha256'] != file_hash(PROTOCOL)
            or preflight['LK_projection_displacement_computed'] is not False
            or preflight['model_physics_render_calls'] != 0
            or review.get('status') != 'pass' or review.get('freeze_commit') != identity['commit']
            or review.get('binding_sha256') != file_hash(binding_path)
            or review.get('preflight_sha256') != file_hash(preflight_path)
            or review.get('protocol_sha256') != file_hash(PROTOCOL) or review.get('authorized_batches') != 1
            or Path(output).resolve() != OUTPUT or OUTPUT.exists()):
        raise ValueError('one clean reviewed admitted-source batch at the fixed new output required')
    packets, admission = load_inputs(binding_path)
    if admission != preflight['admission']:
        raise ValueError('reviewed source admission changed')
    recorder = RunRecorder(output, {'protocol_sha256': file_hash(PROTOCOL), 'reference': 0,
        'seeds': SEEDS, 'captures_per_cell': COUNT, 'lk_settings': lk.LK_SETTINGS, 'endpoints': ENDPOINTS},
        {'run_id': OUTPUT.name, 'code': identity, 'runtime': runtime, 'binding_sha256': file_hash(binding_path),
         'review_sha256': file_hash(review_path), 'preflight_sha256': file_hash(preflight_path)})
    output, completed, written = Path(output), 0, 0
    try:
        for path, name in ((PROTOCOL, 'protocol.md'), (binding_path, 'binding.json'),
                           (preflight_path, 'preflight.json'), (review_path, 'review.json')):
            (output/name).write_bytes(Path(path).read_bytes())
        write_json(output/'admission.json', admission)
        summaries = {}
        for role in ROLES:
            tracks = []
            with (output/f'{role}-tracks.jsonl').open('x') as stream:
                for track in iter_tracks(packets[role], cv2):
                    for row in track:
                        stream.write(json.dumps(jsonable(row), allow_nan=False)+'\n')
                        written += 1
                    stream.flush()
                    os.fsync(stream.fileno())
                    tracks.append(track)
                    completed += 1
            summaries[role] = summarize(tracks)
            recorder.record('cell_complete', {'role': role, 'tracks': len(tracks), 'rows': sum(map(len, tracks))})
        if (completed, written) != (984, 24600):
            raise ValueError('complete two-cell population required')
        write_json(output/'sensor-summary.json', {'cells': summaries, 'reference_capture_id': 0,
            'endpoints': ENDPOINTS, 'holding': None, 'identity_verified': None, 'mechanical_labels_joined': False})
        write_json(output/'sensor-seal.json', {'sha256': {p.name: file_hash(p) for p in sorted(output.iterdir())
            if p.is_file() and p.name != 'episodes.jsonl'}, 'complete': True, 'tracks': completed, 'rows': written,
            'measured_scene_depth_read': False, 'evaluator_read': False})
        recorder.record('termination', {'reason': 'all_postevent_image_motion_rows_sealed',
            'tracks': completed, 'rows': written, 'sensor_seal_sha256': file_hash(output/'sensor-seal.json'), 'retries': 0})
    except BaseException as exc:
        recorder.record('failure', {'reason': repr(exc), 'completed_tracks': completed, 'written_rows': written, 'retries': 0})
        raise
    finally:
        recorder.close()
        write_json(output/'artifacts.json', {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'run'])
    parser.add_argument('--binding', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight')
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.mode == 'preflight':
        preflight(args.binding, args.output)
    elif args.preflight and args.review:
        run(args.binding, args.preflight, args.review, args.output)
    else:
        parser.error('run requires --preflight and --review')

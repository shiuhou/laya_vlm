"""Stored-only four-cell adapter; no CLI, evaluator, world, render or model call.

This prospective library is not an extraction authorization. Actual source
hashes and a reviewed execution freeze must be supplied after matrix completion.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from . import task2_box_temporal_probe as base
from . import task2_short_lift_transfer as prior
from . import task2_track_coordinate_association as association
from .records import file_hash

CONDITIONS = ('whole-close', 'whole-open_hold', 'neck-close', 'neck-open_hold')
APPROACH_COUNTS = {'whole': 30, 'neck': 29}
SEED_COUNT = 492
CROSS_ANCHOR_PREFIX = 6
FRAME_KEYS = ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')
OWN_KEYS = {'robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos', 'robot0_gripper_qvel'}
ROW_KEYS = {'condition', 'anchor', 'arm', 'phase', 'after_step', 'control',
            'source_capture_stream', 'source_capture_seq', 'capture_sim_time',
            'capture_read_sim_time_s', 'cached_geometry_sample_time_s',
            'exact_observation_sample_time_s', 'tcp_read_sim_time_s', 'own_tcp_world_m',
            'tcp_source_field', 'own_observations', 'artifact', 'artifact_sha256',
            'render_preserves_state_and_caches', 'own_source', 'own_packet_status',
            'capture_record_id', 'capture_id'}
HELPER_HASHES = ((base.lk, base.LK_SHA), (base, association.BASE_SHA),
                 (association, prior.ASSOCIATION_SHA),
                 (prior, '71973b2f6f6e1f6d1500881250b2ac7740ee796cbd38ac38f191f449c45c9e63'))


def expected_schedule(condition):
    if condition not in CONDITIONS:
        raise ValueError('exact four registered cells required')
    anchor, _ = condition.split('-', 1)
    count = APPROACH_COUNTS[anchor]
    return ([('reset', -1, None, 'primary', 1)]
            + [('approach', i, 7, 'primary', i+2) for i in range(count)]
            + [('close_or_hold' if j == 0 else 'lift', count+j, c, 'auxiliary', j*8+c+1)
               for j in range(2) for c in range(8)])


def validated_manifest(rows, condition):
    """Schema/source checks only: no image, depth, tracker or evaluator access."""
    schedule = expected_schedule(condition)
    anchor, arm = condition.split('-', 1)
    if len(rows) != len(schedule):
        raise ValueError('complete fixed capture schedule required; no partial extraction')
    artifacts, previous_time = set(), None
    for i, (row, expected) in enumerate(zip(rows, schedule, strict=True)):
        if set(row)-ROW_KEYS:
            raise ValueError('unregistered fields in sensor-only manifest')
        if ((row['condition'], row['anchor'], row['arm'], row['capture_id']) != (condition, anchor, arm, i)
                or tuple(row[k] for k in ('phase', 'after_step', 'control', 'source_capture_stream', 'source_capture_seq')) != expected):
            raise ValueError('capture identity, order or phase/control schedule differs')
        artifact = Path(row['artifact'])
        if artifact.is_absolute() or '..' in artifact.parts or row['artifact'] in artifacts:
            raise ValueError('unique relative source artifact paths required')
        artifacts.add(row['artifact'])
        time = row['capture_sim_time']
        if (not np.isfinite(time) or time < 0 or row['capture_read_sim_time_s'] != time
                or (previous_time is not None and time <= previous_time)):
            raise ValueError('strictly chronological saved read times required')
        previous_time = time
        if row['cached_geometry_sample_time_s'] is not None or row['exact_observation_sample_time_s'] is not None:
            raise ValueError('this source has no exact cache/observation sample time')
        if row['render_preserves_state_and_caches'] is not True:
            raise ValueError('source read-only capture contract required')
        own, tcp = row['own_observations'], row['own_tcp_world_m']
        if own is None:
            if any(row[k] is not None for k in ('own_tcp_world_m', 'tcp_read_sim_time_s', 'tcp_source_field')):
                raise ValueError('missing own observation must stay unknown')
        else:
            if set(own) != OWN_KEYS or tcp != own['robot0_eef_pos']:
                raise ValueError('own TCP must equal the explicitly saved own packet')
            if np.asarray(tcp).shape != (3,) or not np.isfinite(tcp).all():
                raise ValueError('saved own TCP must be finite XYZ')
            read_time = row['tcp_read_sim_time_s']
            if read_time is None or not np.isfinite(read_time) or read_time < 0 or read_time > time:
                raise ValueError('saved own read time required')
        source = row['own_source']
        kind = 'initial_frame_gate' if i == 0 else 'endpoint' if i <= APPROACH_COUNTS[anchor] else 'control_completed'
        field = kind+'.'+('initial_own_observations' if i == 0 else
                         'returned_own_observations' if kind == 'control_completed' else 'own_observations')+'.robot0_eef_pos'
        if (set(source)-{'journal', 'kind', 'step', 'control'} or source['journal'] != 'episodes.jsonl'
                or source['kind'] != kind or source['step'] != (None if i == 0 else row['after_step'])
                or (kind == 'control_completed' and source['control'] != row['control'])
                or (own is not None and row['tcp_source_field'] != field)):
            raise ValueError('unambiguous saved own source linkage required')
    return APPROACH_COUNTS[anchor]


def load_cell(directory, condition, hashes):
    """Read only the pinned sensor manifest/seal and their bound RGB-D NPZs."""
    directory = Path(directory)
    if set(hashes) != {'sensor-captures.json', 'sensor-seal.json'}:
        raise ValueError('both exact sensor receipt hashes required')
    for name, digest in hashes.items():
        if file_hash(directory/name) != digest:
            raise ValueError('pinned sensor receipt changed: '+name)
    rows = json.loads((directory/'sensor-captures.json').read_text())
    seal = json.loads((directory/'sensor-seal.json').read_text())
    reference = validated_manifest(rows, condition)
    expected = {'sensor-captures.json': hashes['sensor-captures.json']}
    expected.update({row['artifact']: row['artifact_sha256'] for row in rows})
    if seal['sha256'] != expected or seal['journal_parse_errors'] or seal['holding'] is not None:
        raise ValueError('complete exact sensor seal required')
    # Hash linkage only; never decode the evaluator-bearing journal.
    if file_hash(directory/'episodes.jsonl') != seal['journal_sha256_linkage_only']:
        raise ValueError('source journal linkage hash changed')
    frames = [prior.frame_from_capture(directory, row, seal['sha256']) for row in rows]
    return {'condition': condition, 'frames': frames, 'meta': deepcopy(rows),
            'tcps': [deepcopy(row['own_tcp_world_m']) for row in rows],
            'reference_index': reference, 'source_sha256': deepcopy(hashes),
            'source_journal_sha256': seal['journal_sha256_linkage_only']}


def same_arrays(a, b):
    return all(a[k].dtype == b[k].dtype and a[k].shape == b[k].shape
               and a[k].tobytes() == b[k].tobytes() for k in FRAME_KEYS)


def check_sensor_prefixes(packets, initial_frame):
    """Exact source comparisons only; never computes tracking or projection."""
    if tuple(packets) != CONDITIONS:
        raise ValueError('all four cells in registered order required')
    for packet in packets.values():
        if not same_arrays(packet['frames'][0], initial_frame):
            raise ValueError('initial arrays differ from the fixed BOX seed image')
    comparisons = [(a+'-close', a+'-open_hold', n+1) for a, n in APPROACH_COUNTS.items()]
    comparisons.append(('whole-close', 'neck-close', CROSS_ANCHOR_PREFIX))
    own_fields = ('own_observations', 'own_tcp_world_m', 'tcp_read_sim_time_s', 'capture_sim_time')
    for left, right, count in comparisons:
        for i in range(count):
            a, b = packets[left], packets[right]
            if (not same_arrays(a['frames'][i], b['frames'][i])
                    or any(a['meta'][i][k] != b['meta'][i][k] for k in own_fields)):
                raise ValueError('matched source sensor prefix differs')
    return [{'left': a, 'right': b, 'captures': n, 'exact_sensor_prefix': True} for a, b, n in comparisons]


def load_inputs(matrix, source_hashes):
    """Prospective production loader; actual hashes must be independently frozen."""
    if set(source_hashes) != set(CONDITIONS):
        raise ValueError('pinned hashes for all four completed cells required')
    for module, digest in HELPER_HASHES:
        if file_hash(module.__file__) != digest:
            raise ValueError('frozen temporal helper changed')
    if file_hash(base.SEEDS) != base.SEED_SHA:
        raise ValueError('original fixed BOX seed population changed')
    support = json.loads(base.SEEDS.read_text())
    seeds = [row['pixel_xy'] for row in support['support_G']]
    if support['crop_xyxy'] != [212, 169, 224, 210] or seeds != fixed_seeds():
        raise ValueError('all 492 ordered original seeds required')
    initial_path = base.SOURCE/'close/0000.npz'
    if file_hash(initial_path) != prior.INITIAL_FRAME_SHA:
        raise ValueError('original sealed seed image changed')
    with np.load(initial_path, allow_pickle=False) as data:
        initial = {k: data[k].copy() for k in FRAME_KEYS}
    packets = {condition: load_cell(Path(matrix)/condition, condition, source_hashes[condition]) for condition in CONDITIONS}
    prefixes = check_sensor_prefixes(packets, initial)
    return seeds, packets, {'source_sha256': deepcopy(source_hashes), 'seed_sha256': base.SEED_SHA,
        'source_journal_sha256': {c: p['source_journal_sha256'] for c, p in packets.items()},
        'helper_sha256': {Path(module.__file__).name: digest for module, digest in HELPER_HASHES},
        'initial_frame_sha256': prior.INITIAL_FRAME_SHA, 'sensor_prefixes': prefixes,
        'rows_per_cell': {c: SEED_COUNT*len(p['frames']) for c, p in packets.items()},
        'evaluator_read': False, 'proxy_membership_available': False, 'holding': None}


def fixed_seeds():
    return [[x, y] for y in range(169, 210) for x in range(212, 224)]


def enrich_track(tracked, packet, seed_id, seed):
    reference = packet['reference_index']
    if len(tracked) != len(packet['frames']) or [r['frame'] for r in tracked] != list(range(len(tracked))):
        raise ValueError('every ordered native row must be retained')
    sampled = [association.nearest_surface_sample(row, frame)
               for row, frame in zip(tracked, packet['frames'], strict=True)]
    rows = []
    for i, (native, sample, meta, tcp) in enumerate(zip(tracked, sampled, packet['meta'], packet['tcps'], strict=True)):
        delta, status = None, 'before_preclose'
        if i >= reference:
            status = 'missing_own_tcp' if tcp is None or packet['tcps'][reference] is None else 'available'
            if status == 'available':
                delta = base.reference_delta(sample['surface_point_world_m'], sampled[reference]['surface_point_world_m'],
                                             tcp, packet['tcps'][reference])
        rows.append({**native, **sample, **deepcopy(meta), 'seed_id': seed_id, 'seed_pixel_index_xy': list(seed),
            'own_tcp_world_m': deepcopy(tcp),
            'sampling_convention': association.CONVENTION, 'reference_deltas': {'preclose': delta},
            'reference_status': status, 'identity_verified': None, 'holding': None})
    return rows


def iter_cell_tracks(packet, seeds, cv2):
    """One unchanged LK call per seed; call only in a later admitted extraction."""
    if seeds != fixed_seeds() or cv2.__version__ != base.lk.CV2_VERSION:
        raise ValueError('fixed full seed population and OpenCV version required')
    rgbs = np.stack([frame['rgb'] for frame in packet['frames']])
    for seed_id, seed in enumerate(seeds):
        yield enrich_track(base.lk.track_lk(rgbs, seed, cv2), packet, seed_id, seed)


def summarize_tracks(tracks, packet):
    count, reference = len(packet['frames']), packet['reference_index']
    if (len(tracks) != SEED_COUNT or any(len(t) != count for t in tracks)
            or any([(r['seed_id'], r['capture_id']) for r in t] != [(s, i) for i in range(count)] for s, t in enumerate(tracks))):
        raise ValueError('all 492 seeds and complete ordered rows required')
    result = []
    for i in range(count):
        rows = [track[i] for track in tracks]
        metrics = {}
        for key in base.METRICS:
            values = [r['reference_deltas']['preclose'][key] for r in rows
                      if r['reference_deltas']['preclose'] is not None and r['reference_deltas']['preclose'][key] is not None]
            metrics[key] = base.describe(values) | {'missing_count': SEED_COUNT-len(values)}
        result.append({'capture_id': i, 'denominator': SEED_COUNT,
            'native_surviving_count': sum(r['status'] in base.ACCEPTED for r in rows),
            'native_failure_count': sum(r['status'] == 'native_failure' for r in rows),
            'unknown_after_failure_count': sum(r['status'] == 'unknown_after_native_failure' for r in rows),
            'valid_surface_count': sum(r['surface_point_world_m'] is not None for r in rows),
            'references': {'preclose': {'reference_capture_id': reference, 'available': i >= reference,
                'reference_surface_valid_count': sum(t[reference]['surface_point_world_m'] is not None for t in tracks) if i >= reference else None,
                'reference_own_tcp_available': packet['tcps'][reference] is not None if i >= reference else None,
                'metrics': metrics}}})
    return result


def prefix_disagreements(left, right, count):
    """Compare original nine fields only; keep every mismatch, never repair."""
    if (min(len(left), len(right)) < count
            or any(a['seed_id'] != b['seed_id'] or a['capture_id'] != i or b['capture_id'] != i
                   for i, (a, b) in enumerate(zip(left[:count], right[:count], strict=True)))):
        raise ValueError('matched per-seed native prefixes required')
    return [{'seed_id': a['seed_id'], 'capture_id': i,
             'fields': [k for k in prior.NATIVE_FIELDS if a[k] != b[k]]}
            for i, (a, b) in enumerate(zip(left[:count], right[:count], strict=True))
            if any(a[k] != b[k] for k in prior.NATIVE_FIELDS)]

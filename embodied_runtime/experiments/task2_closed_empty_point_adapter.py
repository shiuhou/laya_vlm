"""Prospective four-image native POINT adapter; no CLI, worker construction or call."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np

from . import task2_closed_empty_image_motion as suffix
from . import task2_point_region_control as native
from .records import file_hash

QUESTION = 'Point to: the wine bottle.'
CASES = (
    ('present-postevent', 'present', 0),
    ('away-postevent', 'away', 0),
    ('away-prelift', 'away', 16),
    ('present-prelift', 'present', 16),
)
HELPER_SHA256 = {
    'task2_point_region_control.py': 'cded84237e2f8953406806d3432634b33bacdaaecb1a9f26dceb365f2f59e86c',
    'task2_box_support.py': '8a8d7d828b4b2f65593975cb0378e5b4e7828c1e27ae432d6ca3bfdae3f179f1',
    'point_grounding_probe.py': 'bdd39fc30195e28d2a1a151bd78383a568f81f77fca81baa26765b3f81f4a09a',
    'adapters/locateanything.py': '5dbc90c5004571cec07486635775040e0bf952df7555b0205d7d367ee67c2704',
}


def verify_helpers():
    experiments = Path(__file__).resolve().parent
    for name, digest in HELPER_SHA256.items():
        path = experiments.parent/name if name.startswith('adapters/') else experiments/name
        if file_hash(path) != digest:
            raise ValueError('existing native POINT helper changed')


def select_images(manifests):
    """Called only on a separately admitted source; metadata never enters a prompt."""
    if set(manifests) != set(suffix.ROLES):
        raise ValueError('both complete prospective source cells required')
    selected = {role: suffix.selected_manifest(manifests[role], 'neck-'+role) for role in suffix.ROLES}
    result = []
    for name, role, index in CASES:
        row = selected[role][index]
        result.append({'case_id': name, 'directory': 'neck-'+role, 'local_suffix_capture_id': index,
            **{key: deepcopy(row[key]) for key in ('capture_id', 'phase', 'after_step', 'control',
                'source_capture_stream', 'source_capture_seq', 'capture_read_sim_time_s',
                'cached_geometry_sample_time_s', 'exact_observation_sample_time_s', 'artifact', 'artifact_sha256')}})
    return result


def load_rgb(source_root, image_spec):
    directory = suffix.relative(source_root, image_spec['directory'])
    path = suffix.relative(directory, image_spec['artifact'])
    if file_hash(path) != image_spec['artifact_sha256']:
        raise ValueError('bound full RGB archive changed')
    with np.load(path, allow_pickle=False) as archive:
        rgb = archive['rgb'].copy()
    if rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
        raise ValueError('native full 384x384 RGB required; no crop or resize')
    return rgb


def prepare_native_input(processor, rgb, case_id):
    """Reuse the native one-image processor path with the sole fixed question."""
    if case_id not in {row[0] for row in CASES} or rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
        raise ValueError('registered case and full native RGB required')
    # `condition` is metadata returned by native_input, never message content.
    return native.native_input(processor, rgb, {'condition': case_id,
        'query': 'the wine bottle', 'question': QUESTION})


def analyze_rgb_return(raw, input_count, model_max_length, eos_token_id):
    """Audit native point syntax in image coordinates; never access depth or pose."""
    observed = raw['observed_decoded_token_sequences']
    if raw['raw_response_type'] != 'str' or len(observed) != 1 or len(observed[0]) != 1:
        raise ValueError('native return or actual generated token audit unavailable')
    audit = native.generation_audit(observed[0][0], input_count, model_max_length, eos_token_id)
    parsed = native.parse_grounding(raw['raw_response'], 384, 384)
    reason = None
    if (not audit['complete_generation'] or audit['length_limit_reached']
            or not 0 < audit['actual_generated_token_count'] <= audit['effective_limit']):
        reason = 'incomplete_or_length_limited'
    elif parsed['status'] != 'single_point':
        reason = parsed['status']
    point = None
    if reason is None:
        p = parsed['points'][0]
        point = {'normalized': p['normalized'], 'continuous_xy': p['continuous_xy'],
                 'pixel_index_xy': p['sample_pixel_xy']}
    return {'raw_output': raw['raw_response'], 'generation_audit': audit, 'parsed': parsed,
        'status': 'admitted_rgb_point' if point is not None else 'not_admitted',
        'reason': reason, 'point': point, 'semantic_target_identity_verified': False,
        'semantic_confidence': None, 'holding': None, 'depth_read': False}

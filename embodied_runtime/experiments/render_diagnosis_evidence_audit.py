"""Independent array/hash audit of stored render diagnosis; no rendering or FK."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import near, require

FIELDS = ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')
INVARIANTS = ('geomgroup', 'render_collision_mesh', 'render_visual_mesh', 'offWidth', 'offHeight',
              'readDepthMap', 'scene_flags', 'model_integrator', 'model_timestep_s')
CENTERS = {24: ((216, 97), (147, 162), (147, 163), (165, 176), (165, 177), (237, 102)),
           25: ((119, 126), (156, 165), (236, 145), (240, 110), (156, 155))}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_digest(value):
    a = np.ascontiguousarray(value)
    return hashlib.sha256(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def audit(root, source):
    def read(name):
        return json.loads((root / name).read_text())
    manifest, seal, artifacts = read('manifest.json'), read('output-seal.json'), read('artifacts.json')
    require(not manifest['code']['dirty_status'] and manifest['code']['commit'].startswith('5b17822'), 'producer freeze')
    require(seal['rgb_witness_inspection_started'] is False, 'numerical seal before visual interpretation')
    for mapping in (seal['sha256'], artifacts):
        for name, expected in mapping.items():
            require(digest(root / name) == expected, 'sealed artifact ' + name)
    require(digest(root / 'protocol.md') == manifest['protocol_sha256'], 'protocol identity')
    data, gate, copies = read('measurements.json'), read('baseline-gate.json'), read('copy-cache-checks.json')
    require(gate['passed'] and data['baseline_gate_passed'] and gate['baseline'] == data['baseline'], 'recorded gate')
    expected = ['initial'] + [f'{s}/{c}/{phase}' for s in range(25) for c in range(8) for phase in ('before', 'after')] + ['25/0/before']
    require([r['label'] for r in gate['state_checks']] == expected, '402 state-gate labels')
    require(all(r['exact'] and r['max_absolute_error'] == 0 for r in gate['state_checks']), 'recorded state-gate pass')
    require(data['counts']['prefix'] == dict(env_controls=200, mj_step=5000, mj_step1=0, mj_step2=0, mj_forward=10000), 'prefix counts')
    require(all(value == 0 for value in data['counts']['diagnostic'].values()), 'no diagnostic physics')
    require(len(copies) == 6 and all(r['exact'] and r['source'] == r['copy'] for r in copies), 'recorded copy/cache identity')
    require(all(set(r['source']) == {'time', *manifest['cache_integrity_fields']} for r in copies), 'explicit checked arrays')
    require(data['no_masks_or_policy'] and not data['fresh_FK_rendered'], 'registered scope')
    output = {}
    for step, capture, expected_hash in ((24, 25, '3999edda9befca7a7dad6080c66bd03f609e408ce5a7563994b9704422029dab'),
                                         (25, 26, '907e9f36073adfdd7397fb79a8c205ce7567d7a729cc69d9b512087a42383d05')):
        path = source / f'frames/capture-{capture:06d}.npz'
        require(digest(path) == expected_hash, 'frozen original frame')
        with np.load(path, allow_pickle=False) as original, np.load(root / f'native-before-{step}.npz', allow_pickle=False) as n, np.load(root / f'zero-msaa-before-{step}.npz', allow_pickle=False) as z:
            native, zero = {k: n[k] for k in FIELDS}, {k: z[k] for k in FIELDS}
            require(all(array_digest(original[k]) == array_digest(native[k]) for k in FIELDS), 'exact original native arrays')
        baseline, result = data['baseline'][str(step)], data['states'][str(step)]
        require(baseline['cache_unchanged_during_capture'] and all(baseline['original_comparison']['array_exact'].values()), 'recorded native capture gate')
        contexts = [data['zero_context'], result['zero_context_after_capture']]
        for context in contexts:
            require(all(context[k] == baseline['context'][k] for k in INVARIANTS), 'sampling-only context change')
            require(context['context_actual_offSamples'] == context['gl']['bound_framebuffer_samples'] == 0, 'actual zero samples')
        require(baseline['context']['context_actual_offSamples'] == baseline['context']['gl']['bound_framebuffer_samples'] == 4, 'actual native samples')
        rgb = np.abs(native['rgb'].astype(int) - zero['rgb'].astype(int))
        depth = zero['depth_m'].astype(float) - native['depth_m']
        comparison = result['native_vs_zero']
        for k in FIELDS:
            require(comparison['native_array_sha256'][k] == array_digest(native[k]) and comparison['other_array_sha256'][k] == array_digest(zero[k]), 'array hash')
            require(comparison['array_exact'][k] == (array_digest(native[k]) == array_digest(zero[k])), 'array equality flag')
        stats = {'rgb_different_pixels': int(np.count_nonzero(np.any(rgb != 0, axis=-1))),
                 'rgb_max_channel_difference': int(rgb.max()), 'depth_different_pixels': int(np.count_nonzero(depth)),
                 'depth_max_absolute_difference_m': float(np.abs(depth).max()), 'depth_mean_absolute_difference_m': float(np.abs(depth).mean())}
        require(all(comparison[k] == value for k, value in stats.items()), 'whole-frame arithmetic')
        require([r['center_pixel_xy'] for r in result['witnesses']] == [list(p) for p in CENTERS[step]], 'all fixed centers')
        centers = []
        for row in result['witnesses']:
            x, y = row['center_pixel_xy']
            require([r['pixel_xy'] for r in row['all_3x3_pixels']] == [[xx, yy] for yy in range(y-1, y+2) for xx in range(x-1, x+2)], 'all fixed neighbors')
            for pixel in row['all_3x3_pixels']:
                xx, yy = pixel['pixel_xy']
                require(pixel['native_rgb'] == native['rgb'][yy, xx].tolist() and pixel['zero_rgb'] == zero['rgb'][yy, xx].tolist(), 'witness RGB')
                require(pixel['native_depth_m'] == float(native['depth_m'][yy, xx]) and pixel['zero_depth_m'] == float(zero['depth_m'][yy, xx]) and pixel['zero_minus_native_depth_m'] == float(depth[yy, xx]), 'witness depth')
            centers.append({'pixel_xy': [x, y], 'native_depth_m': float(native['depth_m'][y, x]),
                            'zero_depth_m': float(zero['depth_m'][y, x]), 'zero_minus_native_mm': float(1000*depth[y, x])})
        for row in result['cache_vs_own_qpos']:
            near(row['position_difference_m'], np.asarray(row['cached_position_world_m']) - row['fk_position_world_m'], 'saved pose difference')
            near(row['rotation_element_max_error'], float(np.abs(np.asarray(row['cached_rotation_world']) - row['fk_rotation_world']).max()), 'saved rotation difference')
        output[step] = {'whole_frame': stats, 'centers': centers,
                        'producer_recorded_max_projected_vertex_difference_px': max(r['projected_vertex_displacement_max_px'] for r in result['cache_vs_own_qpos'])}
    return {'passed': True, 'manifest_sha256': digest(root/'manifest.json'), 'measurements_sha256': digest(root/'measurements.json'),
            'output_seal_sha256': digest(root/'output-seal.json'), 'sealed_artifacts': len(artifacts), 'checked_neighborhood_entries': 99,
            'recorded_state_gate_checks': 402, 'recorded_cache_checks': 6, 'counts': data['counts'], 'frames': output,
            'scope': 'independent stored array/hash/arithmetic audit; recorded live-state/cache gates checked for consistency, not replayed; no rendering, FK or projection'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.raw, args.source)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result))

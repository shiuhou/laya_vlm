"""Audit stored footprint outputs and comparison arithmetic without FK/projection."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, description):
    if not condition:
        raise AssertionError(description)


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}


def exact(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


def stats(values):
    if not len(values):
        return {'count': 0}
    return {'count': len(values), 'minimum': float(values.min()), 'median': float(np.median(values)),
            'maximum': float(values.max()), 'mean_absolute': float(np.abs(values).mean()),
            'maximum_absolute': float(np.abs(values).max())}


def audit(sources):
    run = sources / 'pixel-sample-footprint-02'
    render = sources / 'render-measurement-diagnosis-01'
    prior = sources / 'gripper-visual-mask-control-01/estimator-input'
    artifacts = read(run / 'artifacts.json')
    for name, digest in artifacts.items():
        require(sha(run / name) == digest, 'artifact digest: ' + name)
    manifest = read(run / 'manifest.json')
    require(manifest['code']['commit'] == '0733ea7280e6585848f58e8e29990fd3415028ab' and not manifest['code']['dirty_status'], 'frozen clean code')
    require(read(run / 'process.json')['exit_code'] == 0, 'worker completed')
    for directory, digest in manifest['source_manifest_hashes'].items():
        require(sha(sources / directory / 'artifacts.json') == digest, 'source manifest')
        for name, expected in read(sources / directory / 'artifacts.json').items():
            require(sha(sources / directory / name) == expected, 'source artifact')
    for name, digest in manifest['sensor_input_sha256'].items():
        require(sha(run / 'sensor-input' / name) == digest, 'input seal')
    seal = read(run / 'sensor-output-seal.json')
    require(seal['evaluator_started'] is False and seal['cached_poses_admitted_to_sensor_worker'] is False, 'seal boundary declaration')
    for name, digest in seal['sha256'].items():
        require(sha(run / 'sensor-output' / name) == digest, 'sensor output seal')
    request = read(run / 'sensor-input/request.json')
    require(set(request) == {'visual_calibration', 'triangle_topology', 'own_joint_packets', 'samples_bottom_left'}, 'strict request schema')
    original_request = read(prior / 'request.json')
    require(request['own_joint_packets'] == original_request['own_joint_packets'] and request['visual_calibration'] == original_request['visual_calibration'], 'unchanged own inputs')
    require(request['samples_bottom_left'] == [[.375, .125], [.875, .375], [.125, .625], [.625, .875]], 'native sample calibration')
    topology_path = sources / 'gripper-visual-triangle-topology-01/triangle-topology.json'
    visual_path = sources / 'gripper-visual-calibration-01/gripper-visual-calibration.json'
    require(sha(topology_path) == manifest['triangle_topology_sha256'] == '12bedb9ef0604ba826f8e79a9a6e8d9bfabfe123211181a056ba608130c9fcc1', 'topology identity')
    require(sha(visual_path) == manifest['visual_calibration_sha256'] == 'c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98', 'visual calibration identity')
    require(request['triangle_topology'] == read(topology_path) and request['visual_calibration'] == read(visual_path), 'request exact topology/calibration')
    summary = read(run / 'sensor-output/measurements.json')
    comparison = read(run / 'evaluator/comparison.json')
    source_measurements = read(render / 'measurements.json')
    require(comparison['ownership'] == 'unknown', 'unknown ownership')
    result, center_total, entry_total = {}, 0, 0
    required_arrays = {'resolved_depth_m', 'sample_rays_camera', 'potential_own_coverage', 'potential_own_depth_m',
                       'nearest_own_geometry_index', 'geometric_edge_hit', 'nearest_own_geometry_tie', 'covered_sample_count'}
    for index, boundary in enumerate((24, 25)):
        label, state = f'sample{index}', str(boundary)
        frame = arrays(run / 'sensor-input' / f'{label}.npz')
        native = arrays(render / f'native-before-{boundary}.npz')
        zero = arrays(render / f'zero-msaa-before-{boundary}.npz')
        prior_frame = arrays(prior / f'{label}.npz')
        require(set(frame) == {'depth_m', 'intrinsics', 'camera_to_world'}, 'frame excludes RGB/evaluator')
        require(all(exact(frame[k], native[k]) and exact(frame[k], prior_frame[k]) for k in frame), 'unchanged native frame inputs')
        own, cached = {}, {}
        schema_counts = {}
        for condition, n_samples in [('native', 4), ('center', 1)]:
            own[condition] = arrays(run / 'sensor-output' / f'{label}-{condition}.npz')
            cached[condition] = arrays(run / 'evaluator' / f'{label}-cached-{condition}.npz')
            for kind, output in [('own', own[condition]), ('cached', cached[condition])]:
                require(set(output) == required_arrays, 'strict output arrays')
                coverage = output['potential_own_coverage']
                shape = (*frame['depth_m'].shape, n_samples)
                require(coverage.shape == shape and coverage.dtype == np.bool_, 'coverage shape/dtype')
                require(exact(output['resolved_depth_m'], frame['depth_m']), 'native resolved scalar retained bitwise')
                require(np.array_equal(output['covered_sample_count'], coverage.sum(axis=-1)), 'coverage count arithmetic')
                depth = output['potential_own_depth_m']
                require(depth.shape == shape and np.array_equal(np.isfinite(depth), coverage) and (depth[coverage] > 0).all(), 'predicted depth validity')
                require(np.isnan(depth[~coverage]).all(), 'misses remain NaN')
                geometry = output['nearest_own_geometry_index']
                require(geometry.shape == shape and np.issubdtype(geometry.dtype, np.integer) and (geometry[~coverage] == -1).all() and ((geometry[coverage] >= 0) & (geometry[coverage] < 3)).all(), 'mesh index semantics')
                for field in ['geometric_edge_hit', 'nearest_own_geometry_tie']:
                    require(output[field].shape == shape and output[field].dtype == np.bool_ and not output[field][~coverage].any(), 'edge/tie schema')
                rays = output['sample_rays_camera']
                require(rays.shape == (*shape, 3) and np.isfinite(rays).all() and (rays[..., 2] == 1).all(), 'stored optical ray schema only')
                schema_counts[kind + '_' + condition] = {'hit_samples': int(coverage.sum()),
                    'edge_hit_samples': int(output['geometric_edge_hit'].sum()), 'geometry_tie_samples': int(output['nearest_own_geometry_tie'].sum())}
            require(exact(own[condition]['sample_rays_camera'], cached[condition]['sample_rays_camera']), 'own/cached use identical stored rays')
            metadata = summary[label]['conditions'][condition]
            require(metadata['observed_ownership'] == metadata['unmodeled_or_occluded_space'] == 'unknown', 'unknown metadata')
            a, b = own[condition], cached[condition]
            both = a['potential_own_coverage'] & b['potential_own_coverage']
            different = a['potential_own_coverage'] != b['potential_own_coverage']
            expected = {'coverage_disagreement_samples': int(different.sum()), 'coverage_disagreement_pixels': int(different.any(axis=-1).sum()),
                        'cached_minus_own_depth_on_common_hits_m': stats(b['potential_own_depth_m'][both] - a['potential_own_depth_m'][both])}
            require(comparison['states'][state]['cached_vs_own_qpos'][condition] == expected, 'cache comparison arithmetic')
        count = own['native']['covered_sample_count']
        center = own['center']['potential_own_coverage'][..., 0]
        delta = zero['depth_m'].astype(float) - native['depth_m'].astype(float)
        counts = {str(n): {str(hit).lower(): int(((count == n) & (center == hit)).sum()) for hit in (False, True)} for n in range(5)}
        require(summary[label]['coverage_by_native_count_and_center'] == counts, 'every pixel count stratum')
        full_stats = {str(n): {str(hit).lower(): stats(delta[(count == n) & (center == hit)]) for hit in (False, True)} for n in range(5)}
        require(comparison['states'][state]['zero_minus_native_depth_by_own_coverage_m'] == full_stats, 'every pixel resolved-depth statistics')
        recorded_witnesses = comparison['states'][state]['fixed_witnesses']
        original_witnesses = source_measurements['states'][state]['witnesses']
        require(len(recorded_witnesses) == len(original_witnesses), 'all registered centers retained')
        centers, all_agree = [], True
        for actual, original in zip(recorded_witnesses, original_witnesses):
            require(actual['registered_center_xy'] == original['center_pixel_xy'], 'registered center identity')
            require(len(actual['all_3x3_pixels']) == len(original['all_3x3_pixels']) == 9, 'all fixed neighbors retained')
            for pixel, reference in zip(actual['all_3x3_pixels'], original['all_3x3_pixels']):
                x, y = reference['pixel_xy']
                expected = {'pixel_xy': [x, y], 'native_resolved_depth_m': float(native['depth_m'][y, x]),
                            'zero_minus_native_resolved_depth_m': float(delta[y, x]),
                            'own_native_sample_coverage': own['native']['potential_own_coverage'][y, x].tolist(),
                            'own_center_coverage': bool(center[y, x]),
                            'cached_native_sample_coverage': cached['native']['potential_own_coverage'][y, x].tolist(),
                            'cached_center_coverage': bool(cached['center']['potential_own_coverage'][y, x, 0])}
                require(pixel == expected, 'registered pixel exact recorded data')
                all_agree &= pixel['own_native_sample_coverage'] == pixel['cached_native_sample_coverage'] and pixel['own_center_coverage'] == pixel['cached_center_coverage']
                entry_total += 1
            x, y = actual['registered_center_xy']
            hits = own['native']['potential_own_coverage'][y, x].tolist()
            centers.append({'pixel_xy': [x, y], 'own_sample_coverage': hits, 'own_center_coverage': bool(center[y, x]),
                            'zero_minus_native_depth_mm': float(delta[y, x]) * 1000,
                            'cached_coverage_agrees': hits == cached['native']['potential_own_coverage'][y, x].tolist() and bool(center[y, x]) == bool(cached['center']['potential_own_coverage'][y, x, 0])})
            center_total += 1
        result[state] = {'coverage_count_and_center': counts, 'array_counts': schema_counts,
                         'cached_comparison': comparison['states'][state]['cached_vs_own_qpos'], 'registered_centers': centers,
                         'all_registered_neighborhood_coverage_agrees': bool(all_agree)}
    require(center_total == 11 and entry_total == 99, 'fixed center/entry totals')
    return {'status': 'pass', 'freeze': manifest['code']['commit'], 'artifact_count': len(artifacts),
            'artifacts_sha256': sha(run / 'artifacts.json'), 'sensor_output_seal_sha256': sha(run / 'sensor-output-seal.json'),
            'comparison_sha256': sha(run / 'evaluator/comparison.json'), 'registered_centers': center_total,
            'registered_neighborhood_entries': entry_total, 'states': result,
            'limits': ['stored arrays, hashes and arithmetic only; no FK or projection rerun',
                       'seal-before-evaluator order is source-reviewed and declared in sealed artifacts; no timestamped journal',
                       'geometric potential coverage is not observed depth ownership, GPU raster equivalence, or clearance',
                       'missing arm geometry and occlusion remain unknown']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))

"""Independent stored-record arithmetic audit; no model, scene, or projection calls."""
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


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, description):
    if not condition:
        raise AssertionError(description)


def audit(sources):
    run = sources / 'task2-box-support-run-02'
    frame_path = sources / 'interaction-observability-paired-01/close/0000.npz'
    mask_path = sources / 'interaction-observability-paired-01/evaluator-only/close-0000-bottle-mask.npy'
    require(sha(frame_path) == '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969', 'frozen frame')
    require(sha(mask_path) == '2a474be6d469dc2df45edfb03c97b23a1adf021f9a48551994a619f501a0b747', 'frozen proxy')
    config = read(run / 'resolved_config.yaml')
    manifest = read(run / 'manifest.json')
    require(manifest['code']['commit'] == 'ba7ab2e6d58932cef893f4d3549cd550279b2d65' and not manifest['code']['dirty_status'], 'clean freeze')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_box_support.py'] == '9986c4f79578dd4e2691726f21df7ba0706ac8b9876a255ca078eed2f9bb43a6', 'reviewed source identity')
    require(manifest['environment']['CUDA_VISIBLE_DEVICES'] == '0' and manifest['dtype'] == 'torch.bfloat16', 'fixed device and dtype')
    require(manifest['model']['content_id'] == canonical(manifest['model']['files_sha256']) == config['expected_model_content_id'] == '4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f', 'recorded model identity')
    require(config['question'] == 'Locate a single instance that matches the following description: the wine bottle.', 'fixed prompt')
    require(config['settings'] == {'max_new_tokens': 256, 'use_cache': True, 'generation_mode': 'hybrid', 'temperature': 0., 'do_sample': False, 'verbose': False}, 'settings')
    require(sha(run / 'protocol.md') == config['protocol_sha256'] == '8476959edc85bd60750b233e76404fdb1b723b679075aa1393559d06ca0a5efd', 'protocol seal')
    lines = (run / 'episodes.jsonl').read_bytes().splitlines(keepends=True)
    rows, previous = [], None
    for index, line in enumerate(lines):
        require(line.endswith(b'\n'), 'complete journal line')
        row = json.loads(line)
        require(row['seq'] == index and row['previous_record_id'] == previous, 'journal chain')
        require(canonical({k: v for k, v in row.items() if k != 'record_id'}) == row['record_id'], 'record hash')
        require(row['config_hash'] == canonical(config), 'record config')
        previous = row['record_id']
        rows.append(row)
    expected_kinds = ['run_start', 'manifest_update', 'rgb_input_sealed', 'manifest_update', 'call_started',
                      'generation_return_sealed', 'model_output_sealed', 'sensor_outputs_sealed', 'termination']
    require([r['kind'] for r in rows] == expected_kinds, 'one call, response then sensor seal')
    final_manifest = dict(rows[0]['data']['manifest'])
    for row in rows:
        if row['kind'] == 'manifest_update':
            final_manifest.update(row['data'])
        if row['kind'].endswith('_sealed'):
            require(sha(run / row['data']['artifact']) == row['data']['sha256'], 'sealed artifact')
    require(final_manifest == manifest, 'manifest journal reconstruction')
    require(rows[-1]['data'] == {'reason': 'sensor_outputs_complete', 'model_calls': 1, 'physics_calls': 0, 'renders': 0, 'retries': 0}, 'one-call termination')
    require(rows[-2]['data']['evaluator_opened'] is False, 'sensor seal boundary')
    preflight = read(sources / 'task2-box-support-processor-preflight-01.json')
    require(rows[4]['data']['input_token_ids'] == preflight['input_token_ids'], 'actual preflight input tokens unchanged')
    require(rows[4]['data']['image_grid_hws'] == [[28, 28]], 'actual input grid')
    model, returned, sensor = [read(run / name) for name in ('model-output.json', 'generation-return.json', 'sensor-representation.json')]
    expected_raw = '<ref>the wine bottle</ref><box><542><408><596><582></box><|im_end|>'
    require(model['raw_output'] == returned['raw_response'] == expected_raw, 'raw model response')
    require(returned['raw_response_type'] == 'str' and returned['returned_value_repr'] == repr(expected_raw), 'returned response form')
    tokens = returned['observed_decoded_token_sequences']
    require(len(tokens) == len(tokens[0]) == 1, 'one returned sequence')
    generated = tokens[0][0]
    generation = model['generation_audit']
    require(generated == generation['actual_generated_token_ids'] and len(generated) == generation['actual_generated_token_count'] == 12, 'token count')
    require(generated[-1] == generation['eos_token_id'] == 151645 and generation['terminal_eos_observed'] and generation['complete_generation'] and not generation['length_limit_reached'], 'terminal EOS')
    require(generation['input_token_count'] == len(preflight['input_token_ids']) == 237 and generation['effective_limit'] == 256, 'token limits')
    coords = [542 / 1000 * 384, 408 / 1000 * 384, 596 / 1000 * 384, 582 / 1000 * 384]
    require(model['admitted_box'] == coords and model['parsed']['status'] == 'single_box', 'parsed BOX arithmetic')
    box = list(map(int, coords))
    require(sensor['box_xyxy'] == box == [208, 156, 228, 223], 'provider integer BOX')
    with np.load(frame_path, allow_pickle=False) as archive:
        frame = {k: archive[k] for k in archive.files}
    rgb = np.load(run / 'rgb-input.npy', allow_pickle=False)
    require(rgb.dtype == frame['rgb'].dtype and rgb.shape == frame['rgb'].shape and rgb.tobytes() == frame['rgb'].tobytes(), 'model original RGB bytes')
    require(rows[2]['data']['rgb_bytes_sha256'] == hashlib.sha256(rgb.tobytes()).hexdigest(), 'sealed RGB payload hash')
    depth = frame['depth_m']
    x1, y1, x2, y2 = box
    px, py = max(1, (x2 - x1) // 5), max(1, (y2 - y1) // 5)
    bounds = [x1 + px, y1 + py, x2 - px, y2 - py]
    require(sensor['crop_xyxy'] == bounds == [212, 169, 224, 210], 'fixed interior crop')
    expected_pixels = [(x, y) for y in range(bounds[1], bounds[3]) for x in range(bounds[0], bounds[2])
                       if np.isfinite(depth[y, x]) and .01 <= depth[y, x] <= 5]
    support = sensor['support_G']
    require([tuple(p['pixel_xy']) for p in support] == expected_pixels, 'every valid pixel, no cleanup')
    for point, (x, y) in zip(support, expected_pixels):
        require(point['depth_m'] == float(depth[y, x]) and point['rgb'] == rgb[y, x].tolist(), 'support exact RGB/depth')
        require(np.asarray(point['position_world_m']).shape == (3,) and np.isfinite(point['position_world_m']).all(), 'stored world point schema only')
    values = np.asarray([depth[y, x] for x, y in expected_pixels])
    median = float(np.median(values))
    require(sensor['depth_statistics'] == {'median_m': median, 'mad_m': float(np.median(np.abs(values - median))),
                                          'std_m': float(np.std(values)), 'valid_ratio': 1.}, 'depth summary')
    require(sensor['min_depth_m'] == float(values.min()) and sensor['max_depth_m'] == float(values.max()), 'depth extrema')
    for name, rank in [('lower', (len(values) - 1) // 2), ('upper', len(values) // 2)]:
        expected = np.flatnonzero(values == np.sort(values)[rank]).tolist()
        require(sensor['median_contributor_indices'][name] == expected, 'all tied rank contributors')
    center = sensor['center_sample']
    u, v = (x1 + x2) / 2, (y1 + y2) / 2
    x, y = int(np.floor(u)), int(np.floor(v))
    require(center == {'continuous_xy': [u, v], 'sample_pixel_xy': [x, y], 'depth_m': float(depth[y, x]),
                       'depth_valid': True, 'depth_minus_median_m': float(depth[y, x]) - median}, 'center depth')
    require(sensor['point_P']['position_camera_m'][2] == median and sensor['point_P']['box_xyxy'] == box, 'P retained median and BOX')
    require(sensor['support_pixel_center_offset'] == .5 and not sensor['support_is_segmentation'] and sensor['resolved_depth_ownership'] is None, 'representation semantics')
    evaluation = run / 'evaluation'
    for name, digest in read(evaluation / 'artifacts.json').items():
        require(sha(evaluation / name) == digest, 'evaluation artifact hashes')
    start = read(evaluation / 'evaluation-start.json')
    require(start['wall_time_unix_s'] > rows[-1]['wall_time'] and start['labels_opened'] is False, 'separate evaluator order')
    require(start['source_journal_sha256'] == sha(run / 'episodes.jsonl') and start['sensor_sha256'] == sha(run / 'sensor-representation.json'), 'evaluation source seals')
    result = read(evaluation / 'proxy-analysis.json')
    mask = np.load(mask_path, allow_pickle=False)
    labels = [bool(mask[y, x]) for x, y in expected_pixels]
    require(result['selected_pixel_proxy_membership'] == labels, 'all support proxy memberships')
    require(result['selected_count'] == len(labels) == 492 and result['selected_proxy_overlap_count'] == sum(labels) == 414, 'support overlap counts')
    require(result['proxy_visible_count'] == int(mask.sum()) == 777, 'visible proxy count')
    require(result['selected_proxy_overlap_fraction'] == sum(labels) / len(labels) and result['proxy_visible_coverage_fraction'] == sum(labels) / int(mask.sum()), 'overlap fractions')
    strata = {'proxy_interior': 0, 'proxy_boundary_band': 0, 'proxy_exterior': 0}
    for x, y in expected_pixels:
        neighborhood = [bool(mask[yy, xx]) if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] else False
                        for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2)]
        name = 'proxy_interior' if all(neighborhood) else 'proxy_boundary_band' if any(neighborhood) else 'proxy_exterior'
        strata[name] += 1
    require(strata == result['selected_strata_counts'], 'independent fixed neighborhood strata')
    for name, indices in sensor['median_contributor_indices'].items():
        count = sum(labels[i] for i in indices)
        require(result['median_contributors'][name] == {'count': len(indices), 'rendered_proxy_agreement_count': count,
                'rendered_proxy_agreement_fraction': count / len(indices)}, 'median contributor proxy counts')
    require(result['center_pixel_proxy_membership'] == bool(mask[int(np.floor(v)), int(np.floor(u))]), 'center proxy')
    require(result['resolved_depth_ownership'] is None and result['semantic_confidence'] is None, 'evaluation limits')
    return {'status': 'pass', 'freeze': manifest['code']['commit'], 'journal_records': len(rows),
            'journal_sha256': sha(run / 'episodes.jsonl'), 'sensor_sha256': sha(run / 'sensor-representation.json'),
            'proxy_sha256': sha(evaluation / 'proxy-analysis.json'), 'model_calls': 1, 'generated_tokens': len(generated),
            'box_xyxy': box, 'crop_xyxy': bounds, 'selected_count': len(labels), 'proxy_overlap_count': sum(labels),
            'proxy_visible_count': int(mask.sum()), 'proxy_strata': strata,
            'depth_median_m': median, 'depth_min_m': float(values.min()), 'depth_max_m': float(values.max()),
            'center_minus_median_mm': center['depth_minus_median_m'] * 1000,
            'median_contributor_indices': sensor['median_contributor_indices'],
            'limits': ['stored hashes, arrays and scalar arithmetic only', 'world coordinates source-reviewed; no projection rerun',
                       'recorded model identity map checked; weights not reread', 'no inference, physics or rendering',
                       'archived rendered mask is a membership proxy, not depth ownership or semantic confidence']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))

"""Sealed HO23 four-layer scoring; annotations never enter generation.

The operational mode reads no annotations and makes no semantic-grade claim.
All proportions retain denominators; proposals are not executable acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import math
from pathlib import Path

import numpy as np

from ..contracts import require
from ..perception.evaluation_annotations import _inside, image_binding
from .p1_formal50_scoring import box_metrics, polygon_mask, score_mask, _percentiles
from .p1_heldout_annotation_packet import load_packet, validate_complete
from .p1_segmentation_probe import read, write, seal, verify_seal
from .records import file_hash, code_identity

INITS = list(range(27, 50))


def proportion(n, denominator):
    """Descriptive Wilson 95% interval; frames, not masks, are the unit."""
    if not denominator:
        return dict(n=n, denominator=0, rate=None, wilson95=None)
    p, z = n / denominator, 1.959963984540054
    scale = 1 + z*z/denominator
    middle = (p + z*z/(2*denominator))/scale
    half = z*math.sqrt(p*(1-p)/denominator + z*z/(4*denominator**2))/scale
    return dict(n=n, denominator=denominator, rate=p, wilson95=[max(0, middle-half), min(1, middle+half)])


def matched(a, b):
    require(len(a) == len(b), 'paired denominator differs')
    gains = sum(not x and y for x, y in zip(a, b))
    losses = sum(x and not y for x, y in zip(a, b))
    discordant = gains + losses
    p = min(1., 2*sum(math.comb(discordant, k) for k in range(min(gains, losses)+1))/2**discordant) if discordant else 1.
    return dict(denominator=len(a), A=sum(a), B=sum(b), gains=gains, losses=losses,
                net_gain=gains-losses, rate_difference=(gains-losses)/len(a) if a else None,
                exact_discordance_two_sided_p=p, descriptive_only=True)


def box_score(box, image, label):
    result = box_metrics(box, image, label)
    bbox, iou = None, None
    if label is not None and label.any():
        yy, xx = np.nonzero(label)
        bbox = [int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)]
        intersection = max(0, min(box[2], bbox[2])-max(box[0], bbox[0])) * max(0, min(box[3], bbox[3])-max(box[1], bbox[1]))
        union = (box[2]-box[0])*(box[3]-box[1]) + (bbox[2]-bbox[0])*(bbox[3]-bbox[1]) - intersection
        iou = intersection/union if union else None
    result.update(human_support_bbox_xyxy=bbox, human_support_bbox_iou=iou,
        localization_correct=(result['annotated_coverage'] >= .9 and iou >= .5) if iou is not None else None)
    return result


def candidate_pool(natives):
    """No winner: aggregate every raw and every source/point-admitted proposal."""
    raw = [c for native in natives for c in native['candidates']]
    admitted = [c for native in natives if native['mask_point_admission']['admitted'] for c in native['candidates']]
    def counts(items):
        inside = sum(c.get('evaluation_category') == 'VALID_DRAWER_FRONT_CANDIDATE' for c in items)
        outside = sum(c.get('inside_annotated_region') is False for c in items)
        unknown = sum(c.get('inside_annotated_region') is None for c in items)
        return dict(total=len(items), correct=inside, outside=outside, unscored=unknown,
                    any_correct=inside > 0, clean=inside > 0 and outside == 0 and unknown == 0)
    return dict(raw=counts(raw), admitted=counts(admitted))


def verified_generation(root):
    """All stage outputs and bindings are checked before any label access."""
    from .p1_box_grounding_heldout import inputs
    root = Path(root)
    for stage, name in (('capture', 'manifest.json'), ('grounding', 'outputs.json'),
                        ('masks', 'outputs.json'), ('geometry', 'results.json')):
        verify_seal(root/stage)
        require(name in read(root/stage/'sealed.json')['files'], 'unsealed stage output')
    registration, sensors = inputs(root)
    capture = read(root/'capture/manifest.json')
    calls = read(root/'grounding/outputs.json')
    expected_calls = [(init, kind) for init in INITS for kind in ['POINT', *(['A', 'B'] if init % 2 == 0 else ['B', 'A'])]]
    require([(x['init_index'], x['kind']) for x in calls] == expected_calls, 'all 69 canonical calls required')
    by_call = {(x['init_index'], x['kind']): x for x in calls}
    for call in calls:
        src = sensors[call['init_index']][0]
        require(call['image'] == src['image'] and call['source_identity'] == src['source_identity']
                and call['evaluation_labels_used'] is False, 'grounding source differs')
        key = 'point_query' if call['kind'] == 'POINT' else 'query_'+call['kind']
        require(call['query'] == registration['config'][key], 'query binding differs')
        if 'raw_output' in call:
            require(hashlib.sha256(call['raw_output'].encode()).hexdigest() == call['response_sha256'], 'raw reply hash differs')
    masks, geometry = read(root/'masks/outputs.json'), read(root/'geometry/results.json')
    expected = [(init, arm, ordinal) for init in INITS for arm in (['A', 'B'] if init % 2 == 0 else ['B', 'A'])
                for ordinal in (range(len(by_call[init, arm]['ordered_boxes'])) if by_call[init, arm]['ordered_boxes'] else [None])]
    require([(r['init_index'], r['arm'], r['box_index']) for r in masks] == expected
            and [(r['init_index'], r['arm'], r['box_index']) for r in geometry] == expected, 'all BOX slots required')
    for mask, geo in zip(masks, geometry):
        require(all(geo.get(k) == v for k, v in mask.items()), 'geometry altered source receipt')
        src = sensors[mask['init_index']][0]
        point, box = by_call[mask['init_index'], 'POINT'], by_call[mask['init_index'], mask['arm']]
        require(mask['image'] == src['image'] and mask['source_identity'] == src['source_identity']
                and mask['point_query'] == point['query'] and mask['box_query'] == box['query']
                and mask['point_response_sha256'] == point.get('response_sha256')
                and mask['box_response_sha256'] == box.get('response_sha256')
                and mask['evaluation_labels_used'] is False, 'mask source/query differs')
        if mask['box_index'] is not None:
            require(mask['box_xyxy'] == box['ordered_boxes'][mask['box_index']], 'BOX ordinal differs')
        if mask['status'] == 'COMPLETE':
            path = Path(mask['artifact_uri']).resolve()
            require(path.is_relative_to((root/'masks').resolve()) and file_hash(path) == mask['artifact_sha256'], 'native artifact differs')
            require(str(path.relative_to((root/'masks').resolve())) in read(root/'masks/sealed.json')['files'], 'native artifact unsealed')
            with np.load(path, allow_pickle=False) as data:
                native = data['masks']
                require(native.dtype == bool and native.shape == (3, src['image']['height'], src['image']['width'])
                        and np.array_equal(native, data['logits'] > 0), 'native outputs differ')
                require([hashlib.sha256(m.tobytes()).hexdigest() for m in native] == mask['raw_mask_sha256'], 'native ordinal/hash differs')
                require(data['predicted_ious'].tolist() == mask['predicted_ious'], 'SAM score receipt differs')
            require([n['ordinal'] for n in geo['native_results']] == [0, 1, 2], 'all native geometry required')
            for result in geo['native_results']:
                estimate, ordinal = result['estimate'], result['ordinal']
                binding = estimate['mask_binding']
                require(estimate['source_identity'] == mask['source_identity'] == binding['source_identity']
                        and binding['raw_mask_sha256'] == mask['raw_mask_sha256'][ordinal]
                        and binding['mask_index'] == ordinal and binding['box_index'] == mask['box_index']
                        and binding['box_xyxy'] == mask['box_xyxy'] == estimate['original_box_xyxy']
                        and binding['query'] == mask['box_query']
                        and binding['box_response_sha256'] == mask['box_response_sha256']
                        and binding['evaluation_labels_used'] is False
                        and estimate['measurement_contract'] == 'native-mask-depth/2', 'estimate binding differs')
                u, v = mask['prompt_admission']['sample_pixel_xy']
                require(result['mask_point_admission']['admitted'] == bool(native[ordinal, v, u]), 'point-mask admission differs')
        else:
            require(not geo['native_results'], 'upstream failure cannot acquire geometry')
    for stage in ('grounding', 'masks', 'geometry'):
        require(read(root/stage/'condition.json')['registration_sha256'] == file_hash(root/'registration.json'), 'stage registration differs')
    return registration, sensors, capture, by_call, geometry


def build_rows(sensors, calls, geometry, truth_by_image=None):
    from .p1_mask_support_reanalysis import config
    cfg = config()
    rows = []
    for init in INITS:
        src, view, _ = sensors[init]
        image, point = src['image'], calls[init, 'POINT']
        truth = truth_by_image[image['image_id']]['entities']['drawer_front_pushable'] if truth_by_image is not None else None
        label = polygon_mask(image, truth) if truth is not None else None
        xy = point.get('point_xy')
        uv = point.get('sample_pixel_xy')
        depth = float(view['depth_m'][uv[1], uv[0]]) if point['source_admitted'] and uv is not None else None
        depth_ok = bool(depth is not None and np.isfinite(depth) and cfg.min_depth_m <= depth <= cfg.max_depth_m)
        inside = bool(_inside(np.asarray([xy]), truth['polygons'])[0]) if label is not None and xy is not None else None
        row = dict(init_index=init, image_id=image['image_id'], human_status=truth['status'] if truth else 'ANNOTATION_PENDING',
            point=dict(typed_admitted=point['source_admitted'], reason=point['reason'], complete_eos=bool(point.get('audit', {}).get('terminal_eos_observed') and point.get('audit', {}).get('complete_generation')),
                point_xy=xy, sample_pixel_xy=uv, sampled_depth_m=depth if depth is not None and np.isfinite(depth) else None,
                depth_available=depth_ok, inside_human_region=inside, inference_s=point.get('inference_s')), arms={})
        for arm in ('A', 'B'):
            call = calls[init, arm]
            arm_rows = [g for g in geometry if g['init_index'] == init and g['arm'] == arm]
            boxes, natives = [], []
            for g in arm_rows:
                metrics = box_score(g['box_xyxy'], image, label) if g['box_xyxy'] is not None and truth is not None else None
                box = dict(box_index=g['box_index'], box_xyxy=g['box_xyxy'], box_metrics=metrics,
                    sam_status=g['status'], failure_stage=g.get('failure_stage'), prompt_admission=g.get('prompt_admission'),
                    encode_s=g.get('encode_s'), predict_s=g.get('predict_s'), masks=[])
                if g['status'] == 'COMPLETE':
                    with np.load(g['artifact_uri'], allow_pickle=False) as data:
                        for n in g['native_results']:
                            ordinal = n['ordinal']
                            if truth is not None:
                                scored = score_mask(image, truth, data['masks'][ordinal], n['estimate'], ordinal=ordinal,
                                    box=g['box_xyxy'], stage_ledger=n['stage_ledger'])
                            else:
                                patch = n['estimate']['patch']
                                scored = dict(native_mask_ordinal=ordinal, geometry_status=patch['geometry_status'],
                                    reason_codes=patch['reason_codes'], geometry_metrics=patch['metrics'], stage_ledger=n['stage_ledger'],
                                    candidates=[dict(point_id=c['point_id'], inside_annotated_region=None,
                                        evaluation_category='ANNOTATION_PENDING', usable_status=c['usable_status']) for c in patch['candidates']])
                            scored.update(mask_point_admission=n['mask_point_admission'], geometry_s=n['geometry_s'],
                                          predicted_iou=g['predicted_ious'][ordinal], calibrated_confidence=None)
                            box['masks'].append(scored)
                            natives.append(scored)
                boxes.append(box)
            pools = candidate_pool(natives)
            if truth is None:
                for pool in pools.values():
                    pool.update(correct=None, outside=None, any_correct=None, clean=None)
            row['arms'][arm] = dict(typed_admitted=call['source_admitted'], reason=call['reason'],
                complete_eos=bool(call.get('audit', {}).get('terminal_eos_observed') and call.get('audit', {}).get('complete_generation')),
                inference_s=call.get('inference_s'), boxes=boxes,
                any_box_correct=(any(b['box_metrics']['localization_correct'] is True for b in boxes if b['box_metrics']) if label is not None else None),
                all_boxes_correct=(bool(call['ordered_boxes']) and all(b['box_metrics']['localization_correct'] is True for b in boxes if b['box_metrics']) if label is not None else None),
                generated_sam_boxes=sum(b['sam_status'] == 'COMPLETE' for b in boxes), native_mask_count=len(natives),
                pools=pools, failure_reasons=sorted(set([b['failure_stage'] for b in boxes if b['failure_stage']] + [r for n in natives for r in n['reason_codes']])),
                clean=(pools['admitted']['clean'] if truth is not None else None))
        rows.append(row)
    return rows


def summarize(rows, *, labels_available):
    visible = [r for r in rows if r['human_status'] == 'VISIBLE']
    result = dict(frame_count=len(rows), annotation_status='SCORED' if labels_available else 'AWAITING_INDEPENDENT_HUMAN',
        visibility_counts=dict(Counter(r['human_status'] for r in rows)),
        point=dict(complete_eos=proportion(sum(r['point']['complete_eos'] for r in rows), len(rows)),
            typed=proportion(sum(r['point']['typed_admitted'] for r in rows), len(rows)),
            depth_available=proportion(sum(r['point']['depth_available'] for r in rows), len(rows)),
            inside_visible=proportion(sum(r['point']['inside_human_region'] is True for r in visible), len(visible)) if labels_available else None,
            inside_all=proportion(sum(r['point']['inside_human_region'] is True for r in rows), len(rows)) if labels_available else None,
            inside_typed_visible=proportion(sum(r['point']['inside_human_region'] is True for r in visible), sum(r['point']['typed_admitted'] for r in visible)) if labels_available else None,
            depth_among_typed=proportion(sum(r['point']['depth_available'] for r in rows), sum(r['point']['typed_admitted'] for r in rows)),
            failures=dict(Counter(r['point']['reason'] or 'TYPED_ADMITTED' for r in rows))), arms={},
        p1_pass_claimed=False, executable_acceptance=False, temporal_tested=False, continuous_end_to_end_hz_measured=False,
        status='P2 remains blocked pending held-out scoring / temporal P1 gate')
    for arm in ('A', 'B'):
        boxes = [b for r in rows for b in r['arms'][arm]['boxes']]
        natives = [n for b in boxes for n in b['masks']]
        clean = sum(r['arms'][arm]['clean'] is True for r in rows)
        wrong = sum(r['arms'][arm]['pools']['admitted']['outside'] for r in visible)
        summary = dict(complete_eos=proportion(sum(r['arms'][arm]['complete_eos'] for r in rows), len(rows)),
            typed=proportion(sum(r['arms'][arm]['typed_admitted'] for r in rows), len(rows)),
            box_localization_all=proportion(sum(r['arms'][arm]['any_box_correct'] is True for r in rows), len(rows)) if labels_available else None,
            box_localization_visible=proportion(sum(r['arms'][arm]['any_box_correct'] is True for r in visible), len(visible)) if labels_available else None,
            all_boxes_correct_visible=proportion(sum(r['arms'][arm]['all_boxes_correct'] is True for r in visible), len(visible)) if labels_available else None,
            point_compatible_boxes=proportion(sum(bool(b['prompt_admission'] and b['prompt_admission']['admitted']) for b in boxes), sum(b['box_xyxy'] is not None for b in boxes)),
            point_compatible_frames=proportion(sum(any(b['prompt_admission'] and b['prompt_admission']['admitted'] for b in r['arms'][arm]['boxes']) for r in rows), len(rows)),
            sam_generated_frames=sum(r['arms'][arm]['generated_sam_boxes'] > 0 for r in rows),
            sam_generated_boxes=sum(b['sam_status'] == 'COMPLETE' for b in boxes), native_mask_count=len(natives),
            upstream_unavailable_boxes=sum(b['sam_status'] != 'COMPLETE' for b in boxes),
            upstream_failures=dict(Counter(b['failure_stage'] for b in boxes if b['failure_stage'])),
            native_reasons_nonexclusive=dict(Counter(reason for n in natives for reason in n['reason_codes'])),
            native_evaluation_taxonomy=dict(Counter(n.get('evaluation_category', 'ANNOTATION_PENDING') for n in natives)),
            candidate_counts={pool: {key: (sum(r['arms'][arm]['pools'][pool][key] for r in rows) if labels_available or key in ('total', 'unscored') else None)
                for key in ('total', 'correct', 'outside', 'unscored')} for pool in ('raw', 'admitted')},
            clean_all=proportion(clean, len(rows)) if labels_available else None,
            clean_visible=proportion(clean, len(visible)) if labels_available else None,
            timing=dict(box_inference=_percentiles([r['arms'][arm]['inference_s'] for r in rows]),
                sam_encode=_percentiles([b['encode_s'] for b in boxes]), sam_predict=_percentiles([b['predict_s'] for b in boxes]),
                geometry=_percentiles([n['geometry_s'] for n in natives])))
        summary['spatial_ready_signal'] = (len(visible) >= 19 and clean >= 19 and clean/len(visible) >= .8 and wrong == 0) if labels_available else None
        result['arms'][arm] = summary
    result['point']['timing'] = _percentiles([r['point']['inference_s'] for r in rows])
    if labels_available:
        common = [r for r in rows if all(r['arms'][arm]['generated_sam_boxes'] > 0 for arm in ('A', 'B'))]
        result['paired'] = dict(box_localization_visible=matched([r['arms']['A']['any_box_correct'] is True for r in visible], [r['arms']['B']['any_box_correct'] is True for r in visible]),
            clean_all=matched([r['arms']['A']['clean'] is True for r in rows], [r['arms']['B']['clean'] is True for r in rows]),
            clean_common_sam=matched([r['arms']['A']['clean'] is True for r in common], [r['arms']['B']['clean'] is True for r in common]),
            common_sam_init_indices=[r['init_index'] for r in common])
        result['substantial_engineering_gain'] = result['paired']['clean_all']['net_gain'] >= 3
        result['interpretation'] = ('OBSERVABILITY_LIMITED_INCONCLUSIVE' if len(visible) < 19 else
            'SPATIAL_READY_SIGNAL_ONLY_TEMPORAL_PENDING' if result['arms']['B']['spatial_ready_signal'] else
            'PARTIAL_BOX_IMPROVEMENT_END_TO_END_BLOCKED' if result['paired']['box_localization_visible']['net_gain'] > 0 else
            'NO_DEMONSTRATED_END_TO_END_REPAIR')
    return result


def run(root, *, packet=None, annotations=None):
    root = Path(root)
    registration, sensors, capture, calls, geometry = verified_generation(root)
    labels, receipt = None, None
    require((packet is None) == (annotations is None), 'packet and annotations required together')
    if annotations is not None:
        # First label read occurs here, after complete stage verification above.
        receipt = validate_complete(annotations, packet)
        manifest = load_packet(packet)
        require(manifest['source_run_manifest_sha256'] == file_hash(root/'capture/manifest.json'), 'packet capture binding differs')
        require([image_binding(x) for x in manifest['images']] == [image_binding(x['image']) for x in capture['inputs']], 'packet frame bindings differ')
        labels = {r['image_id']: r for r in read(annotations)['annotations']}
    rows = build_rows(sensors, calls, geometry, labels)
    summary = summarize(rows, labels_available=labels is not None)
    out = root/('scoring' if labels is not None else 'operational-summary')
    out.mkdir(exist_ok=False)
    write(out/'condition.json', dict(code=code_identity(), registration_sha256=file_hash(root/'registration.json'),
        generation_seals={s:file_hash(root/s/'sealed.json') for s in ('capture', 'grounding', 'masks', 'geometry')},
        annotation_receipt=receipt, evaluation_only=True, no_runtime_input=True))
    write(out/'rows.json', rows)
    write(out/'summary.json', summary)
    with (out/'all23.csv').open('x', newline='') as stream:
        fields = ['init_index', 'image_id', 'human_status', 'point_reason', 'point_typed', 'point_inside']
        fields += [f'{arm}_{key}' for arm in ('A', 'B') for key in ('box_correct', 'sam_boxes', 'native_masks', 'raw_candidates', 'admitted_candidates', 'correct', 'outside', 'clean', 'failures')]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = {k:row[k] for k in ('init_index', 'image_id', 'human_status')}
            flat.update(point_reason=row['point']['reason'], point_typed=row['point']['typed_admitted'], point_inside=row['point']['inside_human_region'])
            for arm in ('A', 'B'):
                r = row['arms'][arm]
                for key, value in dict(box_correct=r['any_box_correct'], sam_boxes=r['generated_sam_boxes'], native_masks=r['native_mask_count'],
                    raw_candidates=r['pools']['raw']['total'], admitted_candidates=r['pools']['admitted']['total'], correct=r['pools']['admitted']['correct'],
                    outside=r['pools']['admitted']['outside'], clean=r['clean'], failures=';'.join(r['failure_reasons'])).items():
                    flat[f'{arm}_{key}'] = value
            writer.writerow(flat)
    seal(out)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--packet')
    parser.add_argument('--annotations')
    parser.add_argument('--operational-only', action='store_true')
    args = parser.parse_args()
    require(args.operational_only or (args.packet and args.annotations), 'choose annotation-free summary or full scoring')
    require(not args.operational_only or (args.packet is None and args.annotations is None), 'operational mode must not read annotation paths')
    result = run(args.output, packet=args.packet, annotations=args.annotations)
    print(result['status'])


if __name__ == '__main__':
    main()

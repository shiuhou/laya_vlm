"""Export audited extra-closure comparison and complete measured boundary data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import task2_additional_stationary_grasp as probe
from . import task2_additional_stationary_grasp_rgb as rgb
from .records import file_hash

AUDIT_SHA = '13a6741bbf430be8c47a99217fe32acbe7f9d7cb5ad3e671ebd689eb24e95ad3'
CLOSEOUT_SHA = '011564a3e1504080f4b10ce1095fd3280985d4b710147ef9b0ad381af7b2ae2b'
FREEZE = '945c96d81916f7952d9b40565c52b00085363544'
PHASES = ('close_or_hold', 'additional_close', 'lift')


def produce(audit_path):
    if file_hash(audit_path) != AUDIT_SHA:
        raise ValueError('Closed independent extra-closure audit required')
    audit = probe.prior.base.read(audit_path)
    if audit['status'] != 'PASS' or audit['freeze'] != FREEZE or audit['matrix_outcome'] != 'all_registered_cells_complete':
        raise ValueError('Both completed cells at the reviewed freeze required')
    closeout_path = rgb.RAW.with_name(rgb.RAW.name + '-execution-closeout.json')
    if file_hash(closeout_path) != CLOSEOUT_SHA:
        raise ValueError('Reviewed execution closeout changed')
    closeout = probe.prior.base.read(closeout_path)
    old_path = probe.AUDIT
    if file_hash(old_path) != probe.AUDIT_SHA:
        raise ValueError('Closed four-cell comparison audit changed')
    old = probe.prior.base.read(old_path)
    images_path = rgb.OUTPUT / (rgb.PREFIX + '_rgb_sources.json')
    images = probe.prior.base.read(images_path)
    for condition, sheet in images['conditions'].items():
        path = rgb.OUTPUT / sheet['sheet']
        if file_hash(path) != sheet['sheet_sha256']:
            raise ValueError('RGB sheet changed')
        with Image.open(path) as image:
            for panel in sheet['panels']:
                row = panel['source_sensor_row']
                with np.load(rgb.RAW / condition / row['artifact'], allow_pickle=False) as frame:
                    displayed = np.asarray(image.crop(panel['sheet_native_RGB_rectangle_xyxy']))
                    if not np.array_equal(displayed, frame['rgb']):
                        raise ValueError('Sheet pixels differ from original stored RGB')
    conditions = []
    for checked, recorded in zip(audit['conditions'], closeout['conditions']):
        name = checked['condition']
        if name != recorded['condition'] or file_hash(rgb.RAW / name / 'episodes.jsonl') != checked['journal_sha256']:
            raise ValueError('Closed condition binding changed')
        if file_hash(rgb.RAW / name / 'evaluator-only/labels.json') != checked['sensor_evidence']['labels_sha256']:
            raise ValueError('Closed endpoint labels changed')
        measured = []
        previous = None
        for phase, own in zip(PHASES, checked['own_motion']['primitive_endpoints']):
            rows = [row for row in checked['endpoint_measurements'] if row['phase'] == phase]
            first, endpoint = rows[0], rows[-1]
            # Before-first-GRASP bottle labels were not separately sampled. Do not invent them.
            baseline = first if previous is None else previous
            measured.append({'phase': phase, 'own_arm_and_joints': own, 'endpoint': endpoint,
                'bottle_delta_baseline': 'first_returned_control_endpoint_not_primitive_start' if previous is None else 'previous_primitive_endpoint',
                'bottle_center_delta_mm': [a-b for a, b in zip(endpoint['bottle_center_mm'], baseline['bottle_center_mm'])],
                'bottle_bottom_delta_mm': endpoint['bottle_bottom_mm']-baseline['bottle_bottom_mm'],
                'before_first_GRASP_bottle_label_separately_recorded': False,
                'all_eight_endpoints': rows})
            previous = endpoint
        conditions.append({'condition': name, 'registered_prediction': checked['registered_prediction'],
            'primitive_measurements': measured, 'all_24_own_rows': checked['own_motion']['all_suffix_own_rows'],
            'native_contacts': checked['native_contacts'], 'first_GRASP_prefix': checked['first_GRASP_prefix'],
            'first_bilateral_samples': recorded['descriptive_stored_labels_not_independent_audit']['first_bilateral_samples'],
            'replay': checked['replay'], 'suffix': checked['suffix'], 'lift_motion': checked['lift_motion'],
            'source_journal_sha256': checked['journal_sha256'],
            'original_one_GRASP_comparison': next(row for row in old['conditions'] if row['condition'] == name),
            'original_open_control_comparison': next(row for row in old['conditions'] if row['condition'] == name.replace('close', 'open_hold'))})
    summary = {'physical_producer_freeze': FREEZE, 'main_integration_was_not_physics_producer': 'd29a805',
        'report_code_is_separate_from_frozen_execution': True, 'raw_directory': str(rgb.RAW),
        'independent_audit_sha256': AUDIT_SHA, 'closed_four_cell_audit_sha256': probe.AUDIT_SHA,
        'matrix_journal_sha256': audit['matrix_journal_sha256'], 'request_sha256': audit['request_sha256'],
        'preflight_sha256': audit['preflight_sha256'], 'review_sha256': audit['review_sha256'],
        'execution_closeout_sha256': CLOSEOUT_SHA, 'RGB_source_ledger_sha256': file_hash(images_path),
        'conditions': conditions, 'new_matched_close_open_witness': None,
        'comparison_scope': audit['comparison_scope'], 'limits': audit['limits'],
        'driver_returncode': 0, 'outer_tool_session_exit_code': 0, 'retries': 0, 'new_model_calls': 0,
        'new_report_render_calls': 0, 'new_report_physics_calls': 0, 'task_success_claim': False}
    probe.prior.approach.write(rgb.OUTPUT / (rgb.PREFIX + '_summary.json'), summary)
    findings(summary)
    print(json.dumps({'report': 'written', 'audit_sha256': AUDIT_SHA, 'own_rows': 48,
                      'endpoint_measurements': 48, 'original_RGB_panels_verified': 36, 'new_physics_calls': 0}))


def findings(summary):
    rows, drift_rows = [], []
    for condition in summary['conditions']:
        name = condition['condition']
        before = condition['original_one_GRASP_comparison']
        added, lift = condition['primitive_measurements'][1:]
        rows.append(f"| {name} | {before['lift_bilateral_endpoints']}/8; "
            f"{before['native_contacts']['by_phase_and_stage']['lift/native_before']['bilateral_pad_samples']}/200 | "
            f"true | 8/8; 200/200 | {condition['lift_motion']['bottle_center_delta_mm'][2]:.6f} | "
            f"{condition['lift_motion']['bottle_bottom_delta_mm']:.6f} |")
        own = added['own_arm_and_joints']
        bottle = ', '.join(f'{v:+.6f}' for v in added['bottle_center_delta_mm'])
        drift_rows.append(f"| {name} | {own['tcp_translation_norm_mm']:.6f} | {own['rotation_change_deg']:.6f} | "
                          f"[{bottle}] | {own['after_joints']['signed_joint_separation_mm']:.6f} |")
    text = f'''# Additional closed-jaw interval: relation established before lift

Both fixed cells completed once and passed all six original atomic validations,
full recorded-control/native/primary-image replays and all 48 auxiliary-image
checks. Each fresh approach and first GRASP matched its sealed original cell
before the additional interval. No threshold, target, posture or action sequence
was tuned. Both registered predictions were satisfied.

| Anchor | Original one-GRASP lift endpoints; native BEFORE | After added interval, prelift bilateral | New lift endpoints; native BEFORE | Center lift (mm) | Bottom lift (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

Native AFTER counts equal BEFORE counts in every table entry. New rise is measured
from the final additional-GRASP endpoint. The original open-hold controls had zero
rise and zero bilateral endpoints, but lack the added interval; this close-only
experiment does not inherit the previous matched close/open witness.

At both first-GRASP endpoints, bilateral contact was absent and both jaws were
still moving at about 0.099 m/s per joint. First bilateral evidence in the added
interval appeared at whole control 1/native index 28 (BEFORE time 12.956 s) and
neck control 0/native index 17 (12.534 s). These are first recorded cache samples,
not exact continuous contact-onset times. The added interval had 172/200 whole
and 183/200 neck bilateral samples at each native stage; its final endpoint was
bilateral in both. The following lift had 200/200 at each stage and 8/8 endpoints.

| Anchor | Added interval arm translation norm (mm) | Arm rotation (deg) | Bottle center change [x,y,z] (mm) | Final signed joint separation (mm) |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(drift_rows)}

The separation is arithmetic qpos difference, not physical pad gap. At the end
of the added interval, joint velocities were approximately 3–4×10⁻⁵ m/s each;
this is measured proprioception, not a holding classifier. The summary retains
all 48 qpos/qvel/TCP packets, every close1/close2/lift endpoint, full arm deltas and
rotation changes, bottle center/bottom changes and raw/strong contact families.
Before-first-GRASP bottle labels were not separately sampled: its reported bottle
change uses control 0 to control 7, explicitly not a full primitive-start delta.
Added-interval and lift changes use their preceding primitive endpoints exactly.
Bottle rotation remains unknown without a recorded source-specific mapping.

Establishment was not clean. Whole's added interval included 12 raw non-pad finger
samples overlapping bilateral pads at each native stage; one per stage exceeded
0.05 N, with maximum 0.385890355 N. Neck had 10 raw zero-force finger overlaps per
stage. Table contacts persisted for 34 whole and 27 neck raw samples per stage
(32 and 27 above threshold). The subsequent lift had no raw non-pad robot/bottle
or bottle/table contact at any saved native sample. These observations do not
establish a clean continuous grasp or support-free retention. Raw families and
support histories remain in the summary; complete native force vectors remain
in the linked sealed journals.

The added action supplied eight more controls / 0.4 s of retained closure, with
measured arm drift and bottle rearrangement. It supports the distinction between
command completion and a subsequently established contact relation. It does not
isolate pure latency. After a retained CLOSED command, executed STOP-hold and
GRASP use the same nominal arm/jaw control under this executor; GRASP is not a
unique token winner. Approach STOP's non-execution remains a separate convention.
No fixed-two-GRASP policy is inferred.

The [whole RGB sheet]({rgb.PREFIX}_whole-close_rgb.png) and
[neck RGB sheet]({rgb.PREFIX}_neck-close_rgb.png) each contain 18 original frames:
before first GRASP, after first GRASP, every added-GRASP endpoint and every lift
endpoint. All 36 native-resolution RGB panels match sealed source arrays exactly.
The [source ledger]({rgb.PREFIX}_rgb_sources.json) binds each panel and the
[full measured summary]({rgb.PREFIX}_summary.json) preserves data and comparisons.
No new rendering, masks, model calls or physics were used for this report.

Physics ran from clean producer `{FREEZE}` using `laya-embodied`; main integration
`d29a805` and report commits were not the physics producer. Independent audit
`{AUDIT_SHA}` binds both cells. Matrix journal
`{summary['matrix_journal_sha256']}` completed normally. The subprocess, driver and
outer tool session returned 0; no retries occurred. The earlier four-cell
launcher's 143/0 discrepancy remains in that earlier report and is not present here.
'''
    with (rgb.OUTPUT / (rgb.PREFIX + '_findings.md')).open('x') as stream:
        stream.write(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', required=True, type=Path)
    produce(parser.parse_args().audit)

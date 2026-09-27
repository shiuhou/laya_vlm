"""Package the closed four-cell audit and lossless suffix records without physics."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from . import task2_point_anchor_grasp_transfer as probe
from .records import file_hash, load_records

RAW = probe.base.RAW / 'task2-point-anchor-grasp-transfer-run-01'
OUTPUT = probe.base.ROOT / 'docs/evidence/autonomous_research'
FREEZE = '1702cb2739bfdb2817a329c8047e16bcb7836657'
AUDIT_SHA = '6051e9a498f73e8399b232a2d64b9a0174e8e0ab8d3187cffdb69a4c31a9a018'
PREFIX = 'task2_point_anchor_grasp_transfer'


def produce(audit_path):
    if file_hash(audit_path) != AUDIT_SHA:
        raise ValueError('Exact closed independent four-cell audit required')
    audit = probe.base.read(audit_path)
    if (audit['status'] != 'PASS' or audit['freeze'] != FREEZE or audit['matrix_outcome'] != 'all_four_complete'
            or audit['matrix_journal_sha256'] != file_hash(RAW / 'episodes.jsonl')
            or [row['condition'] for row in audit['conditions']] != list(probe.ORDER)):
        raise ValueError('Complete fixed four-cell source required')
    traces, summaries = {}, []
    for checked in audit['conditions']:
        name = checked['condition']
        directory = RAW / name
        if file_hash(directory / 'episodes.jsonl') != checked['journal_sha256']:
            raise ValueError('Closed source journal changed')
        records, errors = load_records(directory / 'episodes.jsonl')
        if errors or records[0]['data']['manifest']['code']['commit'] != FREEZE:
            raise ValueError('Source journal/freeze mismatch')
        for filename, key in (('result.json', 'result_sha256'), ('auxiliary-result.json', 'auxiliary_result_sha256')):
            if file_hash(RAW / (name + '-replay') / filename) != checked['replay'][key]:
                raise ValueError('Closed replay changed')
        boundary = next(i for i, row in enumerate(records) if row['kind'] == 'approach_prefix_verified')
        labels_path = directory / 'evaluator-only' / 'labels.json'
        if file_hash(labels_path) != checked['sensor_evidence']['labels_sha256']:
            raise ValueError('Closed evaluator labels changed')
        traces[name] = {'journal_sha256': checked['journal_sha256'],
            'records': [{key: row[key] for key in ('record_id', 'kind', 'data')} for row in records[boundary:]],
            'evaluator_labels_sha256': file_hash(labels_path), 'evaluator_labels': probe.base.read(labels_path),
            'audited_endpoint_measurements': checked['endpoint_measurements'],
            'source_array_artifacts_remain_in_raw_directory': True}
        summaries.append({key: checked[key] for key in ('condition', 'outcome', 'journal_sha256', 'prefix', 'suffix',
            'replay', 'termination', 'native_contacts', 'lift_bilateral_endpoints', 'lift_endpoint_count', 'lift_motion')})
    trace = {'raw_directory': str(RAW), 'freeze': FREEZE, 'independent_audit_sha256': AUDIT_SHA,
        'scope': 'every suffix journal record including all native snapshots, controls, action results and endpoint labels; no approach tensor duplication',
        'conditions': traces}
    trace_path = OUTPUT / (PREFIX + '_suffix_traces.json.gz')
    encoded = json.dumps(trace, indent=2, allow_nan=False).encode() + b'\n'
    with trace_path.open('xb') as stream:
        stream.write(gzip.compress(encoded, mtime=0))
    # Ensure the portable lossless artifact contains the complete source-derived payload.
    if json.loads(gzip.decompress(trace_path.read_bytes())) != trace:
        raise ValueError('Lossless suffix trace roundtrip failed')
    summary = {'raw_directory': str(RAW), 'freeze': FREEZE, 'independent_audit_sha256': AUDIT_SHA,
        'matrix_journal_sha256': audit['matrix_journal_sha256'], 'request_sha256': audit['request_sha256'],
        'preflight_sha256': audit['preflight_sha256'], 'review_sha256': audit['review_sha256'],
        'conditions': summaries, 'registered_local_witnesses': audit['local_witnesses'],
        'launcher': audit['launcher'], 'limits': audit['limits'], 'full_suffix_traces_sha256': file_hash(trace_path),
        'new_model_calls': 0, 'retries': 0, 'winner_selected': False, 'task_success_claim': False,
        'interpretation': 'Both final GRASP endpoints have no raw robot/bottle contact; bilateral contact is established during lift. Neck has the sampled endpoint witness but neither close arm has bilateral contact at every native lift sample.'}
    probe.approach.write(OUTPUT / (PREFIX + '_summary.json'), summary)
    write_findings(summary)
    print(json.dumps({'report': 'written', 'independent_audit_sha256': AUDIT_SHA,
        'suffix_records': {name: len(value['records']) for name, value in traces.items()},
        'suffix_traces_sha256': file_hash(trace_path), 'physics_calls': 0}))


def write_findings(summary):
    rows = []
    for condition in summary['conditions']:
        name = condition['condition']
        native = condition['native_contacts']['by_phase_and_stage']
        before, after = [native['lift/' + stage]['bilateral_pad_samples'] for stage in ('native_before', 'native_after')]
        motion = condition['lift_motion']
        rows.append(f"| {name} | {motion['bottle_center_delta_mm'][2]:.6f} | {motion['bottle_bottom_delta_mm']:.6f} | "
            f"{condition['lift_bilateral_endpoints']}/8 | {before}/200; {after}/200 |")
    text = f'''# Fixed POINT approaches transferred to scripted close/open-hold and lift

All four fresh cells completed once, with eight passing atomic validations and
four exact full replays plus four exact 16-image auxiliary replays. Each approach
matched its own archived source before the scripted intervention. There were no
unexpected-contact aborts, model calls, retries or selected winners.

| Cell | Bottle center rise (mm) | Bottom rise (mm) | Bilateral lift endpoints | Native BEFORE; AFTER |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

Rise uses the final close/hold endpoint as the reference. The literal registered
sampled-endpoint witness is **false for whole** (7/8 rather than required 8/8) and
**true for neck** (8/8 with positive rise versus the open control's zero rise and
0/8 bilateral endpoints). All four validators in each matched pair passed.
These are descriptive local results, not a clean interaction-valid grasp or
full drawer-task success. Neither close arm maintained bilateral pads at all
200 BEFORE and all 200 AFTER lift samples.

Both final GRASP endpoints had no raw robot/bottle contact and no bilateral-pad
relation. Whole had no robot/bottle contact during GRASP; neck had brief unilateral
pad contact during GRASP (8 raw pad rows, 4 above 0.05 N, at each native stage),
then no contact at its final GRASP endpoint. Bilateral pad contact was established
during the subsequent lift. Command completion therefore did not establish the
registered contact relation before lift.

The full suffix traces preserve every raw contact, force vector and geom identity.
During lift, raw finger contacts overlapped bilateral pads in 9 whole and 8 neck
samples at each native stage. Those finger rows had zero normal force; there
were no above-threshold non-pad robot/bottle rows. Hand and other robot/bottle
families had no recorded rows. Keeping raw and thresholded evidence separate is
necessary: the neck sampled witness is not promoted to an unambiguous contact
mechanism. Both conditions retained early native bottle/table contacts (whole
28 raw/23 strong samples; neck 17 raw/15 strong, at each stage). Whole's first lift
endpoint still had table contacts; its later seven and all eight neck lift
endpoints had none. These sampled contact absences do not establish support-free
retention or a clean continuous grasp. Bottle rotation is unknown without a
recorded source-specific quaternion mapping; center and bottom changes are
reported separately.

The experiment used sensor-selected approaches followed by fixed scripted
interventions: eight-control GRASP versus executed eight-control STOP-hold, then
one nominal 10 mm MV_UP. Approach STOP itself executed nothing. Whole and neck
approach endpoints were already about 9 mm apart; the earlier own-anchor 43 mm
versus 5 mm distances do not establish grasp superiority. No target, posture,
threshold or action sequence was adjusted after outcomes.

Execution used the literal source environment, `laya-embodied`, at clean freeze
`{FREEZE}` with preflight02
`{summary['preflight_sha256']}`. Preflight03 is an unexecuted alternative-environment
preparation. The matrix journal records normal completion and the matrix subprocess
returned 0. The outer tool's final poll returned 143 despite printed driver status
0 and the complete exit receipt. That launcher discrepancy remains explicit in
the audit and execution closeout; there was no repeated physics attempt.

Independent raw audit: `{AUDIT_SHA}`. Matrix journal:
`{summary['matrix_journal_sha256']}`. The audit reuses the byte-exact closed approach
prefixes; it does not rerun their geometry tensor computation. See the
[summary]({PREFIX}_summary.json) and
[lossless full suffix traces]({PREFIX}_suffix_traces.json.gz) for all four results,
source hashes, action validations, native-stage aggregates and complete suffix
records. Existing RGB interpretations are retained separately; no images are
duplicated here.

The next prepared hypothesis is whether one additional stationary GRASP interval
establishes bilateral contact before lift and throughout all sampled native lift
stages. Geometry or slip may remain limiting. Preparation does not authorize new
dynamics.
'''
    path = OUTPUT / (PREFIX + '_findings.md')
    with path.open('x') as stream:
        stream.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', required=True, type=Path)
    produce(parser.parse_args().audit)


if __name__ == '__main__':
    main()

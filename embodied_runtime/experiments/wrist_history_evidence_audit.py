"""Independent stored wrist projection, contact-cohort and score audit."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import near, require
from .task1_substep_evidence_audit import stream_records

SOURCE_SHA = 'e8e253cefe4c694c6091e1bf944a8f269cfc47c7ed08c053419d97e1a73615d4'
COHORTS = ('gripper_only', 'arm_only', 'gripper_and_arm', 'no_robot_scene_above_1N', 'self_contact_present')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def distribution(values):
    if not values:
        return dict(count=0, min=None, p05=None, median=None, p95=None, max=None)
    return dict(count=len(values), **dict(zip(('min', 'p05', 'median', 'p95', 'max'), np.quantile(values, [0, .05, .5, .95, 1]).tolist())))


def pair_rank(values, negatives):
    if not values or not negatives:
        return None
    differences = np.asarray(values)[:, None] - np.asarray(negatives)[None, :]
    return ((differences > 0).sum(axis=1) + .5 * (differences == 0).sum(axis=1)) / len(negatives)


def audit(raw, source):
    identity = {}
    journal = list(stream_records(raw/'episodes.jsonl', identity))
    require([r['kind'] for r in journal] == ['run_start', 'frozen_analysis', 'sensors_sealed', 'features_sealed', 'labels_sealed', 'termination'], 'sealing order')
    frozen = journal[1]['data']
    require(frozen['code']['commit'] == 'adc7eb4e448615a271e58951f19a3dbe1c64e44a' and not frozen['code']['dirty_status'], 'reviewed freeze')
    artifact_hashes = {'sensors.jsonl': journal[2]['data']['sensors_sha256'], 'sensor_metadata.json': journal[2]['data']['metadata_sha256'],
                'features.jsonl': journal[3]['data']['features_sha256'], 'labels.jsonl': journal[4]['data']['labels_sha256'],
                'summary.json': journal[5]['data']['summary_sha256'], 'protocol.md': frozen['protocol_sha256']}
    require(all(digest(raw/name) == h for name, h in artifact_hashes.items()), 'sealed artifact hashes')
    sensors, features, labels = [read_rows(raw/name) for name in ('sensors.jsonl', 'features.jsonl', 'labels.jsonl')]
    summary = json.loads((raw/'summary.json').read_text())
    require(len(sensors) == len(features) == len(labels) == 970, 'complete controls')
    source_identity, native_samples, controls = {}, 0, 0
    for record in stream_records(source/'episodes.jsonl', source_identity):
        kind, d = record['kind'], record['data']
        if kind == 'environment':
            groups = {k: set(d['geometry'][k]['ids']) for k in ('robot', 'arm', 'gripper', 'drawer')}
            require(groups['arm'].isdisjoint(groups['gripper']) and groups['arm'] | groups['gripper'] == groups['robot'], 'robot partition')
            require({k:d[k] for k in ('sensors', 'model_timestep_s', 'control_timestep_s', 'integrator')} == json.loads((raw/'sensor_metadata.json').read_text()), 'sensor metadata')
        elif kind == 'control_started':
            index, substep = d['global_control'], 0
            require(index == controls and all(all(row[k] == d[k] for k in ('global_control', 'step', 'control')) for row in (sensors[index], features[index], labels[index])), 'lineage')
        elif kind == 'integrator_call_started':
            before_time = d['before']['time_s']
            if substep == 0:
                require(sensors[index]['before_time_s'] == before_time, 'baseline read time')
                for channel, unit, key in (('force', 'N', 'force_ee'), ('torque', 'Nm', 'torque_ee')):
                    require(sensors[index][f'baseline_{channel}_{unit}'] == d['before']['wrist_sensor_buffers'][key]['values'], 'baseline sensor values')
        elif kind == 'integrator_call_completed':
            after = d['after']; sample = sensors[index]['after'][substep]
            require(sample == {'time_s': after['time_s'], 'force_N': after['wrist_sensor_buffers']['force_ee']['values'], 'torque_Nm': after['wrist_sensor_buffers']['torque_ee']['values']}, 'projected native sensor sample')
            actual = dict(gripper=False, arm=False, self=False, gripper_drawer=False, raw_external_rows=0, strong_contacts=[])
            for contact in after['contacts']:
                a, b = contact['geom_ids']; ar, br = a in groups['robot'], b in groups['robot']
                actual['raw_external_rows'] += int(ar != br)
                if contact['normal_force_N'] <= 1:
                    continue
                if ar and br:
                    actual['self'] = True
                    actual['strong_contacts'].append({**contact, 'group': 'self'})
                elif ar != br:
                    robot, scene = (a, b) if ar else (b, a)
                    group = 'gripper' if robot in groups['gripper'] else 'arm'
                    actual[group] = True
                    actual['gripper_drawer'] |= group == 'gripper' and scene in groups['drawer']
                    actual['strong_contacts'].append({**contact, 'group': group, 'scene_is_drawer': scene in groups['drawer']})
            require(labels[index]['native_samples'][substep] == {'substep': substep, 'interval_s': [before_time, after['time_s']], **actual}, 'native contact gold')
            substep += 1; native_samples += 1
        elif kind == 'control_completed':
            require(substep == 25 and len(sensors[index]['after']) == 25, 'native sample count')
            label = labels[index]
            flags = {k: any(s[k] for s in label['native_samples']) for k in ('gripper', 'arm', 'self')}
            category = 'self_contact_present' if flags['self'] else 'gripper_and_arm' if flags['gripper'] and flags['arm'] else 'gripper_only' if flags['gripper'] else 'arm_only' if flags['arm'] else 'no_robot_scene_above_1N'
            require(label['cohort'] == category and all(label[k] == v for k, v in flags.items()), 'cohort reduction')
            require(label['endpoint_gripper'] == label['native_samples'][-1]['gripper'] and label['endpoint_missed_gripper_only'] == (category == 'gripper_only' and not label['endpoint_gripper']), 'fixed missed subset')
            for channel, unit in (('force', 'N'), ('torque', 'Nm')):
                baseline = sensors[index][f'baseline_{channel}_{unit}']
                seq = np.asarray([s[f'{channel}_{unit}'] for s in sensors[index]['after']])
                changes = np.sqrt(np.sum((seq - baseline)**2, axis=1))
                near(features[index][f'endpoint_{channel}_change_{unit}'], changes[-1], 'endpoint arithmetic')
                near(features[index][f'temporal_{channel}_change_{unit}'], changes.max(), 'temporal arithmetic')
            controls += 1
    require(source_identity['sha256'] == SOURCE_SHA and controls == 970 and native_samples == 24250, 'canonical source completeness')
    counts = Counter(l['cohort'] for l in labels)
    require(summary['cohort_counts'] == {k:counts[k] for k in COHORTS}, 'cohort count table')
    negatives = [i for i, l in enumerate(labels) if l['cohort'] == 'no_robot_scene_above_1N']
    subsets = {'all_gripper_only': [i for i, l in enumerate(labels) if l['cohort'] == 'gripper_only'],
               'endpoint_missed_gripper_only': [i for i, l in enumerate(labels) if l['endpoint_missed_gripper_only']]}
    for channel, unit in (('force', 'N'), ('torque', 'Nm')):
        for subset, indices in subsets.items():
            result = summary['primary_force_secondary_torque'][channel][subset]
            scores = {}
            for mode in ('endpoint', 'temporal'):
                key = f'{mode}_{channel}_change_{unit}'
                positive, negative = [features[i][key] for i in indices], [features[i][key] for i in negatives]
                expected = result[mode]
                require(expected['positive'] == distribution(positive) and expected['negative'] == distribution(negative), 'distribution arithmetic')
                scores[mode] = float(pair_rank(positive, negative).mean()) if positive and negative else None
                near(expected['auroc'], scores[mode], 'independent pairwise AUROC')
                require(expected['positive_values_within_negative_observed_range'] == sum(min(negative) <= x <= max(negative) for x in positive), 'positive overlap')
                require(expected['negative_values_within_positive_observed_range'] == sum(min(positive) <= x <= max(positive) for x in negative), 'negative overlap')
            near(result['auroc_temporal_minus_endpoint'], scores['temporal']-scores['endpoint'], 'AUROC difference')
        for cohort in COHORTS:
            for mode in ('endpoint', 'temporal'):
                require(summary['all_cohort_distributions'][channel][cohort][mode] == distribution([f[f'{mode}_{channel}_change_{unit}'] for f,l in zip(features,labels) if l['cohort']==cohort]), 'all cohort distributions')
    require([x['global_control'] for x in summary['endpoint_missed_controls']] == subsets['endpoint_missed_gripper_only'], 'all missed examples')
    for example in summary['endpoint_missed_controls']:
        i = example['global_control']
        require(all(example[k] == v for k, v in features[i].items()), 'complete missed features')
        for key, rank in example['negative_cohort_ranks'].items():
            near(rank, pair_rank([features[i][key]], [features[j][key] for j in negatives])[0], 'missed negative rank')
        require(example['gripper_contact_native_intervals'] == [{'substep': s['substep'], 'interval_s': s['interval_s'], 'contacts': [c for c in s['strong_contacts'] if c['group']=='gripper']} for s in labels[i]['native_samples'] if s['gripper']], 'all missed intervals')
    return {'passed': True, 'analysis_identity': identity, 'source_identity': source_identity, 'sealed_artifacts': artifact_hashes,
            'controls': controls, 'native_samples': native_samples, 'cohort_counts': summary['cohort_counts'],
            'endpoint_missed_controls': len(subsets['endpoint_missed_gripper_only']), 'comparisons': summary['primary_force_secondary_torque'],
            'scope': 'independent stored source projection/gold/arithmetic audit; no model, physics, FK, projection or new features'}


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
    print(json.dumps({k:result[k] for k in ('passed', 'analysis_identity', 'source_identity', 'controls', 'native_samples', 'cohort_counts', 'endpoint_missed_controls')}))

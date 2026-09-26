"""Read-only arithmetic for the existing bottle contact witness; no simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def inventory(root: Path):
    names = ('manifest.json', 'evaluator-only/labels.json', 'endpoints.json', 'sensors.jsonl')
    blobs = {name: (root / name).read_bytes() for name in names}
    hashes = {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()}
    assert hashes['manifest.json'] == 'b68dfcbf65048555069bb1c27639915ec2fda9c520822600f81549547031b02f'
    assert hashes['evaluator-only/labels.json'] == '493c7b1ff32943217351d73b631c385199dfaab4d3ed8427a52de32c768945c5'
    manifest = json.loads(blobs['manifest.json'])
    labels = json.loads(blobs['evaluator-only/labels.json'])
    endpoints = json.loads(blobs['endpoints.json'])
    sensors = [json.loads(line) for line in blobs['sensors.jsonl'].splitlines()]
    assert len(labels) == 274 and len(sensors) == 272 and len(endpoints) == 36
    for row in labels:
        pads = {contact['hand'] for contact in row['contacts']
                if contact['normal_force_N'] > .05 and contact['moving_target']}
        bilateral = all(f'gripper0_finger{side}_pad_collision' in pads for side in (1, 2))
        assert row['valid_grasp_relation'] == bilateral
    assert all(not any(row['sensor']['command'][3:6]) for row in sensors)
    result = {'passed': True, 'source_hashes': hashes, 'producer_commit': manifest['code']['commit'],
              'contact_threshold_strict_gt_N': .05, 'sample_period_s': .05,
              'all_native_rotation_commands_zero': True, 'arms': {}}
    for arm in ('close', 'open_hold'):
        selected = [row for row in sensors if row['arm'] == arm]
        assert len(selected) == 136
        local = []
        for step in range(13, 17):
            rows = [row for row in labels if row['arm'] == arm and row['after_step'] == step]
            assert [row['control'] for row in rows] == list(range(8))
            before = next(row for row in labels if row['arm'] == arm
                          and row['after_step'] == step - 1 and row['control'] == 7)
            after = rows[-1]
            local.append({'step': step, 'before_bilateral': before['valid_grasp_relation'],
                          'bilateral_samples': [row['valid_grasp_relation'] for row in rows],
                          'center_rise_mm': after['bottle_center_mm'][2] - before['bottle_center_mm'][2],
                          'bottom_before_mm': before['bottle_bottom_mm'], 'bottom_after_mm': after['bottle_bottom_mm'],
                          'gripper_contact_row_count': sum(len(row['contacts']) for row in rows)})
        b, a = [next(row['sensor'] for row in endpoints if row['arm'] == arm and row['after_step'] == step)
                for step in (12, 13)]
        delta = np.asarray(a['returned_observations']['robot0_eef_pos']) - b['returned_observations']['robot0_eef_pos']
        rotation = np.asarray(a['tcp_fk_rotation_world']) @ np.asarray(b['tcp_fk_rotation_world']).T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1, 1))))
        qa, qb = [np.asarray(x['returned_observations']['robot0_eef_quat']) for x in (a, b)]
        obs_angle = float(np.degrees(2 * np.arccos(np.clip(abs(np.dot(qa, qb)) /
                          (np.linalg.norm(qa) * np.linalg.norm(qb)), -1, 1))))
        expected_grip = 1. if arm == 'close' else -1.
        assert all(row['sensor']['command'][-1] == expected_grip for row in selected if row['step'] == 13)
        result['arms'][arm] = {'local_slices': local, 'step13_hold_check': {
            'returned_tcp_delta_mm': (1000 * delta).tolist(),
            'exact_validator_translation_norm_mm': float(1000 * np.linalg.norm(delta)),
            'passes_hold_translation_1_5mm': bool(np.linalg.norm(delta) <= .0015),
            'grip_commands_match': True, 'returned_quaternion_rotation_deg': obs_angle,
            'archived_scratch_FK_rotation_deg': angle, 'exact_cached_site_matrix_rotation_deg': None,
            'exact_full_AtomicExecutor_validation': 'unavailable; cached site matrices were not archived'}}
    result['scope'] = 'stored-evidence arithmetic only; no physics, FK, projection, inference, or controller change'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.source)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'source_hashes': result['source_hashes']}))

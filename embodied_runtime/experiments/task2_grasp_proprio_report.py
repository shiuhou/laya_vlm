"""Descriptive own-joint telemetry from the completed four-cell sensor archive.

No contact labels, images, simulator, learned model or holding classifier are read.
This is an exploratory report, not a prospectively registered decision rule.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .records import file_hash
from .task2_point_anchor_retention_adapter import CONDITIONS, validated_manifest


def summarize(matrix: Path):
    cells = {}
    for condition in CONDITIONS:
        directory = matrix / condition
        manifest = directory / 'sensor-captures.json'
        seal_path = directory / 'sensor-seal.json'
        seal = json.loads(seal_path.read_text())
        if file_hash(manifest) != seal['sha256']['sensor-captures.json']:
            raise ValueError('Sensor manifest differs from its completed source seal')
        rows = json.loads(manifest.read_text())
        reference = validated_manifest(rows, condition)
        extracted = []
        for row in rows[reference:]:
            own = row['own_observations']
            qpos = own['robot0_gripper_qpos']
            qvel = own['robot0_gripper_qvel']
            if len(qpos) != 2 or len(qvel) != 2:
                raise ValueError('Expected the two original signed prismatic joint fields')
            extracted.append({
                'capture_id': row['capture_id'], 'phase': row['phase'],
                'after_step': row['after_step'], 'control': row['control'],
                'capture_read_sim_time_s': row['capture_read_sim_time_s'],
                'exact_observation_sample_time_s': row['exact_observation_sample_time_s'],
                'own_source': row['own_source'],
                'gripper_qpos_m': qpos, 'gripper_qvel_m_s': qvel,
                'signed_joint_separation_m': qpos[0] - qpos[1],
                'signed_joint_separation_rate_m_s': qvel[0] - qvel[1],
                'tcp_world_m': own['robot0_eef_pos'],
            })
        if len(extracted) != 17:
            raise ValueError('Preclose and all sixteen suffix control endpoints required')
        cells[condition] = {
            'source_manifest_sha256': file_hash(manifest),
            'source_seal_sha256': file_hash(seal_path),
            'rows': extracted,
        }
    return {
        'version': 'task2-grasp-proprio-descriptive-v1', 'source_matrix': str(matrix.resolve()),
        'generator_sha256': file_hash(__file__), 'evaluator_read': False,
        'provenance': 'saved proprioception', 'holding_inferred': False,
        'physical_pad_gap_inferred': False, 'new_threshold': None,
        'warning': 'Joint-coordinate separation is not a measured object width or pad-surface clearance.',
        'cells': cells,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = summarize(args.matrix)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()

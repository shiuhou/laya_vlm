"""Stored-only evaluator summary; no sensor feature, decision or simulator calls."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root, output):
    result = {'source': str(root.resolve()), 'generator_sha256': sha(Path(__file__)),
              'provenance': 'simulator oracle evaluation of recorded transitions',
              'continuous_relation_claim': False, 'cells': {}}
    for condition in ('neck-present', 'neck-away'):
        directory = root / condition
        journal = directory / 'episodes.jsonl'
        native = defaultdict(list)
        groups = None
        for line in journal.open():
            row = json.loads(line)
            data = row['data']
            if row['kind'] == 'initial_frame_gate':
                groups = {k: set(v) for k, v in data['groups_evaluator_only'].items()}
            if row['kind'] not in ('native_before', 'native_after') or data['step'] < 29:
                continue
            assert groups is not None and data['step'] in (29, 30, 31)
            pads, strong_pads, other_forces, table_forces = set(), set(), [], []
            for contact in data['contacts']:
                a, b = contact['geom_ids']
                force = contact['normal_force_N']
                if a in groups['bottle']:
                    a, b = b, a
                if b not in groups['bottle']:
                    continue
                if a in groups['pads']:
                    pads.add(a)
                    if force > .05:  # Existing descriptive threshold; raw rows are retained too.
                        strong_pads.add(a)
                elif a in groups['robot']:
                    other_forces.append(force)
                if 'table_collision' in contact['geom_names']:
                    table_forces.append(force)
            native[(data['step'], row['kind'])].append({
                'raw_bilateral': len(pads) == 2, 'strong_bilateral': len(strong_pads) == 2,
                'raw_other_robot': bool(other_forces), 'strong_other_robot': any(f > .05 for f in other_forces),
                'maximum_other_robot_force_N': max(other_forces, default=0.),
                'raw_table': bool(table_forces), 'strong_table': any(f > .05 for f in table_forces)})
        labels_path = directory / 'evaluator-only/labels.json'
        labels = json.loads(labels_path.read_text())
        phases = {}
        for step, phase in enumerate(('close_or_hold', 'additional_close', 'lift'), 29):
            endpoints = [r['label'] for r in labels if r['step'] == step]
            assert len(endpoints) == 8
            phases[phase] = {'end_center_mm': endpoints[-1]['bottle_center_mm'],
                             'end_bottom_mm': endpoints[-1]['bottle_bottom_mm'],
                             'official_success': endpoints[-1]['official_success'],
                             'grasp_relation_endpoints': [r['valid_grasp_relation'] for r in endpoints]}
            for stage in ('native_before', 'native_after'):
                rows = native[(step, stage)]
                assert len(rows) == 200
                summary = {k: sum(r[k] for r in rows) for k in rows[0]
                           if k != 'maximum_other_robot_force_N'}
                summary.update(samples=len(rows), maximum_other_robot_force_N=max(
                    r['maximum_other_robot_force_N'] for r in rows))
                phases[phase][stage] = summary
        result['cells'][condition] = {'journal_sha256': sha(journal), 'labels_sha256': sha(labels_path),
            'phases': phases,
            'lift_center_rise_mm': phases['lift']['end_center_mm'][2] - phases['additional_close']['end_center_mm'][2],
            'lift_bottom_rise_mm': phases['lift']['end_bottom_mm'] - phases['additional_close']['end_bottom_mm']}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))

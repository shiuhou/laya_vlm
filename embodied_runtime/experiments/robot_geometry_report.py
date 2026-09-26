"""Read-only verification and robot-only plotting of sealed FK probe artifacts.

No simulator, full archived state, scene geometry, controller or policy is used.
This is post-result reporting; it does not alter the frozen experiment criteria.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hull(points):
    """Convex enclosure of a finite vertex projection; not reconstructed faces."""
    points = sorted(set(map(tuple, points)))
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves = []
    for sequence in (points, reversed(points)):
        half = []
        for point in sequence:
            while len(half) >= 2 and cross(half[-2], half[-1], point) <= 0:
                half.pop()
            half.append(point)
        halves.append(half[:-1])
    return np.asarray(halves[0]+halves[1])


def report(source, output):
    source, output = Path(source), Path(output)
    def read(name):
        return json.loads((source/name).read_text())
    checks = []
    def check(name, condition):
        if not condition:
            raise ValueError(f'Report audit failed: {name}')
        checks.append(name)
    artifacts = read('artifacts.json')
    for name, expected in artifacts.items():
        check('artifact hash: '+name, digest(source/name) == expected)
    manifest, calibration = read('manifest.json'), read('robot-calibration.json')
    request, estimates = read('estimator-input.json'), read('sensor-estimates.json')
    packets, seal = read('encoder-packets.json'), read('sensor-estimates-seal.json')
    summary, setup = read('summary.json'), read('static-setup.json')
    truth = read('evaluator-recomputed-poses.json')['states']
    check('clean frozen producer', not manifest['code']['dirty_status'])
    check('sealed estimator output', seal['sha256'] == digest(source/'sensor-estimates.json'))
    check('sealed sanitized input', seal['input_sha256'] == digest(source/'estimator-input.json'))
    check('seal before evaluator', seal['evaluator_transforms_computed_yet'] is False)
    check('request fields', set(request) == {'calibration', 'joint_packets'})
    check('calibration identity', request['calibration'] == calibration)
    check('calibration fields', set(calibration) == {'version', 'bodies', 'sites', 'geometries'})
    body_names = set()
    joints = {}
    for body in calibration['bodies']:
        check('parent-first body: '+body['name'], body['parent'] is None or body['parent'] in body_names)
        body_names.add(body['name'])
        for joint in body['joints']:
            check('unique joint: '+joint['name'], joint['name'] not in joints)
            joints[joint['name']] = joint['kind']
    check('seven hinges two slides', sorted(joints.values()) == ['hinge']*7+['slide']*2)
    for family in ('sites', 'geometries'):
        for item in calibration[family]:
            check('robot-owned '+item['name'], item['body'] in body_names)
    for name, packet in request['joint_packets'].items():
        check('nine scalar own joints: '+name, set(packet) == set(joints)
              and all(np.asarray(v).shape == () and np.isfinite(v) for v in packet.values()))
    for name, packet in packets['nonrobot_state_poison_extracted'].items():
        original = name.split('/')[0]
        check('poison packet equality: '+name, packet == packets['original'][original])
        check('poison output equality: '+name, estimates[name] == estimates[original])
    # Numeric dict equality alone does not distinguish signed zeros. Compare the
    # parsed float64 bit patterns too before reporting bitwise identity.
    def numbers(value):
        if isinstance(value, dict):
            return [n for k in sorted(value) for n in numbers(value[k])]
        if isinstance(value, list):
            return [n for v in value for n in numbers(v)]
        return [value] if isinstance(value, (int, float)) else []
    for name in packets['nonrobot_state_poison_extracted']:
        original = name.split('/')[0]
        check('poison float64 bit identity: '+name,
              np.asarray(numbers(estimates[name]), dtype=np.float64).tobytes()
              == np.asarray(numbers(estimates[original]), dtype=np.float64).tobytes())
    recomputed_errors = {}
    for row in summary['comparison_rows']:
        predicted = estimates[row['state']][row['family']][row['name']]
        expected = truth[row['state']][row['family']][row['name']]
        for field, recorded in row['max_abs_error'].items():
            error = float(np.max(np.abs(np.asarray(predicted[field])-expected[field])))
            check('comparison '+row['state']+'/'+row['name']+'/'+field,
                  error == recorded and error <= summary['tolerance'])
            recomputed_errors[field] = max(recomputed_errors.get(field, 0), error)
    for name, recorded in summary['positive_own_joint_max_geometry_change_m'].items():
        error = max(float(np.max(np.abs(np.asarray(geom['vertices_world_m'])
                    - estimates['pre_action25']['geometries'][geom_name]['vertices_world_m'])))
                    for geom_name, geom in estimates[name]['geometries'].items())
        check('positive dependency: '+name, error == recorded and error > 1e-8)
    half_steps = read('constructor-half-step-evaluator-only.json')['setup_calls']
    check('one recorded constructor half-step', len(half_steps) == setup['constructor_mj_step1_calls'] == 1)
    check('constructor time and joints unchanged', all(r['before'] == r['after'] for r in half_steps))
    check('zero constructor time', setup['sim_time_s'] == 0)
    check('zero dynamic controls', summary['physics_controls_executed'] == 0 and not summary['physics_step_calls'])
    check('probe passed', summary['passed'])
    tcp_name = 'gripper0_grip_site'
    selected = estimates['pre_action25']
    tcp = np.asarray(selected['sites'][tcp_name]['position_world_m'])
    rotation = np.asarray(selected['sites'][tcp_name]['rotation_world'])
    projected = {name:(np.asarray(g['vertices_world_m'])-tcp)@rotation*1000
                 for name,g in selected['geometries'].items()}
    union = np.concatenate(list(projected.values()))
    derived = {
        'raw_directory': str(source), 'producer_commit': manifest['code']['commit'],
        'protocol_sha256': manifest['protocol_sha256'], 'source_sha256': manifest['source_sha256'],
        'raw_artifact_hashes': artifacts, 'artifacts_manifest_sha256': digest(source/'artifacts.json'),
        'passed': True, 'post_result_audit_check_count':len(checks),
        'state_metadata':packets['metadata'], 'exported_robot_counts':setup['exported_robot_counts'],
        'own_joint_kinds':joints, 'own_joint_count':len(joints),
        'comparison_item_rows':len(summary['comparison_rows']),
        'max_errors_recomputed':recomputed_errors, 'frozen_tolerance':summary['tolerance'],
        'poison_variant_count':len(packets['nonrobot_state_poison_extracted']),
        'poison_output_float64_bits_equal':True,
        'positive_max_vertex_coordinate_changes_m':summary['positive_own_joint_max_geometry_change_m'],
        'cached_tcp_difference_norms_m':{k:float(np.linalg.norm(v)) for k,v in
                                        summary['recomputed_tcp_minus_archived_returned_tcp_m'].items()},
        'cached_tcp_sample_times_unknown':True,
        'base_calibration':summary['base_calibration'],
        'pre_action25_tcp_world_m':tcp.tolist(),
        'pre_action25_gripper_bounds_tcp_frame_mm':[union.min(axis=0).tolist(),union.max(axis=0).tolist()],
        'pre_action25_geometries':{name:{'bounds_tcp_frame_mm':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],
                                        'bounds_world_m':selected['geometries'][name]['aabb_world_m'],
                                        'vertex_count':len(v)} for name,v in projected.items()},
        'constructor_mj_step1_calls':len(half_steps), 'constructor_time_qpos_qvel_unchanged':True,
        'dynamic_controls_or_integration_steps':0,
        'scope':'same-qpos FK correctness and input dependency; known static robot calibration',
        'limitations':['simulator-state-derived encoder analogues, not independent physical sensors',
                      'shared static model; physical calibration/model accuracy unvalidated',
                      'fresh MjData evaluator does not recover original cached contact-time transforms',
                      'gripper collision proxy extents only; arm link collision extents untested',
                      'no scene, contact, safety, action admission or policy claim'],
    }
    output.mkdir(parents=True, exist_ok=True)
    with (output/'robot_geometry_observability_summary.json').open('x') as stream:
        json.dump(derived, stream, indent=2, allow_nan=False); stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 5))
    fig.subplots_adjust(bottom=.23, top=.80, wspace=.35)
    colors = ['#64748b','#0891b2','#164e63','#ea580c','#7c2d12']
    for ax, (a,b) in zip(axes, [(0,2),(0,1),(1,2)]):
        for (name, vertices), color in zip(projected.items(), colors):
            polygon = hull(vertices[:, [a,b]])
            label = name.removeprefix('gripper0_').removesuffix('_collision').replace('_',' ')
            ax.fill(polygon[:,0],polygon[:,1],facecolor=color,edgecolor=color,alpha=.45,label=label)
        ax.plot(0,0,'k+',ms=10,mew=2,label='TCP origin')
        ax.set(xlabel=f'TCP {"xyz"[a]} (mm)',ylabel=f'TCP {"xyz"[b]} (mm)',aspect='equal')
        ax.grid(alpha=.2)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center',
               bbox_to_anchor=(.5,.025), ncol=6, frameon=False, fontsize=9)
    fig.suptitle('Robot-only gripper collision proxies before action 25\n'
                 'Projected vertex hulls in the TCP frame; no scene geometry',fontsize=13)
    fig.savefig(output/'robot_geometry_observability_gripper.png',dpi=180)
    plt.close(fig)
    print(json.dumps({'post_result_audit_checks':len(checks), 'max_errors':recomputed_errors,
                      'portable_summary':str(output/'robot_geometry_observability_summary.json')},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report(args.source, args.output)

"""Check saved target-region tensor using fixed original facets; no FK or search."""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

from task2_box_evidence_audit import read, require, sha

FREEZE = '22fa806d0221c0aa2f663841ffd80f3ba69d2ff2'
GEOMS = ['gripper0_hand_collision', 'gripper0_finger1_collision', 'gripper0_finger1_pad_collision',
         'gripper0_finger2_collision', 'gripper0_finger2_pad_collision']


def audit(sources):
    run = sources/'task2-finite-gap-target-region-run-01'
    original = sources/'task2-finite-gap-control-run-01'
    manifest, request = read(run/'manifest.json'), read(run/'request.json')
    preflight_path = sources/'task2-finite-gap-target-region-preflight-01.json'
    require(sha(preflight_path) == manifest['preflight_sha256'] == '1c44b7533e96390efcb26f244fbd10239c6cd00b7220f10e0853bab80dfd9923', 'actual reviewed source-only preflight')
    preflight = read(preflight_path)
    require(all(manifest[k] == v for k,v in preflight.items() if k != 'python'), 'complete preflight provenance')
    require(manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'clean reviewed freeze')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_finite_gap_target_region.py'] == '8e1293e35df80d85c3f09b489bfc33526eda9219c4b10872d06ef2b9ecbca944', 'reviewed worker')
    require(sha(run/'request.json') == manifest['request_sha256'], 'sanitized request seal')
    require(sha(run/'protocol.md') == manifest['protocol_sha256'] == '99199e30289ce5f68319afad801fde6f78a12a6f69152eceb4587350fee555d9', 'protocol identity')
    require(sha(run/'review.md') == manifest['review_sha256'] and FREEZE in (run/'review.md').read_text(), 'prospective review receipt')
    require(not (run/'failure.json').exists(), 'no ignored partial failure')
    for name,digest in manifest['finite_gap_source_sha256'].items():
        require(sha(original/name) == digest, 'sealed finite-gap source unchanged')
    for name,digest in manifest['source_sha256'].items():
        require(sha(sources/'task2-endpoint-containment-veto-run-01'/name) == digest, 'original terminal source unchanged')
    old_request, old_result = read(original/'request.json'), read(original/'features/result.json')
    reference = {k:old_result[k] for k in ('finite_gap_lower_site_m','finite_gap_upper_site_m','calibrated_pad_vertices_site_m','mount')}
    require(request == {**{k:old_request[k] for k in ('point_P_world_m','own_packet','calibration','full_support')},'sealed_geometry_reference':reference}, 'exact fixed sensor-only request; no prior scores/outcome labels')
    seal = read(run/'feature-seal.json')
    require(set(seal) == {'features/result.json','features/containment.npz'}, 'complete feature seal')
    for name,digest in seal.items():
        require(sha(run/name) == digest, 'feature bytes match seal')
    result = read(run/'features/result.json')
    require(result['geometry'] == reference and result['own_packet'] == request['own_packet'] and result['point_P_world_m'] == request['point_P_world_m'], 'fixed prior gap/mount/own/P exactly reproduced')
    require(result['geometry_order'] == GEOMS and result['tensor_shape'] == [8,1340,5], 'all indexed corners/support/proxies')
    require(result['halfspace_numeric_tolerance'] == 1e-12 and result['physical_margin_m'] == 0, 'unchanged numerical convention without physical margin')
    require(result['no_pose_selected'] and result['no_adaptive_refinement'] and result['not_entire_discrete_rule_STOP_set'] and not result['one_step_scores_recomputed'] and result['model_physics_render_calls'] == 0 and not result['automatic_extension'], 'bounded offline region scope')
    arrays_path = run/'features/containment.npz'
    require(sha(arrays_path) == result['containment_artifact_sha256'], 'tensor result seal')
    with np.load(arrays_path, allow_pickle=False) as a:
        require(set(a.files) == {'inside','hypothetical_TCP_world_m','gap_corners_site_m','endpoint_choices'}, 'complete tensor schema')
        inside, positions, gap_corners, choices = [a[k].copy() for k in ('inside','hypothetical_TCP_world_m','gap_corners_site_m','endpoint_choices')]
    require(inside.shape == (8,1340,5) and inside.dtype == np.bool_, 'full boolean tensor')
    low, high = np.asarray(reference['finite_gap_lower_site_m']), np.asarray(reference['finite_gap_upper_site_m'])
    rotation = np.asarray(reference['mount']['returned_site_rotation_world'])
    point, tcp = np.asarray(request['point_P_world_m']), np.asarray(request['own_packet']['robot0_eef_pos'])
    require(low.shape == high.shape == point.shape == tcp.shape == (3,) and np.all(low <= high), 'nonempty finite gap dimensions')
    require(np.allclose(rotation.T@rotation,np.eye(3),rtol=0,atol=1e-10) and np.isclose(np.linalg.det(rotation),1.,rtol=0,atol=1e-10), 'proper fixed rotation')
    expected_choices = np.asarray(list(product((0,1),repeat=3)),dtype=int)
    expected_gap = (1-expected_choices)*low+expected_choices*high
    expected_positions = point-expected_gap@rotation.T
    require(np.array_equal(choices,expected_choices) and np.array_equal(gap_corners,expected_gap) and np.array_equal(positions,expected_positions), 'all eight asymmetric rotated target corners exactly')
    residual = float(np.max(np.abs((point-positions)@rotation-gap_corners)))
    require(residual == result['maximum_target_relation_residual_m'] and residual <= 1e-12, 'inverse target-region relation')
    require(len(np.unique(positions,axis=0)) == result['unique_target_corner_count'], 'indexed versus distinct corners')
    full = request['full_support']
    points = np.asarray([r['position_world_m'] for r in full])
    require(points.shape == (1340,3) and np.isfinite(points).all(), 'full fixed support')
    # One original facet system per proxy. Only query points shift; no translated hull refits.
    independent = np.zeros_like(inside)
    minimum_pair_slack = np.empty((1340,5))
    facet_counts = {}
    for j,name in enumerate(GEOMS):
        vertices = np.asarray(old_request['original_proxy_vertices_world_m'][name])
        hull = ConvexHull(vertices)
        equations = hull.equations
        facet_counts[name] = len(equations)
        minimum = np.full(1340,np.inf)
        for i,position in enumerate(positions):
            shifted = points-(position-tcp)
            signed_slack = -(shifted@equations[:,:3].T+equations[:,3])
            independent[i,:,j] = np.all(signed_slack >= -1e-12,axis=1)
            minimum = np.minimum(minimum,signed_slack.min(axis=1))
            require(result['corners'][i]['proxy_vertices_world_m'][name] == (vertices+(position-tcp)).tolist(), 'every translated vertex set from exact saved current proxy')
        minimum_pair_slack[:,j] = minimum
    require(np.array_equal(independent,inside), 'all53600 memberships match independent fixed-facet calculation')
    for i,row in enumerate(result['corners']):
        require(row['index'] == i and row['gap_endpoint_choices'] == choices[i].tolist() and row['gap_corner_site_m'] == gap_corners[i].tolist() and row['hypothetical_TCP_world_m'] == positions[i].tolist(), 'saved corner identity')
        require(row['contained_point_union_count'] == int(inside[i].any(axis=1).sum()) and row['any_containment'] == bool(inside[i].any()), 'each separate-solid union count')
        require(set(row['per_proxy']) == set(GEOMS), 'all proxies retained')
        for j,name in enumerate(GEOMS):
            indices = np.flatnonzero(inside[i,:,j]).tolist()
            require(row['per_proxy'][name] == {'contained_point_count':len(indices),'full_support_indices':indices}, 'all full-support index lists')
    pairs = np.argwhere(independent.all(axis=0))
    witnesses = [{'full_support_index':int(p),'proxy':GEOMS[j],**full[p]} for p,j in pairs]
    require(result['common_same_point_same_proxy_witnesses'] == witnesses, 'same point and same proxy across ALL8, no union substitution')
    certificate = 'entire_target_region_excluded' if len(pairs) else 'no_common_witness_certificate'
    require(result['certificate'] == certificate and result['negative_certificate_is_inconclusive'] == (not bool(len(pairs))) and result['all_eight_corner_unions_positive'] == bool(inside.any(axis=(1,2)).all()), 'certificate and weaker union result remain distinct')
    margins = [{'full_support_index':int(p),'pixel_xy':full[p]['pixel_xy'],'proxy':GEOMS[j],
                'minimum_signed_corner_facet_slack_m':float(minimum_pair_slack[p,j]),
                'strictly_inside_all_corners':bool(minimum_pair_slack[p,j] > 0.)} for p,j in pairs]
    return {'status':'pass','freeze':FREEZE,'feature_seal_sha256':sha(run/'feature-seal.json'),
        'result_sha256':sha(run/'features/result.json'),'tensor_sha256':sha(arrays_path),
        'tensor_entries_checked':int(inside.size),'corner_union_counts':[r['contained_point_union_count'] for r in result['corners']],
        'certificate':certificate,'common_same_pair_count':len(pairs),'fixed_facets_per_proxy':facet_counts,
        'all_common_pairs_strictly_inside':bool(len(margins)) and all(m['strictly_inside_all_corners'] for m in margins),
        'minimum_common_pair_corner_slack_m':min((m['minimum_signed_corner_facet_slack_m'] for m in margins),default=None),
        'maximum_common_pair_corner_slack_m':max((m['minimum_signed_corner_facet_slack_m'] for m in margins),default=None),
        'common_pair_slacks':margins,'maximum_target_relation_residual_m':residual,
        'limits':['all saved memberships checked with one fixed facet system per proxy and shifted stored points',
                  'stored geometry and scalar algebra only; no FK/projection/model/physics/render rerun or pose search',
                  'strict facet slack characterizes frozen geometric calculation, not physical safety margin or calibrated uncertainty',
                  'same-pair convexity concerns exact zero-distance region at fixed orientation/jaws, not entire discrete STOP set or all orientations']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources',type=Path,default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = audit(args.sources)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='common_pair_slacks'},indent=2))

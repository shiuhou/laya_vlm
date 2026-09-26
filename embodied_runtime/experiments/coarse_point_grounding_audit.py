"""Post-run oracle-only single-ray identity audit of recorded coarse POINT calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .coarse_point_probe import admit_point
from .point_grounding_probe import parse_grounding, generation_audit
from .records import code_identity, file_hash, load_records, repository_identity, package_directory, versions
from .target_referent import resolve_handle_geom, surface_centroid

PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/coarse_point_grounding_audit.md'


def pixel_ray(pixel, intrinsics, camera_to_world):
    k, t = np.asarray(intrinsics), np.asarray(camera_to_world)
    surface_centroid(np.ones((1,1)), np.ones((1,1), bool), k, t)
    x,y = pixel
    camera_ray = np.array([(x+.5-k[0,2])/k[0,0], (y+.5-k[1,2])/k[1,1], 1.])
    norm = float(np.linalg.norm(camera_ray))
    return (np.ascontiguousarray(t[:3,3], dtype=np.float64),
            np.ascontiguousarray(t[:3,:3]@(camera_ray/norm), dtype=np.float64), norm)


def ray_measurement(origin, direction, norm, distance, hit, designated, sensor_depth, identity):
    valid_hit = hit >= 0 and 0 <= distance <= 5.
    result = {'source':'oracle_sim', 'privileged':True,
        'ray_origin_world_m':origin.tolist(), 'ray_direction_world_unit':direction.tolist(),
        'ray_range_m':float(distance), 'raw_hit_geom_id':int(hit),
        'designated_handle_geom_id':int(designated), 'sensor_optical_depth_m':float(sensor_depth),
        'membership':'unknown_no_ray_hit', 'target_member':None,
        'ray_surface_world_m':None, 'ray_optical_depth_m':None,
        'sensor_minus_ray_optical_depth_mm':None, 'absolute_depth_residual_mm':None,
        **identity}
    if valid_hit:
        depth = distance/norm
        result.update(target_member=hit==designated,
            membership='designated_top_handle' if hit==designated else 'other_visual_geom',
            ray_surface_world_m=(origin+direction*distance).tolist(), ray_optical_depth_m=float(depth),
            sensor_minus_ray_optical_depth_mm=float((sensor_depth-depth)*1000),
            absolute_depth_residual_mm=float(abs(sensor_depth-depth)*1000))
        if hit != designated and (identity.get('mesh_name') or '').endswith('_handle_vis') and (identity.get('body_name') or '').startswith('wooden_cabinet_'):
            result['membership'] = 'other_cabinet_handle'
    return result


def unique_rows(records, kind, key):
    result = {}
    for row in records:
        if row['kind'] != kind:
            continue
        value = row['data'][key]
        if value in result:
            raise ValueError(f'duplicate {kind}/{key}')
        result[value] = row
    return result


def evaluate(source, output):
    from ..adapters.libero import LiberoWorldBackend
    import mujoco
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError('new evaluator artifact required')
    records, errors = load_records(source/'episodes.jsonl')
    if errors:
        raise ValueError('invalid source evidence chain')
    start = next(r['data'] for r in records if r['kind']=='run_start')
    config = start['resolved_config']
    if config['version'] != 'fresh-point-coarse-approach-v1' or config['seed'] != 1 or config['init_state_id'] != 0:
        raise ValueError('unexpected source condition')
    capture = unique_rows(records,'vision_capture','capture_seq')
    completed = unique_rows(records,'point_call_completed','capture_seq')
    started = unique_rows(records,'point_call_started','capture_seq')
    decisions = unique_rows(records,'decision_boundary','capture_seq')
    paused = unique_rows(records,'paused_state_check','step')
    backend = LiberoWorldBackend.from_task('top_drawer', seed=1, init_state_id=0, render=False,
        libero_root=config['libero_root'], config_dir=config['config_dir'])
    try:
        import jev_libero.world
        import libero
        import robosuite.environments.base
        w, sim = backend.world, backend.world.env.sim
        env_repos = {'jev':repository_identity(package_directory(jev_libero.world)),
                     'libero':repository_identity(package_directory(libero))}
        expected_repos = next(r['data']['environment_repositories'] for r in records
            if r['kind']=='manifest_update' and 'environment_repositories' in r['data'])
        if env_repos != expected_repos:
            raise ValueError('evaluator environment repository identity mismatch')
        if w.config != next(r['data']['task_config'] for r in records if r['kind']=='environment'):
            raise ValueError('task configuration changed')
        groups = np.asarray(mujoco.MjvOption().geomgroup,dtype=np.uint8).copy()
        flags = {'render_collision_mesh':bool(w.env.env.render_collision_mesh),
                 'render_visual_mesh':bool(w.env.env.render_visual_mesh)}
        groups[0], groups[1] = int(flags['render_collision_mesh']), int(flags['render_visual_mesh'])
        if groups[0] or not groups[1]:
            raise ValueError('visual mesh ray audit requires visual-only render flags')
        designated = resolve_handle_geom(w)
        rows = []
        for seq, capture_row in capture.items():
            c = capture_row['data']
            artifact = source/c['artifact']
            if file_hash(artifact) != c['artifact_sha256']:
                raise ValueError('capture artifact changed')
            row = {'capture_seq':seq, 'capture_record_id':capture_row['record_id'],
                'frame_sha256':c['artifact_sha256'], 'source':'oracle_sim_evaluator', 'privileged':True}
            rows.append(row)
            if seq not in completed or seq not in started:
                row.update(status='unknown_missing_call'); continue
            call = completed[seq]['data']
            with np.load(artifact) as data:
                frame = {key:data[key].copy() for key in data.files}
            parsed = parse_grounding(call['raw_output'],frame['rgb'].shape[1],frame['rgb'].shape[0])
            a = call['generation_audit']
            audit = generation_audit(a['actual_generated_token_ids'],len(started[seq]['data']['input_token_ids']),
                a['model_max_length'],a['eos_token_id'])
            if parsed != call['parsed'] or audit != a:
                raise ValueError('POINT parsing/token audit does not reconstruct')
            row.update(raw_output=call['raw_output'], parsed=parsed, generation_audit=audit)
            try:
                admitted = admit_point(parsed,audit,frame)
            except ValueError as exc:
                row.update(status='unknown_not_admitted', reason=str(exc)); continue
            if seq not in decisions:
                row.update(status='unknown_missing_decision_state'); continue
            decision = decisions[seq]['data']
            if admitted != decision['admitted']:
                raise ValueError('admitted point does not reproduce')
            step = decision['step']
            if step not in paused:
                row.update(status='unknown_missing_capture_state'); continue
            p = paused[step]['data']
            if not p['unchanged'] or p['before'] != p['after']:
                raise ValueError('source capture state was not unchanged')
            sim.set_state_from_flattened(np.asarray(p['before']))
            sim.forward()
            if not np.array_equal(sim.get_state().flatten(),p['before']):
                raise ValueError('restored flattened state differs')
            if not np.isclose(float(w.data.time),c['capture_sim_time'],atol=1e-10,rtol=0):
                raise ValueError('restored time does not match capture')
            origin,direction,norm = pixel_ray(admitted['sample_pixel_xy'],frame['intrinsics'],frame['camera_to_world'])
            hit, distance = np.full(1,-1,np.int32), np.full(1,-1.,np.float64)
            before = sim.get_state().flatten().copy()
            mujoco.mj_multiRay(w.model,w.data,origin,direction,groups,1,-1,hit,distance,None,1,5.)
            if not np.array_equal(before,sim.get_state().flatten()):
                raise ValueError('ray evaluator mutated flattened state')
            g = int(hit[0])
            identity = {'geom_name':None,'body_name':None,'mesh_name':None}
            if g >= 0:
                identity['geom_name'] = mujoco.mj_id2name(w.model,mujoco.mjtObj.mjOBJ_GEOM,g)
                identity['body_name'] = mujoco.mj_id2name(w.model,mujoco.mjtObj.mjOBJ_BODY,int(w.model.geom_bodyid[g]))
                if w.model.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
                    identity['mesh_name'] = mujoco.mj_id2name(w.model,mujoco.mjtObj.mjOBJ_MESH,int(w.model.geom_dataid[g]))
            row.update(status='evaluated', boundary=step, capture_sim_time=c['capture_sim_time'],
                sample_pixel_xy=admitted['sample_pixel_xy'], sensor_point_world_m=admitted['position_world_m'],
                selected_primitive=decision['selected'], terminal_observation=decision['terminal_observation'],
                **ray_measurement(origin,direction,norm,float(distance[0]),g,designated,admitted['depth_m'],identity))
        evaluated = [r for r in rows if r['status']=='evaluated']
        result = {'version':'coarse-point-postrun-grounding-audit-v1','post_run_evaluator_only':True,
            'source':str(source),'source_episodes_sha256':file_hash(source/'episodes.jsonl'),
            'source_manifest_sha256':file_hash(source/'manifest.json'), 'protocol_sha256':file_hash(PROTOCOL),
            'evaluator_code':code_identity(), 'versions':versions(), 'environment_repositories':env_repos,
            'ray_backend':'mujoco-multiRay-one-ray', 'ray_geomgroups':groups.tolist(), 'ray_cutoff_m':5.,
            'render_flags':flags,'geomgroup_basis':'reconstructed MjvOption defaults + robosuite environment flags',
            'robosuite_render_flag_source_sha256':file_hash(robosuite.environments.base.__file__),
            'designated_handle_geom_id':designated, 'rows':rows,
            'summary':{'captures':len(rows),'evaluated':len(evaluated),
                'target_hits':sum(r.get('target_member') is True for r in rows),
                'other_geometry_hits':sum(r.get('target_member') is False for r in rows),
                'unknown':sum(r.get('target_member') is None for r in rows),
                'membership_counts':{key:sum(r.get('membership')==key for r in rows)
                    for key in sorted({r['membership'] for r in evaluated})}},
            'limitations':['shared calibration not independently verified',
                'pixel-center ray differs from antialiased raster boundary coverage',
                'flattened geometry reconstruction is not controller/execution replay',
                'correct referent surface is not grasp feasibility or collision safety']}
        with output.open('x') as stream:
            json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
        return result
    finally:
        backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    result = evaluate(args.source,args.output)
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':
    main()

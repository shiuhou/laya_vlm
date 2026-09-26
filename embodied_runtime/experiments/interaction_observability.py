"""Frozen native-prefix sensor diagnostic; no runtime holding estimator."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image

from .records import code_identity, file_hash, jsonable, versions, repository_identity

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / 'docs/research/interaction_observability_protocol.md'
SOURCE = ROOT / 'docs/evidence/privileged_reference/task2_valid_interaction_gate_failure.jsonl'
SOURCE_SHA256 = '6d2b9d347c4fe0576ab7400e4dd0f1995da09ed29f0900fca564ca483d281ce3'
ARMS = ('close', 'open_hold')
OBS_KEYS = ('robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos', 'robot0_gripper_qvel')


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(jsonable(value), stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def prefix(arm):
    if arm not in ARMS or file_hash(SOURCE) != SOURCE_SHA256:
        raise ValueError('condition or archived source differs')
    rows = [json.loads(line) for line in SOURCE.read_text().splitlines()]
    rows = [r for r in rows if r['kind'] == 'step']
    if [r['step'] for r in rows] != list(range(22)):
        raise ValueError('source step sequence differs')
    actions = [r['choice'] for r in rows[:17]]
    if actions[13:] != ['close', 'z+40mm', 'z+40mm', 'z+40mm']:
        raise ValueError('registered grasp/lift prefix differs')
    if arm == 'open_hold':
        actions[13] = 'hold'
    return actions


def validate_seed(seed, image_sha256, shape):
    if set(seed) != {'image_sha256', 'provenance', 'points'}:
        raise ValueError('unexpected seed schema')
    if seed['image_sha256'] != image_sha256 or seed['provenance'] != 'human_RGB_only_before_close':
        raise ValueError('seed provenance differs')
    if [p['role'] for p in seed['points']] != ['bottle_landmark_1', 'bottle_landmark_2', 'table_reference']:
        raise ValueError('two bottle landmarks and table reference required')
    h, w = shape[:2]
    for point in seed['points']:
        if set(point) != {'role', 'pixel_xy'}:
            raise ValueError('unexpected seed fields')
        xy = np.asarray(point['pixel_xy'], dtype=float)
        if xy.shape != (2,) or not np.isfinite(xy).all() or not (0 <= xy[0] < w and 0 <= xy[1] < h):
            raise ValueError('seed outside image')
    return seed


class RobotSensors:
    """Robot observations and aggregate physical sensor channels only."""
    def __init__(self, world):
        self.w = world
        self.robot = world.env.robots[0]
        self.scratch = world.mujoco.MjData(world.model)
        force_id = world.env.sim.model.sensor_name2id(self.robot.gripper.important_sensors['force_ee'])
        self.ft_site = int(world.model.sensor_objid[force_id])

    def read(self, obs, command):
        w, robot = self.w, self.robot
        w.mujoco.mj_copyData(self.scratch, w.model, w.data)
        w.mujoco.mj_forward(w.model, self.scratch)
        qpos = np.asarray(w.data.qpos[robot._ref_gripper_joint_pos_indexes]).copy()
        qvel = np.asarray(w.data.qvel[robot._ref_gripper_joint_vel_indexes]).copy()
        raw = {'read_sim_time_s': float(w.data.time), 'wall_time_unix_s': time.time(),
            'physics_timestep_s': float(w.model.opt.timestep), 'command': list(command),
            'returned_observations': {key: np.asarray(obs[key]).tolist() for key in OBS_KEYS},
            'direct_gripper_qpos_m': qpos.tolist(), 'direct_gripper_qvel_mps': qvel.tolist(),
            'joint_aperture_m': float(np.sum(np.abs(qpos))),
            'tcp_fk_world_m': self.scratch.site_xpos[robot.eef_site_id].tolist(),
            'tcp_fk_rotation_world': self.scratch.site_xmat[robot.eef_site_id].reshape(3,3).tolist(),
            'wrist_force_local_N': np.asarray(robot.ee_force).tolist(),
            'wrist_torque_local_Nm': np.asarray(robot.ee_torque).tolist(),
            'wrist_sensor_names': dict(robot.gripper.important_sensors),
            'wrist_frame_site': w.env.sim.model.site_id2name(self.ft_site),
            'wrist_frame_rotation_world_at_read_time': self.scratch.site_xmat[self.ft_site].reshape(3,3).tolist(),
            'wrist_sample_sim_time_s': None, 'returned_observation_sample_times_s': None,
            'holding': None,
            'observable_timers': {key: {'time_since_last_sample_s': value._time_since_last_sample,
                'sampled': value._sampled, 'sampling_rate_Hz': 1. / value._sampling_timestep}
                for key, value in w.env.env._observables.items() if key in OBS_KEYS}}
        # JSON's strict number validation is also a stop-on-nonfinite sensor check.
        json.dumps(jsonable(raw), allow_nan=False)
        return raw


def evaluation(world):
    """Privileged endpoint labels, buffered only; never consumed by sensors/control."""
    f = world.features()
    return {'privileged': True, 'sim_time_s': float(world.data.time),
        'valid_grasp_relation': f['valid_grasp_relation'],
        'bottle_center_mm': f['target_center_mm'], 'bottle_bottom_mm': f['target_bottom_mm'],
        'geometric_finger_gap_mm': f['finger_gap_mm'], 'contacts': f['contacts'],
        'official_success': f['success'], 'state': world.env.sim.get_state().flatten().tolist()}


def capture(world, source, directory, capture_id, metadata, oracle_images):
    before = world.env.sim.get_state().flatten().copy()
    frame = source.capture()
    artifact = f'{capture_id:04d}.npz'
    np.savez_compressed(directory / artifact, **frame)
    Image.fromarray(frame['rgb']).save(directory / f'{capture_id:04d}.png')
    segmentation = world.env.sim.render(width=source.width, height=source.height,
        camera_name=source.camera_name, segmentation=True)
    segmentation = np.asarray(segmentation)[::-1].copy()
    bottle_ids = [i for i in range(world.model.ngeom)
                  if (world.env.sim.model.geom_id2name(i) or '').startswith('wine_bottle_1_')]
    mask = ((segmentation[..., 0] == int(world.mujoco.mjtObj.mjOBJ_GEOM)) &
            np.isin(segmentation[..., 1], bottle_ids))
    oracle_images.append((metadata['arm'], capture_id, mask))
    if not np.array_equal(world.env.sim.get_state().flatten(), before):
        raise RuntimeError('render changed simulator state')
    row = {**metadata, 'capture_id': capture_id, 'artifact': str(directory.name+'/'+artifact),
        'artifact_sha256': file_hash(directory/artifact),
        'rgb_artifact': str(directory.name+f'/{capture_id:04d}.png'),
        'rgb_sha256': file_hash(directory/f'{capture_id:04d}.png'),
        'capture_read_sim_time_s': frame['capture_sim_time'],
        'cached_geometry_sample_time_s': None, 'render_preserves_state': True}
    return frame, row


def collect(args):
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    from ..adapters.libero_rgbd import LiberoRgbdSource
    import jev_libero.world

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'version': 'interaction-observability-v1', 'code': code_identity(),
        'protocol_sha256': file_hash(PROTOCOL), 'source_sha256': file_hash(SOURCE),
        'argv': sys.argv, 'python': sys.executable, 'versions': versions(),
        'jev': repository_identity(Path(jev_libero.world.__file__).parent),
        'environment': {k: os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID')},
        'actions': {arm: prefix(arm) for arm in ARMS},
        'semantic_initialization': 'human_RGB_only_before_close', 'holding': None,
        'wrench_calibration': None, 'policy': False, 'original_control_replay': False,
        'standard_reset_settling_controls': 10, 'seed': 1, 'init_state_id': 0}
    write_json(out/'manifest.json', manifest)
    (out/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    oracle, oracle_images, captures, endpoints = [], [], [], []
    sensor_stream = (out/'sensors.jsonl').open('x')
    seed = None
    reference_prefix = []
    sealed = False

    def sensor_record(row):
        sensor_stream.write(json.dumps(jsonable(row), allow_nan=False)+'\n')
        sensor_stream.flush()
        os.fsync(sensor_stream.fileno())

    try:
        for arm in ARMS:
            backend = WineBottleBottomDrawerAdapter().make_backend(args, render=True)
            w = backend.world
            directory = out/arm
            directory.mkdir()
            source, sensors = LiberoRgbdSource(w), RobotSensors(w)
            capture_id = 0
            try:
                init = sensors.read(w.obs, [0.,0.,0.,0.,0.,0.,-1.])
                endpoints.append({'arm':arm, 'after_step':-1, 'sensor':init})
                oracle.append({'arm':arm, 'after_step':-1, 'control':None, **evaluation(w)})
                frame, meta = capture(w, source, directory, capture_id,
                    {'arm':arm,'after_step':-1,'control':None}, oracle_images)
                captures.append(meta)
                capture_id += 1
                for step, action in enumerate(prefix(arm)):
                    controls = []
                    original_step = w.env.step
                    override = w.env.__dict__.get('step')

                    def observed(command):
                        nonlocal capture_id
                        before = float(w.data.time)
                        result = original_step(command)
                        sensed = sensors.read(result[0], command)
                        if sensed['read_sim_time_s'] <= before:
                            raise RuntimeError('control time failed to advance')
                        control = len(controls)
                        row = {'arm':arm, 'step':step, 'control':control,
                            'primitive':action, 'before_sim_time_s':before, 'sensor':sensed}
                        sensor_record(row)
                        controls.append(row)
                        oracle.append({'arm':arm, 'after_step':step, 'control':control, **evaluation(w)})
                        if step >= 13:
                            _, meta = capture(w, source, directory, capture_id,
                                {'arm':arm,'after_step':step,'control':control}, oracle_images)
                            captures.append(meta)
                            capture_id += 1
                        return result

                    w.env.step = observed
                    try:
                        result = w.execute(action, grip=backend._grip_cmd, record=False)
                    finally:
                        if override is None:
                            w.env.__dict__.pop('step', None)
                        else:
                            w.env.step = override
                    backend._grip_cmd = result['grip']
                    if len(controls) != 8 or result['steps'] != len(controls):
                        raise RuntimeError('unexpected native control count; no continuation')
                    endpoint = {'arm':arm, 'after_step':step, 'sensor':controls[-1]['sensor']}
                    endpoints.append(endpoint)
                    if step <= 12:
                        frame, meta = capture(w, source, directory, capture_id,
                            {'arm':arm,'after_step':step,'control':7}, oracle_images)
                        captures.append(meta)
                        capture_id += 1
                        comparable = {k:v for k,v in endpoint['sensor'].items() if k!='wall_time_unix_s'}
                        same = {'rgb_sha256':meta['rgb_sha256'], 'sensor':comparable}
                        if arm == ARMS[0]:
                            reference_prefix.append(same)
                        elif same != reference_prefix[step]:
                            raise RuntimeError('paired shared RGB/robot prefix differs')
                    if step == 12 and seed is None:
                        Image.fromarray(frame['rgb']).save(out/'seed-required.png')
                        write_json(out/'seed-request.json', {'image_sha256':file_hash(out/'seed-required.png'),
                            'required_provenance':'human_RGB_only_before_close', 'paused_before_step':13,
                            'roles':['bottle_landmark_1','bottle_landmark_2','table_reference']})
                        print(f'SEED_REQUIRED {out}/seed-required.png', flush=True)
                        deadline = time.monotonic()+600
                        while not (out/'seed.json').exists():
                            if time.monotonic()>deadline:
                                raise TimeoutError('RGB-only seed deadline exceeded')
                            time.sleep(.2)
                        seed = validate_seed(json.loads((out/'seed.json').read_text()),
                            file_hash(out/'seed-required.png'), frame['rgb'].shape)
                        write_json(out/'seed-frozen.json', {'seed':seed, 'seed_file_sha256':file_hash(out/'seed.json'),
                            'wall_time_unix_s':time.time(), 'sim_time_s':float(w.data.time),
                            'next_action':action if step!=12 else prefix(arm)[13], 'no_post_close_controls_yet':True})
                    print(json.dumps({'arm':arm, 'completed_step':step, 'primitive':action,
                        'controls':len(controls), 'sim_time_s':float(w.data.time)}), flush=True)
            finally:
                backend.close()
        write_json(out/'captures.json', captures)
        write_json(out/'endpoints.json', endpoints)
        sensor_stream.close()
        sensor_paths = [out/'sensors.jsonl', out/'captures.json', out/'endpoints.json', out/'seed.json']
        sensor_paths += [out/c[key] for c in captures for key in ('artifact','rgb_artifact')]
        write_json(out/'sensor-seal.json', {'wall_time_unix_s':time.time(),
            'sha256':{str(p.relative_to(out)):file_hash(p) for p in sensor_paths},
            'oracle_labels_available_to_seed_or_sensor_estimator':False})
        sealed = True
        oracle_dir = out/'evaluator-only'
        oracle_dir.mkdir()
        write_json(oracle_dir/'labels.json', oracle)
        for arm, capture_id, mask in oracle_images:
            np.save(oracle_dir/f'{arm}-{capture_id:04d}-bottle-mask.npy', mask)
        write_json(out/'completed.json', {'sensor_sealed_before_oracle_write':sealed,
            'controls':len(oracle)-2, 'primitives':34, 'holding':None})
    except BaseException as exc:
        write_json(out/'failure.json', {'type':type(exc).__name__, 'message':str(exc),
            'sensor_sealed':sealed, 'no_retry':True})
        raise
    finally:
        if not sensor_stream.closed:
            sensor_stream.close()


def analyze(source):
    """Consumes sensor artifacts only; oracle files are not arguments or inputs."""
    import cv2
    from .point_temporal_probe import track_lk, CV2_VERSION
    from ..vision import camera_to_world, pixel_to_camera
    source = Path(source)
    if cv2.__version__ != CV2_VERSION:
        raise ValueError('frozen OpenCV version differs')
    seal = json.loads((source/'sensor-seal.json').read_text())
    for path, digest in seal['sha256'].items():
        if file_hash(source/path) != digest:
            raise ValueError('sealed sensor artifact changed')
    seed = json.loads((source/'seed-frozen.json').read_text())['seed']
    captures = json.loads((source/'captures.json').read_text())
    controls = [json.loads(line) for line in (source/'sensors.jsonl').read_text().splitlines()]
    result = {'holding':None, 'threshold_or_confidence_fit':False, 'arms':{}}
    for arm in ARMS:
        frames = [c for c in captures if c['arm']==arm and c['after_step']>=12]
        arrays = [np.load(source/c['artifact'], allow_pickle=False) for c in frames]
        rgbs = np.stack([f['rgb'] for f in arrays])
        rows = []
        for point in seed['points']:
            tracked = track_lk(rgbs, point['pixel_xy'], cv2)
            first_point, first_tcp = None, None
            for index, (track, meta, frame) in enumerate(zip(tracked, frames, arrays, strict=True)):
                control = next(r for r in controls if r['arm']==arm and r['step']==meta['after_step'] and r['control']==meta['control'])
                tcp = np.asarray(control['sensor']['tcp_fk_world_m'])
                xyz, depth, pixel = None, None, None
                if track['status'] in ('seeded','native_status_ok'):
                    xy = np.asarray(track['point_pixel_index_xy'])
                    x,y = np.floor(xy).astype(int)
                    if 0 <= x < rgbs.shape[2] and 0 <= y < rgbs.shape[1]:
                        depth = float(frame['depth_m'][y,x])
                        pixel = [int(x),int(y)]
                        if np.isfinite(depth) and .01 <= depth <= 5:
                            xyz = camera_to_world(pixel_to_camera(x+.5,y+.5,depth,frame['intrinsics']),frame['camera_to_world'])
                if index==0:
                    first_point, first_tcp = xyz, tcp
                delta = None if xyz is None or first_point is None else xyz-first_point
                tcp_delta = tcp-first_tcp
                rows.append({**track, 'role':point['role'], 'capture_id':meta['capture_id'],
                    'after_step':meta['after_step'], 'control':meta['control'],
                    'sample_pixel_xy':pixel, 'depth_m':depth, 'surface_point_world_m':xyz,
                    'surface_point_delta_m':delta, 'tcp_delta_m':tcp_delta,
                    'point_minus_tcp_delta_m':None if delta is None else delta-tcp_delta,
                    'retention_label':None, 'identity_verified':None})
        for f in arrays:
            f.close()
        result['arms'][arm] = rows
    write_json(source/'sensor-analysis.json', result)
    write_json(source/'sensor-analysis-seal.json', {'sha256':file_hash(source/'sensor-analysis.json'),
        'wall_time_unix_s':time.time(), 'oracle_labels_read':False})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('collect','analyze'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    args = parser.parse_args()
    args.seed, args.init_state_id = 1, 0
    collect(args) if args.mode=='collect' else analyze(args.output)


if __name__ == '__main__':
    main()

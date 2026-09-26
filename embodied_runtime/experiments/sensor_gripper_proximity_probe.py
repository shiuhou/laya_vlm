"""Frozen archive adapter for the read-only two-capture proximity diagnostic."""
from __future__ import annotations

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from .records import code_identity, file_hash, jsonable, load_records, versions
from .robot_only_geometry import extract_own_positions

ARCHIVE_SHA256 = 'e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf'
CALIBRATION_SHA256 = '11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa'
ADMISSION_MAP_SHA256 = 'f60adc5b01aa0ccd527459d5711269a66f85b70b8b4cc32105033768251fec51'
SELECTION = ((24,'frames/capture-000025.npz','3999edda9befca7a7dad6080c66bd03f609e408ce5a7563994b9704422029dab'),
             (25,'frames/capture-000026.npz','907e9f36073adfdd7397fb79a8c205ce7567d7a729cc69d9b512087a42383d05'))
PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/sensor_gripper_proximity_protocol.md'


def write(path,value):
    with Path(path).open('x') as stream:
        json.dump(jsonable(value),stream,indent=2,allow_nan=False);stream.write('\n')


def unique(rows,kind,predicate):
    found = [r for r in rows if r['kind']==kind and predicate(r['data'])]
    if len(found)!=1:
        raise ValueError('Frozen source selector must yield exactly one record')
    return found[0]


def run(source,robot_source,output):
    source,robot_source,output = Path(source),Path(robot_source),Path(output)
    if file_hash(source/'episodes.jsonl') != ARCHIVE_SHA256:
        raise ValueError('Frozen archive differs')
    if file_hash(robot_source/'robot-calibration.json') != CALIBRATION_SHA256:
        raise ValueError('Frozen static robot calibration differs')
    if file_hash(robot_source/'archive-admission-map.json') != ADMISSION_MAP_SHA256:
        raise ValueError('Frozen own-joint admission mapping differs')
    code = code_identity()
    if code['dirty_status']:
        raise ValueError('Commit frozen instrumentation before any archived measurement')
    rows, errors = load_records(source/'episodes.jsonl')
    if errors:
        raise ValueError('Archive evidence chain invalid')
    calibration = json.loads((robot_source/'robot-calibration.json').read_text())
    mapping = json.loads((robot_source/'archive-admission-map.json').read_text())
    if list(mapping['own_qpos_flat_indices'].values()) != list(range(1,10)):
        raise ValueError('Frozen nine-own-joint extraction changed')
    output.mkdir(parents=True,exist_ok=False)
    inputs = output/'estimator-input';inputs.mkdir()
    write(output/'manifest.json',{'scope':'development diagnostic: observed depth to own gripper proxy distance',
        'code':code,'protocol_sha256':file_hash(PROTOCOL),'versions':{**versions(),'scipy':version('scipy')},
        'archive_source':str(source),'archive_sha256':ARCHIVE_SHA256,
        'robot_calibration_source':str(robot_source),'robot_calibration_sha256':CALIBRATION_SHA256,
        'own_joint_admission_map_sha256':ADMISSION_MAP_SHA256,
        'held_out':False,'dynamics_or_simulator_used':False,'policy_or_filter_used':False})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    try:
        packets,metadata = {},[]
        for i,(step,artifact,expected_hash) in enumerate(SELECTION):
            label = f'sample{i}'
            if file_hash(source/artifact)!=expected_hash:
                raise ValueError('Frozen recorded RGB-D artifact differs')
            capture = unique(rows,'vision_capture',lambda d:d['artifact']==artifact)
            control = unique(rows,'control_observation',lambda d:d['step']==step and d['control']==0)
            state = control['data']['state_before']
            if state[0]!=capture['data']['capture_sim_time'] or len(state)!=77:
                raise ValueError('Captured frame and own-position source time/layout differ')
            packet = extract_own_positions(state,mapping['own_qpos_flat_indices'])
            poison_checks = {}
            allowed = {0,*mapping['own_qpos_flat_indices'].values(),*mapping['own_qvel_flat_indices'].values()}
            excluded = [j for j in range(len(state)) if j not in allowed]
            for variant in ('nan_nonrobot','finite_nonrobot'):
                poisoned = np.asarray(state,dtype=float).copy()
                poisoned[excluded] = np.nan if variant=='nan_nonrobot' else 1234.5+np.arange(len(excluded))*.25
                poison_checks[variant] = extract_own_positions(poisoned,mapping['own_qpos_flat_indices']) == packet
            if not all(poison_checks.values()):
                raise ValueError('Archive adapter depends on excluded coordinates')
            packets[label] = packet
            with np.load(source/artifact,allow_pickle=False) as frame:
                if set(frame.files)!={'rgb','depth_m','intrinsics','camera_to_world'}:
                    raise ValueError('Unexpected raw sensor schema')
                np.savez_compressed(inputs/f'{label}.npz',**{k:frame[k] for k in ('depth_m','intrinsics','camera_to_world')})
            metadata.append({'sample':label,'development_boundary':step,'artifact':artifact,'artifact_sha256':expected_hash,
                'capture_record_id':capture['record_id'],'capture_seq':capture['seq'],
                'capture_sim_time':capture['data']['capture_sim_time'],'camera_calibration_id':capture['data']['calibration_id'],
                'own_joint_source_record_id':control['record_id'],'own_joint_source_seq':control['seq'],
                'own_joint_source_field':'state_before','own_joint_flat_indices':mapping['own_qpos_flat_indices'],
                'own_joint_provenance':'simulator-state-derived own-joint encoder analogues',
                'nonrobot_state_poison_packet_equal':poison_checks,'nonrobot_poisoned_coordinate_count':len(excluded)})
        write(inputs/'request.json',{'calibration':calibration,'own_joint_packets':packets})
        write(output/'preparation.json',{'samples':metadata,'worker_receives_rgb':False,
            'worker_receives_archive_path_or_full_state':False,'worker_receives_contact_target_or_scene_geometry':False,
            'camera_calibration':'recorded simulator K/T assumed known; physical accuracy unvalidated',
            'base_calibration':'known static world installation transform assumed; physical accuracy unvalidated',
            'partial_mask':'five gripper proxies only; arm/wrist and visual-proxy mismatch not masked completely'})
        completed = subprocess.run([sys.executable,'-m','embodied_runtime.experiments.sensor_gripper_proximity',
            '--input',str(inputs),'--output',str(output/'estimator-output')],capture_output=True,text=True,check=True)
        write(output/'estimator-process.json',{'returncode':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr})
        write(output/'estimator-output-seal.json',{'wall_time_unix_s':time.time(),
            'input_sha256':{p.name:file_hash(p) for p in sorted(inputs.iterdir())},
            'output_sha256':{p.name:file_hash(p) for p in sorted((output/'estimator-output').iterdir())},
            'rgb_witness_inspection_started':False,'no_scene_or_contact_evaluator':True})
        write(output/'artifacts.json',{str(p.relative_to(output)):file_hash(p) for p in sorted(output.rglob('*')) if p.is_file()})
        print(json.dumps({'status':'sealed','output':str(output),'samples':len(metadata),'physics_steps':0}))
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'message':str(exc),'physics_steps':0})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-initial-point-02')
    parser.add_argument('--robot-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/robot-geometry-observability-03')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    run(args.source,args.robot_source,args.output)

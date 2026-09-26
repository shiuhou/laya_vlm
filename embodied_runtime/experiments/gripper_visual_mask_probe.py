"""Frozen input adapter for the visual-mask-only proximity control."""
from __future__ import annotations

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from .records import code_identity,file_hash,versions
from .robot_geometry_probe import write

VISUAL_SHA256='c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98'
REFERENCE_FILES={
    'estimator-input/request.json':'02e9d19a3cdbee61eb4cf34601040a3110ff83a2946f141f674c7ec96e47663e',
    'estimator-input/sample0.npz':'67b0024f17052f3b8e6f95398d06873605872b295180c697ef504119091dcd8b',
    'estimator-input/sample1.npz':'98b7631887dafbcdf2e0d11481d03ef23cee1709f9de4c086281ecb957a2bd38',
    'estimator-output/sample0-arrays.npz':'23c2244e761473cc6e5de55d1c37f0d787635d14a87f6590b2ee231cbdeed0ac',
    'estimator-output/sample1-arrays.npz':'0b9e7e62802a9af9dfb86b2717efa7d9bb22e85e7b078e138b67582dcdf20f77'}
PROTOCOL=Path(__file__).resolve().parents[2]/'docs/research/gripper_visual_mask_protocol.md'


def run(reference,visual_source,output):
    reference,visual_source,output=map(Path,(reference,visual_source,output))
    code=code_identity()
    if code['dirty_status']:raise ValueError('Freeze visual-mask worker before measurement')
    for name,expected in REFERENCE_FILES.items():
        if file_hash(reference/name)!=expected:raise ValueError('Prior input/distance-map bytes differ: '+name)
    if file_hash(visual_source/'gripper-visual-calibration.json')!=VISUAL_SHA256:raise ValueError('Frozen visual calibration differs')
    visual=json.loads((visual_source/'gripper-visual-calibration.json').read_text())
    original=json.loads((reference/'estimator-input/request.json').read_text())
    if any(visual[key]!=original['calibration'][key] for key in ('version','bodies','sites')):raise ValueError('Known robot chain differs')
    output.mkdir(parents=True,exist_ok=False);inputs=output/'estimator-input';inputs.mkdir()
    write(output/'manifest.json',{'code':code,'versions':{**versions(),'scipy':version('scipy')},'protocol_sha256':file_hash(PROTOCOL),
        'reference_source':str(reference),'reference_files_sha256':REFERENCE_FILES,'visual_export_source':str(visual_source),
        'visual_calibration_sha256':VISUAL_SHA256,'new_dynamics_or_rendering':False,'development_data_only':True})
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    try:
        for relative in REFERENCE_FILES:
            if not relative.endswith('request.json'):shutil.copyfile(reference/relative,inputs/Path(relative).name)
        write(inputs/'request.json',{'visual_calibration':visual,'own_joint_packets':original['own_joint_packets'],
            'distance_proxy_names':[g['name'] for g in original['calibration']['geometries']]})
        result=subprocess.run([sys.executable,'-m','embodied_runtime.experiments.gripper_visual_mask_control','--input',str(inputs),
            '--output',str(output/'estimator-output')],capture_output=True,text=True,check=True)
        write(output/'process.json',{'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        write(output/'estimator-output-seal.json',{'wall_time_unix_s':time.time(),
            'input_sha256':{p.name:file_hash(p) for p in sorted(inputs.iterdir())},
            'output_sha256':{p.name:file_hash(p) for p in sorted((output/'estimator-output').iterdir())},
            'rgb_witness_inspection_started':False,'distance_maps_recomputed':False})
        write(output/'artifacts.json',{str(p.relative_to(output)):file_hash(p) for p in sorted(output.rglob('*')) if p.is_file()})
        print(json.dumps({'status':'sealed','source_distance_maps':'unchanged','output':str(output)}))
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'message':str(exc)});raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--reference',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/sensor-gripper-proximity-01')
    p.add_argument('--visual-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/gripper-visual-calibration-01')
    p.add_argument('--output',required=True);a=p.parse_args();run(a.reference,a.visual_source,a.output)

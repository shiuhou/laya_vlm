"""Frozen exploratory offline plane probe; never reads evaluator files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def points(frame):
    yy, xx = np.mgrid[275:306, 156:187]
    depth = frame['depth_m'][yy,xx]
    valid = np.isfinite(depth) & (depth >= .01) & (depth <= 5.)
    k = frame['intrinsics']
    camera = np.stack(((xx+.5-k[0,2])*depth/k[0,0],
                       (yy+.5-k[1,2])*depth/k[1,1], depth, np.ones_like(depth)), axis=-1)
    return (camera @ frame['camera_to_world'].T)[valid,:3]


def residual_summary(values):
    return {'min_mm': float(np.min(values)*1000), 'max_mm':float(np.max(values)*1000),
            'rms_mm':float(np.sqrt(np.mean(values**2))*1000),
            'median_abs_mm':float(np.median(np.abs(values))*1000),
            'max_abs_mm':float(np.max(np.abs(values))*1000)}


def run(source, output, protocol):
    import cv2
    from PIL import Image, ImageDraw

    source, output, protocol = map(Path, (source, output, protocol))
    if cv2.__version__ != '4.11.0':
        raise ValueError('Frozen OpenCV version changed')
    # The output directory and freeze record must be created before running.
    freeze = json.loads((output/'freeze.json').read_text())
    if freeze['protocol_sha256'] != digest(protocol) or freeze['script_sha256'] != digest(__file__):
        raise ValueError('Exploratory protocol or script changed after freeze')
    seal = json.loads((source/'sensor-seal.json').read_text())
    for name, expected in seal['sha256'].items():
        if digest(source/name) != expected:
            raise ValueError('Sealed sensor input changed')
    analysis_seal = json.loads((source/'sensor-analysis-seal.json').read_text())
    if digest(source/'sensor-analysis.json') != analysis_seal['sha256']:
        raise ValueError('Sealed sensor analysis changed')
    analysis = json.loads((source/'sensor-analysis.json').read_text())
    captures = json.loads((source/'captures.json').read_text())
    seed = json.loads((source/'seed.json').read_text())
    if seed['points'][2]['pixel_xy'] != [171,290]:
        raise ValueError('Original table seed changed')
    result = {'scope':'post-outcome exploratory sensor-only support-plane feasibility',
              'holding':None, 'source':str(source), 'patch_xyxy_inclusive':[156,275,186,305],
              'fixed_before_numeric_fitting':True, 'oracle_inputs':False,
              'opencv_version':cv2.__version__, 'arms':{}, 'input_sha256':{
                  'sensor_seal':digest(source/'sensor-seal.json'),
                  'sensor_analysis':digest(source/'sensor-analysis.json'),
                  'protocol':digest(protocol), 'freeze':digest(output/'freeze.json')}}
    for arm in ('close','open_hold'):
        rows = []
        selected = [c for c in captures if c['arm'] == arm and c['after_step'] >= 12]
        for index, c in enumerate(selected):
            with np.load(source/c['artifact'], allow_pickle=False) as arr:
                frame = {key:arr[key].copy() for key in arr.files}
            xyz = points(frame)
            if len(xyz) < 3:
                raise ValueError('Fewer than three valid patch points; no recovery')
            center = xyz.mean(axis=0)
            values, vectors = np.linalg.eigh((xyz-center).T @ (xyz-center)/len(xyz))
            normal = vectors[:,0]
            if normal[2] < 0:
                normal = -normal
            offset = -float(normal @ center)
            if index == 0:
                seed_frame, seed_normal, seed_offset = frame, normal, offset
                seed_rows = {r['role']:r for r in analysis['arms'][arm] if r['capture_id'] == c['capture_id']}
                marked = Image.fromarray(frame['rgb'])
                ImageDraw.Draw(marked).rectangle((156,275,186,305),outline='magenta',width=2)
                marked.save(output/f'{arm}-patch.png')
            row = {'capture_id':c['capture_id'], 'after_step':c['after_step'], 'control':c['control'],
                'valid_patch_points':len(xyz), 'centroid_world_m':center.tolist(), 'normal_world':normal.tolist(),
                'offset_m':offset, 'covariance_eigenvalues_m2':values.tolist(),
                'within_frame_plane_residual':residual_summary(xyz @ normal+offset),
                'seed_plane_residual':residual_summary(xyz @ seed_normal+seed_offset),
                'calibration_exactly_equal_to_seed':bool(np.array_equal(frame['intrinsics'],seed_frame['intrinsics']) and
                    np.array_equal(frame['camera_to_world'],seed_frame['camera_to_world'])),
                'patch_rgb_exactly_equal_to_seed':bool(np.array_equal(frame['rgb'][275:306,156:187],seed_frame['rgb'][275:306,156:187])),
                'patch_depth_exactly_equal_to_seed':bool(np.array_equal(frame['depth_m'][275:306,156:187],seed_frame['depth_m'][275:306,156:187])),
                'landmarks':{}}
            for r in (r for r in analysis['arms'][arm] if r['capture_id'] == c['capture_id']):
                xyz_landmark = r['surface_point_world_m']
                initial = seed_rows[r['role']]['surface_point_world_m']
                row['landmarks'][r['role']] = {'tracker_status':r['status'],
                    'seed_plane_signed_distance_mm':None if xyz_landmark is None else float((np.dot(seed_normal,xyz_landmark)+seed_offset)*1000),
                    'seed_plane_distance_change_mm':None if xyz_landmark is None or initial is None else
                        float(np.dot(seed_normal,np.asarray(xyz_landmark)-initial)*1000)}
            rows.append(row)
            if index == 1:
                diagnostics = []
                previous = cv2.cvtColor(seed_frame['rgb'],cv2.COLOR_RGB2GRAY)
                current = cv2.cvtColor(frame['rgb'],cv2.COLOR_RGB2GRAY)
                for p in seed['points']:
                    point = np.asarray(p['pixel_xy'],np.float32).reshape(1,1,2)
                    nxt, status, minimum_eigenvalue = cv2.calcOpticalFlowPyrLK(previous,current,point,None,
                        winSize=(21,21),maxLevel=3,criteria=(3,30,.01),
                        flags=cv2.OPTFLOW_LK_GET_MIN_EIGENVALS,minEigThreshold=.0001)
                    diagnostics.append({'role':p['role'], 'forward_status':int(status[0,0]),
                        'min_eigenvalue':float(minimum_eigenvalue[0,0]), 'unchanged_minEigThreshold':.0001})
        result['arms'][arm] = {'frames':rows,'first_transition_LK_min_eigenvalue_diagnostic':diagnostics}
    write(output/'sensor-results.json',result)
    write(output/'sensor-results-seal.json',{'wall_time_unix_s':time.time(),
        'oracle_labels_read':False, 'sha256':digest(output/'sensor-results.json')})
    write(output/'artifacts.json',{p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file()})
    print(json.dumps({arm:{'frames':len(v['frames']),
        'max_plane_fit_residual_mm':max(r['within_frame_plane_residual']['max_abs_mm'] for r in v['frames']),
        'max_seed_plane_residual_mm':max(r['seed_plane_residual']['max_abs_mm'] for r in v['frames']),
        'unchanged_patch_rgb':all(r['patch_rgb_exactly_equal_to_seed'] for r in v['frames']),
        'unchanged_patch_depth':all(r['patch_depth_exactly_equal_to_seed'] for r in v['frames']),
        'last_landmarks':v['frames'][-1]['landmarks'],
        'LK_diagnostic':v['first_transition_LK_min_eigenvalue_diagnostic']} for arm,v in result['arms'].items()},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--protocol',default=str(Path(__file__).resolve().parents[2]/'docs/research/retention_support_plane_probe_protocol.md'))
    args = parser.parse_args()
    run(args.source,args.output,args.protocol)

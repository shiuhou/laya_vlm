"""Offline evaluator of sealed sensor traces; no estimator feedback or physics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .interaction_observability import ARMS, write_json
from .records import file_hash


def describe(values):
    return {'n':len(values), 'min':float(min(values)) if values else None,
        'median':float(np.median(values)) if values else None,
        'max':float(max(values)) if values else None}


def report(source):
    source = Path(source)
    seal = json.loads((source/'sensor-analysis-seal.json').read_text())
    if file_hash(source/'sensor-analysis.json') != seal['sha256'] or seal['oracle_labels_read'] is not False:
        raise ValueError('sensor-only analysis is not intact/sealed')
    analysis = json.loads((source/'sensor-analysis.json').read_text())
    captures = json.loads((source/'captures.json').read_text())
    controls = [json.loads(line) for line in (source/'sensors.jsonl').read_text().splitlines()]
    labels = json.loads((source/'evaluator-only/labels.json').read_text())
    output = source/'evaluation'
    output.mkdir(exist_ok=False)
    summary = {'version':'interaction-observability-evaluation-v1', 'run':str(source),
        'semantic_initialization_actual':'assistant_RGB_visual_annotation_before_close',
        'provenance_erratum':'Raw schema says human_RGB_only_before_close; annotator was the Codex assistant, not a human.',
        'holding':None, 'arms':{}, 'sensor_analysis_sha256':seal['sha256'],
        'sensor_seal_sha256':file_hash(source/'sensor-seal.json'),
        'manifest_sha256':file_hash(source/'manifest.json'), 'seed_sha256':file_hash(source/'seed.json'),
        'oracle_labels_sha256':file_hash(source/'evaluator-only/labels.json')}
    membership = []
    for arm in ARMS:
        rows = analysis['arms'][arm]
        trajectory = [r for r in labels if r['arm']==arm and r['after_step']>=12 and
                      (r['after_step']>12 or r['control']==7)]
        sensors = [r for r in controls if r['arm']==arm]
        before, after = trajectory[0],trajectory[-1]
        arm_result = {'native_primitives':17, 'native_controls':len(sensors),
            'sensor_read_sim_time_s':[sensors[0]['before_sim_time_s'], sensors[-1]['sensor']['read_sim_time_s']],
            'per_control_duration_s':describe([r['sensor']['read_sim_time_s']-r['before_sim_time_s'] for r in sensors]),
            'oracle_bottle_center_delta_mm':(np.asarray(after['bottle_center_mm'])-before['bottle_center_mm']).tolist(),
            'oracle_bilateral_after_seed_controls':sum(r['valid_grasp_relation'] for r in trajectory[1:]),
            'oracle_bilateral_by_step':{str(step):[r['valid_grasp_relation'] for r in trajectory if r['after_step']==step]
                                       for step in (13,14,15,16)},
            'raw_wrist_force_norm_N_after_seed':describe([float(np.linalg.norm(r['sensor']['wrist_force_local_N']))
                                                         for r in sensors if r['step']>=13]),
            'endpoint_sensors':{}, 'landmarks':{}}
        for step in (12,13,14,15,16):
            sensor = next(r['sensor'] for r in sensors if r['step']==step and r['control']==7)
            oracle = next(r for r in trajectory if r['after_step']==step and r['control']==7)
            arm_result['endpoint_sensors'][str(step)] = {key:sensor[key] for key in
                ('joint_aperture_m','direct_gripper_qvel_mps','wrist_force_local_N','wrist_torque_local_Nm','tcp_fk_world_m')}
            arm_result['endpoint_sensors'][str(step)]['evaluator_geometric_gap_mm'] = oracle['geometric_finger_gap_mm']
        for role in ('bottle_landmark_1','bottle_landmark_2','table_reference'):
            rr = [r for r in rows if r['role']==role]
            membership_rows = []
            for r in rr:
                pixel = r['sample_pixel_xy']
                mask = np.load(source/f'evaluator-only/{arm}-{r["capture_id"]:04d}-bottle-mask.npy', allow_pickle=False)
                on_bottle = None if pixel is None else bool(mask[pixel[1],pixel[0]])
                entry = {'arm':arm,'role':role,'capture_id':r['capture_id'],'after_step':r['after_step'],
                    'control':r['control'],'on_bottle_visual_geometry':on_bottle,'tracker_status':r['status'],
                    'forward_backward_residual_px':r['forward_backward_residual_px']}
                membership_rows.append(entry)
                membership.append(entry)
            first_miss = next((r for r in membership_rows if r['on_bottle_visual_geometry'] is False),None)
            arm_result['landmarks'][role] = {
                'frames':len(rr),'native_ok_after_seed':sum(r['status']=='native_status_ok' for r in rr[1:]),
                'on_bottle_including_seed':sum(r['on_bottle_visual_geometry'] is True for r in membership_rows),
                'off_bottle_including_seed':sum(r['on_bottle_visual_geometry'] is False for r in membership_rows),
                'unknown_including_seed':sum(r['on_bottle_visual_geometry'] is None for r in membership_rows),
                'first_off_bottle':first_miss,
                'forward_backward_residual_px':describe([r['forward_backward_residual_px'] for r in rr
                                                        if r['forward_backward_residual_px'] is not None]),
                'endpoint_surface_point_delta_m':rr[-1]['surface_point_delta_m'],
                'endpoint_tcp_delta_m':rr[-1]['tcp_delta_m'],
                'endpoint_point_minus_tcp_delta_m':rr[-1]['point_minus_tcp_delta_m']}
        summary['arms'][arm] = arm_result

    # Verify matched common prefix independently, excluding wall-clock time only.
    common = []
    for step in range(13):
        for control in range(8):
            pair = [next(r for r in controls if r['arm']==arm and r['step']==step and r['control']==control) for arm in ARMS]
            def comparable(r):
                return {k:v for k,v in r['sensor'].items() if k!='wall_time_unix_s'}
            common.append(comparable(pair[0])==comparable(pair[1]))
    summary['shared_prefix_controls_bitwise_equal'] = all(common)
    summary['shared_prefix_controls_compared'] = len(common)
    summary['shared_prefix_rgb_equal'] = all(
        next(c['rgb_sha256'] for c in captures if c['arm']==ARMS[0] and c['after_step']==step)==
        next(c['rgb_sha256'] for c in captures if c['arm']==ARMS[1] and c['after_step']==step)
        for step in range(-1,13))
    write_json(output/'summary.json', summary)
    write_json(output/'membership.json', membership)

    sheet = Image.new('RGB',(5*384,2*424),'white')
    colors = {'bottle_landmark_1':'orange','bottle_landmark_2':'cyan','table_reference':'magenta'}
    for row,arm in enumerate(ARMS):
        for col,step in enumerate((12,13,14,15,16)):
            c = next(c for c in captures if c['arm']==arm and c['after_step']==step and c['control']==7)
            img = Image.open(source/c['rgb_artifact']).convert('RGB')
            draw = ImageDraw.Draw(img)
            for r in analysis['arms'][arm]:
                if r['capture_id']==c['capture_id'] and r['sample_pixel_xy'] is not None:
                    x,y = r['point_pixel_index_xy']
                    draw.ellipse((x-3,y-3,x+3,y+3),outline=colors[r['role']],width=2)
            x,y = col*384,row*424
            sheet.paste(img,(x,y+40))
            ImageDraw.Draw(sheet).text((x+5,y+8),f'{arm}, after {step}; RGB tracker markers',fill='black')
    sheet.save(output/'trajectory-contact-sheet.png')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2,3,figsize=(15,8))
    for index,arm in enumerate(ARMS):
        rows = analysis['arms'][arm]
        for role in ('bottle_landmark_1','bottle_landmark_2'):
            rr = [r for r in rows if r['role']==role]
            axes[index,0].plot(range(33),[np.nan if r['surface_point_delta_m'] is None else 1000*r['surface_point_delta_m'][2] for r in rr],label=role)
        axes[index,0].plot(range(33),[1000*r['tcp_delta_m'][2] for r in rr],color='black',linestyle='--',label='robot TCP FK')
        oracle = [r for r in labels if r['arm']==arm and r['after_step']>=12 and (r['after_step']>12 or r['control']==7)]
        axes[index,0].plot(range(33),[r['bottle_center_mm'][2]-oracle[0]['bottle_center_mm'][2] for r in oracle],linestyle=':',label='EVALUATOR bottle')
        for role in ('bottle_landmark_1','bottle_landmark_2'):
            rr = [r for r in rows if r['role']==role]
            axes[index,1].plot(range(33),[r['forward_backward_residual_px'] or 0 for r in rr],label=role)
        ss = [r['sensor'] for r in controls if r['arm']==arm and r['step']>=13]
        axes[index,2].plot(range(1,33),[np.linalg.norm(r['wrist_force_local_N']) for r in ss],label='aggregate raw force')
        for j,title in enumerate(('Vertical displacement (mm)','Forward/backward residual (px)','Raw wrist force norm (N)')):
            axes[index,j].set_title(f'{arm}: {title}')
            axes[index,j].set_xlabel('Native controls after seed')
            axes[index,j].grid(alpha=.3)
            axes[index,j].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output/'trajectory-sensors.png',dpi=140)
    plt.close(fig)
    write_json(output/'artifacts.json', {p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    print(json.dumps(report(parser.parse_args().source),indent=2))

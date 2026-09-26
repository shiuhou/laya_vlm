"""Read-only verification and post-seal plots of raster/cache evaluator results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .records import file_hash
from .render_measurement_diagnosis import CONTEXT_INVARIANTS,WITNESSES,array_hash


def report(source,robot_source,visual_source,output):
    source,robot_source,visual_source,output=map(Path,(source,robot_source,visual_source,output))
    def read(path):return json.loads(Path(path).read_text())
    checks=[]
    def check(name,condition):
        if not condition:raise ValueError('Render report audit failed: '+name)
        checks.append(name)
    manifest=read(source/'manifest.json');seal=read(source/'output-seal.json');artifacts=read(source/'artifacts.json')
    for name,expected in artifacts.items():check('artifact '+name,file_hash(source/name)==expected)
    for name,expected in seal['sha256'].items():check('seal '+name,file_hash(source/name)==expected)
    check('sealed before inspection',seal['rgb_witness_inspection_started'] is False)
    gate=read(source/'baseline-gate.json');measurements=read(source/'measurements.json');copies=read(source/'copy-cache-checks.json')
    check('402 exact state checks',len(gate['state_checks'])==402 and all(c['exact'] and c['max_absolute_error']==0 for c in gate['state_checks']))
    check('both baseline gates',gate['passed'] and measurements['baseline_gate_passed'] and set(gate['baseline'])=={'24','25'})
    check('six checked copy/render operations',len(copies)==6 and all(c['exact'] and c['source']==c['copy'] for c in copies))
    check('zero diagnostic stepping and forward',all(value==0 for value in measurements['counts']['diagnostic'].values()))
    check('historical prefix count',measurements['counts']['prefix']['env_controls']==200)
    calibrations={'collision':read(robot_source/'robot-calibration.json'),'visual':read(visual_source/'gripper-visual-calibration.json')}
    check('collision calibration hash',file_hash(robot_source/'robot-calibration.json')==manifest['robot_calibration_sha256'])
    check('visual calibration hash',file_hash(visual_source/'gripper-visual-calibration.json')==manifest['visual_calibration_sha256'])
    frames={};witness_centers={};projection_summary={}
    for step,artifact in ((24,'capture-000025.npz'),(25,'capture-000026.npz')):
        label=str(step);result=measurements['states'][label];baseline=measurements['baseline'][label]
        with np.load(source/f'native-before-{step}.npz',allow_pickle=False) as f:native={k:f[k] for k in f.files}
        with np.load(source/f'zero-msaa-before-{step}.npz',allow_pickle=False) as f:zero={k:f[k] for k in f.files}
        with np.load(Path(manifest['source'])/'frames'/artifact,allow_pickle=False) as f:
            for key in f.files:check(f'original frame bytes {step}/{key}',array_hash(f[key])==array_hash(native[key]))
        native_context=baseline['context']
        for zero_context in (measurements['zero_context'],result['zero_context_after_capture']):
            check('actual zero samples '+label,zero_context['context_actual_offSamples']==0)
            for key in CONTEXT_INVARIANTS:check(f'context invariant {step}/{key}',native_context[key]==zero_context[key])
        difference=zero['depth_m'].astype(float)-native['depth_m'].astype(float)
        rgb=np.abs(zero['rgb'].astype(int)-native['rgb'].astype(int));stats=result['native_vs_zero']
        for key in native:check(f'frame digest {step}/{key}',array_hash(native[key])==stats['native_array_sha256'][key] and array_hash(zero[key])==stats['other_array_sha256'][key])
        check('RGB difference count '+label,int(np.count_nonzero(np.any(rgb!=0,axis=-1)))==stats['rgb_different_pixels'])
        check('depth difference count '+label,int(np.count_nonzero(difference))==stats['depth_different_pixels'])
        check('depth maximum '+label,float(np.max(np.abs(difference)))==stats['depth_max_absolute_difference_m'])
        check('depth mean '+label,float(np.mean(np.abs(difference)))==stats['depth_mean_absolute_difference_m'])
        check('witness registration '+label,[tuple(w['center_pixel_xy']) for w in result['witnesses']]==list(WITNESSES[step]))
        centers=[]
        for witness in result['witnesses']:
            cx,cy=witness['center_pixel_xy'];pixels=witness['all_3x3_pixels']
            check(f'all neighbors {step}/{cx}/{cy}',[p['pixel_xy'] for p in pixels]==[[x,y] for y in range(cy-1,cy+2) for x in range(cx-1,cx+2)])
            for p in pixels:
                x,y=p['pixel_xy']
                check(f'witness values {step}/{x}/{y}',p['native_rgb']==native['rgb'][y,x].tolist() and p['zero_rgb']==zero['rgb'][y,x].tolist()
                    and p['native_depth_m']==float(native['depth_m'][y,x]) and p['zero_depth_m']==float(zero['depth_m'][y,x])
                    and p['zero_minus_native_depth_m']==difference[y,x])
            centers.append({**pixels[4],'zero_minus_native_depth_mm':pixels[4]['zero_minus_native_depth_m']*1000})
        projection=[]
        for row in result['cache_vs_own_qpos']:
            geom=next(g for g in calibrations[row['family']]['geometries'] if g['name']==row['geometry'])
            v=np.asarray(geom['vertices_local_m']);cached=v@np.asarray(row['cached_rotation_world']).T+row['cached_position_world_m']
            fk=v@np.asarray(row['fk_rotation_world']).T+row['fk_position_world_m']
            t,k=native['camera_to_world'],native['intrinsics']
            def uv(points):
                camera=(points-t[:3,3])@t[:3,:3];projected=camera@k.T
                return projected[:,:2]/projected[:,2,None]
            pixel_delta=np.linalg.norm(uv(cached)-uv(fk),axis=1);world_delta=np.linalg.norm(cached-fk,axis=1)
            check(f'projected displacement {step}/{row["geometry"]}',abs(float(pixel_delta.max())-row['projected_vertex_displacement_max_px'])<1e-12)
            check(f'world displacement {step}/{row["geometry"]}',abs(float(world_delta.max())-row['vertex_displacement_max_m'])<1e-14)
            projection.append({'geometry':row['geometry'],'max_world_displacement_um':row['vertex_displacement_max_m']*1e6,
                               'max_projected_displacement_px':row['projected_vertex_displacement_max_px']})
        projection_summary[label]=projection;witness_centers[label]=centers;frames[step]=(native,zero)
    output.mkdir(parents=True,exist_ok=True)
    summary={'raw_directory':str(source),'producer_commit':manifest['code']['commit'],'protocol_sha256':manifest['protocol_sha256'],
        'raw_artifact_hashes':artifacts,'artifacts_manifest_sha256':file_hash(source/'artifacts.json'),
        'post_seal_check_count':len(checks),'baseline_state_checks':len(gate['state_checks']),
        'original_RGB_depth_K_T_byte_identical':True,'copy_cache_operations_checked':len(copies),
        'counts':measurements['counts'],'native_context':measurements['baseline']['24']['context'],
        'zero_context':measurements['zero_context'],'fixed_center_results':witness_centers,
        'cache_FK_geometry_discrepancies':projection_summary,
        'frame_difference_summaries':{label:r['native_vs_zero'] for label,r in measurements['states'].items()},
        'limits':['explicit evaluator scene; no estimator/mask integration',
            'sampling effect demonstrated at fixed caches; no guarantee of residual pixel identity',
            'cache mismatch separately nonzero; no fresh-FK render condition',
            'development data only; no physical-calibration, free-space, action-gate or safety claim'],
        'process_note':'Exit 0 with ignored EGL destructor cleanup exceptions after all results were sealed; original log retained.'}
    with (output/'render_measurement_diagnosis_summary.json').open('x') as f:json.dump(summary,f,indent=2,allow_nan=False);f.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for step in (24,25):
        native,zero=frames[step];centers=WITNESSES[step];n=len(centers)
        fig,axes=plt.subplots(3,n,figsize=(2.5*n,7.8))
        fig.subplots_adjust(left=.04,right=.99,bottom=.05,top=.86,hspace=.48,wspace=.18)
        max_delta=max(abs(p['zero_minus_native_depth_m'])*1000 for w in measurements['states'][str(step)]['witnesses'] for p in w['all_3x3_pixels'])
        for col,(x,y) in enumerate(centers):
            for row,frame in enumerate((native,zero)):
                ax=axes[row,col];ax.imshow(frame['rgb'][y-8:y+9,x-8:x+9],extent=(x-8,x+9,y+9,y-8),interpolation='nearest')
                ax.plot(x+.5,y+.5,'+',color='white',ms=10,mew=1)
                ax.set_title(f'({x},{y}) z={float(frame["depth_m"][y,x]):.6f} m',fontsize=8)
                ax.set_xticks([]);ax.set_yticks([])
                if col==0:ax.set_ylabel('Native: 4 samples' if row==0 else 'Zero multisampling')
            delta=(zero['depth_m'][y-1:y+2,x-1:x+2].astype(float)-native['depth_m'][y-1:y+2,x-1:x+2].astype(float))*1000
            ax=axes[2,col];ax.imshow(delta,cmap='coolwarm',vmin=-max_delta,vmax=max_delta)
            for yy in range(3):
                for xx in range(3):ax.text(xx,yy,f'{delta[yy,xx]:+.1f}',ha='center',va='center',fontsize=8)
            ax.set_xticks([]);ax.set_yticks([]);ax.set_title('Zero − native depth (mm)',fontsize=8)
            if col==0:ax.set_ylabel('All fixed 3 × 3 pixels')
        fig.suptitle(f'Boundary {step}: sampling intervention with exactly preserved caches\nFixed 17 × 17 RGB crops; white cross is the registered center',fontsize=12)
        fig.savefig(output/f'render_measurement_witnesses_pre{step}.png',dpi=170);plt.close(fig)
    print(json.dumps({'checks_passed':len(checks),'summary':str(output/'render_measurement_diagnosis_summary.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--robot-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/robot-geometry-observability-03')
    p.add_argument('--visual-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/gripper-visual-calibration-01')
    a=p.parse_args();report(a.source,a.robot_source,a.visual_source,a.output)

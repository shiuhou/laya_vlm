"""Post-seal visual-mask comparison and RGB-D witnesses, without scene labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .records import file_hash


def report(source,output):
    source,output=Path(source),Path(output)
    def read(path):return json.loads(Path(path).read_text())
    checks=[]
    def check(name,condition):
        if not condition:raise ValueError('Visual-mask report audit failed: '+name)
        checks.append(name)
    manifest=read(source/'manifest.json');seal=read(source/'estimator-output-seal.json');artifacts=read(source/'artifacts.json')
    for name,expected in artifacts.items():check('artifact '+name,file_hash(source/name)==expected)
    for family in ('input','output'):
        for name,expected in seal[family+'_sha256'].items():
            check('seal '+family+'/'+name,file_hash(source/f'estimator-{family}'/name)==expected)
    check('seal before RGB',seal['rgb_witness_inspection_started'] is False)
    check('clean frozen producer',not manifest['code']['dirty_status'])
    reference=Path(manifest['reference_source']);ref_manifest=read(reference/'manifest.json')
    metadata=read(reference/'preparation.json')['samples']
    prior=read(reference/'estimator-output/measurements.json')
    old_request=read(reference/'estimator-input/request.json');request=read(source/'estimator-input/request.json')
    check('own joint packets unchanged',request['own_joint_packets']==old_request['own_joint_packets'])
    check('distance proxy order unchanged',request['distance_proxy_names']==[g['name'] for g in old_request['calibration']['geometries']])
    check('body/site calibration unchanged',all(request['visual_calibration'][k]==old_request['calibration'][k] for k in ('version','bodies','sites')))
    for name,expected in manifest['reference_files_sha256'].items():
        check('original fixed file '+name,file_hash(reference/name)==expected)
        if not name.endswith('request.json'):check('byte-identical copied input '+name,file_hash(source/'estimator-input'/Path(name).name)==expected)
    visual_source=Path(manifest['visual_export_source']);selection=read(visual_source/'selection.json')
    for name,expected in read(visual_source/'artifacts.json').items():check('static export artifact '+name,file_hash(visual_source/name)==expected)
    check('visual calibration identity',file_hash(visual_source/'gripper-visual-calibration.json')==manifest['visual_calibration_sha256'])
    check('visual calibration payload',request['visual_calibration']==read(visual_source/'gripper-visual-calibration.json'))
    measurements=read(source/'estimator-output/measurements.json');frames={};masks={}
    for meta in metadata:
        label=meta['sample'];result=measurements[label];names=result['geometry_names']
        raw=Path(ref_manifest['archive_source'])/meta['artifact']
        check('raw RGB-D hash '+label,file_hash(raw)==meta['artifact_sha256'])
        with np.load(raw,allow_pickle=False) as f:frame={key:f[key] for key in f.files}
        with np.load(source/'estimator-input'/f'{label}-arrays.npz',allow_pickle=False) as f:
            distance,old,valid=[f[key] for key in ('distance_to_proxy_m','partial_gripper_mask','valid_depth_mask')]
        with np.load(source/'estimator-output'/f'{label}-visual-mask.npz',allow_pickle=False) as f:
            visual,individual=f['visual_mask'],f['individual_visual_masks']
        check('visual union '+label,np.array_equal(visual,individual.any(axis=-1)) and individual.shape[-1]==3)
        expected={'old_collision':int(old.sum()),'new_visual':int(visual.sum()),'newly_excluded':int((visual&~old).sum()),
                  'newly_admitted':int((old&~visual).sum()),'intersection':int((old&visual).sum())}
        check('mask replacement counts '+label,expected==result['mask_counts'])
        for group,g in result['groups'].items():
            eligible=valid&~(old if group=='collision_mask_residual' else visual)
            values=distance[eligible];best=np.argmin(values,axis=1);minimum=np.min(values,axis=1)
            for name,stats in [('union',g['union']),*g['per_proxy'].items()]:
                selected=minimum if name=='union' else values[:,names.index(name)]
                check(f'point count {label}/{group}/{name}',len(selected)==stats['point_count'])
                if not len(selected):check('unknown empty',stats['nearest'] is None);continue
                check(f'quantiles {label}/{group}/{name}',np.array_equal(np.quantile(selected,[0,.01,.1,.5]),list(stats['quantiles_m'].values())))
                for level,count in stats['counts_at_or_below_m'].items():check(f'count {label}/{group}/{name}/{level}',int(np.count_nonzero(selected<=float(level)))==count)
                witness=stats['nearest'];x,y=witness['pixel_xy'];idx=names.index(witness['proxy'])
                check(f'nearest {label}/{group}/{name}',eligible[y,x] and distance[y,x,idx]==selected.min()==witness['distance_m'])
                k,t=frame['intrinsics'],frame['camera_to_world'];z=frame['depth_m'][y,x]
                point=t[:3,:3]@(np.linalg.solve(k,[x+.5,y+.5,1])*z)+t[:3,3]
                check(f'backprojection {label}/{group}/{name}',np.max(np.abs(point-witness['point_world_m']))<1e-12)
                if group=='collision_mask_residual':
                    old_stats=prior[label]['groups']['outside_partial_gripper_silhouette']['union' if name=='union' else 'per_proxy']
                    if name!='union':old_stats=old_stats[name]
                    check(f'baseline reproduced {label}/{name}',stats['quantiles_m']==old_stats['quantiles_m'] and
                          stats['counts_at_or_below_m']==old_stats['counts_at_or_below_m'] and witness['pixel_xy']==old_stats['nearest']['pixel_xy'])
            for level,counts in g['union']['nearest_proxy_contributions_at_or_below_m'].items():
                check(f'contributions {label}/{group}/{level}',counts=={name:int(np.count_nonzero((minimum<=float(level))&(best==i))) for i,name in enumerate(names)})
        for name,entry in result['old_nearest_witness_exclusion'].items():
            x,y=entry['old_nearest_pixel_xy'];check('old witness exclusion '+label+'/'+name,entry['excluded_by_visual_mask']==bool(visual[y,x]))
        frames[label]=frame;masks[label]=(old,visual)
        result['development_boundary']=meta['development_boundary']
        result['new_nearest_pixel_rgb']={name:frame['rgb'][s['nearest']['pixel_xy'][1],s['nearest']['pixel_xy'][0]].tolist()
            for name,s in result['groups']['visual_mask_residual']['per_proxy'].items() if s['nearest'] is not None}
    output.mkdir(parents=True,exist_ok=True)
    portable={'raw_directory':str(source),'producer_commit':manifest['code']['commit'],'raw_artifact_hashes':artifacts,
        'artifacts_manifest_sha256':file_hash(source/'artifacts.json'),'visual_static_export':selection,
        'reference_files_sha256':manifest['reference_files_sha256'],'post_seal_check_count':len(checks),
        'development_data_only':True,'distance_maps_unchanged':True,'samples':measurements,
        'limits':['visual projection convex enclosures are not exact rendered segmentation','gripper only; no arm mask',
                  'camera/base calibration and cache alignment assumed','residual identities and occluded space unknown',
                  'no gate, contact prediction, free-space or policy claim']}
    with (output/'gripper_visual_mask_summary.json').open('x') as f:json.dump(portable,f,indent=2,allow_nan=False);f.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#d946ef','#06b6d4','#2563eb','#f97316','#dc2626']
    fig,axes=plt.subplots(2,3,figsize=(15,9))
    for row,(label,result) in enumerate(measurements.items()):
        f=frames[label];h,w=f['depth_m'].shape;old,visual=masks[label]
        projected=np.concatenate([np.asarray(p['polygon_pixel_xy']) for p in result['visual_projection'].values() if p['polygon_pixel_xy']])
        left,top=np.maximum(np.floor(projected.min(axis=0)).astype(int)-32,0)
        right,bottom=np.minimum(np.ceil(projected.max(axis=0)).astype(int)+32,[w,h])
        axes[row,0].imshow(f['rgb'],extent=(0,w,h,0));axes[row,1].imshow(f['rgb'],extent=(0,w,h,0))
        crop=f['depth_m'][top:bottom,left:right];vmin,vmax=np.quantile(crop[np.isfinite(crop)&(crop>0)],[.02,.98])
        im=axes[row,2].imshow(f['depth_m'],extent=(0,w,h,0),vmin=vmin,vmax=vmax,cmap='viridis')
        fig.colorbar(im,ax=axes[row,2],label='Optical depth (m)',shrink=.7)
        for ax in axes[row]:
            ax.contour(np.arange(w)+.5,np.arange(h)+.5,old,levels=[.5],colors=['#f59e0b'],linewidths=.7)
            ax.contour(np.arange(w)+.5,np.arange(h)+.5,visual,levels=[.5],colors=['#22d3ee'],linewidths=.7)
            for i,(name,color) in enumerate(zip(result['geometry_names'],colors),1):
                witness=result['groups']['visual_mask_residual']['per_proxy'][name]['nearest']
                if witness is None:continue
                x,y=witness['pixel_center_xy'];ax.plot(x,y,'x',color=color,ms=7,mew=1.2)
                ax.annotate(str(i),(x,y),xytext=(4,6),textcoords='offset points',color=color,fontsize=8,weight='bold')
            ax.set(xlabel='Pixel x',ylabel='Pixel y')
        for ax in axes[row,1:]:ax.set_xlim(left,right);ax.set_ylim(bottom,top)
        for ax,title in zip(axes[row],('Full RGB','Fixed visual-proxy crop','Raw depth')):ax.set_title(f'Boundary {result["development_boundary"]}: {title}')
    fig.suptitle('Visual-mask replacement over unchanged collision-distance maps\nOrange=prior collision mask, cyan=visual mask; new witnesses: 1 hand, 2 finger1, 3 pad1, 4 finger2, 5 pad2',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/'gripper_visual_mask_overlays.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,5,figsize=(13,7))
    fig.subplots_adjust(hspace=.4,wspace=.12,top=.84,bottom=.04,left=.05,right=.99)
    for row,(label,result) in enumerate(measurements.items()):
        f=frames[label];h,w=f['depth_m'].shape
        for i,name in enumerate(result['geometry_names']):
            ax=axes[row,i];witness=result['groups']['visual_mask_residual']['per_proxy'][name]['nearest']
            if witness is None:ax.set_axis_off();continue
            x,y=witness['pixel_xy'];left,right=max(0,x-8),min(w,x+9);top,bottom=max(0,y-8),min(h,y+9)
            ax.imshow(f['rgb'][top:bottom,left:right],extent=(left,right,bottom,top),interpolation='nearest');ax.plot(x+.5,y+.5,'+',color='white',ms=12,mew=1)
            ax.set_title(f'{i+1}: {witness["distance_m"]*1000:.3f} mm at ({x},{y})',fontsize=9)
            if i==0:ax.set_ylabel(f'Boundary {result["development_boundary"]}')
            ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('New residual witnesses after visual exclusion (fixed 17 x 17 RGB patches)\nIdentity remains unknown; white cross marks the sampled pixel',fontsize=12)
    fig.savefig(output/'gripper_visual_mask_witnesses.png',dpi=170);plt.close(fig)
    print(json.dumps({'checks_passed':len(checks),'summary':str(output/'gripper_visual_mask_summary.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();report(a.source,a.output)

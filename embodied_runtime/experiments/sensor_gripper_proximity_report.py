"""Post-seal verification and raw RGB-D witness display; no scene oracle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .records import file_hash


def report(source,output):
    source,output = Path(source),Path(output)
    def read(name):
        return json.loads((source/name).read_text())
    checks = []
    def check(name,condition):
        if not condition:
            raise ValueError('Post-seal report check failed: '+name)
        checks.append(name)
    manifest, preparation = read('manifest.json'), read('preparation.json')
    seal,artifacts = read('estimator-output-seal.json'), read('artifacts.json')
    for name,expected in artifacts.items():
        check('artifact '+name,file_hash(source/name)==expected)
    for family in ('input','output'):
        for name,expected in seal[family+'_sha256'].items():
            check('seal '+family+'/'+name,file_hash(source/f'estimator-{family}'/name)==expected)
    check('sealed before RGB inspection',seal['rgb_witness_inspection_started'] is False)
    check('clean frozen producer',not manifest['code']['dirty_status'])
    request = read('estimator-input/request.json')
    check('request boundary',set(request)=={'calibration','own_joint_packets'})
    check('two opaque samples',set(request['own_joint_packets'])=={'sample0','sample1'})
    measurements = read('estimator-output/measurements.json')
    frames,masks,portable = {},{},{}
    for meta in preparation['samples']:
        label = meta['sample'];result = measurements[label]
        raw = Path(manifest['archive_source'])/meta['artifact']
        check('raw frame hash '+label,file_hash(raw)==meta['artifact_sha256'])
        with np.load(raw,allow_pickle=False) as data:
            frame = {k:data[k] for k in data.files}
        with np.load(source/'estimator-input'/f'{label}.npz',allow_pickle=False) as data:
            check('sensor schema '+label,set(data.files)=={'depth_m','intrinsics','camera_to_world'})
            for key in data.files:
                check('sensor exact copy '+label+'/'+key,np.array_equal(data[key],frame[key],equal_nan=True))
        with np.load(source/'estimator-output'/f'{label}-arrays.npz',allow_pickle=False) as data:
            distance,mask,valid,individual = [data[key] for key in ('distance_to_proxy_m','partial_gripper_mask',
                                              'valid_depth_mask','per_proxy_projected_masks')]
        names = result['geometry_names']
        check('five proxy maps '+label,distance.shape==(*frame['depth_m'].shape,5) and len(names)==5)
        check('validity rule '+label,np.array_equal(valid,np.isfinite(frame['depth_m'])&(frame['depth_m']>0)))
        check('invalid samples unknown '+label,np.isnan(distance[~valid]).all())
        check('nonnegative finite valid distances '+label,np.isfinite(distance[valid]).all() and (distance[valid]>=0).all())
        check('mask union '+label,np.array_equal(mask,individual.any(axis=-1)))
        check('valid count '+label,int(valid.sum())==result['valid_depth_pixels'])
        check('mask count '+label,int(mask.sum())==result['partial_mask_pixels'])
        for group,summary in result['groups'].items():
            eligible = valid if group=='all_valid_depth' else valid&~mask
            for name,stats in [('union',summary['union']),*summary['per_proxy'].items()]:
                values = np.min(distance,axis=-1) if name=='union' else distance[:,:,names.index(name)]
                selected = values[eligible]
                check(f'point count {label}/{group}/{name}',len(selected)==stats['point_count'])
                nearest = stats['nearest']
                if not len(selected):
                    check('empty is unknown',nearest is None and stats['quantiles_m'] is None)
                    continue
                check(f'quantiles {label}/{group}/{name}',np.array_equal(np.quantile(selected,[0,.01,.1,.5]),
                      [stats['quantiles_m'][key] for key in ('minimum','p01','p10','median')]))
                for level,count in stats['counts_at_or_below_m'].items():
                    check(f'count {label}/{group}/{name}/{level}',int(np.count_nonzero(selected<=float(level)))==count)
                x,y = nearest['pixel_xy']
                check(f'nearest map {label}/{group}/{name}',eligible[y,x] and values[y,x]==selected.min()==nearest['distance_m'])
                k,t,z = frame['intrinsics'],frame['camera_to_world'],float(frame['depth_m'][y,x])
                point = t[:3,:3]@(np.linalg.solve(k,[x+.5,y+.5,1])*z)+t[:3,3]
                check(f'witness backprojection {label}/{group}/{name}',np.max(np.abs(point-nearest['point_world_m']))<1e-12)
                geometric_distance = np.linalg.norm(point-nearest['closest_solid_proxy_point_world_m'])
                check(f'witness distance {label}/{group}/{name}',abs(geometric_distance-nearest['distance_m'])<1e-12)
            best = np.argmin(distance[eligible],axis=-1)
            minimum = np.min(distance[eligible],axis=-1)
            for level,counts in summary['union']['nearest_proxy_contributions_at_or_below_m'].items():
                actual = {name:int(np.count_nonzero((minimum<=float(level))&(best==i))) for i,name in enumerate(names)}
                check(f'proxy contributions {label}/{group}/{level}',actual==counts)
        frames[label],masks[label] = frame,mask
        portable[label] = {'development_boundary':meta['development_boundary'],
            'capture_sim_time_s':meta['capture_sim_time'],'raw_sensor_sha256':meta['artifact_sha256'],
            **result,
            'nearest_pixel_rgb':{group:{name:frame['rgb'][stats['nearest']['pixel_xy'][1],stats['nearest']['pixel_xy'][0]].tolist()
                for name,stats in value['per_proxy'].items() if stats['nearest'] is not None}
                for group,value in result['groups'].items()}}
    output.mkdir(parents=True,exist_ok=True)
    summary = {'raw_directory':str(source),'producer_commit':manifest['code']['commit'],
        'protocol_sha256':manifest['protocol_sha256'],'raw_artifact_hashes':artifacts,
        'artifacts_manifest_sha256':file_hash(source/'artifacts.json'),
        'post_seal_check_count':len(checks),'development_data_only':True,'samples':portable,
        'interpretation_limits':['distance to observed points, not scene clearance',
            'partial gripper projection mask; residual point identity unknown',
            'occluded, missing and out-of-view geometry unknown',
            'simulator camera/base calibration and own-joint encoder analogues assumed',
            'no contact classification, action gate, policy or new dynamics']}
    with (output/'sensor_gripper_proximity_summary.json').open('x') as stream:
        json.dump(summary,stream,indent=2,allow_nan=False);stream.write('\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = ['#d946ef','#06b6d4','#2563eb','#f97316','#dc2626']
    fig,axes = plt.subplots(2,3,figsize=(15,9))
    for row,(label,result) in enumerate(measurements.items()):
        frame = frames[label];height,width = frame['depth_m'].shape
        polygons = [np.asarray(p['polygon_pixel_xy']) for p in result['projection'].values() if p['polygon_pixel_xy']]
        projected = np.concatenate(polygons)
        left,top = np.maximum(np.floor(projected.min(axis=0)).astype(int)-32,0)
        right,bottom = np.minimum(np.ceil(projected.max(axis=0)).astype(int)+32,[width,height])
        axes[row,0].imshow(frame['rgb'],extent=(0,width,height,0))
        axes[row,1].imshow(frame['rgb'],extent=(0,width,height,0))
        crop = frame['depth_m'][top:bottom,left:right]
        finite = crop[np.isfinite(crop)&(crop>0)]
        vmin,vmax = np.quantile(finite,[.02,.98])
        im=axes[row,2].imshow(frame['depth_m'],extent=(0,width,height,0),vmin=vmin,vmax=vmax,cmap='viridis')
        fig.colorbar(im,ax=axes[row,2],label='Recorded optical depth (m)',shrink=.7)
        for ax in axes[row]:
            for name,color in zip(result['geometry_names'],colors):
                polygon = np.asarray(result['projection'][name]['polygon_pixel_xy'])
                if len(polygon):
                    closed = np.vstack((polygon,polygon[0]));ax.plot(closed[:,0],closed[:,1],color=color,lw=.8)
            for group,suffix,marker in (('all_valid_depth','a','o'),('outside_partial_gripper_silhouette','r','x')):
                for i,(name,color) in enumerate(zip(result['geometry_names'],colors),1):
                    witness = result['groups'][group]['per_proxy'][name]['nearest']
                    if witness is None:continue
                    x,y = witness['pixel_center_xy']
                    ax.plot(x,y,marker=marker,color=color,markerfacecolor='none',
                            linestyle='None',markersize=6,markeredgewidth=1.1)
                    ax.annotate(f'{i}{suffix}',(x,y),xytext=(3,-9 if suffix=='a' else 7),textcoords='offset points',
                                color=color,fontsize=7,weight='bold')
            ax.set(xlabel='Pixel x',ylabel='Pixel y')
        for ax in axes[row,1:]:ax.set_xlim(left,right);ax.set_ylim(bottom,top)
        boundary = portable[label]['development_boundary']
        for ax,title in zip(axes[row],('Full RGB','Proxy crop + witnesses','Raw depth + witnesses')):
            ax.set_title(f'Before boundary {boundary}: {title}')
    fig.suptitle('Observed-point proximity witnesses after numerical sealing\n'
                 '1=hand, 2=finger1, 3=pad1, 4=finger2, 5=pad2; a=all points, r=partial-mask residual',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/'sensor_gripper_proximity_overlays.png',dpi=170);plt.close(fig)
    # Fixed 17x17 raw RGB witness patches, with no identity classifier.
    fig,axes = plt.subplots(4,5,figsize=(13,10))
    for si,(label,result) in enumerate(measurements.items()):
        frame=frames[label];height,width=frame['depth_m'].shape
        for gi,group in enumerate(('all_valid_depth','outside_partial_gripper_silhouette')):
            for i,name in enumerate(result['geometry_names']):
                ax=axes[2*si+gi,i];witness=result['groups'][group]['per_proxy'][name]['nearest']
                if witness is None:ax.set_axis_off();continue
                x,y=witness['pixel_xy'];left,right=max(0,x-8),min(width,x+9);top,bottom=max(0,y-8),min(height,y+9)
                ax.imshow(frame['rgb'][top:bottom,left:right],extent=(left,right,bottom,top),interpolation='nearest')
                ax.plot(x+.5,y+.5,'+',color='white',ms=12,mew=1)
                ax.set_title(f'{i+1}: {witness["distance_m"]*1000:.3f} mm at ({x},{y})',fontsize=9)
                if i==0:ax.set_ylabel(f'Boundary {portable[label]["development_boundary"]}\n'+('All points' if gi==0 else 'Partial-mask residual'))
                ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Fixed raw RGB witness patches (17 x 17 pixels)\nWhite cross marks measured pixel; residual identity remains unknown',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/'sensor_gripper_proximity_witnesses.png',dpi=170);plt.close(fig)
    print(json.dumps({'checks_passed':len(checks),'summary':str(output/'sensor_gripper_proximity_summary.json')},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report(args.source,args.output)

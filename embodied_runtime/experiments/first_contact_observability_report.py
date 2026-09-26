"""Read-only raw projection checks and portable report; no model or simulator load."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from .records import file_hash, load_records


def summarize(raw, figures):
    raw,figures=Path(raw),Path(figures)
    rows,errors=load_records(raw/'episodes.jsonl')
    if errors or any(r['kind']=='failure' for r in rows):raise ValueError('complete failure-free audit required')
    def one(kind):
        found=[r['data'] for r in rows if r['kind']==kind]
        if len(found)!=1:raise ValueError('one '+kind+' required')
        return found[0]
    start=one('run_start');source=Path(start['resolved_config']['source'])
    if file_hash(source/'episodes.jsonl')!=start['resolved_config']['source_sha256']:raise ValueError('source changed')
    source_rows,source_errors=load_records(source/'episodes.jsonl')
    if source_errors:raise ValueError('source chain invalid')
    for name,digest in one('artifact_manifest').items():
        if file_hash(raw/name)!=digest:raise ValueError('raw audit artifact changed')
    for path,digest in one('source_and_query')['artifact_sha256'].items():
        if file_hash(path)!=digest:raise ValueError('source frame changed')
    measurements=[r['data'] for r in rows if r['kind']=='visibility_measurement']
    frames={};checked=0;max_error=0.
    for m in measurements:
        capture=next(r['data'] for r in source_rows if r['kind']=='vision_capture' and r['data']['capture_seq']==m['capture_seq'])
        with np.load(source/capture['artifact']) as a:frame={k:a[k].copy() for k in a.files}
        frames[m['step']]=frame;k,t=frame['intrinsics'],frame['camera_to_world']
        query=np.array(m['primary_projection']['world_m'])
        xyz_camera=t[:3,:3].T@(query-t[:3,3]);uv=np.array([k[0,0]*xyz_camera[0]/xyz_camera[2]+k[0,2],k[1,1]*xyz_camera[1]/xyz_camera[2]+k[1,2]])
        np.testing.assert_allclose(uv,m['primary_projection']['pixel_coordinates'],rtol=0,atol=1e-10)
        np.testing.assert_array_equal(np.floor(uv).astype(int),m['primary_projection']['containing_pixel_xy'])
        for n in m['neighborhoods']:
            counts=Counter()
            for s in n['all_samples']:
                if s['status']!='measured':continue
                x,y=s['pixel_xy'];z=float(frame['depth_m'][y,x])
                local=np.array([(x+.5-k[0,2])*z/k[0,0],(y+.5-k[1,2])*z/k[1,1],z])
                world=t[:3,:3]@local+t[:3,3]
                error=float(np.linalg.norm(world-s['sensor_point_world_m']));max_error=max(max_error,error)
                assert error<1e-12 and z==s['sensor_optical_depth_m']
                np.testing.assert_allclose(np.linalg.norm(world-query)*1000,s['sensor_to_query_euclidean_mm'],rtol=0,atol=1e-9)
                counts[s['evaluator_visual_ray']['category']]+=1;checked+=1
            assert dict(counts)==n['ray_category_counts']
    motion=one('motion_correspondence');env=one('evaluator_environment')
    face_distances=(np.asarray(env['box_halfsize_m'])-np.abs(motion['post_endpoint_local_contact_coordinate_m']))*1000
    if figures.exists():raise FileExistsError('new report-figure directory required')
    figures.mkdir(parents=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap,BoundaryNorm
    fig,axes=plt.subplots(2,3,figsize=(12,8),layout='constrained')
    for row,m in enumerate(measurements):
        step=m['step'];f=frames[step];x,y=m['primary_projection']['containing_pixel_xy']
        xlo,xhi=max(0,x-32),min(384,x+33);ylo,yhi=max(0,y-32),min(384,y+33)
        axes[row,0].imshow(f['rgb'][ylo:yhi,xlo:xhi],extent=(xlo,xhi,yhi,ylo))
        axes[row,0].set_title(f'Before action {step}: recorded RGB',fontsize=11)
        a,b,c,d=max(0,x-5),min(384,x+6),max(0,y-5),min(384,y+6)
        im=axes[row,1].imshow(f['depth_m'][c:d,a:b]*1000,extent=(a,b,d,c),interpolation='nearest')
        axes[row,1].set_title('Recorded optical depth (mm)',fontsize=11);fig.colorbar(im,ax=axes[row,1],shrink=.8)
        labels=np.full((d-c,b-a),2)
        for s in m['neighborhoods'][-1]['all_samples']:
            px,py=s['pixel_xy']
            if s['status']=='measured':labels[py-c,px-a]={'scene':0,'robot':1,'no_hit':2}[s['evaluator_visual_ray']['category']]
        colors=ListedColormap(['#7161a4','#4a9b86','#bbbbbb']);norm=BoundaryNorm([-.5,.5,1.5,2.5],3)
        im=axes[row,2].imshow(labels,extent=(a,b,d,c),cmap=colors,norm=norm,interpolation='nearest')
        axes[row,2].set_title('Evaluator ray category',fontsize=11)
        cb=fig.colorbar(im,ax=axes[row,2],ticks=[0,1,2],shrink=.8);cb.ax.set_yticklabels(['Scene','Robot','No hit'])
        for ax in axes[row]:
            ax.plot(x+.5,y+.5,'+',color='orange',ms=12);ax.set_xlabel('pixel x');ax.set_ylabel('pixel y')
    fig.suptitle('Orange: containing pixel of an oracle contact-region query; ray categories are evaluator labels',fontsize=11)
    fig.savefig(figures/'depth-and-occlusion.png',dpi=160);plt.close(fig)
    figure_manifest={'source_raw_sha256':file_hash(raw/'episodes.jsonl'),'report_script_sha256':file_hash(__file__),
                     'artifacts':{'depth-and-occlusion.png':file_hash(figures/'depth-and-occlusion.png')},
                     'original_raw_figures_unchanged':True,'no_new_simulator_or_model_calls':True}
    (figures/'manifest.json').write_text(json.dumps(figure_manifest,indent=2)+'\n')
    return {'version':'first-contact-observability-summary-v0.1','raw_path':str(raw),
            'raw_sha256':file_hash(raw/'episodes.jsonl'),'source_episodes_sha256':start['resolved_config']['source_sha256'],
            'recorded_run_start':start,'source_and_query':one('source_and_query'),'evaluator_environment':env,
            'motion_correspondence':motion,'post_endpoint_local_distance_to_each_box_face_mm':face_distances.tolist(),
            'first_two_nearest_face_distance_difference_mm':float(np.diff(np.sort(face_distances)[:2])[0]),
            'visibility_measurements':measurements,'artifact_manifest':one('artifact_manifest'),
            'independent_raw_projection_reconstruction':{'source':'separate read-only report code; no experiment helper import',
                'reconstructed_pixel_samples_including_registered_window_overlap':checked,
                'maximum_3d_reconstruction_error_m':max_error,'all_checks_passed':True,
                'scope':'raw sensor backprojection/query projection/distances and category-count arithmetic; not independent ray intersections'},
            'review_figures':{'path':str(figures),**figure_manifest},'termination':one('termination'),'record_diagnostics':errors,
            'limitations':['all contact/box/ray identities are evaluator-only oracle queries',
                'raw depth support is separate from oracle contact correspondence',
                'contact midpoint and final-state FK differ; exact first-touch substep is unstored',
                'nearest box face is unstable at the edge relative to observed timing discrepancy',
                'fresh-FK global renders differ from recorded frames; local differences are reported',
                'ray and raster depth disagree near boundaries; no exact semantic mask claim',
                'no post-contact depth; RGB changes are not a measured depth trajectory',
                'visible nearby support is not full shape/free-space/affordance or safe-action coverage',
                'no model call or task primitive after evaluator bootstrap; no controller or gate change']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',required=True);p.add_argument('--figures',required=True);p.add_argument('--summary',required=True)
    args=p.parse_args();result=summarize(args.raw,args.figures)
    Path(args.summary).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['independent_raw_projection_reconstruction'],indent=2))


if __name__=='__main__':main()

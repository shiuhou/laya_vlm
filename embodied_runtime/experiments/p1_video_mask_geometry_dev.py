"""CPU-only fresh geometry for sealed SAM2 video outputs; no new inference."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.recording import replay_frames
from ..perception.surface_association import sensor_view_identity
from ..perception.tracked_mask_geometry import evaluate_tracked_mask
from .p1_flow_mask_tracking_dev import review_panel
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import read, write, seal, verify_seal
from .records import code_identity, file_hash


def read_current_mask(root, row, shape):
    """Preserve rejected raw outputs too, but never create missing model masks."""
    if row['model_evaluation'] != 'EVALUATED':
        require(not row.get('artifact_uri'), 'unevaluated model cannot supply mask')
        return None
    path = Path(row['artifact_uri']).resolve()
    require(path.is_relative_to(Path(root).resolve()) and file_hash(path) == row['artifact_sha256'],
            'video mask artifact changed','SOURCE_MISMATCH')
    with np.load(path,allow_pickle=False) as data:
        mask, logits = data['mask'],data['logits']
        require(mask.dtype == bool and mask.shape == tuple(shape) and logits.shape == (1,1,*shape)
                and np.array_equal(mask,logits[0,0] > 0)
                and sha256(mask.tobytes()).hexdigest() == row['mask_sha256'],
                'current video mask/logit binding differs','SOURCE_MISMATCH')
        if row['status'] == 'TRACKED':
            require(np.isfinite(logits).all() and np.isfinite(data['lowres_logits']).all()
                    and np.isfinite(data['object_score_logits']).all() and (data['object_score_logits'] > 0).all(),
                    'TRACKED mask contradicts raw video admission outputs','SOURCE_MISMATCH')
        return mask.copy()


def run(video_root, output):
    video_root,out = Path(video_root).resolve(),Path(output)
    verify_seal(video_root)
    condition,outputs = read(video_root/'condition.json'),read(video_root/'outputs.json')
    require(condition['condition'] == 'sam2-video-singlemask/1'
            and condition['threshold'] == 0 and condition['max_gap_s'] == .3
            and condition['evaluation_labels_used'] is False and condition['oracle_inputs'] is False
            and outputs['runtime_failure'] is None,'complete declared sensor-only video condition required')
    geometry = Path(condition['geometry'])
    require(file_hash(geometry/'sealed.json') == condition['geometry_seal_sha256'],'initial geometry seal changed')
    verify_seal(geometry)
    recording = Path(condition['recording'])
    require(file_hash(recording/'frames.jsonl') == condition['recording_frames_sha256'],'recording manifest changed')
    decisions = outputs['seed_decisions']
    admitted = [d for d in decisions if d['admitted']]
    keys = [d['hypothesis_id'] for d in admitted]
    require(len(keys) == len(set(keys)) == outputs['hypotheses'],'native hypothesis denominator changed')
    rows = outputs['records']
    expected = {(key,index) for key in keys for index in range(outputs['frames'])}
    actual = [(r['hypothesis_id'],r['frame_index']) for r in rows]
    require(len(actual) == len(set(actual)) and set(actual) == expected,'missing or duplicated video source slots')
    by_slot = {(r['hypothesis_id'],r['frame_index']):r for r in rows}
    sources = condition['source_identities']
    require(len(sources) == outputs['frames'],'source denominator changed')
    bundles = iter(replay_frames(recording))
    out.mkdir(parents=True,exist_ok=False)
    write(out/'condition.json',dict(condition='p1-sealed-video-mask-current-depth-geometry/1',code=code_identity(),
        video_root=str(video_root),video_seal_sha256=file_hash(video_root/'sealed.json'),
        recording=str(recording),recording_frames_sha256=file_hash(recording/'frames.jsonl'),
        geometry_config=config().to_dict(),measurement_contract='tracked-current-mask-depth/1',
        geometry_search_domain='full-frame-masked-depth/1',evaluation_labels_used=False,oracle_inputs=False,
        inference_performed=False,no_native_winner=True,online_freshness_evaluated=False,
        continuous_end_to_end_hz_measured=False,for_execution=False))
    write(out/'seed-decisions.json',decisions)
    counts,first,previous,panels,clocks,timings = Counter(),{},{},[],[],[]
    completed=0
    try:
        with (out/'transitions.jsonl').open('x') as stream:
            for index,source in enumerate(sources):
                envelope,views = next(bundles)
                matching = [v for v in views if sensor_view_identity(v) == source]
                require(len(matching) == 1,'exact recorded current source missing','SOURCE_MISMATCH')
                view = dict(matching[0],frame_id=matching[0]['canonical_frame_id'],episode_id=envelope.episode_id)
                display=[]
                for key in keys:
                    binding = by_slot[key,index]
                    require(binding['source_identity'] == source,'video output source order changed','SOURCE_MISMATCH')
                    mask = read_current_mask(video_root,binding,view['depth_m'].shape)
                    started=time.perf_counter()
                    measurement=evaluate_tracked_mask(view,mask,binding,geometry_config=config(),
                        eef_position_base_m=envelope.payload['proprio']['eef_position_base_m'],
                        track_id=key,feature_id='video-native-support',previous_binding=previous.get(key),max_gap_s=.3)
                    elapsed=time.perf_counter()-started
                    patch=measurement['patch']
                    admission=measurement['admission']
                    effective=dict(binding)
                    if not admission['admitted']:
                        effective.update(status='LOST',reason_codes=[admission['reason']])
                    previous[key]=effective
                    boundary=(binding['reason_codes'][0] if binding['status'] != 'TRACKED' and binding['reason_codes']
                              else admission['reason'] if not admission['admitted'] else
                              patch['reason_codes'][0] if patch['reason_codes'] else
                              'NO_GEOMETRY_CANDIDATE' if not patch['candidates'] else None)
                    row=dict(hypothesis_id=key,source_identity=source,frame_index=index,track=binding,
                        **measurement,first_boundary=boundary,geometry_s=elapsed,
                        candidate_evidence_ids=[] if patch is None else [content_hash(dict(source=source,
                            lineage=key,generation=binding['generation'],point_id=c['point_id'])) for c in patch['candidates']],
                        reference_status='UNKNOWN',verify_status='UNKNOWN',for_execution=False)
                    stream.write(canonical_json(row)+'\n')
                    counts[key+'/'+binding['status']]+=1
                    counts[key+'/'+measurement['geometry_evaluation']]+=1
                    if patch is not None:
                        timings.append(elapsed)
                        counts[key+'/'+patch['geometry_status']]+=1
                        if patch['candidates']:
                            counts[key+'/WITH_GEOMETRY_CANDIDATES']+=1
                    if boundary is not None:
                        first.setdefault(key,dict(frame_index=index,frame_id=source['frame_id'],reason=boundary))
                    display.append((row,mask))
                stream.flush()
                panels.append(review_panel(view,display))
                clocks.append(source['capture_monotonic_ns'])
                completed+=1
        require(next(bundles,None) is None,'recording has unregistered additional frames')
        summary=dict(frames=completed,hypotheses=len(keys),native_seed_decisions=len(decisions),
            matched_denominator=completed*len(keys),counts=dict(counts),first_boundaries=first,
            geometry_s=None if not timings else dict(count=len(timings),p50=float(np.percentile(timings,50)),p95=float(np.percentile(timings,95))),
            reference_status='UNKNOWN',verify_status='UNKNOWN',inference_performed=False,evaluation_labels_used=False,
            online_freshness_evaluated=False,continuous_end_to_end_hz_measured=False,p1_pass_claimed=False,for_execution=False)
        write(out/'summary.json',summary)
        if panels:
            gaps=np.diff(clocks)/1e6
            durations=[max(1,round(float(g))) for g in gaps]+[max(1,round(float(np.median(gaps)))) if len(gaps) else 100]
            panels[0].save(out/'tracked-support-geometry.gif',save_all=True,append_images=panels[1:],duration=durations,loop=0)
            for index in sorted({0,1,min(3,len(panels)-1),len(panels)//2,len(panels)-1}):
                if index < len(panels):
                    panels[index].save(out/f'review-frame-{index:03d}.png')
        seal(out)
        return summary
    except Exception as exc:
        write(out/'failure.json',dict(error=repr(exc),frames_completed=completed,hidden_retry=False))
        seal(out)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    run(a.video,a.output)


if __name__=='__main__':
    main()

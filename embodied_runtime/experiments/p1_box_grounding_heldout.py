"""One fixed sensor-only HO23 A/B experiment; labels belong to separate scoring."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
from ..contracts import content_hash,require
from ..perception.recording import FrameRecorder,replay_frames
from ..perception.surface_association import sensor_view_identity
from ..perception.semantic_output import parse_semantic_reply
from ..perception.semantic_prompt import point_prompt,mask_point_admission
from ..perception.segmented_patch import estimate_segmented_patch
from .p1_semantic_grounding import infer_audited,_load_worker,_explicit_gpu_mask,_cuda_allocation,MODEL_CONTENT_ID
from .p1_identity_prompt import infer_point
from .p1_formal50 import ledger
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import SAM_SETTINGS,read,write,seal,verify_seal
from .records import code_identity,file_hash,versions

CONFIG=Path('configs/p1_box_grounding_heldout_v1.json')
DESIGN=Path('docs/p1-autonomous-box-repair-design.md')
EXPOSURE=Path('/tmp/laya-heldout-exposure-20261008')
SAM_SOURCE_REG=Path('runs/p1/identity-point-sam-20261007/registration.json')


def validate_condition(c):
    from .p1_semantic_grounding import QUERIES
    from .point_grounding_probe import SETTINGS
    require(c['init_indices']==list(range(27,50)) and c['model_calls']==69,'fixed HO23 required')
    require(c['query_A']==c['point_query']==QUERIES['drawer_front_pushable'] and
        c['query_B']=='the exterior front panel of the open top drawer in the small tabletop cabinet','query changed')
    require(c['generation_settings']==SETTINGS and c['frame_retry_count']==0,'decoder/retry changed')


def registration(root):
    root=Path(root);r=read(root/'registration.json')
    require(content_hash({k:v for k,v in r.items() if k!='registration_content_sha256'})==r['registration_content_sha256'],'registration changed')
    validate_condition(r['config'])
    for p,h in r['source_files_sha256'].items():require(file_hash(p)==h,'source changed: '+p)
    require(content_hash(config().to_dict())==r['geometry_config_sha256'],'geometry changed')
    return r


def prepare(root):
    c=read(CONFIG);validate_condition(c);code=code_identity();require(not code['dirty_status'],'freeze execution code first')
    audit=read(EXPOSURE/'audit-summary.json')
    require(not audit['fatal_conflict'] and audit['status']=='NO_PRIOR_OBSERVATION_EXPOSURE_FOUND_IN_AVAILABLE_LOCAL_EVIDENCE','heldout exposure gate failed')
    b=read(SAM_SOURCE_REG);assets=b['environment_receipt']
    paths=[Path(p) for p in code['source_sha256']]+[CONFIG,DESIGN,SAM_SOURCE_REG,Path(assets['checkpoint_path']),
        Path(assets['dependency_lock_path']),Path(assets['environment_record']['freeze_path'])]
    paths.extend(Path(assets['sam_source'])/p for p in b['sam_source_files_sha256'])
    paths.extend(EXPOSURE.glob('*.json'))
    inv=read(EXPOSURE/'init-state-inventory.json');require(file_hash(inv['source'])==inv['source_sha256'],'init source changed');paths.append(Path(inv['source']))
    root=Path(root);root.mkdir(exist_ok=False);shutil.copytree(EXPOSURE,root/'exposure')
    r=dict(condition=c['condition'],config=c,code=code,geometry_config_sha256=content_hash(config().to_dict()),
        model_content_id=MODEL_CONTENT_ID,environment_receipt=assets,sam_settings=SAM_SETTINGS,
        source_files_sha256={str(p.absolute()):file_hash(p) for p in paths},init_source=inv['source'],
        init_source_sha256=inv['source_sha256'],init_state_hashes={str(x['init_index']):x['array_sha256'] for x in inv['state_rows']},
        registered_at_utc=datetime.now(timezone.utc).isoformat(),evaluation_labels_used=False,for_execution=False,
        annotation_inputs=[],hidden_retry=False)
    r['registration_content_sha256']=content_hash(r);write(root/'registration.json',r)


def capture(root):
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_sensor_env import LiberoSensorEnv
    from PIL import Image
    root=Path(root);r=registration(root);c=r['config'];out=root/'capture';out.mkdir(exist_ok=False);(out/'images').mkdir()
    historical=set(read(root/'exposure/historical-rgb-hashes.json')['hashes']);seen=set();rows=[]
    write(out/'process.json',dict(code=code_identity(),versions=versions(),executable=sys.executable,pid=os.getpid(),
        environment={k:os.environ.get(k) for k in ('MUJOCO_GL','MUJOCO_EGL_DEVICE_ID','CUDA_VISIBLE_DEVICES','LIBGL_ALWAYS_SOFTWARE')},
        controls='constructor settling only; no post-reset command'))
    for init in c['init_indices']:
        backend=LiberoWorldBackend.from_task(c['task'],seed=c['seed'],init_state_id=init,
            libero_root='/home/junhongli/projects/LIBERO',config_dir='/tmp/laya-ho23-libero',render=True)
        sensor=None
        try:
            sensor=LiberoSensorEnv(backend.world,camera_names=c['camera_names'],width=c['width'],height=c['height'],
                retained_gripper_command=lambda:'OPEN' if backend.gripper_command()<0 else 'CLOSE')
            folder=root/f'init-{init:03d}'
            with FrameRecorder(folder,episode_id=f'p1-box-ho23/init{init}',clock_domain='ho23/local-process',condition=c['condition']) as recorder:
                bundle=sensor.sensor_port().capture()
                recorder.append(bundle['views'],bundle['proprio'],emitted_monotonic_ns=time.monotonic_ns())
        finally:
            if sensor is not None:sensor.close()
            backend.world.close()
        recorded=list(replay_frames(folder));require(len(recorded)==1,'one capture bundle required');env,views=recorded[0]
        view=next(v for v in views if v['camera_id']==c['model_camera']);refs={x['camera_id']:x['rgb_blob']['sha256'] for x in env.payload['views']}
        blob=refs[c['model_camera']];pixels=hashlib.sha256(view['rgb'].tobytes()).hexdigest()
        path=out/'images'/f'init-{init:03d}.png';Image.fromarray(view['rgb']).save(path)
        # Save failed first capture before enforcing exposure/duplicate checks.
        image=dict(image_id=view['canonical_frame_id'],frame_id=view['canonical_frame_id'],source_frame_id=view['frame_id'],
            episode_id=env.episode_id,init_index=init,camera_id=view['camera_id'],width=c['width'],height=c['height'],
            rgb_blob_sha256=blob,rgb_pixel_sha256=pixels,png_sha256=file_hash(path),image_path=str(path.absolute()))
        canonical=dict(view,frame_id=view['canonical_frame_id'])
        row=dict(input_index=len(rows),image=image,source_identity=sensor_view_identity(canonical),
            recording=str(folder.absolute()),init_state_array_sha256=r['init_state_hashes'][str(init)],
            historical_rgb_duplicate=blob in historical,within_batch_duplicate=pixels in seen)
        write(out/f'init-{init:03d}.json',row);rows.append(row)
        require(not row['historical_rgb_duplicate'] and not row['within_batch_duplicate'],'capture duplicate/exposure: stop without replacement')
        seen.add(pixels);print('captured',init,flush=True)
    recording_hashes={str(p.relative_to(root)):file_hash(p) for init in c['init_indices'] for p in (root/f'init-{init:03d}').rglob('*') if p.is_file()}
    write(out/'manifest.json',dict(config=c,inputs=rows,recording_files_sha256=recording_hashes,
        registration_sha256=file_hash(root/'registration.json'),heldout_duplicate_check='PASS',evaluation_labels_used=False))
    seal(out)


def inputs(root):
    root=Path(root);r=registration(root);verify_seal(root/'capture');m=read(root/'capture/manifest.json')
    require(m['registration_sha256']==file_hash(root/'registration.json') and m['heldout_duplicate_check']=='PASS','capture admission missing')
    for p,h in m['recording_files_sha256'].items():require(file_hash(root/p)==h,'recorded sensor changed')
    result={}
    for row in m['inputs']:
        env,views=next(replay_frames(row['recording']));v=next(v for v in views if v['camera_id']==r['config']['model_camera'])
        v=dict(v,frame_id=v['canonical_frame_id']);require(sensor_view_identity(v)==row['source_identity'],'sensor binding differs')
        result[row['image']['init_index']]=(row,v,env.payload['proprio'])
    require(list(result)==list(range(27,50)),'full canonical23 required')
    return r,result


def grounding(root):
    root=Path(root);r,sensor=inputs(root);out=root/'grounding';out.mkdir(exist_ok=False)
    worker,identity=_load_worker();write(out/'model.json',identity)
    write(out/'condition.json',dict(code=code_identity(),versions=versions(),executable=sys.executable,pid=os.getpid(),
        registration_sha256=file_hash(root/'registration.json'),generation_settings=r['config']['generation_settings'],
        evaluation_labels_used=False,generator_inputs=['full_RGB','registered_query'],calibrated_confidence=None))
    rows=[]
    for init,(src,view,_) in sensor.items():
        kinds=['POINT',*(['A','B'] if init%2==0 else ['B','A'])]
        for kind in kinds:
            query=r['config']['point_query' if kind=='POINT' else 'query_'+kind];stem=f'init-{init:03d}-{kind}'
            def emit(name,value):write(out/f'{stem}-{name}.json',value)
            record=dict(init_index=init,kind=kind,image=src['image'],source_identity=src['source_identity'],query=query,
                status='FAILURE',reason=None,source_admitted=False,point_xy=None,sample_pixel_xy=None,ordered_boxes=[],
                evaluation_labels_used=False,for_execution=False,hidden_retry=False)
            try:
                answer=(infer_point if kind=='POINT' else infer_audited)(worker,view['rgb'],query,emit)
                raw,audit=answer[:2];elapsed=answer[2] if len(answer)>2 else read(out/f'{stem}-raw-output.json').get('inference_s')
                record.update(status='COMPLETE',raw_output=raw,audit=audit,inference_s=elapsed,response_sha256=hashlib.sha256(raw.encode()).hexdigest())
                if audit['complete_generation'] and audit['terminal_eos_observed']:
                    typed=parse_semantic_reply(raw,src['image']['width'],src['image']['height'],mode='point' if kind=='POINT' else 'box',audit=audit)
                    record.update(typed=typed.evidence(),source_admitted=typed.admitted,reason=typed.reason)
                    if typed.admitted:
                        if kind=='POINT':record.update(point_xy=list(typed.selected[0].pixels),sample_pixel_xy=list(typed.selected[0].sample_pixel_xy))
                        else:record['ordered_boxes']=[list(x.pixels) for x in typed.selected]
                else:record['reason']='INCOMPLETE_GENERATION'
            except Exception as exc:
                record.update(reason='INFERENCE_RUNTIME_FAILURE',error=repr(exc));write(out/f'{stem}.json',record);raise
            write(out/f'{stem}.json',record);rows.append(record);print(init,kind,record['reason'] or 'TYPED_ADMITTED',flush=True)
    write(out/'outputs.json',rows);seal(out)


def masks(root):
    import torch
    root=Path(root);r,sensor=inputs(root);verify_seal(root/'grounding');out=root/'masks';out.mkdir(exist_ok=False)
    assets=r['environment_receipt']
    require(os.path.abspath(sys.executable)==os.path.abspath(assets['python_executable']) and torch.__version__=='2.5.1+cu121','SAM env differs')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG')==':4096:8','workspace differs')
    allocation=_cuda_allocation(torch,_explicit_gpu_mask())
    import sam2
    require(Path(sam2.__file__).resolve().is_relative_to(Path(assets['sam_source']).resolve()),'SAM source differs')
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    from .sam2_deterministic_grid import install_and_verify
    torch.manual_seed(1);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
    write(out/'condition.json',dict(code=code_identity(),allocation=allocation,executable=sys.executable,pid=os.getpid(),
        sam_settings=SAM_SETTINGS,registration_sha256=file_hash(root/'registration.json'),grounding_seal_sha256=file_hash(root/'grounding/sealed.json'),evaluation_labels_used=False))
    model=build_sam2(assets['sam_config'],assets['checkpoint_path'],device='cuda:0',apply_postprocessing=False)
    write(out/'dense-grid-equivalence.json',install_and_verify(model))
    predictor=SAM2ImagePredictor(model,mask_threshold=0.,max_hole_area=0.,max_sprinkle_area=0.)
    calls={(x['init_index'],x['kind']):x for x in read(root/'grounding/outputs.json')};rows=[]
    with torch.inference_mode():
        for init,(src,view,_) in sensor.items():
            point=calls[init,'POINT']
            for arm in (['A','B'] if init%2==0 else ['B','A']):
                boxrec=calls[init,arm];boxes=boxrec['ordered_boxes']
                for index,box in enumerate(boxes if boxes else [None]):
                    row=dict(init_index=init,arm=arm,image=src['image'],source_identity=src['source_identity'],box_index=index if box is not None else None,
                        box_xyxy=box,box_query=boxrec['query'],point_query=point['query'],box_response_sha256=boxrec.get('response_sha256'),
                        point_response_sha256=point.get('response_sha256'),status='UPSTREAM_UNAVAILABLE',mask_count=0,hidden_retry=False,
                        evaluation_labels_used=False,for_execution=False,encode_s=None,predict_s=None)
                    stem=f'init-{init:03d}-{arm}-box-{index:03d}'
                    if not boxrec['source_admitted'] or box is None:row['failure_stage']='BOX_'+str(boxrec['reason'])
                    else:
                        prompt=point_prompt(view,box,point,query=r['config']['point_query'],config=config());row['prompt_admission']=prompt
                        if not prompt['admitted']:row['failure_stage']=prompt['reason']
                        else:
                            try:
                                torch.cuda.synchronize();start=time.perf_counter();predictor.set_image(view['rgb'].copy());torch.cuda.synchronize();row['encode_s']=time.perf_counter()-start
                                start=time.perf_counter();logits,scores,lowres=predictor.predict(point_coords=np.asarray([prompt['point_xy']],dtype=np.float32),
                                    point_labels=np.asarray([1],dtype=np.int32),box=np.asarray(box,dtype=np.float32),multimask_output=True,return_logits=True)
                                torch.cuda.synchronize();row['predict_s']=time.perf_counter()-start;native=logits>0.
                                path=out/f'{stem}.npz';np.savez_compressed(path,logits=logits,predicted_ious=scores,lowres_logits=lowres,masks=native)
                                row.update(artifact_uri=str(path.absolute()),artifact_sha256=file_hash(path))
                                require(logits.shape==(3,*view['depth_m'].shape) and scores.shape==(3,) and all(np.isfinite(x).all() for x in (logits,scores,lowres)),'invalid native outputs')
                                row.update(status='COMPLETE',mask_count=3,raw_mask_sha256=[hashlib.sha256(x.tobytes()).hexdigest() for x in native],
                                    predicted_ious=scores.tolist(),native_mask_pixel_counts=[int(x.sum()) for x in native],calibrated_confidence=None,
                                    sam_input_box_float32=np.asarray(box,dtype=np.float32).tolist(),sam_input_point_float32=np.asarray([prompt['point_xy']],dtype=np.float32).tolist())
                            except Exception as exc:
                                row.update(status='RUNTIME_FAILURE',error=repr(exc));write(out/f'{stem}.json',row);raise
                    write(out/f'{stem}.json',row);rows.append(row)
            print('SAM preserved',init,flush=True)
    write(out/'outputs.json',rows);seal(out)


def geometry(root):
    root=Path(root);r,sensor=inputs(root);verify_seal(root/'masks');out=root/'geometry';out.mkdir(exist_ok=False);rows=[]
    write(out/'condition.json',dict(code=code_identity(),versions=versions(),geometry_config=config().to_dict(),
        registration_sha256=file_hash(root/'registration.json'),masks_seal_sha256=file_hash(root/'masks/sealed.json'),
        evaluation_labels_used=False,for_execution=False,measurement_contract='native-mask-depth/2'))
    for record in read(root/'masks/outputs.json'):
        row=dict(record,native_results=[])
        if record['status']=='COMPLETE':
            _,view,proprio=sensor[record['init_index']];require(file_hash(record['artifact_uri'])==record['artifact_sha256'],'mask artifact changed')
            with np.load(record['artifact_uri'],allow_pickle=False) as data:
                require(np.array_equal(data['masks'],data['logits']>0) and len(data['masks'])==3,'native corpus differs')
                for ordinal,native in enumerate(data['masks']):
                    binding=dict(source_identity=record['source_identity'],sensor_view_sha256=content_hash(record['source_identity']),
                        query=record['box_query'],box_index=record['box_index'],box_xyxy=record['box_xyxy'],box_response_sha256=record['box_response_sha256'],
                        mask_index=ordinal,raw_mask_sha256=record['raw_mask_sha256'][ordinal],mask_artifact_uri=record['artifact_uri'],mask_artifact_sha256=record['artifact_sha256'],
                        coordinate_convention='top-left-origin-pixel-xyxy',mask_input_channels=['rgb'],evaluation_labels_used=False,provenance='learned estimate')
                    start=time.perf_counter();estimate=estimate_segmented_patch(view,record['box_xyxy'],native,mask_binding=binding,config=config(),
                        track_id='drawer_front_pushable',feature_id=f"box-{record['box_index']}/mask-{ordinal}",seed=0,
                        eef_position_base_m=proprio['eef_position_base_m'],measurement_contract='native-mask-depth/2')
                    row['native_results'].append(dict(ordinal=ordinal,estimate=estimate,geometry_s=time.perf_counter()-start,
                        stage_ledger=ledger(estimate['patch']),mask_point_admission=mask_point_admission(native,record['prompt_admission'],ordinal)))
        else:row['geometry_evaluation']='NOT_EVALUATED'
        write(out/f"init-{record['init_index']:03d}-{record['arm']}-box-{record['box_index']}.json",row);rows.append(row)
    write(out/'results.json',rows);seal(out)


def launch(root,stage,gpu):
    root=Path(root);r=registration(root);require(gpu.startswith('GPU-'),'GPU UUID required')
    executable=('/home/junhongli/miniforge3/envs/locateanything/bin/python' if stage=='grounding' else r['environment_receipt']['python_executable'])
    cmd=[executable,'-m','embodied_runtime.experiments.p1_box_grounding_heldout',stage,'--output',str(root)]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu,CUBLAS_WORKSPACE_CONFIG=':4096:8',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    started=datetime.now(timezone.utc).isoformat();result=None;timed_out=False
    with (root/f'{stage}-process.log').open('x') as log:
        try:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
        except subprocess.TimeoutExpired:timed_out=True
    write(root/f'{stage}-process.json',dict(command=cmd,started_at_utc=started,ended_at_utc=datetime.now(timezone.utc).isoformat(),
        exit_code=result.returncode if result else None,timeout=timed_out,gpu_uuid=gpu,hidden_retry=False))
    require(not timed_out and result and result.returncode==0,'first process failed; no retry')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','capture','grounding','masks','geometry','launch-grounding','launch-masks']);p.add_argument('--output',required=True);p.add_argument('--gpu-uuid');a=p.parse_args()
    try:
        if a.stage.startswith('launch-'):launch(a.output,a.stage.removeprefix('launch-'),a.gpu_uuid or '')
        else:globals()[a.stage](a.output)
    except Exception as exc:
        out=Path(a.output)/a.stage
        if out.is_dir() and not (out/'sealed.json').exists():
            write(out/'runtime-failure.json',dict(error=repr(exc),hidden_retry=False));seal(out)
        raise
if __name__=='__main__':main()

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from embodied_runtime.experiments import visual_subgoal_probe as probe
from embodied_runtime.experiments.records import file_hash, load_records


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    import cv2
    video = tmp_path/'source.mp4'
    video.write_bytes(b'synthetic sequential video')
    monkeypatch.setattr(probe,'VIDEO_SHA256',file_hash(video))
    class Capture:
        calls = 0
        released = False
        def isOpened(self):
            return True
        def getBackendName(self):
            return 'FFMPEG'
        def get(self,key):
            return {cv2.CAP_PROP_FRAME_WIDTH:960,cv2.CAP_PROP_FRAME_HEIGHT:600,
                    cv2.CAP_PROP_FPS:20.,cv2.CAP_PROP_FRAME_COUNT:344}[key]
        def read(self):
            image = np.zeros((600,960,3),np.uint8)
            image[:,:600] = [self.calls%256,2,3]
            image[:,600:] = [91,92,93]  # forbidden HUD region
            self.calls += 1
            return True,image
        def release(self):
            self.released = True
    cap = Capture()
    monkeypatch.setattr(cv2,'VideoCapture',lambda path,backend:cap)
    output = tmp_path/'inputs'
    manifest = probe.prepare(video,output)
    return SimpleNamespace(directory=output,manifest=manifest,capture=cap)


def test_sequential_exact_frame_crop_excludes_hud_and_retains_lineage(prepared):
    assert prepared.capture.calls == 320 and prepared.capture.released
    assert probe.load_inputs(prepared.directory) == prepared.manifest
    for i,frame in enumerate(probe.FRAMES):
        image = np.asarray(Image.open(prepared.directory/f'rgb-{i}.png'))
        assert image.shape == (600,600,3)
        assert np.all(image == [3,2,frame%256])
    extraction = json.loads((prepared.directory/'extraction.json').read_text())
    assert extraction['zero_based_frame_indices'] == [7,55,135,183,239,319]
    assert extraction['crop_xyxy'] == [0,0,600,600]
    assert prepared.manifest['not_original_control_replay_or_raw_sensor']
    assert prepared.manifest['source_type'] == 'lossy_resampled_primitive_trace_video_reconstruction'
    assert [e['image_index'] for e in prepared.manifest['examples']] == list(range(6))
    for example in prepared.manifest['examples']:
        assert not {'phase','frame','label','oracle','source_frame'} & set(example)


def test_source_hash_rejected_before_decode_or_output(tmp_path,monkeypatch):
    import cv2
    source = tmp_path/'wrong.mp4'
    source.write_bytes(b'wrong')
    monkeypatch.setattr(cv2,'VideoCapture',lambda *a:pytest.fail('must not decode wrong source'))
    with pytest.raises(ValueError,match='source-video identity'):
        probe.prepare(source,tmp_path/'unused')
    assert not (tmp_path/'unused').exists()


@pytest.mark.parametrize('change',['order','prompt','privileged','image','image_field'])
def test_changed_or_augmented_manifest_rejected(prepared,change):
    manifest = deepcopy(prepared.manifest)
    if change=='order':
        manifest['planned_calls'] = list(reversed(manifest['planned_calls']))
    elif change=='prompt':
        manifest['instruction'] += ' Close the gripper.'
    elif change=='privileged':
        manifest['held_state'] = True
    elif change=='image_field':
        manifest['examples'][0]['phase'] = 'approach'
    else:
        Image.new('RGB',(600,600),'red').save(prepared.directory/'rgb-0.png')
    (prepared.directory/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        probe.load_inputs(prepared.directory)


class Processor:
    image_processor = SimpleNamespace(merge_size=2,patch_size=14)
    image_token = 'image'
    tokenizer = SimpleNamespace(model_max_length=512,convert_tokens_to_ids=lambda _:4)
    duplicate_image_token = False
    inject_text_image = False
    def apply_chat_template(self,messages,**kwargs):
        return json.dumps(messages)
    def __call__(self,*,text,images,return_tensors,truncation):
        import torch
        assert truncation is False and return_tensors=='pt'
        is_visual = images is not None or self.inject_text_image
        result = {'input_ids':torch.tensor([[4,4] if self.duplicate_image_token else [4,5] if is_visual else [5,5]]),
                  'attention_mask':torch.ones((1,2),dtype=torch.long)}
        if is_visual:
            result.update(image_grid_thw=torch.tensor([[1,2,2]]),pixel_values=torch.ones((4,10)))
        return result


def test_exact_seven_messages_vary_only_image_item_and_never_read_labels(prepared):
    assert len(probe.PLANNED_CALLS)==7 and probe.PLANNED_CALLS[0]['image_index'] is None
    # No evaluator file exists here; preprocessing can access only input manifest/images.
    processor = Processor()
    calls = [probe.prepare_call(processor,prepared.directory,p,prepared.manifest['examples'])
             for p in probe.PLANNED_CALLS]
    _, text = calls[0]
    assert text['messages'] == [{'role':'user','content':[{'type':'text','text':probe.INSTRUCTION}]}]
    assert text['consumed_pixel_values'] is None and text['image_grid_thw'] is None
    assert text['image_pad_token_count']==0
    for _,visual in calls[1:]:
        assert visual['messages'][0]['content'] == [{'type':'image'},*text['messages'][0]['content']]
        assert visual['consumed_pixel_values']['dtype']=='torch.bfloat16'
        assert visual['image_pad_token_count']==1
        assert not visual['truncation']


@pytest.mark.parametrize('defect',['image_tokens','context','text_image'])
def test_native_input_mismatch_fails_before_generation(prepared,defect):
    processor = Processor()
    planned = probe.PLANNED_CALLS[1]
    if defect=='image_tokens':
        processor.duplicate_image_token = True
    elif defect=='context':
        processor.tokenizer = SimpleNamespace(model_max_length=32,convert_tokens_to_ids=lambda _:4)
    else:
        processor.inject_text_image = True
        planned = probe.PLANNED_CALLS[0]
    with pytest.raises(ValueError):
        probe.prepare_call(processor,prepared.directory,planned,prepared.manifest['examples'])


class Tokenizer:
    all_special_ids = [9]
    def decode(self,ids,skip_special_tokens):
        return ''.join({1:'transport_',2:'object',3:'invalid',9:'' if skip_special_tokens else '<eos>'}[i] for i in ids)


def generation_fixture(ids=(1,2,9),visual=True):
    p = {'input_ids':[4,5,6],'consumed_pixel_values':{'sha256':'pixels','dtype':'torch.bfloat16'} if visual else None,
         'image_grid_thw':[[1,28,28]] if visual else None,'attention_mask':[[1,1,1]]}
    traces = [{'input_ids':[p['input_ids'] if i==0 else [ids[i-1]]],
               'pixel_values':p['consumed_pixel_values'] if i==0 else None,
               'image_grid_thw':p['image_grid_thw'],'attention_mask':p['attention_mask']} for i in range(len(ids))]
    raw = {'generated_ids':list(ids),'sequence_ids':p['input_ids']+list(ids),'forward_traces':traces,
           'raw_decoded_text':Tokenizer().decode(ids,False),'decoded_text':Tokenizer().decode(ids,True)}
    logits = np.zeros((len(ids),10))
    for i,j in enumerate(ids):
        logits[i,j] = 1
    return p,raw,logits


@pytest.mark.parametrize('visual',[False,True])
def test_native_audit_accepts_new_objective_vocabulary_for_text_and_rgb(visual):
    p,raw,logits = generation_fixture(visual=visual)
    result = probe.validate_generation(p,raw,logits,Tokenizer(),9,10)
    assert result['status']=='valid' and result['label']=='transport_object'


@pytest.mark.parametrize('defect',['image','grid','consumed_ids','logits','decode'])
def test_native_audit_still_rejects_consumption_or_greedy_inconsistency(defect):
    p,raw,logits = generation_fixture()
    raw = deepcopy(raw)
    if defect=='image':
        raw['forward_traces'][0]['pixel_values']['sha256']='changed'
    elif defect=='grid':
        raw['forward_traces'][0]['image_grid_thw']=[[1,2,2]]
    elif defect=='consumed_ids':
        raw['forward_traces'][1]['input_ids']=[[2]]
    elif defect=='logits':
        logits[0,3]=2
    else:
        raw['decoded_text']='approach_object'
    with pytest.raises(ValueError):
        probe.validate_generation(p,raw,logits,Tokenizer(),9,10)


@pytest.mark.parametrize('ids',[(3,9),tuple([3]*32),(9,1,2,9)])
def test_invalid_and_incomplete_outputs_remain_outcomes(ids):
    p,raw,logits = generation_fixture(ids)
    result = probe.validate_generation(p,raw,logits,Tokenizer(),9,10)
    assert result['status']=='invalid' and result['label'] is None


def test_preflight_failure_is_preserved(tmp_path,monkeypatch):
    def fail(*args):
        raise ValueError('preflight mismatch')
    monkeypatch.setattr(probe,'_run',fail)
    args = SimpleNamespace(output=tmp_path/'run',mode='preflight',source=tmp_path/'inputs',
                           preflight_source=None,evaluation_sha256='a'*64)
    with pytest.raises(ValueError,match='preflight mismatch'):
        probe.run(args)
    rows,errors = load_records(args.output/'episodes.jsonl')
    assert not errors and [r['kind'] for r in rows]==['run_start','failure']


def test_actual_prepared_inputs_when_available():
    source = Path('runs/autonomous-research/visual-subgoal-inputs-02')
    if not (source/'manifest.json').exists():
        pytest.skip('prepared source unavailable')
    manifest = probe.load_inputs(source)
    assert len(manifest['examples'])==6 and manifest['repeats']==1


def evaluation():
    labels = [['approach_object'],['approach_object','establish_grasp'],['transport_object'],None,None,None]
    return {'examples':[{'image_index':i,'primary_evaluation':i<3,'acceptable_labels':allowed}
                        for i,allowed in enumerate(labels)]}


def calls(labels):
    return [{**planned,'status':'valid','label':label} for planned,label in zip(probe.PLANNED_CALLS,labels)]


def test_only_early_three_scored_and_late_proposals_never_declared_unsafe():
    result = probe.score_calls(calls(['approach_object','approach_object','establish_grasp','transport_object',
                                    'release_object','approach_drawer','advance_drawer']),evaluation())
    assert result['primary_denominator']==3
    assert result['primary_annotation_agreements']==result['primary_useful_accepted_proposals']==3
    assert result['task_only_primary_annotation_agreements']==2
    for row in result['rows'][3:]:
        assert row['annotation_agreement'] is row['useful_accepted_proposal'] is None
        assert row['task_only_annotation_agreement'] is None


def test_all_uncertain_does_not_pass_usefulness():
    result = probe.score_calls(calls(['uncertain']*7),evaluation())
    assert result['primary_useful_accepted_proposals']==0
    assert result['primary_annotation_agreements']==0
    assert result['rgb_uncertain_count']==6


def test_late_gold_labels_or_extra_calls_rejected():
    labels = evaluation()
    labels['examples'][4]['acceptable_labels'] = ['uncertain']
    with pytest.raises(ValueError,match='evaluator scope'):
        probe.score_calls(calls(['uncertain']*7),labels)
    with pytest.raises(ValueError,match='seven completed'):
        probe.score_calls(calls(['uncertain']*7)[:-1],evaluation())

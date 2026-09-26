from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.experiments.visual_target_verification_run import validate_generation


class Tokenizer:
    all_special_ids=[9]

    def decode(self, ids, skip_special_tokens):
        return ''.join({1:'target_',2:'handle',3:'oops',9:'' if skip_special_tokens else '<eos>'}[i] for i in ids)


def fixture(ids=(1,2,9)):
    presentation={'input_ids':[4,5,6], 'consumed_pixel_values':{'sha256':'pixels','dtype':'torch.bfloat16'},
                  'image_grid_thw':[[1,28,28]], 'attention_mask':[[1,1,1]]}
    traces=[]
    for i in range(len(ids)):
        traces.append({'input_ids':[presentation['input_ids'] if i==0 else [ids[i-1]]],
                       'pixel_values':presentation['consumed_pixel_values'] if i==0 else None,
                       'image_grid_thw':presentation['image_grid_thw'],
                       'attention_mask':presentation['attention_mask']})
    raw={'generated_ids':list(ids),'sequence_ids':presentation['input_ids']+list(ids),'forward_traces':traces,
         'raw_decoded_text':Tokenizer().decode(ids,False),'decoded_text':Tokenizer().decode(ids,True)}
    logits=np.zeros((len(ids),10))
    for i,j in enumerate(ids):
        logits[i,j]=1
    return presentation,raw,logits


def test_valid_native_sequence_checks_actual_ids_image_and_raw_logits():
    p,r,scores=fixture()
    result=validate_generation(p,r,scores,Tokenizer(),9,10)
    assert result['status']=='valid' and result['label']=='target_handle' and result['terminal_eos']


@pytest.mark.parametrize('corruption',['image','grid','mask','prefix','consumed_ids','logits','decode'])
def test_corrupt_processor_or_consumed_evidence_fails(corruption):
    p,r,scores=fixture()
    r=deepcopy(r)
    if corruption=='image':
        r['forward_traces'][0]['pixel_values']['sha256']='other'
    elif corruption=='grid':
        r['forward_traces'][0]['image_grid_thw']=[[1,20,20]]
    elif corruption=='mask':
        r['forward_traces'][0]['attention_mask']=[[0,1,1]]
    elif corruption=='prefix':
        r['sequence_ids'][0]=99
    elif corruption=='consumed_ids':
        r['forward_traces'][1]['input_ids']=[[2]]
    elif corruption=='logits':
        scores[0,3]=2
    else:
        r['decoded_text']='other_handle'
    with pytest.raises(ValueError):
        validate_generation(p,r,scores,Tokenizer(),9,10)


def test_invalid_label_and_budget_exhaustion_are_outcomes_not_infrastructure_errors():
    p,r,scores=fixture((3,9))
    result=validate_generation(p,r,scores,Tokenizer(),9,10)
    assert result['status']=='invalid' and result['terminal_eos']
    p,r,scores=fixture(tuple([3]*32))
    result=validate_generation(p,r,scores,Tokenizer(),9,10)
    assert result['status']=='invalid' and result['length_limit_reached'] and result['no_terminal_eos']


def test_unexpected_special_token_is_not_salvaged():
    p,r,scores=fixture((9,1,2,9))
    result=validate_generation(p,r,scores,Tokenizer(),9,10)
    assert result['status']=='invalid' and result['unexpected_special_token']


def test_image_token_loss_detected_before_inference(tmp_path):
    import torch
    from PIL import Image
    from types import SimpleNamespace
    from embodied_runtime.experiments.visual_target_verification_run import prepare_image
    Image.fromarray(np.zeros((20,20,3),np.uint8)).save(tmp_path/'image.png')
    class Processor:
        image_processor=SimpleNamespace(merge_size=2,patch_size=14)
        image_token='image'
        tokenizer=SimpleNamespace(model_max_length=512,convert_tokens_to_ids=lambda _:4)
        duplicate=False
        def apply_chat_template(self,*args,**kwargs):
            return 'fixed prompt'
        def __call__(self,**kwargs):
            return {'input_ids':torch.tensor([[4,4] if self.duplicate else [4,5]]),
                    'attention_mask':torch.ones((1,2),dtype=torch.long),
                    'image_grid_thw':torch.tensor([[1,2,2]]),'pixel_values':torch.ones((4,10))}
    processor=Processor()
    example={'source_index':0,'marked_artifact':'image.png','marked_sha256':'hash'}
    _,presentation=prepare_image(processor,tmp_path,example)
    assert presentation['image_pad_token_count']==1
    processor.duplicate=True
    with pytest.raises(ValueError,match='image token count'):
        prepare_image(processor,tmp_path,example)


def test_preflight_startup_failure_is_preserved(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from embodied_runtime.experiments import visual_target_verification_run as m
    from embodied_runtime.experiments.records import load_records
    def fail(*args):
        raise ValueError('processor startup failure')
    monkeypatch.setattr(m,'_run',fail)
    args=SimpleNamespace(output=str(tmp_path/'run'),mode='preflight',source=str(tmp_path/'inputs'),preflight_source=None)
    with pytest.raises(ValueError,match='processor startup'):
        m.run(args)
    rows,diagnostics=load_records(tmp_path/'run'/'episodes.jsonl')
    assert not diagnostics and [r['kind'] for r in rows]==['run_start','failure']
    assert rows[-1]['data']['retries']==0

from hashlib import sha256

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments.p1_video_mask_geometry_dev import read_current_mask
from embodied_runtime.experiments.records import file_hash


def test_sealed_mask_reader_preserves_failures_and_rejects_false_tracked(tmp_path):
    mask=np.zeros((8,12),bool)
    mask[2:6,3:9]=True
    logits=np.where(mask,1.,-1.).astype(np.float32)[None,None]
    path=tmp_path/'frame.npz'
    np.savez_compressed(path,mask=mask,logits=logits,lowres_logits=logits,object_score_logits=np.array([-1.]))
    row=dict(model_evaluation='EVALUATED',artifact_uri=str(path),artifact_sha256=file_hash(path),
             mask_sha256=sha256(mask.tobytes()).hexdigest(),status='LOST')
    assert np.array_equal(read_current_mask(tmp_path,row,mask.shape),mask)
    with pytest.raises(ProtocolError,match='contradicts raw'):
        read_current_mask(tmp_path,dict(row,status='TRACKED'),mask.shape)
    assert read_current_mask(tmp_path,dict(model_evaluation='NOT_EVALUATED'),mask.shape) is None
    with pytest.raises(ProtocolError,match='unevaluated model'):
        read_current_mask(tmp_path,dict(row,model_evaluation='NOT_EVALUATED'),mask.shape)


def test_mask_logits_relation_cannot_be_relabelled(tmp_path):
    mask=np.ones((8,12),bool)
    path=tmp_path/'frame.npz'
    np.savez_compressed(path,mask=mask,logits=np.full((1,1,8,12),-1.))
    row=dict(model_evaluation='EVALUATED',artifact_uri=str(path),artifact_sha256=file_hash(path),
             mask_sha256=sha256(mask.tobytes()).hexdigest(),status='LOST')
    with pytest.raises(ProtocolError,match='mask/logit binding'):
        read_current_mask(tmp_path,row,mask.shape)

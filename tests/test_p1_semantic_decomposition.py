import numpy as np
from embodied_runtime.experiments.p1_semantic_decomposition import human_prompt, admit


def test_annotation_prompt_exact_padded_edt_and_row_major_ties():
    for mask in (np.ones((4,6),dtype=bool), np.array([[1,1,0],[1,0,1],[1,1,1]],dtype=bool)):
        p=human_prompt(mask)
        padded=np.pad(mask,1);inside=np.argwhere(padded);outside=np.argwhere(~padded)
        distances=((inside[:,None,:]-outside[None,:,:])**2).sum(axis=2).min(axis=1)
        v,u=inside[np.argmax(distances)]-1
        assert p['point_xy']==[u+.5,v+.5]
        assert p['annotation_clearance_pixels']==np.sqrt(distances.max())
    assert human_prompt(np.ones((4,6),dtype=bool))['box_xyxy']==[0,0,6,4]


def test_box_incompatibility_keeps_human_point_without_clamping():
    mask=np.ones((4,6),dtype=bool);p=human_prompt(mask);view={'depth_m':np.ones((4,6))}
    result=admit(view,[3,0,6,4],p)
    assert not result['admitted'] and result['reason']=='POINT_OUTSIDE_ORIGINAL_BOX'
    assert result['point_xy']==p['point_xy']
    result=admit(view,p['box_xyxy'],p)
    assert result['admitted'] and result['evaluation_labels_used'] and not result['for_execution']

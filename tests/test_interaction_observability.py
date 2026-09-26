import inspect

import pytest

from embodied_runtime.experiments.interaction_observability import (
    RobotSensors, analyze, prefix, validate_seed,
)


def test_fixed_native_prefix_has_only_registered_jaw_intervention():
    a,b = prefix('close'),prefix('open_hold')
    assert len(a)==len(b)==17
    assert [(i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]==[(13,'close','hold')]
    with pytest.raises(ValueError):
        prefix('recovery')


def test_semantic_seed_requires_image_binding_roles_and_inbounds_pixels():
    seed = {'image_sha256':'image', 'provenance':'human_RGB_only_before_close',
        'points':[{'role':role,'pixel_xy':[2,3]} for role in
                  ('bottle_landmark_1','bottle_landmark_2','table_reference')]}
    assert validate_seed(seed,'image',(20,20,3))==seed
    with pytest.raises(ValueError):
        validate_seed(seed,'other',(20,20,3))
    seed['points'][0]['pixel_xy']=[30,3]
    with pytest.raises(ValueError):
        validate_seed(seed,'image',(20,20,3))


def test_sensor_reader_and_analyzer_have_no_oracle_dependencies():
    reader = inspect.getsource(RobotSensors)
    assert '.features(' not in reader and '.contact' not in reader
    assert 'holding\': None' in reader
    analysis = inspect.getsource(analyze)
    assert 'evaluator-only' not in analysis and 'labels.json' not in analysis
    assert 'retention_label\':None' in analysis

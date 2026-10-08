from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_flow_mask_tracking_dev as runner
from test_p1_automatic_patch_tracking import fixture


def test_native_admission_preserves_ordinals_and_exact_source(tmp_path):
    _, view, records = fixture(tmp_path)
    seeds, decisions = runner.native_seeds(records, view)
    assert [s['native_mask_ordinal'] for s in seeds] == [0, 2]
    assert len(decisions) == 3 and decisions[1]['reason'] == 'POINT_MASK_CONTRADICTION'
    with pytest.raises(ProtocolError, match='first-frame'):
        runner.native_seeds(records, dict(view, frame_seq=99))


def test_geometry_receives_only_current_depth_under_current_support(monkeypatch):
    view = dict(depth_m=np.full((10, 12), 1.234), intrinsics_K=np.eye(3), T_base_camera=np.eye(4),
                frame_id='current/9', calibration_version='cal', capture_sim_time_s=3., capture_monotonic_ns=3000000000)
    mask = np.zeros((10, 12), bool)
    mask[2:8, 3:9] = True
    seen = {}
    def estimate(depth, k, transform, **kwargs):
        seen.update(depth=depth, **kwargs)
        return SimpleNamespace(to_dict=lambda: {})
    monkeypatch.setattr(runner, 'estimate_visible_patch', estimate)
    runner.fresh_geometry(view, mask, [3, 2, 9, 8], {'eef_position_base_m': [0, 0, 0]}, 'native-2')
    assert np.isnan(seen['depth'][~mask]).all() and np.all(seen['depth'][mask] == 1.234)
    assert np.all(view['depth_m'] == 1.234)
    assert seen['source_frame_id'] == 'current/9' and seen['capture_monotonic_ns'] == 3000000000
    assert np.array_equal(seen['depth_availability_mask'], mask)

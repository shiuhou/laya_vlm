"""Delayed seed safety: real history only, bounded retention and honest clocks."""
import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.rgbd_history import RGBDHistory


def frame(seq, *, wall=None, depth=.5):
    return dict(episode_id='episode', camera_id='frontview', frame_id=f'f{seq}', frame_seq=seq,
        calibration_version='cal', capture_sim_time_s=seq*.1,
        capture_monotonic_ns=seq*100_000_000 if wall is None else wall, frame='robot_base',
        rgb=np.random.default_rng(4).integers(0, 255, (64, 64, 3), dtype=np.uint8),
        depth_m=np.full((64, 64), depth, dtype=np.float32),
        intrinsics_K=np.array([[100., 0, 32], [0, 100., 32], [0, 0, 1]]), T_base_camera=np.eye(4))


def history(**kw):
    return RGBDHistory('episode', 'frontview', **dict(max_frames=10, max_bytes=1_000_000,
                                                    max_age_s=5., **kw))


def catch(buffer, source, clock=lambda: (.2, 200_000_000)):
    return buffer.catch_up(source, (20.,20.,44.,44.), query='drawer front', clock=clock)


def test_owned_pixels_authentic_clocks_and_current_check_after_replay():
    buffer = history()
    original = frame(0)
    source = buffer.append(original)
    original['depth_m'][:] = np.nan
    original['rgb'][:] = 0
    buffer.append(frame(1))
    buffer.append(frame(2))
    owned = buffer._frames[0][1]
    with pytest.raises(ValueError):
        owned['depth_m'].setflags(write=True)
    with pytest.raises(TypeError):
        owned['frame_seq'] = 50
    calls = []
    result = catch(buffer, source, lambda: (calls.append('checked') or .2, 200_000_000))
    assert result.current_eligible and calls == ['checked']
    assert [t.capture_monotonic_ns for t in result.transitions] == [0,100_000_000,200_000_000]
    assert all(t.status == 'TRACKED' for t in result.transitions)
    assert len({t.track_generation for t in result.transitions}) == 1
    assert result.tracker.current.capture_sim_time_s == .2
    stale = catch(buffer, source, lambda: (1., 1_000_000_000))
    assert not stale.current_eligible and stale.reason == 'LATEST_FRAME_STALE'
    assert stale.tracker.current.capture_monotonic_ns == 200_000_000


@pytest.mark.parametrize('bound', ['frames', 'bytes', 'age'])
def test_capacity_eviction_never_replaces_missing_source(bound):
    sample = frame(0)
    size = sum(sample[k].nbytes for k in ('rgb','depth_m','intrinsics_K','T_base_camera'))
    args = dict(max_frames=10,max_bytes=1_000_000,max_age_s=5.)
    args.update({'frames':dict(max_frames=1),'bytes':dict(max_bytes=size),
                 'age':dict(max_age_s=.05)}[bound])
    buffer = RGBDHistory('episode','frontview',**args)
    source = buffer.append(sample)
    buffer.append(frame(1))
    assert len(buffer) == 1 and buffer.retained_bytes == size
    with pytest.raises(ProtocolError,match='exact seed source'):
        catch(buffer,source)


@pytest.mark.parametrize('failure', ['gap', 'lost'])
def test_gap_or_loss_stops_catchup_without_reappearance_reseed(failure):
    buffer = history()
    source = buffer.append(frame(0))
    buffer.append(frame(1,wall=600_000_000) if failure == 'gap' else frame(1,depth=np.nan))
    buffer.append(frame(2,wall=700_000_000))
    result = catch(buffer,source,lambda: pytest.fail('clock must not certify failed lineage'))
    assert not result.current_eligible and len(result.transitions) == 2
    assert result.transitions[-1].status == 'LOST'
    assert result.reason == ('TRACKING_GAP' if failure == 'gap' else 'DEPTH_OR_GEOMETRY_INCONSISTENT')
    assert result.retained_frame_ids == ('f0','f1','f2')


def test_cross_camera_out_of_order_and_false_source_rejected():
    buffer = history()
    source = buffer.append(frame(0))
    with pytest.raises(ProtocolError,match='episode/camera'):
        buffer.append(dict(frame(1),camera_id='wrist'))
    with pytest.raises(ProtocolError,match='order'):
        buffer.append(frame(0))
    with pytest.raises(ProtocolError,match='exact seed source'):
        catch(buffer,'0'*64)
    with pytest.raises(ProtocolError,match='current clock'):
        catch(buffer,source,lambda:(-1.,0))


def test_recorded_canonical_identity_matches_tracker_lineage():
    buffer = history()
    source = buffer.append(dict(frame(0), canonical_frame_id='episode/front/0'))
    result = catch(buffer,source,lambda:(0.,0))
    assert result.current_eligible
    assert result.transitions[0].frame_id == 'episode/front/0'
    assert result.retained_frame_ids == ('episode/front/0',)

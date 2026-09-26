import inspect

import numpy as np

from embodied_runtime.experiments.depth_support_probe import directional_diagnostic, separate_depth


def test_depth_split_has_no_oracle_and_partitions_all_valid_pixels():
    assert set(inspect.signature(separate_depth).parameters)=={'depth', 'box'}
    depth = np.array([[1, 1, 1, 1], [2, 2, 2, 2]], dtype=float)
    r = separate_depth(depth, [0, 0, 4, 2])
    assert r['foreground_indices']==[0, 1, 2, 3]
    assert r['background_indices']==[4, 5, 6, 7]
    assert r['gap_m']==1
    assert set(r['foreground_indices']) | set(r['background_indices']) == set(r['valid_indices'])


def test_depth_ties_lower_split_and_unknown_insufficient_support():
    r = separate_depth(np.ones((2, 4)), [0, 0, 4, 2])
    assert r['split_rank']==3 and r['zero_gap_ambiguous']
    assert r['foreground_indices']==[0, 1, 2]
    assert separate_depth(np.ones((1, 5)), [0, 0, 5, 1])['status']=='unknown'
    depth = np.array([[np.nan, 0, 6, 1, 1, 1]])
    assert separate_depth(depth, [0, 0, 6, 1])['valid_count']==3


def test_minimum_size_ignores_single_far_outlier():
    depth = np.array([1]*10+[2]*10+[5], float).reshape(3, 7)
    r = separate_depth(depth, [0, 0, 7, 3])
    assert r['foreground_count']==10 and r['background_count']==11


def test_direction_sets_keep_ties_and_report_worst_regret():
    r = directional_diagnostic([1, 1, 0], [0, 0, 0], [1, 0, 0])
    assert r['preferred_set']==['x+', 'y+']
    assert r['oracle_preferred_set']==['x+']
    assert r['preferred_sets_intersect'] and not r['preferred_sets_equal']
    assert not r['all_preferred_improve']
    assert r['regret_min_mm']==0 and r['regret_max_mm']>10
    assert directional_diagnostic(None, [0, 0, 0], [1, 0, 0])=={'status': 'unknown'}


def test_at_target_hold_preferred():
    r = directional_diagnostic([0, 0, 0], [0, 0, 0], [0, 0, 0])
    assert r['preferred_set']==['hold'] and r['regret_max_mm']==0

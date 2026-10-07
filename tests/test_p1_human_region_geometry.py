from embodied_runtime.experiments.p1_human_region_geometry import frame_report


def test_early_plane_rejection_does_not_fabricate_tool_failure_or_semantic_success():
    patch=dict(geometry_status='UNKNOWN',reason_codes=['INSUFFICIENT_PLANE_SUPPORT'],candidates=[],
        metrics=dict(component_sizes=[100],fitted_point_count=100,plane_support_ratio=.4,
                     uncertainty_calibrated=False))
    r=frame_report(patch)
    assert r['first_rejection']=='INSUFFICIENT_PLANE_SUPPORT'
    assert r['erosion_m'] is None and r['candidate_rejection_counts'] is None
    assert r['stage_ledger']['tool_candidate_gates']=='NOT_EVALUATED'
    assert 'semantic_source_admission' not in r['stage_ledger'] and r['for_execution'] is False


def test_valid_local_plane_with_zero_tool_points_is_rejected_at_tool_gate():
    patch=dict(geometry_status='VALID',reason_codes=['NO_TOOL_INTERIOR_CANDIDATE'],candidates=[],
        metrics=dict(component_sizes=[100],fitted_point_count=90,boundary_point_count=30,
          position_sigma_m=.003,erosion_m=.016,grid_cell_count=20,
          candidate_rejection_counts={'insufficient_edge_margin':20},uncertainty_calibrated=False))
    r=frame_report(patch)
    assert r['geometry_status']=='VALID' and r['tool_interior_candidate_count']==0
    assert r['first_rejection']=='NO_TOOL_INTERIOR_CANDIDATE'
    assert r['stage_ledger']['tool_candidate_gates']=='REJECTED'

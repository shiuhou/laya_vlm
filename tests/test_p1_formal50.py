from embodied_runtime.experiments.p1_formal50 import ledger


def test_ambiguity_preserves_downstream_not_evaluated():
    stages = ledger({"reason_codes": ["AMBIGUOUS_DEPTH_COMPONENTS"],
                     "metrics": {"component_sizes": [400, 380]}})
    assert stages["depth_components"] == "REJECTED"
    assert stages["plane_local_geometry"] == "NOT_EVALUATED"
    assert stages["tool_candidate_gates"] == "NOT_EVALUATED"


def test_no_tool_candidate_is_not_a_plane_failure():
    stages = ledger({"reason_codes": ["NO_TOOL_INTERIOR_CANDIDATE"], "metrics": {
        "component_sizes": [400], "fitted_point_count": 400, "boundary_point_count": 90,
        "position_sigma_m": .002, "candidate_rejection_counts": {"insufficient_edge_margin": 20}}})
    assert stages["plane_local_geometry"] == "EVALUATED"
    assert stages["tool_candidate_gates"] == "REJECTED"


def test_measured_sigma_does_not_imply_later_uncertainty_gate_ran():
    stages = ledger({"reason_codes": ["ERODED_PLANE_DEGENERATE"], "metrics": {
        "component_sizes": [400], "fitted_point_count": 400, "boundary_point_count": 90,
        "position_sigma_m": .002}})
    assert stages["visible_boundary"] == "REJECTED"
    assert stages["uncertainty"] == "NOT_EVALUATED"

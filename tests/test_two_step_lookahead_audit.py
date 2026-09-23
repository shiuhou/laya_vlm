from embodied_runtime.experiments.two_step_lookahead_audit import (
    classification,
    physical_first_actions,
)


def test_open_hold_alias_is_one_physical_first_action():
    assert physical_first_actions({"open": {}, "hold": {}}, -1.) == {"hold"}
    assert physical_first_actions({"close": {}, "hold": {}}, 1.) == {"hold"}


def test_witness_classification_counts_physical_first_actions():
    assert classification({}, -1.) == "NO VALID WITNESS"
    assert classification({"open": {}, "hold": {}}, -1.) == "SINGLE VALID FIRST-STEP WITNESS"
    assert classification({"open": {}, "hold": {}, "z-3mm": {}}, -1.) == (
        "MULTIPLE VALID FIRST-STEP WITNESSES"
    )

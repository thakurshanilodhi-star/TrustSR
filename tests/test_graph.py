import pytest
from trustsr.graph import classify_contamination, quarantine_set

EDGES = [("M1", "D1"), ("M2", "D1"), ("D1", "P1"), ("P1", "A1"), ("M2", "D2"), ("D2", "P2"), ("M1", "S1")]


def observed(missing):
    return [e for e in EDGES if e not in missing]


def test_complete_graph_flags_all_descendants():
    r = classify_contamination(EDGES, ["M2"])
    assert r["potentially_contaminated"] == ["A1", "D1", "D2", "P1", "P2"] and r["unknown_unverified"] == []


def test_missing_internal_edge_marks_endpoint_and_descendants_unknown():
    r = classify_contamination(observed([("D1", "P1")]), ["M2"], [("D1", "P1")])
    assert r["unknown_unverified"] == ["A1", "P1"]


def test_both_source_edges_declared_is_fully_covered():
    miss = [("M2", "D1"), ("M2", "D2")]
    r = classify_contamination(observed(miss), ["M2"], miss)
    assert quarantine_set(r) >= {"D1", "D2", "P1", "P2", "A1", "M2"}


def test_undeclared_missing_edges_are_not_seen():
    miss = [("M2", "D1"), ("M2", "D2")]
    r = classify_contamination(observed(miss), ["M2"], [])   # nobody told the policy
    assert r["potentially_contaminated"] == [] and r["unknown_unverified"] == []


def test_unaffected_branch_costs_unknowns():
    r = classify_contamination(observed([("M1", "S1")]), ["M2"], [("M1", "S1")])
    assert "S1" in r["unknown_unverified"]


def test_isolated_endpoint_of_missing_edge_still_unknown():
    r = classify_contamination([("A", "B")], ["A"], [("X", "Y")])
    assert r["unknown_unverified"] == ["Y"]


def test_cycles_terminate():
    r = classify_contamination([("A", "B"), ("B", "A"), ("B", "C")], ["A"])
    assert r["potentially_contaminated"] == ["B", "C"]


def test_inconsistent_missing_edge_rejected():
    with pytest.raises(ValueError):
        classify_contamination(EDGES, ["M2"], [("D1", "P1")])


def test_malformed_inputs_rejected():
    for args in (([("A",)], ["A"]), ([("A", 1)], ["A"]), ([("A", "B")], []), ([("A", "B")], [1])):
        with pytest.raises(ValueError):
            classify_contamination(*args)


def test_bare_strings_are_rejected_not_split_into_characters():
    import pytest
    from trustsr.graph import classify_contamination
    with pytest.raises(ValueError):
        classify_contamination([("A", "B")], "AB")          # would otherwise poison nodes "A" and "B"
    with pytest.raises(ValueError):
        classify_contamination("AB", ["A"])
    with pytest.raises(ValueError):
        classify_contamination([("A", "B")], ["A"], declared_missing_edges="CD")

from trustsr.contamination import detect_contamination

def test_clean_state_is_not_contaminated():
    assert detect_contamination({"x": 1}, {"x": 1})["contaminated"] is False

def test_changed_missing_and_extra_keys_detected():
    result = detect_contamination({"x": 1, "y": 2}, {"x": 9, "z": 3})
    assert result["changed_keys"] == ["x"]
    assert result["missing_keys"] == ["y"]
    assert result["extra_keys"] == ["z"]
    assert result["contaminated"] is True

from trustsr.audit import AuditLog


def test_empty_log_invalid_by_default():
    assert AuditLog().verify() is False
    assert AuditLog().verify(require_nonempty=False) is True


def test_valid_chain_and_head():
    log = AuditLog(); log.append("a", {"n": 1}); log.append("b", {"n": 2})
    assert log.verify() and log.verify(trusted_head=log.head)


def test_truncation_detected_with_trusted_head():
    log = AuditLog(); log.append("a", {}); log.append("b", {}); head = log.head
    log._events.pop()
    assert log.verify() is True            # internally consistent...
    assert log.verify(trusted_head=head) is False  # ...but not the trusted head


def test_tampered_event_detected():
    log = AuditLog(); log.append("a", {"n": 1})
    log._events[0].details["n"] = 2
    assert log.verify() is False


def test_caller_mutation_after_append_does_not_alter_log():
    log = AuditLog(); d = {"n": 1}; log.append("a", d); d["n"] = 99
    assert log.verify() and log.events[0].details == {"n": 1}


def test_non_json_details_rejected():
    import pytest
    with pytest.raises(ValueError):
        AuditLog().append("a", {"x": float("nan")})


def test_mutating_event_returned_by_append_does_not_change_log():
    log = AuditLog()
    returned = log.append("a", {"nested": {"n": 1}})
    returned.details["nested"]["n"] = 99
    assert log.verify()
    assert log.events[0].details == {"nested": {"n": 1}}


def test_mutating_event_details_from_events_accessor_does_not_change_log():
    log = AuditLog()
    log.append("a", {"nested": {"n": 1}})
    exposed = log.events
    exposed[0].details["nested"]["n"] = 99
    assert log.verify()
    assert log.events[0].details == {"nested": {"n": 1}}


def test_mutating_event_list_copy_does_not_change_log():
    log = AuditLog()
    log.append("a", {"n": 1})
    exposed = log.events
    exposed[0].details["n"] = 2
    assert log.verify()
    assert log.events[0].details == {"n": 1}

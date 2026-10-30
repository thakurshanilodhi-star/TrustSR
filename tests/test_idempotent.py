import pytest
from trustsr.idempotent import IdempotentReceiver, ConflictError


def test_retry_after_lost_ack_is_noop():
    r = IdempotentReceiver()
    assert r.store("e1", {"n": 1}) == "stored"
    assert r.store("e1", {"n": 1}) == "duplicate" and len(r) == 1


def test_conflicting_payload_rejected():
    r = IdempotentReceiver(); r.store("e1", {"n": 1})
    with pytest.raises(ConflictError):
        r.store("e1", {"n": 2})
    assert len(r) == 1


def test_bad_event_ids_rejected():
    for bad in ("", None, 3):
        with pytest.raises(ValueError):
            IdempotentReceiver().store(bad, {})


def test_reconcile():
    r = IdempotentReceiver(); r.store("a", {}); r.store("z", {})
    rep = r.reconcile(["a", "b", "b"])
    assert rep == {"missing": ["b"], "unexpected": ["z"], "intended_has_duplicates": True}


def test_concurrent_retries_create_exactly_one_record():
    import threading
    from trustsr.idempotent import IdempotentReceiver
    r, results, lock = IdempotentReceiver(), [], threading.Lock()

    def worker():
        out = r.store("evt", {"n": 1})
        with lock:
            results.append(out)
    threads = [threading.Thread(target=worker) for _ in range(40)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert len(r) == 1 and results.count("stored") == 1 and results.count("duplicate") == 39

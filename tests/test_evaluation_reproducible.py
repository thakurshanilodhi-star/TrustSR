"""The synthetic comparison must be reproducible: same code -> same decisions (keys are ephemeral)."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCENARIOS = ["clean", "contaminated_state", "incomplete_scope", "audit_tampered", "missing_recovery_events"]
EXPECTED_FAILED_GATES = {"clean": [], "contaminated_state": ["contamination_removed"], "incomplete_scope": ["scope_complete"],
                         "audit_tampered": ["audit_valid"], "missing_recovery_events": ["recovery_complete"]}


def _load():
    spec = importlib.util.spec_from_file_location("run_synthetic_evaluation", ROOT / "experiments" / "run_synthetic_evaluation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _decisions(mod):
    from trustsr.verification import verify_recovery
    out = {}
    for name in SCENARIOS:
        report = verify_recovery(**mod.build_case(name))
        out[name] = (report["decision"], sorted(k for k, v in report["gates"].items() if not v))
    return out


def test_decisions_are_identical_across_runs_with_fresh_keys():
    mod = _load()
    first, second = _decisions(mod), _decisions(mod)
    assert first == second
    assert first["clean"][0] == "PASS"
    for name, failed in EXPECTED_FAILED_GATES.items():
        # each corrupted scenario must fail at least its intended gate (others may fail as a consequence)
        assert set(failed) <= set(first[name][1]), (name, first[name])
        assert (first[name][0] == "PASS") == (name == "clean")

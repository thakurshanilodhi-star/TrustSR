"""The package's graph policy must agree with the Lab 01.4 notebook implementation."""
import contextlib, io, json, os, pathlib, tempfile
import pytest
from trustsr.graph import classify_contamination

NB = pathlib.Path(__file__).resolve().parent.parent / "labs/01_contamination/TRUSTSR_Lab_01_4_Ground_Truth_Independent_Uncertainty_Policy.ipynb"


def test_graph_policy_matches_lab_01_4():
    matplotlib = pytest.importorskip("matplotlib"); matplotlib.use("Agg")
    pytest.importorskip("pandas"); pytest.importorskip("networkx")
    nb = json.load(open(NB, encoding="utf-8")); cwd = os.getcwd(); os.chdir(tempfile.mkdtemp())
    ns = {"__name__": "__main__", "display": print}
    try:
        for cell in nb["cells"]:
            if cell["cell_type"] != "code":
                continue
            src = "".join(l for l in "".join(cell["source"]).splitlines(True) if not l.lstrip().startswith(("%", "!")))
            if "results = [evaluate_scenario" in src:
                # load the scenario list but stop before the notebook's own evaluation/assertions
                exec(src.split("results = [evaluate_scenario")[0], ns)
                break
            with contextlib.redirect_stdout(io.StringIO()):
                exec(src, ns)
        for name, missing in ns["scenarios"]:
            observed = ns["build_observed_graph"](missing)
            lab_potential, lab_unknown = ns["conservative_observed_graph_policy"](observed, ns["POISON_SOURCE"], missing)
            pkg = classify_contamination(list(observed.edges()), [ns["POISON_SOURCE"]], missing)
            assert set(pkg["potentially_contaminated"]) == set(lab_potential), name
            assert set(pkg["unknown_unverified"]) == set(lab_unknown), name
    finally:
        os.chdir(cwd)

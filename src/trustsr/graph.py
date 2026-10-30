"""Dependency-graph contamination propagation with an explicit uncertainty boundary.

Ported from Lab 01.4 (ground-truth-independent policy). Inputs are only the *observed*
dependency edges, the known poison source(s) and the *declared* missing edges. Nothing
here discovers missing edges: an undeclared missing edge is invisible (see Lab 01.7).
"""
from collections import deque
from typing import Iterable

Edge = tuple[str, str]


def _adjacency(edges: Iterable[Edge]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for edge in edges:
        if not (isinstance(edge, (tuple, list)) and len(edge) == 2 and all(isinstance(n, str) for n in edge)):
            raise ValueError(f"Edge must be a (source, dependent) pair of strings: {edge!r}")
        u, v = edge
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set())
    return adj


def descendants(adj: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    queue = deque([start])
    while queue:
        for nxt in adj.get(queue.popleft(), ()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def classify_contamination(observed_edges: Iterable[Edge], poison_sources: Iterable[str],
                           declared_missing_edges: Iterable[Edge] = ()) -> dict[str, list[str]]:
    """Return ``confirmed``, ``potentially_contaminated`` and ``unknown_unverified`` node lists.

    * confirmed: the declared poison source(s).
    * potentially_contaminated: reachable from a source in the observed graph.
    * unknown_unverified: for every declared missing edge (u, v), v and everything reachable
      from v in the observed graph, unless already confirmed/potential.

    Everything in the three lists must be treated as untrusted (fail closed). Raises
    ``ValueError`` if a "missing" edge is actually present in the observed edges, or if
    inputs are malformed.
    """
    for name, value in (("observed_edges", observed_edges), ("declared_missing_edges", declared_missing_edges),
                        ("poison_sources", poison_sources)):
        if isinstance(value, (str, bytes)):
            raise ValueError(f"{name} must be a collection, not a bare string")
    edges = list(observed_edges)
    missing = list(declared_missing_edges)
    sources = set(poison_sources)
    if not sources or not all(isinstance(s, str) for s in sources):
        raise ValueError("poison_sources must be a non-empty collection of strings")
    adj = _adjacency(edges)
    _adjacency(missing)  # validates shape
    present = {tuple(e) for e in edges}
    clash = [tuple(e) for e in missing if tuple(e) in present]
    if clash:
        raise ValueError(f"Declared missing edges are present in the observed graph: {clash}")

    potential: set[str] = set()
    for source in sources:
        potential |= descendants(adj, source)
    potential -= sources
    unknown: set[str] = set()
    for _, v in missing:
        unknown.add(v)
        unknown |= descendants(adj, v)
    unknown -= potential | sources
    return {"confirmed": sorted(sources), "potentially_contaminated": sorted(potential),
            "unknown_unverified": sorted(unknown)}


def quarantine_set(classification: dict[str, list[str]]) -> set[str]:
    """Nodes that must not be trusted: confirmed + potential + unknown."""
    return set().union(*classification.values())

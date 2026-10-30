"""Contamination detection against an explicitly supplied clean reference state."""
from typing import Any


def detect_contamination(reference: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    """Return changed/missing/extra keys. This is a comparison, not a causal detector."""
    ref_keys, obs_keys = set(reference), set(observed)
    changed = sorted(k for k in ref_keys & obs_keys if reference[k] != observed[k])
    missing = sorted(ref_keys - obs_keys)
    extra = sorted(obs_keys - ref_keys)
    return {"contaminated": bool(changed or missing or extra), "changed_keys": changed, "missing_keys": missing, "extra_keys": extra}


def normalize_keys(keys: Any) -> list[str] | None:
    """Return a sorted, de-duplicated key list, ``None`` for "all keys", or raise ``TypeError``.

    A bare string is rejected: ``sorted(set("mode"))`` would silently become four one-letter keys.
    """
    if keys is None:
        return None
    if isinstance(keys, (str, bytes)) or not isinstance(keys, (list, tuple, set, frozenset)) \
            or not all(isinstance(k, str) for k in keys):
        raise TypeError("keys must be a list/tuple/set of strings (or None for full recovery)")
    return sorted(set(keys))

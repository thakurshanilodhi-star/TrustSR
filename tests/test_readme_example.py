"""The README's minimal example must run as written (guards against documentation drift)."""
import pathlib, re

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def test_readme_minimal_example_executes_and_uses_an_independent_head():
    text = README.read_text(encoding="utf-8")
    block = re.search(r"## Minimal example\s+```python\n(.*?)```", text, re.S).group(1)
    assert "trusted_audit_head=log.head" not in block, "example must not pass the log's own head"
    assert "HeadAnchor" in block and "anchor.load()" in block
    exec(compile(block, "README.md", "exec"), {"__name__": "__readme__"})

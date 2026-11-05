"""The README's minimal example must run as written (guards against documentation drift)."""
import pathlib, re

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def test_readme_minimal_example_executes_and_uses_an_independent_head():
    text = README.read_text(encoding="utf-8")
    
    # Seedhe "## Minimal example" heading ke baad wala python block pakdo
    match = re.search(r"##\s+Minimal\s+example\s*```python\s*\r?\n(.*?)```", text, re.S | re.IGNORECASE)
    assert match is not None, "Could not find '## Minimal example' python code block in README.md"
    
    target_block = match.group(1)
    
    assert "trusted_audit_head=log.head" not in target_block, "example must not pass the log's own head"
    assert "HeadAnchor" in target_block and "anchor.load()" in target_block
    
    exec(compile(target_block, "README.md", "exec"), {"__name__": "__readme__"})

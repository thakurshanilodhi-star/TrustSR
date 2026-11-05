"""The README's minimal example must run as written (guards against documentation drift)."""
import pathlib, re

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def test_readme_minimal_example_executes_and_uses_an_independent_head():
    text = README.read_text(encoding="utf-8")
    
    # Sabhi python code blocks ko nikal lo
    python_blocks = re.findall(r"```python\s*\r?\n(.*?)```", text, re.S)
    assert len(python_blocks) > 0, "README.md must contain at least one python code block"
    
    # Woh block dhundho jisme TrustSR ka minimal example likha hai
    target_block = None
    for block in python_blocks:
        if "generate_keypair" in block and "verify_recovery" in block:
            target_block = block
            break
            
    assert target_block is not None, "Could not find the TrustSR minimal example code block in README.md"
    
    assert "trusted_audit_head=log.head" not in target_block, "example must not pass the log's own head"
    assert "HeadAnchor" in target_block and "anchor.load()" in target_block
    
    exec(compile(target_block, "README.md", "exec"), {"__name__": "__readme__"})

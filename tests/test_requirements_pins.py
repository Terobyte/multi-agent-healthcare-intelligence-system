def test_databricks_vectorsearch_pinned():
    """Block 2 of requirements2.md mandates databricks-vectorsearch>=0.40."""
    lines = open("requirements.txt").read().splitlines()
    hits = [l for l in lines if l.strip().lower().startswith("databricks-vectorsearch")]
    assert hits, "databricks-vectorsearch missing from requirements.txt"
    # Confirm a version pin >= 0.40 (>=, ==, ~=, or explicit 0.4x+)
    assert any(">=0.4" in l or "==0.4" in l or "~=0.4" in l for l in hits), f"version pin too loose: {hits}"

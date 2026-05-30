from app.grounding import (
    search_bible,
    validate_verse_reference,
    verify_and_ground_verses,
    build_scripture_context
)

print("\n── Semantic search: 'God loves us' ──")
results = search_bible("God loves us", top_k=3)
for r in results:
    print(f"  {r['reference']} (score: {r['score']}): {r['text'][:60]}...")

print("\n── Verse validation ──")
tests = ["John 3:16", "Exodus 45:12", "John 25:3", "Genesis 1:1", "Fake 99:99"]
for ref in tests:
    v = validate_verse_reference(ref)
    status = "VALID" if v['valid'] else f"INVALID — {v['reason']}"
    print(f"  {ref}: {status}")

print("\n── Hallucination guard ──")
result = verify_and_ground_verses(["John 3:16", "Exodus 45:12", "Philippians 4:13"])
print("  Verified:", [v['reference'] for v in result['verified']])
print("  Rejected:", [v['reference'] for v in result['rejected']])

print("\n── Scripture context for prompt ──")
ctx = build_scripture_context("anxiety and worry")
print(ctx)
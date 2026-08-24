from knowledge_base import KB

kb = KB()

print("=" * 60)
print("KNOWLEDGE BASE CONTENTS")
print("=" * 60)

print("\n=== REGISTERED MODELS ===")
models = kb.get_all_models()
for m in models:
    print(f"  - {m}")
    info = kb.get_model_info(m)
    if info:
        for k, v in info.items():
            print(f"      {k}: {v}")

print("\n=== DOCUMENTATION ===")
docs = kb.get_all_docs()
for d in docs:
    print(f"\n--- {d} ---")
    content = kb.read_doc(d)
    if content:
        print(content[:500] if len(content) > 500 else content)

print("\n=== LEARNINGS ===")
status = kb.get_status()
print(f"Total learnings: {status.get('learnings', 0)}")

print("\n=== SHARED CONTEXT ===")
ctx = kb.get_all_context()
for k, v in ctx.items():
    print(f"  {k}: {v}")

print("\n=== SYSTEM STATUS ===")
print(kb.get_status())
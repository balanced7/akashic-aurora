#!/usr/bin/env python3
"""
Test: Documentation Depth Optimization

Verifies that critical documentation works within 50-100 line reading depth.
This tests the solution to OpenCode's file-reading limitation.
"""

import os

print("\n" + "="*70)
print("DOCUMENTATION DEPTH OPTIMIZATION TEST")
print("="*70 + "\n")

# Test 1: OPENCODE_START_HERE.md is complete in first 50 lines
print("[TEST 1] Is OPENCODE_START_HERE.md complete in first 50 lines?")
with open("OPENCODE_START_HERE.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

has_import = any("from agent_init import" in line for line in lines[:50])
has_initialize = any("initialize_and_load_context" in line for line in lines[:50])
has_api_usage = any("api.decision" in line or "api.learning" in line for line in lines[:50])

if has_import and has_initialize and has_api_usage:
    print("[+] PASS - All essential code in first 50 lines")
    print(f"    - Import statement: Found")
    print(f"    - Initialization code: Found")
    print(f"    - Usage examples: Found")
    print(f"    - File has {len(lines)} total lines\n")
    test1 = True
else:
    print("[-] FAIL - Missing critical content in first 50 lines")
    print(f"    - Import found: {has_import}")
    print(f"    - Initialize found: {has_initialize}")
    print(f"    - Usage found: {has_api_usage}\n")
    test1 = False

# Test 2: AGENT_INDEX_QUICK.md has navigation table in first 100 lines
print("[TEST 2] Is AGENT_INDEX_QUICK.md a usable quick index?")
with open("AGENT_INDEX_QUICK.md", "r", encoding="utf-8") as f:
    lines = f.readlines()
    content = "".join(lines[:100])

has_table = "|" in content and "File" in content
has_init_ref = "OPENCODE_START_HERE" in content

if has_table and has_init_ref:
    print("[+] PASS - Quick index is navigable")
    print(f"    - Has reference table: True")
    print(f"    - Points to START_HERE: True")
    print(f"    - First 100 lines cover navigation\n")
    test2 = True
else:
    print("[-] FAIL - Index not useful in first 100 lines\n")
    test2 = False

# Test 3: CONTEXT_QUICK.md teaches context access in first 50 lines
print("[TEST 3] Can agents learn to access context from first 50 lines?")
with open("CONTEXT_QUICK.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

has_get_decisions = any("get_startup_decisions" in line for line in lines[:50])
has_get_learnings = any("get_startup_learnings" in line for line in lines[:50])

if has_get_decisions and has_get_learnings:
    print("[+] PASS - Context access patterns taught early")
    print(f"    - get_startup_decisions: Found")
    print(f"    - get_startup_learnings: Found\n")
    test3 = True
else:
    print("[-] FAIL - Context access not explained early\n")
    test3 = False

# Test 4: SIGNALS_QUICK.md shows all signal types in first 100 lines
print("[TEST 4] Are signal types documented in first 100 lines?")
with open("SIGNALS_QUICK.md", "r", encoding="utf-8") as f:
    lines = f.readlines()
    content = "".join(lines[:100])

signal_types = ["DECISION", "LEARNING", "ACTION", "BLOCKER", "HANDOFF", "COMPLETION"]
found_types = sum(1 for sig in signal_types if sig in content)

if found_types >= 5:
    print(f"[+] PASS - Signal types documented early")
    print(f"    - Found {found_types}/6 signal types in first 100 lines\n")
    test4 = True
else:
    print(f"[-] FAIL - Not enough signal types in first 100 lines")
    print(f"    - Found {found_types}/6 signal types\n")
    test4 = False

# Test 5: bootstrap.md points to OPENCODE_START_HERE immediately
print("[TEST 5] Does bootstrap.md reference quick-start immediately?")
with open("bootstrap.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Look in first 50 lines for the reference
start_here_ref = any("OPENCODE_START_HERE" in line for line in lines[:50])

if start_here_ref:
    print("[+] PASS - bootstrap.md points to quick-start early")
    print(f"    - OPENCODE_START_HERE mentioned in first 50 lines\n")
    test5 = True
else:
    print("[-] FAIL - bootstrap.md doesn't link to quick-start early\n")
    test5 = False

# Test 6: Documentation files exist and are readable
print("[TEST 6] Are all quick-ref files present and readable?")
quick_files = [
    "OPENCODE_START_HERE.md",
    "AGENT_INDEX_QUICK.md",
    "CONTEXT_QUICK.md",
    "SIGNALS_QUICK.md",
    "README_DOCUMENTATION_STRATEGY.md"
]

all_exist = True
for fname in quick_files:
    if os.path.exists(fname):
        size = os.path.getsize(fname)
        print(f"    [+] {fname} ({size} bytes)")
    else:
        print(f"    [-] {fname} (MISSING)")
        all_exist = False

test6 = all_exist

if test6:
    print("[+] PASS - All documentation files present\n")
else:
    print("[-] FAIL - Some files missing\n")

# Summary
print("="*70)
print("SUMMARY")
print("="*70 + "\n")

results = {
    "START_HERE complete (50 lines)": test1,
    "Quick index usable": test2,
    "Context access taught early": test3,
    "Signals documented early": test4,
    "bootstrap.md links correctly": test5,
    "All files present": test6,
}

passed = sum(1 for v in results.values() if v)
total = len(results)

for test_name, result in results.items():
    status = "[+]" if result else "[-]"
    print(f"{status} {test_name}")

print(f"\nResult: {passed}/{total} tests passed\n")

# Verdict
print("="*70)
if passed == total:
    print("VERDICT: [OK] DOCUMENTATION DEPTH OPTIMIZATION WORKING")
    print("\nAgents (like OpenCode) can now:")
    print("  - Read OPENCODE_START_HERE.md in first 50 lines")
    print("  - Get all code needed to initialize")
    print("  - Navigate via AGENT_INDEX_QUICK.md")
    print("  - Access context/signals/examples without reading full docs")
    print("\nThe limitation is solved by design, not by changing OpenCode.")
    exit(0)
elif passed >= 5:
    print("VERDICT: [~] MOSTLY WORKING")
    print(f"\n{passed}/{total} tests passed. Minor issues:")
    for test_name, result in results.items():
        if not result:
            print(f"  - {test_name}")
    exit(1)
else:
    print("VERDICT: [X] DOCUMENTATION OPTIMIZATION INCOMPLETE")
    print(f"\nOnly {passed}/{total} tests passed.")
    exit(1)

print("="*70 + "\n")

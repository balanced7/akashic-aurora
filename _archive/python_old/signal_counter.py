import json
import glob
import os
from collections import Counter, defaultdict


FRAMEWORK_TYPES = {"decision", "blocker", "handoff", "completion"}
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_logs")


def count_signals(filepath):
    by_type = Counter()
    errors = 0
    sessions = defaultdict(int)

    with open(filepath, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                signal = json.loads(line)
            except json.JSONDecodeError:
                errors += 1
                continue

            signal_type = signal.get("type", "unknown")
            by_type[signal_type] += 1
            session = signal.get("session", "unknown")
            sessions[session] += 1

    return by_type, errors, sessions


def main():
    jsonl_files = glob.glob(os.path.join(LOG_DIR, "*.jsonl"))

    if not jsonl_files:
        print(f"No .jsonl files found in {LOG_DIR}")
        return

    all_by_type = Counter()
    total_errors = 0
    total_signals = 0
    file_counts = {}

    for filepath in sorted(jsonl_files):
        by_type, errors, sessions = count_signals(filepath)
        fname = os.path.basename(filepath)
        file_total = sum(by_type.values())
        file_counts[fname] = file_total
        all_by_type += by_type
        total_errors += errors
        total_signals += file_total
        print(f"[{fname}] {file_total:>5} signals, {errors} parse errors")

    print()
    print("=" * 56)
    print("  SIGNAL COUNTER REPORT")
    print("=" * 56)
    print()
    print("  Files analyzed:")
    for fname, count in sorted(file_counts.items()):
        pct = 100 * count / max(total_signals, 1)
        print(f"    {fname:<40s} {count:>5} ({pct:5.1f}%)")
    print(f"    {'-' * 48}")
    print(f"    {'TOTAL':<40s} {total_signals:>5}")

    print()
    print("  Signals by type:")
    framework_found = {t: 0 for t in FRAMEWORK_TYPES}
    other_types = {}
    for sig_type, count in sorted(all_by_type.items(), key=lambda x: -x[1]):
        pct = 100 * count / max(total_signals, 1)
        if sig_type in FRAMEWORK_TYPES:
            framework_found[sig_type] = count
        else:
            other_types[sig_type] = count
        print(f"    {sig_type:<40s} {count:>5} ({pct:5.1f}%)")

    print()
    framework_total = sum(framework_found.values())
    if framework_total > 0:
        print(f"  Framework signals count:")
        for sig_type in sorted(FRAMEWORK_TYPES):
            c = framework_found[sig_type]
            print(f"    {sig_type:<40s} {c:>5}")
        print(f"    {'-' * 48}")
        print(f"    {'FRAMEWORK TOTAL':<40s} {framework_total:>5}")
    else:
        print(f"  No framework-signal files (DECISION/BLOCKER/HANDOFF/COMPLETION)")
        print(f"  found in existing logs. This is expected -- these are OpenCode")
        print(f"  session logs with their own type taxonomy.")

    print()
    print(f"  Parse errors: {total_errors}")
    print(f"  Total signals across all files: {total_signals}")
    print()

    if total_errors > 0:
        print("  !! Some lines failed to parse as JSON.")
        print()

    if other_types:
        print("  Patterns:")
        print(f"    Most common type:  {max(other_types, key=other_types.get)}")
        print(f"    Least common type: {min(other_types, key=other_types.get)}")
        print(f"    Unique type count: {len(other_types)}")


if __name__ == "__main__":
    main()

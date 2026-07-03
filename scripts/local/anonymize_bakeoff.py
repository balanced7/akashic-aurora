#!/usr/bin/env python3
"""Anonymize bakeoff drafts before grading (blind-ish review discipline).

Copies research/bakeoff/<model>/<task>.md to research/bakeoff/anon/<task>/<LETTER>.md
with model identifiers scrubbed from the text, and seals the letter->model mapping in
MAPPING-do-not-open-until-scored.json. The grader reads only anon/, locks scores, then
opens the mapping. Letters are assigned per-task via a content hash (deterministic,
no randomness source needed; not inferable without the originals at hand -- honest
label: this blinds convenience-peeking, not a determined grader who wrote the harness).
"""
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAKE = os.path.join(REPO, "research", "bakeoff")
ANON = os.path.join(BAKE, "anon")
SCRUB = [r"glm[-\s]?4\.?7[-\s]?flash", r"qwen3[-\s]?coder(?::?30b)?", r"gpt[-\s]?oss(?::?20b)?",
         r"bakeoff_[a-z0-9-]+"]


def main() -> int:
    models = [d for d in os.listdir(BAKE)
              if os.path.isdir(os.path.join(BAKE, d)) and d not in ("anon", "tasks")]
    mapping = {}
    for model in models:
        mdir = os.path.join(BAKE, model)
        for name in os.listdir(mdir):
            if not name.endswith(".md"):
                continue
            task = name[:-3]
            with open(os.path.join(mdir, name), encoding="utf-8") as f:
                text = f.read()
            for pat in SCRUB:
                text = re.sub(pat, "[model]", text, flags=re.IGNORECASE)
            letter = "ABCDEFGH"[int(hashlib.sha256((model + task).encode()).hexdigest(), 16) % 8]
            tdir = os.path.join(ANON, task)
            os.makedirs(tdir, exist_ok=True)
            # collision fallback: walk forward until free
            base = letter
            i = 0
            while os.path.exists(os.path.join(tdir, letter + ".md")):
                i += 1
                letter = "ABCDEFGH"[("ABCDEFGH".index(base) + i) % 8]
            with open(os.path.join(tdir, letter + ".md"), "w", encoding="utf-8") as f:
                f.write(text)
            mapping.setdefault(task, {})[letter] = model
    with open(os.path.join(ANON, "MAPPING-do-not-open-until-scored.json"), "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=1)
    print(f"anonymized {sum(len(v) for v in mapping.values())} draft(s) across {len(mapping)} task(s) -> {ANON}")
    print("grade anon/<task>/<LETTER>.md, lock scores, THEN open the mapping.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

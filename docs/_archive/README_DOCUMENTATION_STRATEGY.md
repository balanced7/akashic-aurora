# Documentation Strategy: Depth-Optimized for Agents

## The Problem

Agents (like OpenCode) read files with limited depth—typically 50-100 lines per file. This means:
- Large detailed documentation gets truncated
- Agents may not read the full context they need
- System appears broken when it's actually just documentation-limited

## The Solution

**Design documentation in layers optimized for reading depth.**

### Layer 1: QUICK (50-100 lines) ✓ Agents READ THIS
Operational guides that fit entirely in first 50-100 lines:
- `OPENCODE_START_HERE.md` - Initialization + basic use
- `AGENT_INDEX_QUICK.md` - Index of quick references
- `CONTEXT_QUICK.md` - How to access loaded context
- `SIGNALS_QUICK.md` - What signals to emit

**Strategy:** Everything an agent needs to operate is in the first 50 lines.

### Layer 2: REFERENCE (200-400 lines) - Agents MIGHT read
Complete guides with examples, for agents who want more detail:
- `AGENT_ONBOARDING.md` - Full onboarding guide
- `AGENT_INIT_QUICK_START.md` - Detailed initialization examples
- `LEARNING_SYSTEM_QUICKSTART.md` - Learning examples

**Strategy:** Optimize the first 100 lines to be self-contained, details below.

### Layer 3: COMPREHENSIVE (500+ lines) - Humans read
Detailed architecture and design docs:
- `FRAMEWORK_PROTOCOL.md` - Full system architecture
- `LEARNING_SYSTEM_PHASE_1.md` - Complete learning system design
- `PHASE_1_CHECKPOINT.md` - Full work summary

**Strategy:** No depth limit here. These are reference material for understanding.

## How to Apply This

### When creating a new document:
1. **Put the most critical info in lines 1-50**
2. **Make lines 1-50 fully functional on their own**
3. **Put examples and details after line 50**
4. **Link to other quick-refs for related topics**

### When writing "quick" versions:
- Remove all background/history
- Remove rationale/reasoning (assume already decided)
- Put code examples first, explanation after
- Link to comprehensive versions for deep dives

### When writing "comprehensive" versions:
- No depth restrictions
- Include background, rationale, design decisions
- Deep technical details welcome
- Reference quick versions for quick access patterns

## Navigation Pattern

All documents should have this structure:

```markdown
# Document Title

**Quick Summary (1-3 lines)** - Agent reads this

## If you just need code:
[Code examples here - 20-30 lines]

---

## If you want to understand more:
[Detailed explanation starts here]

---

## For deep dives:
See [Other Document] for [Topic]
```

## Example: OPENCODE_START_HERE.md

This file is the model. It:
- ✓ Fits in 50 lines
- ✓ Has everything to initialize
- ✓ Has complete code examples
- ✓ Points to detailed docs at bottom
- ✓ No fluff or background

## Directory Organization

```
E:\AI-Setup\
├─ OPENCODE_START_HERE.md         ← Agent reads first
├─ AGENT_INDEX_QUICK.md           ← Navigation for what-they-need
├─ CONTEXT_QUICK.md               ← How to access context
├─ SIGNALS_QUICK.md               ← What signals exist
├─ AGENT_ONBOARDING.md            ← Fuller guide (100+ lines)
├─ AGENT_INIT_QUICK_START.md      ← Initialization examples
├─ bootstrap.md                    ← Entry point (now optimized)
└─ [Detailed reference docs]       ← For humans/learning
```

## Testing This Works

When OpenCode (or any agent) runs:
1. It reads bootstrap.md (150 lines, gets oriented)
2. It reads OPENCODE_START_HERE.md (50 lines, gets code)
3. It imports and initializes (has everything needed)
4. It loads context and works

If this works, the strategy is validated.

## Migration Path

Existing docs don't need to be "quick" unless agents use them. Priority:
1. ✅ OPENCODE_START_HERE.md (done)
2. ✅ AGENT_INDEX_QUICK.md (done)
3. ✅ CONTEXT_QUICK.md (done)
4. ✅ SIGNALS_QUICK.md (done)
5. ⏳ Optimize AGENT_ONBOARDING.md (put examples first, explanation after)
6. ⏳ Optimize AGENT_INIT_QUICK_START.md (move TL;DR to top)
7. ⏳ Create LEARNING_QUICK.md (how to record learnings)

## For Future Phases

When Phase 2 adds automated summaries:
- Summaries themselves can be quick-refs (always <100 lines by design)
- Keep detailed rundown as reference
- Summaries point agents to quick-ref docs

When Phase 3 adds intelligent patterns:
- Pattern recommendations = quick-refs
- Pattern details = comprehensive docs

## Why This Works

Instead of fighting OpenCode's constraints (which we can't change), we **design for them**:
- Agents get what they need in first 50 lines ✓
- Agents can dive deeper if curious ✓
- Documentation is scannable and organized ✓
- System appears to work (because it does) ✓

This is not a limitation workaround—it's good documentation design.

---

**Document Status:** Strategy document (non-code)  
**Last Updated:** 2026-06-16  
**Applies To:** All documentation going forward

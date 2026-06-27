# Documentation Archive - Historical & Superseded Docs

**Last Updated**: 2026-06-17  
**Count**: 94 archived documents  

This directory contains documentation that is superseded, historical, or from exploratory phases.

## Why Archive Instead of Delete?

These documents contain valuable learnings and context about how the system was designed and evolved. They're preserved for:
- Historical understanding
- Finding solutions to similar problems
- Understanding design decisions
- Reference during troubleshooting

## What's Current

**Active Documentation** (in `docs/current/`):
```
├── bootstrap.md                         # Entry point
├── SYSTEMS_ARCHITECTURE.md              # System design
├── IMPLEMENTATION_INVENTORY.md          # Build plan
├── ACTUAL_INVENTORY.md                  # Reality check
├── CONSOLIDATION_WITH_SEMANTICS.md      # This consolidation
├── FRAMEWORK_PROTOCOL.md                # System protocols
├── SIGNAL_REFERENCE.md                  # Signal types
├── CONTEXT_SCHEMA.md                    # Context structure
├── LEARNING_SYSTEM_QUICKSTART.md        # Learning guide
├── LEARNING_SYSTEM_INDEX.md             # Learning navigation
├── PHASE_1_CHECKPOINT.md                # What we built
├── SYSTEM_STATUS.md                     # Current status
├── ERROR_HANDLING_GUIDE.md              # Error patterns
├── BOOTSTRAP_MANIFEST.md                # Doc maintenance
├── SEMANTIC_NAMING_CONVENTION.md        # Code style
└── AGENT_ONBOARDING.md                  # Agent guide
```

## How to Use This Archive

**If You See a Doc Name You Recognize**:
1. Check if it's superseded in `docs/current/`
2. If you need detailed historical context, refer to archived version
3. Update current version if new learnings apply
4. Don't rely on archived docs as primary source

**Example**:
- Question: "How do agents get initialized?"
- Use: `docs/current/AGENT_ONBOARDING.md` (current)
- Reference: `_archive/INITIALIZATION_GUIDE.md` etc. (if needed for context)

## Archive Contents by Category

**System Design** (many variants, consolidated to SYSTEMS_ARCHITECTURE.md):
- ARCHITECTURE.md
- ARCHITECTURE_UNIFIED_2026.md
- FRAMEWORK_FOUNDATION_SUMMARY.md
- etc.

**Agent/Bootstrap Variants** (consolidated to AGENT_ONBOARDING.md):
- AGENT_*.md (10+ files)
- BOOTSTRAP_*.md (8+ files)
- NEW_AGENT_INSTRUCTIONS.md
- etc.

**Session/Context Variants** (consolidated to SYSTEM_STATUS.md):
- SESSION_*.md (12+ files)
- CONTEXT_QUICK.md (note: CONTEXT_SCHEMA.md is kept, similar is archived)
- etc.

**Integration Variants** (consolidated to SYSTEMS_ARCHITECTURE.md):
- INTEGRATION_*.md (6+ files)
- COMPLETE_SYSTEM_INTEGRATION.md
- etc.

**Learning System Variants** (consolidated to LEARNING_SYSTEM_QUICKSTART.md):
- LEARNING_SYSTEM_*.md (5+ files - only QUICKSTART and INDEX kept)
- SYNC_INTEGRATION_*.md
- etc.

**Historical/Exploratory**:
- Various analysis docs from exploratory phases
- Strategic roadmap documents
- Engineering assessments
- etc.

---

## Consolidation Philosophy

**Why Archive Instead of Delete?**
- Preserve intellectual history
- Enable future reference
- Reduce active doc clutter
- Keep current docs authoritative

**Maintenance Rule**:
- Primary docs in `docs/current/` are canonical
- Archive is read-only historical record
- New learnings update current docs, not archive
- Archive stays frozen (except for new additions)

---

**Archive is historical reference. Use `docs/current/` for active guidance.**

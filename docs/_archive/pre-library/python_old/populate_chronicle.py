#!/usr/bin/env python3
"""
Populate Chronicle - Initial History Reconstruction
=================================================

Populates chronicle with reconstructed history from logs.
"""

from chronicle import Chronicle

def main():
    c = Chronicle()
    
    print("Populating chronicle...")
    
    # ============ MILESTONES (High-Level) ============
    c.milestone(
        'Session Logger v1',
        'Single-file JSONL logging with Redis backup',
        tags=['logging', 'infrastructure']
    )
    
    c.milestone(
        'Dual-Write System',
        'Primary + Backup JSONL files for fault tolerance',
        tags=['logging', 'reliability', 'fault-tolerance']
    )
    
    c.milestone(
        'MCP Server Creation',
        'Created ai_setup_mcp.py for AI context access',
        tags=['multi-agent', 'mcp']
    )
    
    c.milestone(
        'Learning Store Unification',
        'Consolidated 5 learning modules into single store.py',
        tags=['architecture', 'consolidation']
    )
    
    c.milestone(
        'Session Archive System',
        'Migrated logs to date-based archive with auto-tagging',
        tags=['logging', 'architecture']
    )
    
    c.milestone(
        'Chronicle System',
        'Three-tier logging: milestones, decisions, failures',
        tags=['documentation', 'chronology']
    )
    
    # ============ ARCHITECTURE DECISIONS ============
    c.decision(
        'Redis for State Management',
        'Use Redis as primary state store for all agents',
        context='Multi-agent system needs shared state',
        rationale=[
            'Fast access (sub-millisecond)',
            'Built-in data structures (hashes, sorted sets)',
            'Persistence via RDB/AOF',
            'Already running for other services'
        ],
        alternatives=[
            {'name': 'SQLite', 'status': 'rejected', 'reason': 'No multi-agent access'},
            {'name': 'File-based', 'status': 'rejected', 'reason': 'Race conditions'},
            {'name': 'Custom server', 'status': 'rejected', 'reason': 'Overkill'}
        ]
    )
    
    c.decision(
        'JSONL for Logging',
        'Human-readable JSON Lines format for logs',
        context='Need crash-recoverable logging with searchability',
        rationale=[
            'Easy to parse and search',
            'Append-only (crash safe)',
            'Human readable for debugging',
            'Can be processed line-by-line'
        ],
        alternatives=[
            {'name': 'Binary format', 'status': 'rejected', 'reason': 'Harder to debug'},
            {'name': 'SQLite', 'status': 'rejected', 'reason': 'Single writer limitation'}
        ]
    )
    
    c.decision(
        'Dual-Write Logging',
        'Write to both primary and backup JSONL files',
        context='OpenCode agents forget to log, need failsafe',
        rationale=[
            'Fault tolerance if one write fails',
            'Agent non-compliance protection',
            'Console fallback if files unavailable'
        ]
    )
    
    c.decision(
        'Auto-Tagging Sessions',
        'Auto-generate tags from keywords in entries',
        context='Need quick filtering without manual tagging',
        rationale=[
            'Consistent tagging',
            'No additional agent burden',
            'Pattern-based accuracy'
        ]
    )
    
    # ============ APPROACHES ============
    c.approach('logging', 'Single JSONL file', status='tried')
    c.approach('logging', 'Single JSONL + Redis backup', status='succeeded',
        learnings=['Redis provides persistence but needs file backup'])
    c.approach('logging', 'Dual JSONL files (primary + backup)', status='succeeded',
        learnings=['Backup catches failures when primary has issues'])
    
    c.approach('architecture', 'Multiple learning modules', status='failed',
        learnings=['Too many modules, hard to maintain', 'Consolidate into single store'])
    c.approach('architecture', 'Unified learning store', status='succeeded',
        learnings=['Single interface, shared Redis patterns', 'Easier to query and maintain'])
    
    # ============ FAILURES ============
    c.failure(
        'logging', 'Dual-write race condition',
        'Parallel ThreadPoolExecutor writes caused corruption',
        'Switched to sequential writes',
        learnings=['Thread safety requires locks or sequential writes']
    )
    
    c.failure(
        'logging', 'Agents forget to log',
        'No enforcement, depends on agent discipline',
        'Added failsafe() and manual_log() for catch-up',
        learnings=['Build redundant systems for agent non-compliance']
    )
    
    c.failure(
        'architecture', 'Too many learning modules',
        '5 separate files with overlapping functionality',
        'Consolidated into single learning/store.py',
        learnings=['Simpler is better, avoid premature abstraction']
    )
    
    c.failure(
        'logging', 'Old log format hard to search',
        'Mixed entry formats, no consistent tagging',
        'Migrated to unified format with auto-tagging',
        learnings=['Plan format upfront to avoid migration later']
    )
    
    # ============ NARRATIVES ============
    c.narrative(
        'Evolution of Session Logging',
        summary='How we went from simple single-file logging to robust multi-tier system',
        chapters=[
            {'event': 'v1', 'description': 'Single JSONL file with Redis backup'},
            {'event': 'v2', 'description': 'Added dual-write for fault tolerance'},
            {'event': 'v3', 'description': 'Added failsafe() for agent non-compliance'},
            {'event': 'v4', 'description': 'Auto-tagging and session archive'},
            {'event': 'v5', 'description': 'Chronicle system for historical retrieval'}
        ],
        insights=[
            'Fault tolerance requires multiple layers',
            'Agent systems need failsafes',
            'Compact format enables better tooling',
            'Historical context requires structured entries'
        ],
        tags=['logging', 'evolution', 'fault-tolerance']
    )
    
    print("Chronicle populated!")
    print()
    print("Run: python chronicle.py --level all")


if __name__ == "__main__":
    main()

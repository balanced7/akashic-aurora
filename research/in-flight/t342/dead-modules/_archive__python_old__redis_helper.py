#!/usr/bin/env python3
"""
Redis Context Helper - Quick Lookups During Work
=============================================

Usage:
    python redis_helper.py brief
    python redis_helper.py lookup "florence"
    python redis_helper.py similar "install redis"
    python redis_helper.py record "Task" --success
"""

import argparse
import sys
sys.path.insert(0, r"E:\AI-Setup")
sys.path.insert(0, r"E:\AI-Setup\learning")

from learning.store import learn
from session_logger import SESSION_ID


def cmd_brief():
    print()
    print("=== LEARNING STORE STATUS ===")
    print()
    ls = learn()
    stats = ls.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")


def cmd_lookup(query):
    print()
    print(f"=== LOOKUP: '{query}' ===")
    print()
    ls = learn()
    
    decisions = ls.get_decisions(days=90)
    matching = [d for d in decisions if query.lower() in d.title.lower() or query.lower() in d.decision.lower()]
    
    if matching:
        print(f"Decisions ({len(matching)}):")
        for d in matching[:5]:
            print(f"  [{d.status}] {d.id}: {d.title}")
    else:
        print("No matching decisions")
    
    components = ["vision", "backend", "database", "infrastructure"]
    for comp in components:
        status = ls.get_component_status(comp)
        working = [a for a in status.get("working", []) if query.lower() in a.get("name", "").lower()]
        if working:
            print(f"\nWorking approaches for {comp}:")
            for a in working[:3]:
                print(f"  - {a.get('name')}")


def cmd_similar(task):
    print()
    print(f"=== SIMILAR: '{task}' ===")
    print()
    ls = learn()
    similar = ls.get_similar(task, limit=5)
    
    if similar:
        print(f"Found {len(similar)} similar experiences:")
        for e in similar:
            status = "[OK]" if e.success else "[XX]"
            print(f"  {status} {e.task[:60]}")
            if e.learnings:
                print(f"      -> {e.learnings[0][:60]}")
    else:
        print("No similar experiences found")


def cmd_record(task, success, score, learnings, approach=""):
    print()
    print(f"=== RECORDING ===")
    print()
    ls = learn()
    exp_id = ls.record(
        task=task,
        approach=approach or "N/A",
        success=success,
        score=score,
        learnings=learnings or [],
        session_id=SESSION_ID
    )
    if exp_id:
        print(f"[OK] Recorded: {exp_id}")
        print(f"  Task: {task[:60]}")


def cmd_insights():
    print()
    print("=== INSIGHTS ===")
    print()
    ls = learn()
    insights = ls.get_insights(min_confidence=0.5)
    
    if insights:
        for i in insights[:5]:
            print(f"[{i.get('confidence', 0):.0%}] {i.get('task', '')[:50]}")
            print(f"    -> {i.get('what_would_help', '')[:60]}")
    else:
        print("No insights yet")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd')
    
    subparsers.add_parser('brief', help='Quick status')
    subparsers.add_parser('insights', help='Show insights')
    
    sp = subparsers.add_parser('lookup', help='Search decisions/approaches')
    sp.add_argument('query', nargs='*', help='Query terms')
    
    sp = subparsers.add_parser('similar', help='Find similar experiences')
    sp.add_argument('task', nargs='*', help='Task description')
    
    sp = subparsers.add_parser('record', help='Record experience')
    sp.add_argument('task', help='Task')
    sp.add_argument('--success', action='store_true')
    sp.add_argument('--score', type=float, default=0.5)
    sp.add_argument('--learnings', nargs='*')
    
    args = parser.parse_args()
    
    if args.cmd == 'brief':
        cmd_brief()
    elif args.cmd == 'lookup':
        query = ' '.join(args.query) if args.query else input("Query: ").strip()
        cmd_lookup(query)
    elif args.cmd == 'similar':
        task = ' '.join(args.task) if args.task else input("Task: ").strip()
        cmd_similar(task)
    elif args.cmd == 'record':
        cmd_record(args.task, args.success, args.score, args.learnings or [])
    elif args.cmd == 'insights':
        cmd_insights()
    else:
        print("Commands: brief, lookup <q>, similar <task>, record <task> [--success] [--score N], insights")


if __name__ == "__main__":
    main()

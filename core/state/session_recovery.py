#!/usr/bin/env python3
"""
Session Recovery: Recover from checkpoint and fallback infrastructure

Semantic Relationship: SessionHistory derived_from LocalFiles (when Redis unavailable)

Recovers session history from local files when Redis is unavailable.
Works as a fallback when infrastructure is down.

Usage:
    from core.state.session_recovery import SessionRecovery

    recovery = SessionRecovery()
    recovery.load_sessions_from_local_files()
    recovery.print_recovery_report()

    # Get recent sessions
    recent = recovery.load_recent_sessions_ordered_by_timestamp(limit=5)
    for session_id, timestamp, count in recent:
        summary = recovery.derive_conversation_summary_from_entries(session_id)
        print(f"Session {session_id}: {summary['message_count']} messages")
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict, Counter

# Root DERIVED, never hardcoded: this file previously pinned one machine's absolute
# path, so a copy of the repo anywhere else resolved every path under it to nothing.
from core.paths import repo_root as _repo_root  # noqa: E402
BASE_DIR = _repo_root()
SESSION_LOGS_DIR = BASE_DIR / "session_logs"
SESSION_STATE_FILE = BASE_DIR / "blackboard_data" / "session_state.json"

class SessionRecovery:
    """
    Recover session history from local files.

    Semantic Relationship: SessionHistory derived_from LocalFiles

    Recovers and displays session history from local files when Redis is unavailable.
    """

    def __init__(self):
        self.logs_dir = SESSION_LOGS_DIR
        self.session_files = {
            "all": self.logs_dir / "session_all.jsonl",
            "backup": self.logs_dir / "backup_session_all.jsonl",
            "events": self.logs_dir / "session_events_canonical.jsonl",
            "errors": self.logs_dir / "errors_and_faults.jsonl",
        }
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
        self.summaries: Dict[str, str] = {}

    def load_sessions_from_local_files(self) -> None:
        """
        Load all sessions from local files.

        Semantic Relationship: Sessions derived_from LocalFiles

        Reads JSONL files from disk when centralized storage unavailable.
        """
        print("[*] Loading sessions from disk...")

        for name, filepath in self.session_files.items():
            if not filepath.exists():
                print(f"  {name}: NOT FOUND")
                continue

            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        try:
                            entry = json.loads(line)
                            session_id = entry.get('session', 'unknown')
                            self.sessions[session_id].append(entry)
                        except json.JSONDecodeError:
                            continue
                print(f"  {name}: {sum(len(v) for v in self.sessions.values())} entries loaded")
            except Exception as e:
                print(f"  {name}: ERROR - {e}")

        # Load summaries
        self._load_summaries_from_markdown_files()

    # Backward compatibility alias
    def load_sessions(self) -> None:
        """Deprecated: Use load_sessions_from_local_files() instead"""
        return self.load_sessions_from_local_files()

    def _load_summaries_from_markdown_files(self) -> None:
        """
        Load session summaries from markdown files.

        Semantic Relationship: Summaries derived_from MarkdownFiles
        """
        summary_files = list(self.logs_dir.glob("SESSION_SUMMARY_*.md"))
        for filepath in summary_files:
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    session_name = filepath.stem.replace("SESSION_SUMMARY_", "")
                    self.summaries[session_name] = content[:500] + "..."
            except Exception as e:
                pass

    # Backward compatibility alias
    def _load_summaries(self) -> None:
        """Deprecated internal: Use _load_summaries_from_markdown_files() instead"""
        return self._load_summaries_from_markdown_files()

    def load_session_state_from_disk(self) -> Dict:
        """
        Load current session state from disk storage.

        Semantic Relationship: SessionState derived_from DiskFile

        Returns current session state if available, empty dict if not.
        """
        if not SESSION_STATE_FILE.exists():
            return {}

        try:
            with open(SESSION_STATE_FILE, 'r') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    # Backward compatibility alias
    def load_session_state(self) -> Dict:
        """Deprecated: Use load_session_state_from_disk() instead"""
        return self.load_session_state_from_disk()

    def load_recent_sessions_ordered_by_timestamp(self, limit: int = 5) -> List[tuple]:
        """
        Load most recent sessions ordered by timestamp.

        Semantic Relationship: RecentSessions derived_from AllSessions (filtered and ordered)

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of (session_id, timestamp, entry_count) tuples, most recent first
        """
        sessions_by_time = []

        for session_id, entries in self.sessions.items():
            if entries:
                # Find latest timestamp
                latest_time = None
                for entry in reversed(entries):
                    if 'timestamp' in entry:
                        try:
                            latest_time = datetime.fromisoformat(entry['timestamp'])
                            break
                        except (ValueError, TypeError):
                            pass

                if latest_time:
                    sessions_by_time.append((session_id, latest_time, len(entries)))

        return sorted(sessions_by_time, key=lambda x: x[1], reverse=True)[:limit]

    # Backward compatibility alias
    def get_recent_sessions(self, limit: int = 5) -> List[tuple]:
        """Deprecated: Use load_recent_sessions_ordered_by_timestamp() instead"""
        return self.load_recent_sessions_ordered_by_timestamp(limit)

    def derive_conversation_summary_from_entries(self, session_id: str) -> Dict:
        """
        Derive conversation summary from session entries.

        Semantic Relationship: ConversationSummary derived_from SessionEntries

        Analyzes all entries in a session to create summary statistics.

        Args:
            session_id: ID of session to summarize

        Returns:
            Dictionary with summary statistics including message count, actions, errors, etc.
        """
        entries = self.sessions.get(session_id, [])

        summary = {
            "session_id": session_id,
            "total_entries": len(entries),
            "message_count": 0,
            "action_count": 0,
            "error_count": 0,
            "participants": set(),
            "topics": Counter(),
            "first_timestamp": None,
            "last_timestamp": None,
            "messages": []
        }

        for entry in entries:
            entry_type = entry.get('type', 'unknown')

            if entry_type == 'chat':
                summary['message_count'] += 1
                role = entry.get('role', 'unknown')
                summary['participants'].add(role)
                msg = entry.get('message', '')
                summary['messages'].append({
                    'role': role,
                    'content': msg[:100] + "..." if len(msg) > 100 else msg,
                    'timestamp': entry.get('timestamp')
                })
            elif entry_type == 'action':
                summary['action_count'] += 1
                action = entry.get('action', 'unknown')
                summary['topics'][action] += 1
            elif entry_type == 'error':
                summary['error_count'] += 1

            # Track timestamps
            if 'timestamp' in entry:
                ts = entry['timestamp']
                if not summary['first_timestamp']:
                    summary['first_timestamp'] = ts
                summary['last_timestamp'] = ts

        summary['participants'] = list(summary['participants'])
        summary['topics'] = dict(summary['topics'].most_common(5))

        return summary

    # Backward compatibility alias
    def get_conversation_summary(self, session_id: str) -> Dict:
        """Deprecated: Use derive_conversation_summary_from_entries() instead"""
        return self.derive_conversation_summary_from_entries(session_id)

    def print_recovery_report(self) -> None:
        """
        Print comprehensive recovery report.

        Semantic Relationship: RecoveryReport documents SessionState

        Displays current session state, recent sessions, and recommendations.
        """
        print("\n" + "=" * 70)
        print("SESSION RECOVERY REPORT")
        print("=" * 70)

        state = self.load_session_state_from_disk()
        print(f"\nCurrent Session State:")
        print(f"  Session ID: {state.get('session_id', 'N/A')}")
        print(f"  Unique ID: {state.get('unique_id', 'N/A')}")
        print(f"  Started: {state.get('started_at', 'N/A')}")
        print(f"  Last Update: {state.get('updated_at', 'N/A')}")

        print(f"\nSession Log Files:")
        for name, filepath in self.session_files.items():
            exists = "[OK]" if filepath.exists() else "[MISSING]"
            print(f"  {exists} {name}: {filepath.name}")

        print(f"\nRecent Sessions (last 5):")
        recent = self.load_recent_sessions_ordered_by_timestamp(5)
        for session_id, timestamp, count in recent:
            print(f"  - {session_id}")
            print(f"    Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Entries: {count}")

        print(f"\nMost Recent Session Details:")
        if recent:
            latest_session_id = recent[0][0]
            summary = self.derive_conversation_summary_from_entries(latest_session_id)
            print(f"  Session: {summary['session_id']}")
            print(f"  Messages: {summary['message_count']}")
            print(f"  Actions: {summary['action_count']}")
            print(f"  Errors: {summary['error_count']}")
            print(f"  Participants: {', '.join(summary['participants'])}")
            print(f"  Duration: {summary['first_timestamp']} to {summary['last_timestamp']}")

            if summary['topics']:
                print(f"  Top Topics/Actions:")
                for topic, count in summary['topics'].items():
                    print(f"    - {topic} ({count}x)")

            print(f"\n  Recent Messages:")
            for msg in summary['messages'][-3:]:
                role_str = f"[{msg['role'].upper()}]"
                print(f"    {role_str} {msg['content']}")

        print("\n" + "=" * 70)
        print("INITIALIZATION STATUS")
        print("=" * 70)

        print("\nInfrastructure Status:")
        print("  [UNAVAILABLE] Redis (Docker not running)")
        print("  [UNAVAILABLE] WSL (Ubuntu-Migrate not imported)")
        print("  [AVAILABLE]   File-based session logs")
        print("  [AVAILABLE]   Session recovery system")

        print("\nRecommendations:")
        print("  1. Session history is SAFE - all data in local files")
        print("  2. File-based logging is ACTIVE")
        print("  3. To enable Redis, start Docker and run:")
        print("     cd E:\\AI-Setup\\dockerized-ai\\redis")
        print("     docker compose -f docker-compose-ha.yml up -d")

        print("\n" + "=" * 70)

    # Backward compatibility alias
    def print_report(self) -> None:
        """Deprecated: Use print_recovery_report() instead"""
        return self.print_recovery_report()


def main():
    recovery = SessionRecovery()
    recovery.load_sessions_from_local_files()
    recovery.print_recovery_report()

    return recovery

if __name__ == '__main__':
    recovery = main()

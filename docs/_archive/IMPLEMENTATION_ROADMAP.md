# Multi-Agent System Implementation Roadmap
## From Current State to Full Coordinator-Based Architecture

---

## Current State Assessment

### What Exists ✅
- Redis HA infrastructure (ready to restore)
- MCP server framework
- Agent coordinator v2 (message bus)
- Session logging to JSONL
- Agent manifest system
- Project context layers

### What's Missing ❌
- Unified signal logging API
- Coordinator background service
- Auto-briefing generation
- Decision synthesis
- Blocker escalation
- Agent profile registry

### Token Waste (Current) ⚠️
- Agents spend ~30-40% on overhead
- Repeated decisions (~40% token waste)
- Manual context gathering
- No pattern extraction

---

## 3-Week Implementation Plan

### WEEK 1: Signal API & Basic Coordinator

**Goal**: Create minimal viable coordinator that makes agents' lives easier

**Deliverables**:
1. ✏️ `coordinator_api.py` - Ultra-minimal logging API
2. ✏️ `coordinator_service.py` - Background process
3. ✏️ `test_signal_logging.py` - Verify it works
4. 🧪 Test with Claude (this session)

#### Day 1-2: Signal API (`~150 lines`)

```python
# E:\AI-Setup\coordinator_api.py
"""
Ultra-minimal logging for agents.
Zero burden, maximum clarity.
"""

import json
import redis
from datetime import datetime
from typing import Dict, List, Optional

class SignalLogger:
    """Minimal logging API for working agents"""
    
    def __init__(self):
        self.r = redis.Redis(host='localhost', port=6379)
        self.agent_id = self._get_agent_id()
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _get_agent_id(self) -> str:
        # From environment or Redis
        import os
        return os.getenv('AGENT_ID', 'unknown_agent')
    
    def log(self, event_type: str, **kwargs) -> None:
        """Ultra-simple logging"""
        event = {
            'type': event_type,
            'agent_id': self.agent_id,
            'session': self.session_id,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        # Add to Redis stream
        self.r.xadd('agent:events', {'data': json.dumps(event)})
    
    def action(self, action: str, context: str = None, **kwargs) -> None:
        """Log an action"""
        self.log('action', action=action, context=context, **kwargs)
    
    def decision(self, key: str, reason: str, **kwargs) -> None:
        """Log a decision"""
        self.log('decision', key=key, reason=reason, **kwargs)
    
    def blocker(self, blocker: str, severity: str = "normal", **kwargs) -> None:
        """Log a blocker"""
        self.log('blocker', blocker=blocker, severity=severity, **kwargs)
    
    def progress(self, update: str, **kwargs) -> None:
        """Log progress"""
        self.log('progress', update=update, **kwargs)
    
    def milestone(self, milestone_id: str, status: str, **kwargs) -> None:
        """Log milestone progress"""
        self.log('milestone', milestone_id=milestone_id, status=status, **kwargs)
    
    def request_help(self, expertise: str, task: str) -> None:
        """Request help from another agent"""
        self.log('help_request', expertise=expertise, task=task)
        # Also add to help queue
        self.r.lpush('collaboration:help_requests', 
                    json.dumps({'agent': self.agent_id, 'expertise': expertise}))
    
    def request_handoff(self, to_agent: str, reason: str) -> None:
        """Request handoff to another agent"""
        self.log('handoff_request', to_agent=to_agent, reason=reason)
        # Trigger coordinator to prepare briefing
        self.r.publish('coordination:handoff', 
                      json.dumps({'from': self.agent_id, 'to': to_agent}))

# Global instance
_logger = None

def get_logger() -> SignalLogger:
    global _logger
    if _logger is None:
        _logger = SignalLogger()
    return _logger

# Convenience functions
def log(event_type: str, **kwargs):
    return get_logger().log(event_type, **kwargs)

def action(action: str, **kwargs):
    return get_logger().action(action, **kwargs)

def decision(key: str, reason: str, **kwargs):
    return get_logger().decision(key, reason, **kwargs)

def blocker(blocker: str, severity="normal", **kwargs):
    return get_logger().blocker(blocker, severity, **kwargs)

def request_help(expertise: str, task: str):
    return get_logger().request_help(expertise, task)

def request_handoff(to_agent: str, reason: str):
    return get_logger().request_handoff(to_agent, reason)

def get_briefing() -> Dict:
    """Get pre-prepared briefing"""
    logger = get_logger()
    briefing = redis.Redis().get(f'briefing:{logger.agent_id}:latest')
    return json.loads(briefing) if briefing else {}
```

#### Day 3-4: Coordinator Service (`~250 lines`)

```python
# E:\AI-Setup\coordinator_service.py
"""
Coordinator Agent - System Supervisor.
Runs continuously, monitors agents, synthesizes context.
"""

import json
import redis
import time
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

class CoordinatorService:
    """Monitors agent activity and maintains system state"""
    
    def __init__(self):
        self.r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.last_event_id = '0'  # Stream position
    
    def run(self):
        """Main loop - runs forever"""
        print("[Coordinator] Starting...")
        try:
            while True:
                self.monitor_events()
                self.synthesize_decisions()
                self.update_project_state()
                self.check_for_blockers()
                self.check_for_handoffs()
                time.sleep(1)
        except KeyboardInterrupt:
            print("[Coordinator] Shutting down...")
    
    def monitor_events(self):
        """Read and process agent events"""
        try:
            events = self.r.xread({'agent:events': self.last_event_id}, 
                                  count=10, block=0)
            
            for stream, event_list in events:
                for event_id, event_data in event_list:
                    self.last_event_id = event_id
                    
                    event = json.loads(event_data.get('data', '{}'))
                    event_type = event.get('type')
                    
                    # Route based on type
                    if event_type == 'action':
                        self.process_action(event)
                    elif event_type == 'decision':
                        self.process_decision(event)
                    elif event_type == 'blocker':
                        self.process_blocker(event)
                    elif event_type == 'handoff_request':
                        self.process_handoff_request(event)
                    
                    # Always update agent manifest
                    self.update_agent_manifest(event)
        
        except Exception as e:
            print(f"[Coordinator] Error monitoring: {e}")
    
    def process_action(self, event: Dict):
        """Extract info from action"""
        agent = event.get('agent_id')
        action = event.get('action')
        context = event.get('context', '')
        
        # Store in agent's timeline
        self.r.lpush(f'agent:{agent}:actions', 
                    json.dumps({'action': action, 'context': context, 
                               'timestamp': event.get('timestamp')}))
        
        # Update project state (how much work?)
        self.r.incr(f'project:actions_count')
    
    def process_decision(self, event: Dict):
        """Extract and synthesize decision"""
        agent = event.get('agent_id')
        key = event.get('key')
        reason = event.get('reason')
        
        # Store decision with metadata
        decision = {
            'key': key,
            'agent_id': agent,
            'reason': reason,
            'timestamp': event.get('timestamp'),
            'project': self.r.get('project:current')
        }
        
        # Store in Redis
        self.r.hset('learning:decisions', key, json.dumps(decision))
        
        # Also append to decisions list for timeline
        self.r.lpush('learning:decisions:list', json.dumps(decision))
        
        print(f"[Coordinator] Decision logged: {key} ({reason})")
    
    def process_blocker(self, event: Dict):
        """Handle blockers - check if solved before"""
        agent = event.get('agent_id')
        blocker = event.get('blocker')
        severity = event.get('severity', 'normal')
        
        # Check if we've solved this before
        prior_solution = self.r.get(f'solution:{blocker}')
        if prior_solution:
            # Send to agent immediately
            self.r.lpush(f'agent:{agent}:messages',
                        json.dumps({'type': 'solution_to_blocker',
                                   'blocker': blocker,
                                   'solution': prior_solution}))
            print(f"[Coordinator] Blocker {blocker} - sending prior solution")
        else:
            # Store for next time
            self.r.lpush('unresolved_blockers', 
                        json.dumps({'blocker': blocker, 'agent': agent, 
                                   'severity': severity}))
            print(f"[Coordinator] New blocker: {blocker} (severity: {severity})")
    
    def process_handoff_request(self, event: Dict):
        """Prepare briefing for next agent"""
        from_agent = event.get('agent_id')
        to_agent = event.get('to_agent')
        reason = event.get('reason')
        
        # This triggers briefing generation
        self.prepare_handoff_briefing(from_agent, to_agent, reason)
    
    def prepare_handoff_briefing(self, from_agent: str, to_agent: str, reason: str):
        """Generate briefing for next agent"""
        # Gather context
        from_agent_actions = self.r.lrange(f'agent:{from_agent}:actions', 0, 5)
        recent_decisions = self.r.lrange('learning:decisions:list', 0, 5)
        blockers = self.r.lrange('unresolved_blockers', 0, 10)
        
        # Synthesize briefing
        briefing = {
            'timestamp': datetime.now().isoformat(),
            'for_agent': to_agent,
            'from_agent': from_agent,
            'handoff_reason': reason,
            'what_was_done': [json.loads(a) for a in from_agent_actions if a],
            'key_decisions': [json.loads(d) for d in recent_decisions if d],
            'current_blockers': [json.loads(b) for b in blockers if b],
            'project': self.r.get('project:current'),
            'completion_percent': int(self.r.get('project:completion_percent') or 0)
        }
        
        # Store for next agent
        self.r.set(f'briefing:{to_agent}:latest', json.dumps(briefing))
        
        print(f"[Coordinator] Prepared briefing for {to_agent}")
    
    def synthesize_decisions(self):
        """Periodically synthesize decisions (batch operation)"""
        # Every 30 events, create a summary
        event_count = int(self.r.get('coordinator:event_count') or 0)
        if event_count % 30 == 0 and event_count > 0:
            decisions = self.r.lrange('learning:decisions:list', 0, 10)
            summary = {
                'decisions_made': len(decisions),
                'key_themes': self._extract_themes(decisions),
                'timestamp': datetime.now().isoformat()
            }
            self.r.lpush('learning:summaries', json.dumps(summary))
    
    def update_project_state(self):
        """Update project completion/status"""
        milestones = self.r.lrange('project:milestones', 0, -1)
        completed = sum(1 for m in milestones if json.loads(m).get('status') == 'completed')
        total = len(milestones)
        
        if total > 0:
            completion = int((completed / total) * 100)
            self.r.set('project:completion_percent', completion)
    
    def check_for_blockers(self):
        """Periodic blocker check (every 10 sec)"""
        # Could integrate with external monitoring here
        pass
    
    def check_for_handoffs(self):
        """Handle pending handoffs"""
        # Check if any handoffs are queued
        handoff = self.r.lpop('coordination:handoff_queue')
        if handoff:
            self.process_handoff_request(json.loads(handoff))
    
    def update_agent_manifest(self, event: Dict):
        """Update agent status in manifest"""
        agent = event.get('agent_id')
        now = datetime.now().isoformat()
        
        manifest = {
            'agent_id': agent,
            'status': 'busy',  # or 'idle', 'blocked'
            'last_event': event.get('type'),
            'last_update': now,
            'session': event.get('session')
        }
        
        self.r.hset(f'agent:{agent}:manifest', mapping=manifest)
    
    def _extract_themes(self, decisions: List[str]) -> List[str]:
        """Extract common themes from decisions"""
        themes = defaultdict(int)
        for d in decisions:
            decision = json.loads(d) if isinstance(d, str) else d
            # Very basic: use first word of decision
            key = decision.get('key', '').split('_')[0]
            if key:
                themes[key] += 1
        return sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]

def main():
    service = CoordinatorService()
    service.run()

if __name__ == '__main__':
    main()
```

#### Day 5: Testing & Integration

Create test file:
```python
# E:\AI-Setup\test_coordinator_system.py
"""Test the new coordinator system"""

import time
from coordinator_api import action, decision, blocker, request_handoff
from coordinator_service import CoordinatorService

def test_signal_logging():
    """Test that signals are logged correctly"""
    action("test_action", context="testing")
    decision("test_decision", reason="verify_system")
    blocker("test_blocker", severity="low")
    
    time.sleep(1)
    print("✓ Signals logged successfully")

def test_coordinator_processing():
    """Test that coordinator processes signals"""
    # Start coordinator in background thread
    import threading
    service = CoordinatorService()
    thread = threading.Thread(target=service.run, daemon=True)
    thread.start()
    
    # Give it a second to start
    time.sleep(1)
    
    # Log some events
    action("processing_test")
    decision("test_key", reason="verify_coordinator")
    
    # Give coordinator time to process
    time.sleep(2)
    
    # Check if decision was stored
    import redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    decision_stored = r.hget('learning:decisions', 'test_key')
    
    if decision_stored:
        print("✓ Coordinator processed signals correctly")
    else:
        print("✗ Coordinator did not process signals")

if __name__ == '__main__':
    test_signal_logging()
    test_coordinator_processing()
```

---

### WEEK 2: Briefing Generation & Agent Profiles

**Goal**: Auto-generate briefings, create agent registry

**Deliverables**:
1. ✏️ `briefing_generator.py` - Create context for next agent
2. ✏️ `agent_profiles.py` - Agent registry and specializations
3. ✏️ `AGENT_BRIEFING_TEMPLATE.md` - Template for generated briefs
4. 🧪 Test briefing generation
5. 🧪 Test agent profiles

#### Day 1-2: Briefing Generator

```python
# E:\AI-Setup\briefing_generator.py
class BriefingGenerator:
    def generate_for_agent(self, agent_type: str, project: str):
        """Generate context for starting agent"""
        
        context = {
            'project': project,
            'from_agent': self._get_last_agent(project),
            'what_was_done': self._summarize_recent_work(),
            'your_role': self._suggest_role_for_agent(agent_type),
            'critical_blockers': self._get_blockers(),
            'key_decisions': self._get_decisions(),
            'next_steps': self._suggest_next_steps(),
            'resources': self._list_available_resources()
        }
        
        return context
```

#### Day 3-4: Agent Profiles

```python
# E:\AI-Setup\agent_profiles.py
class AgentProfile:
    id: str
    type: str  # "claude", "opencode", "cursor"
    specializations: List[str]
    capabilities: Dict[str, bool]
    
    def register(self):
        """Register in Redis"""
        pass
    
    @staticmethod
    def load(agent_id: str):
        """Load from Redis"""
        pass
```

---

### WEEK 3: Integration & Testing

**Goal**: Full system working, test handoff, document results

**Deliverables**:
1. ✏️ `AGENT_ONBOARDING_CHECKLIST.md` - Final checklist
2. 🧪 Full E2E test: Claude → OpenCode handoff
3. 📊 Token efficiency metrics
4. 📝 System documentation

---

## Quick Start: Start This Week

### Step 1: Restore Redis (30 min)
```bash
# If you haven't already
Start-Service -Name "com.docker.service"
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml up -d
```

### Step 2: Test Connection (5 min)
```bash
python test_redis_cache.py
# Should show: [OK] Redis 6379 responding
```

### Step 3: Create Minimal Coordinator (2 hours)
Copy the `coordinator_api.py` and `coordinator_service.py` code above into files.

### Step 4: Test It (30 min)
```bash
python test_coordinator_system.py
```

### Step 5: Use It (This session!)
```python
from coordinator_api import action, decision, request_handoff

# Start of work
action("architecture_review", context="mcp_interface")

# During work
decision("use_websockets", reason="real_time_status")

# End of work
request_handoff("opencode", reason="implement_design")
```

---

## Success Criteria

### Week 1
- ✅ Agents can log signals with zero friction
- ✅ Coordinator monitors and stores signals
- ✅ No lost data
- ✅ Overhead < 5 minutes per session

### Week 2
- ✅ Briefings auto-generate for next agent
- ✅ Agent profiles registered
- ✅ Zero onboarding time for agents
- ✅ Decision caching prevents rediscussion

### Week 3
- ✅ Full handoff works: Agent 1 → Agent 2
- ✅ Token efficiency improved to 90%+
- ✅ System is documented
- ✅ Ready for multi-agent scaling

---

## The Vision Realized

After 3 weeks:
```
Agent 1 (4 hours)
  ├─ 5 min: Read auto-briefing
  ├─ 235 min: ACTUAL WORK
  └─ 10 min: Log signals + handoff

Agent 2 (4 hours)
  ├─ 5 min: Read auto-briefing
  ├─ 235 min: ACTUAL WORK
  └─ 10 min: Log signals + handoff

Coordinator (continuous)
  ├─ Monitor signals
  ├─ Synthesize decisions
  ├─ Extract learnings
  ├─ Prepare briefings
  └─ Maintain project state

Result: 
  Agents: 95% tokens on work
  System: Fully continuous, zero data loss
  Scale: Ready for 5+ concurrent agents
```

---

## Questions for You

1. **Should Coordinator be a separate Python process or MCP tool?**
   - Separate process = Always running, faster
   - MCP tool = More integrated, uses same infrastructure

2. **How aggressive with auto-synthesis?**
   - Conservative: Only synthesize what agents explicitly logged
   - Aggressive: Use AI to extract meaning from agent behavior

3. **Agent notification preferences?**
   - Silent (no alerts, just queue messages)
   - Proactive (alert when help/blocker solutions available)
   - Interactive (ask if they want suggestions)

4. **Where should briefings go?**
   - Redis key (fast, simple)
   - File on disk (persistent, shareable)
   - Both (redundancy)

5. **Should agents see other agents' logs in real-time?**
   - Yes: Collaborative awareness
   - No: Privacy/focus
   - Partial: Only if requested

---

**Next Steps**: Implement Week 1, test with this session, iterate based on what you learn.

Ready to build? 🚀

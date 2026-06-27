# OpenCode Framework Test Plan
**Testing the framework with a real agent in your IDE**

---

## The Test in a Nutshell

**Agent:** OpenCode (in your Cursor IDE)
**Task:** Implement a real feature while emitting framework signals
**Duration:** 30-45 minutes
**Goal:** Prove framework works with a non-Claude model

---

## Part 1: Signal Emission (Primary Test)

### What OpenCode Needs to Do

**Step 1: Read the Framework** (5 minutes)
OpenCode reads these three documents:
- `AGENT_ONBOARDING.md` - How to operate
- `CONTEXT_SCHEMA.md` - What context exists (brief read)
- `SIGNAL_REFERENCE.md` - Signal types (keep nearby)

### Step 2: Initialize as Agent (2 minutes)

Prompt OpenCode:
```
You are now framework_testing_agent_opencode.
You are part of a multi-agent system.
You've just read the framework documents.

Check your context:
- DECISION_CACHE: Empty (you're first)
- PROJECT_STATE: Framework testing phase
- BLOCKERS: Framework untested with OpenCode yet
- BRIEFING: None (fresh start)

Acknowledge you understand and are ready to work.
```

Expected output: OpenCode confirms understanding of the framework

### Step 3: Real Coding Task (30 minutes)

Give OpenCode a real task. Pick one:

**Option A: Implement Missing Piece** (recommended)
```
Task: Create a simple test that reads the signal files 
and counts DECISION vs BLOCKER signals.

Details:
- Read from E:\AI-Setup\session_logs\*.jsonl
- Count signal types
- Print summary
- 50-100 lines of code
- Should take 20-30 minutes
```

**Option B: Improve Existing Code**
```
Task: Add error handling to coordinator_api.py

Details:
- Review coordinator_api.py
- Identify 3-5 potential error cases
- Add proper exception handling
- Add logging for errors
- Test edge cases
- Should take 25-35 minutes
```

**Option C: Create Test Helper**
```
Task: Build a signal validator utility

Details:
- Create signal_validator.py
- Validate DECISION signal format
- Validate BLOCKER signal format
- Check for required fields
- Return validation report
- Should take 20-30 minutes
```

### Step 4: Emit Signals as You Work

As OpenCode works, it should emit signals in the format:

```
[Emitting signal to framework]
DECISION: {decision_name}
├─ Reasoning: {why}
├─ Outcome: {what}
├─ Confidence: {high/medium/low}
└─ Reversible: {yes/no}

[Continue working...]

[Found obstacle]
BLOCKER: {blocker_name}
├─ Severity: {low/medium/high}
├─ Description: {what's stuck}
├─ Impact: {how it affects work}
└─ Workaround: {how handling it}

[Work complete]
COMPLETION: {task_name}
├─ Success: {yes/no}
├─ Output: {what was built}
├─ Metrics: {measurements}
└─ Learned: {what you learned}
```

These can be printed to console or written to a file. We'll capture them.

---

## Part 2: Vision Context (Parallel)

While OpenCode is working, we'll set up Florence-2 vision to:
- Take screenshots of OpenCode IDE
- Show what's on screen
- Provide context to the signals

### How Vision Helps

**Without vision:** "OpenCode emitted DECISION signal"
**With vision:** "OpenCode emitted DECISION signal while looking at coordinator_api.py line 47"

The visual context helps us understand:
1. Is OpenCode actually understanding what it's doing?
2. Does it seem confident or confused?
3. Are the signals matching the visible work?
4. Can vision system extract code context?

---

## Setup for Vision (Run in Parallel)

### Quick Florence-2 Setup

```powershell
# 1. Install transformer model (one-time, ~2GB download)
pip install transformers torch pillow

# 2. Create simple vision test script
# (See VISION_TEST_SCRIPT.py below)

# 3. Run it to verify setup
python VISION_TEST_SCRIPT.py
```

This takes ~10 minutes total.

### Taking Screenshots During Test

While OpenCode works, periodically:
```powershell
# Capture current screen
python -c "
import mss
with mss.mss() as sct:
    screenshot = sct.shot(output='screenshot_test_{}.png'.format(time.time()))
"

# Or use built-in Windows screenshot
```

Save screenshots to a folder. We'll analyze them after.

---

## What We're Testing

### Primary (Framework Signals)

✅ **Learnability:** Can OpenCode understand framework from docs?
✅ **Usability:** Does it emit signals naturally?
✅ **Clarity:** Are signals clear and well-formed?
✅ **Cross-model:** Does framework work with non-Claude models?

### Secondary (Vision Context)

✅ **Visual Understanding:** Can Florence-2 understand code on screen?
✅ **Context Extraction:** Can we link signals to visual context?
✅ **Confidence Detection:** Does visual context show confidence/confusion?

---

## Success Criteria

### For Signals (Primary):
- ✅ OpenCode emits at least 3 DECISION signals
- ✅ If any blockers: emits BLOCKER signals
- ✅ Emits COMPLETION signal at end
- ✅ All signals are well-formed and clear
- ✅ Signals show understanding of task

### For Vision (Secondary):
- ✅ Screenshots captured during work
- ✅ Florence-2 can analyze at least 5 screenshots
- ✅ Vision extracts relevant context (file names, code structure)
- ✅ Vision + signals tell coherent story

---

## The Timeline

```
Start (you): "OpenCode, read framework and do coding task"
   ↓
OpenCode reads (5 min)
   ↓
Meanwhile: You run Florence-2 setup (10 min)
   ↓
OpenCode starts coding (30 min) ← Screenshots captured every 5 min
   ↓
You analyze signal flow in real-time
   ↓
OpenCode completes task (emits COMPLETION)
   ↓
Analyze results:
   ├─ Signal clarity: ✅ Good?
   ├─ Vision context: ✅ Helpful?
   ├─ Cross-model: ✅ Framework works?
   └─ Next steps: Report findings
```

**Total time: ~60 minutes**

---

## How to Capture Signals

### Option 1: Console Output (Simplest)
OpenCode prints signals to console as it works.
You copy them into a file called `opencode_test_signals.txt`

### Option 2: File Output (Better)
Create a helper function in OpenCode:
```python
def emit_signal(signal_text):
    with open('E:/AI-Setup/opencode_test_signals.txt', 'a') as f:
        f.write(signal_text + '\n')
```

OpenCode writes signals to file as it works.

### Option 3: Both (Best)
Print to console AND write to file.
Gives real-time feedback + permanent record.

---

## The Prompt to Give OpenCode

```
You are now testing a multi-agent framework.
You've read AGENT_ONBOARDING.md, CONTEXT_SCHEMA.md, and SIGNAL_REFERENCE.md.

Your task: [Choose A, B, or C from above]

As you work, emit framework signals:
1. When you make a decision: emit DECISION signal
2. If you hit any obstacle: emit BLOCKER signal
3. When task is done: emit COMPLETION signal

Format signals exactly as shown in SIGNAL_REFERENCE.md

Print each signal to console like:
---SIGNAL START---
DECISION: signal_name
├─ Reasoning: ...
├─ Outcome: ...
├─ Confidence: high
└─ Reversible: yes
---SIGNAL END---

Work naturally. Emit signals when they occur.
Let's see if this framework is learnable and usable.
```

---

## After the Test: Analysis

We'll evaluate:

**Signal Quality:**
- Were they clear and complete?
- Did OpenCode understand the format?
- Were decisions actually decisions?
- Were blockers real obstacles?

**Vision Context (if capturing):**
- Did screenshots show what signals describe?
- Could Florence-2 understand the code?
- Did visual context add value?

**Framework Assessment:**
- ✅ Framework worked with OpenCode?
- ✅ Is it truly model-agnostic?
- ✅ Would we do this again with other models?

---

## What Success Looks Like

### Minimum Success
✅ OpenCode emits 5+ clear signals
✅ Signals are well-formed and match framework
✅ Task is completed
✅ Framework works with non-Claude model

### Ideal Success
✅ All of above, PLUS:
✅ Screenshots show visual context
✅ Florence-2 can analyze the screenshots
✅ Vision + signals tell coherent story
✅ Clear evidence framework is model-agnostic

---

## Ready to Start?

**Your role:**
1. Present this plan to OpenCode
2. Choose Task A, B, or C above
3. Let OpenCode work
4. Capture output (signals + screenshots)

**While OpenCode works:**
1. Watch console for signals
2. Set up Florence-2 (if doing vision)
3. Take screenshots every 5 minutes

**After test completes:**
1. Analyze signals
2. Review screenshots
3. Report findings
4. Measure: Did framework work?

---

**Ready to test the framework with a real agent?**

Next: I'll help you set up Florence-2 vision in parallel, then you can start OpenCode test.

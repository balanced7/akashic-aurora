# Execute OpenCode Framework Test
**Step-by-step guide to test the framework with a real agent today**

---

## Quick Overview

**Timeline:** ~60 minutes total
- Parallel setup: 15 min (while OpenCode reads docs)
- OpenCode work: 30-40 min (real coding task)
- Analysis: 15 min (evaluate signals + vision)

**Goal:** Prove the framework works with a non-Claude model

---

## PHASE 1: SETUP (Start Now)

### Step 1: Copy Framework Documents to Easy Location

OpenCode needs quick access to:
- `AGENT_ONBOARDING.md`
- `CONTEXT_SCHEMA.md` 
- `SIGNAL_REFERENCE.md`

These should be in `E:\AI-Setup\` (they are).

### Step 2: Choose Your OpenCode Task

Pick ONE:

**Task A: Signal Counter Tool** (EASIEST - 20 min)
```
Create a Python script that:
1. Reads E:\AI-Setup\session_logs\*.jsonl files
2. Parses JSON signals
3. Counts by type (DECISION, BLOCKER, etc)
4. Outputs summary report
5. Should be 50-100 lines

Example output:
  DECISION signals: 8
  BLOCKER signals: 2
  HANDOFF signals: 1
  COMPLETION signals: 1
  Total: 12 signals
```

**Task B: Error Handler Enhancement** (MEDIUM - 30 min)
```
Improve coordinator_api.py by:
1. Adding try-catch around Redis connection
2. Adding retry logic for failed writes
3. Adding logging for errors
4. Testing the error paths
5. Should add 40-60 lines
```

**Task C: Signal Validator** (HARDEST - 35 min)
```
Create signal_validator.py that:
1. Validates DECISION signal format
2. Validates BLOCKER signal format  
3. Checks for required fields
4. Generates validation report
5. Should be 80-120 lines
```

**Recommendation:** Start with Task A (Signal Counter)
- Clear requirements
- Real work
- Shows understanding
- Fastest to complete

---

## PHASE 2: THE TEST (Main Event)

### Step 3: Prompt OpenCode

Open Cursor (with OpenCode) and paste this prompt:

```
You are now framework_testing_agent_opencode.
You are part of a multi-agent system.

FIRST: Read these three documents:
- E:\AI-Setup\AGENT_ONBOARDING.md
- E:\AI-Setup\CONTEXT_SCHEMA.md  
- E:\AI-Setup\SIGNAL_REFERENCE.md

SECOND: Check your context:
- DECISION_CACHE: Empty (you're first agent)
- PROJECT_STATE: Framework testing phase  
- BLOCKERS: Framework not yet tested with OpenCode
- BRIEFING: None (fresh start)

THIRD: Confirm you understand the framework and are ready to work.

FOURTH: Do this task:

[PASTE YOUR CHOSEN TASK HERE - A, B, or C]

FIFTH: As you work, emit framework signals.

Format signals exactly like this:

---SIGNAL---
DECISION: signal_name
├─ Reasoning: Why you chose this
├─ Outcome: What you chose  
├─ Confidence: high
└─ Reversible: yes
---END---

When you make decisions, emit them.
When you hit blockers, emit them.
When you finish, emit COMPLETION.

Print signals to console so I can see them.
Work naturally. Let's test if this framework works.
```

### Step 4: Start OpenCode (You Trigger It)

1. Paste the prompt into Cursor
2. Press Enter
3. Watch OpenCode work
4. **Copy any signals that appear to console**

---

## PHASE 2B: Vision Setup (Parallel)

### While OpenCode is Reading (First 5 minutes)

**Option 1: Quick Setup (Recommended)**
```powershell
# Takes ~10 minutes
cd E:\AI-Setup
python florence_vision_setup.py
```

This downloads Florence-2 model (~2GB, one-time).
First download takes 3-5 minutes.
Subsequent runs are instant.

**Option 2: Skip Vision**
Just watch the signals. We'll capture them manually.

**Option 3: Manual Screenshots**
```powershell
# Take screenshot of OpenCode as it works
import mss
with mss.mss() as sct:
    sct.shot(output='opencode_screenshot_1.png')
```

---

## PHASE 3: CAPTURE THE OUTPUT

### While OpenCode Works (30-40 minutes)

**What to capture:**

1. **Signals to Console/File**
   - Every DECISION it emits
   - Every BLOCKER it emits
   - The final COMPLETION
   
   Save to: `E:\AI-Setup\opencode_test_signals.txt`

2. **Screenshots (if doing vision)**
   - Take screenshot every 5-10 minutes
   - Save as: `opencode_screenshot_1.png`, `opencode_screenshot_2.png`, etc.
   - Location: `E:\AI-Setup\screenshots\`

3. **Task Output**
   - OpenCode's actual code/task output
   - The files it created/modified
   - Any test results

---

## PHASE 4: ANALYZE (15 minutes)

### After OpenCode Completes

**Evaluate Signals:**

1. **Count them**
   - How many DECISION signals?
   - How many BLOCKER signals?
   - How many COMPLETION signals?

2. **Rate clarity**
   - Are they well-formed?
   - Do they follow the format?
   - Are they clear to read?

3. **Check understanding**
   - Did OpenCode understand the task?
   - Are decisions actually decisions?
   - Are blockers real obstacles?

**Evaluate Vision (if done):**

1. **Screenshots**
   - Do they show OpenCode working?
   - Can you see the code being edited?
   - Any errors visible?

2. **Florence-2 Analysis**
   - Run: `analyze_screenshot('opencode_screenshot_1.png')`
   - What does Florence-2 see?
   - Can it understand IDE context?

3. **Signal + Vision Correlation**
   - When OpenCode emits DECISION signal, what does screenshot show?
   - Does visual context match signal description?

---

## EXPECTED RESULTS

### If Test Passes ✅

**Signals will look like:**
```
---SIGNAL---
DECISION: understand_task_and_plan_approach
├─ Reasoning: Read the task requirements (count signals from JSONL)
│            Need to parse JSON, count types, format output
├─ Outcome: Yes, I understand. Will write Python script.
├─ Confidence: high
└─ Reversible: no
---END---

[Work happens...]

---SIGNAL---
BLOCKER: json_parsing_issue
├─ Severity: low
├─ Description: Some signals might have nested structures
├─ Impact: Counting might be slightly off
└─ Workaround: Using json.loads() which handles nesting
---END---

[More work...]

---SIGNAL---
COMPLETION: signal_counter_script_implementation
├─ Success: yes
├─ Output: Created signal_counter.py (87 lines)
│         Reads JSONL files, counts signals, outputs report
│         Works with nested JSON structures
├─ Metrics: 
│   ├─ Lines written: 87
│   ├─ Time to complete: 28 minutes
│   └─ Test coverage: Basic + edge cases
└─ Learned:
   ├─ Framework format is very learnable
   ├─ Signals are easy to understand
   ├─ Could emit signals naturally as I worked
   └─ Framework is indeed model-agnostic
---END---
```

### If Test Passes with Vision ✅

**Screenshots show:**
- OpenCode in Cursor IDE
- Code being written
- Relevant context visible

**Florence-2 analysis shows:**
- Can understand IDE
- Can see file names, code structure
- Can detect when editing code vs documentation

**Combined story:**
- "While OpenCode emitted DECISION signal about understanding task,"
- "Screenshot showed it had opened the signal_counter_tool spec"
- "Florence-2 confirmed it was looking at the requirement file"
- "Visual context matches signal content"

---

## What We Learn

### About the Framework ✅
- Is it learnable? (Does OpenCode understand from docs?)
- Is it usable? (Can it emit signals naturally?)
- Is it clear? (Are signals well-formed?)
- Is it model-agnostic? (Works with non-Claude model?)

### About OpenCode ✅
- Can it understand complex instructions?
- Can it work within a structured system?
- Does it emit clear reasoning?
- Is it good for implementation tasks? (Confirms model selection)

### About Vision (if done) ✅
- Can Florence-2 understand code contexts?
- Can screenshots help understand agent behavior?
- Does visual + signals give better insight?

---

## Troubleshooting

### OpenCode Doesn't Understand

If OpenCode seems confused:
1. Give it simpler task (Task A instead of C)
2. Provide more explicit instructions
3. Ask it to confirm understanding first

### No Signals Emitted

If OpenCode doesn't emit signals:
1. Remind it to print signals to console
2. Ask it to emit DECISION when starting
3. Make it a requirement (not optional)

### Vision Setup Fails

```powershell
# If pytorch not installing
pip install --upgrade torch torchvision

# If transformers fail
pip install --upgrade transformers

# If you don't have GPU
# It will fall back to CPU (slower but works)
```

---

## Success Criteria

### Minimum (Signals Only)
- ✅ OpenCode reads framework documents
- ✅ OpenCode emits 3+ DECISION signals
- ✅ OpenCode emits COMPLETION signal
- ✅ Signals are readable and make sense
- ✅ Task is completed

### Excellent (Signals + Vision)
- ✅ All of above, PLUS
- ✅ Screenshots captured during work
- ✅ Florence-2 analyzes screenshots
- ✅ Vision + signals tell coherent story
- ✅ Clear evidence framework is model-agnostic

---

## Timeline Estimate

```
Now:        Choose task (2 min)
  ↓
Prompt:     Paste prompt into Cursor (2 min)
  ↓
Setup:      OpenCode reads framework (5 min)
  ↓
Parallel:   You run florence_vision_setup.py (10 min)
  ↓
Work:       OpenCode does task (30-40 min)
            You watch console for signals
            (Optionally take screenshots)
  ↓
Complete:   OpenCode emits COMPLETION signal
  ↓
Analyze:    Review signals and vision (15 min)
  ↓
Report:     Document findings
  ↓
Total:      ~75 minutes
```

---

## Ready to Execute?

**Your next actions:**

1. ✅ Open Cursor with OpenCode
2. ✅ Choose Task A, B, or C (A is recommended)
3. ✅ Paste the prompt above
4. ✅ Press Enter
5. ✅ Watch OpenCode work
6. ✅ (Optional) Run florence_vision_setup.py in parallel
7. ✅ Capture signals and screenshots
8. ✅ Analyze results
9. ✅ Report findings

**Then we'll know:** Does the framework work with real agents? Is it truly model-agnostic?

---

**Ready to test?** 🚀

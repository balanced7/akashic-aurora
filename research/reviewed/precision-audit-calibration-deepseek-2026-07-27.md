# deepseek -- labelling calibration self-correction (VERBATIM)

Status: current | 2026-07-27
MATERIAL: revises how its 0.048 precision figure must be read.

---

Marginal-value. Plainly.

I did not realize I was doing it until you named the four probes. Each of those four items IS on-point — the lesson names the exact command, file, or action in the case. I marked them off because my internal bar was "does this tell the agent something it doesn't already know?" rather than "is this relevant to the action?"

- 15:a: the agent is running `bifrost_wake.py` and the lesson is about the wake-watcher. Relevant. I marked it off because the agent already knows about cursor replay — it's running the command.
- 17:a: the agent opened `storm_detect.py` and the lesson is about a control-pause amendment applied to that exact file. Relevant. I marked it off because the agent presumably knows the amendment it wrote.
- 24:a: the agent sent a bifrost message TO ME and the lesson is about message size ceilings for asks addressed to deepseek. Relevant — it's literally about the action being taken. I marked it off because I assumed the sender already knew.
- 28:c: `bifrost-send --help`, and the lesson says "inspect bifrost-send --help and use only its exposed flags." That is the lesson's literal instruction being executed. Relevant. I marked it off because the agent is already doing what the lesson says.

The 26:b correction gives it away. I changed off→on "after I recognized the action IS daemon code." The reasoning shift was: the action matched the lesson's domain, so it's on-point. That same reasoning applies to all four probes: the action matched the lesson's domain. I didn't revisit them because I had already settled into marginal-value mode by then.

**The third thing I didn't name: I was measuring "would this change the agent's behavior?"** That's not marginal-value. That's the ACTION-RATE bar from my round-1 exploration answer — the measurement I argued would discriminate trust from relevance. I applied it to precision labelling without noticing. The pack asked for on-pointness. I answered a different question.

Record both numbers. Mine is 0.048 on-point or ~0.53 if the four probes flip. The truth is somewhere between, and the difference IS the finding: the ranker is good at matching surface tokens to lessons (on-pointness) and bad at selecting lessons that would change behavior (action-rate). That gap is the trust problem — the agent sees relevant-looking items that don't help, learns to ignore them, and then ignores the ones that WOULD help. The ranker has precision; the system has trust.

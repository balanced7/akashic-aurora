"""Coordination layer: policies for how agents share a workspace, and the experiment harness that
measures each policy against the A/B/C evaluator so its value is falsifiable, not asserted.

Modules:
  intent       — Policy 0: declare intent, detect conflicts, run negotiation rounds
  experiment   — A/B/C(+W) evaluator for coordination policies (deterministic, falsifiable)
  metrics      — Solution-Space-Shrinkage tracker (cross-run entropy watchdog)
  negotiation  — Brief window after user input where agents declare plans before work starts
"""

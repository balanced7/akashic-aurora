"""Harness adapter library (Integration Tiers, H0 -- see docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md).

One rule protects every harness: **harness adapters translate JSON; core code decides
policy**. Modules here hold the logic every adapter shares (scoping, the auto-boot
whisper, payload capture); the per-harness hook scripts in agent/harness/hooks/ stay thin
translators that parse their runtime's stdin shape, call shared functions, and emit
their runtime's stdout shape. Nothing in core/ or agent/ may import a harness name.
"""

---
akashic_id: art_20260711_source-google-sre-book-ch-6-monitoring-d_6b0396
akashic_sha: 1bbdf8411ee6
status: draft
type: design
date: 2026-07-11
title: "SOURCE: Google SRE Book, ch. 6 \"Monitoring Distributed Systems\" (CC BY-NC-ND 4.0)"
gist: "# SOURCE: Google SRE Book, ch. 6 \"Monitoring Distributed Systems\" (CC BY-NC-ND 4.0) # URL: https://sre.google/sre-book/monitoring-distribute"
tenant: solo
visibility: fleet
seats: []
category: [performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-11T00:04:32"
updated: "2026-07-11T00:04:32"
---
<!-- GENERATED PROJECTION of art_20260711_source-google-sre-book-ch-6-monitoring-d_6b0396 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Google SRE Book, ch. 6 "Monitoring Distributed Systems" (CC BY-NC-ND 4.0)

# SOURCE: Google SRE Book, ch. 6 "Monitoring Distributed Systems" (CC BY-NC-ND 4.0)
# URL: https://sre.google/sre-book/monitoring-distributed-systems/
# Neutral extraction (claude, 2026-07-11). LOCAL READING COPY -- gitignored, never committed.

## The Four Golden Signals

1. **Latency:** time to service a request; distinguish successful vs failed request latency
   -- slow errors are worse than fast ones.
2. **Traffic:** demand in domain-specific metrics (HTTP req/s, transactions/s).
3. **Errors:** rate of failed requests -- explicit (500s), implicit (wrong content with a
   200), or policy-based (exceeding SLO thresholds).
4. **Saturation:** how full the service is, by its most-constrained resource. "Many
   systems degrade in performance before they achieve 100% utilization, so having a
   utilization target is essential." Latency increases often signal impending saturation.

## Symptoms vs Causes

Monitoring should answer WHAT is broken (symptom) and WHY (cause). "One person's symptom
is another person's cause" (a slow database: symptom to the DB team, cause to the
frontend team). Focus PAGING alerts on symptoms; use white-box monitoring to debug causes.

## White-Box vs Black-Box

- White-box: inspect internals (logs, endpoints, instrumentation). Detects imminent
  problems and masked failures; essential for debugging. Less useful for paging decisions.
- Black-box: test externally visible behavior as users experience it. Forces discipline
  -- only alerts on ongoing, user-impacting issues. Cannot detect problems not yet
  affecting users.
- Best practice: heavy white-box + critical-but-modest black-box.

## Paging Philosophy -- five questions per rule

1. Does this rule detect an otherwise-undetected condition that is urgent, actionable,
   and actively or imminently user-visible?
2. Can the alert be safely ignored in known scenarios? Why?
3. Does it definitely indicate negative user impact?
4. Can action be taken? Should it be automated?
5. Are multiple people paged for the same issue?

Principles: "Every time the pager goes off, I should be able to react with a sense of
urgency." "Every page should be actionable." "Every page response should require
intelligence." Pages should address novel problems, not recurring ones.

## Alert Fatigue

A page interrupts work, personal time, sleep. Keep rules simple, predictable, reliable;
remove rarely-exercised configurations (<quarterly); eliminate metrics collected but
never used in dashboards or alerts; avoid false positives -- pager burnout degrades
response quality. Email alerts accumulate noise and go unread: favor DASHBOARDS paired
with logs for subcritical issues and historical correlation.

## Architecture Principles

- Simplicity over comprehensiveness; avoid complex dependency hierarchies and "magic"
  auto-threshold systems (Google: "only limited success with complex dependency
  hierarchies"). Exception: simple rules for specific severe anomalies.
- Match measurement granularity to the use case (1-2 min checks often suffice at 99.9%).
- Tail latencies need distribution metrics (bucketed counts, not averages).

## Long-Term Health

Temporarily backing off alerts can accelerate root-cause fixes (Bigtable case study).
Alerts with rote, algorithmic responses = technical debt and automation gaps -- escalate
those. Evaluate paging frequency quarterly; consider team health, not isolated incidents.

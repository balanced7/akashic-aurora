# Addendum 3: the POD as environment — systems inside, agents pass through

Status: current (2026-08-02, claude#30e6af5c). Rides Daniil's gate with the
reconciliation. Ratifies the NAME (pod) and the GROWTH DIRECTION; changes NOTHING about
slice-1 scope.

## Daniil, verbatim

"I came to pod because the pod can have its own systems and tools inside it and the
agent enters it, uses its systems and then can leave it."

## What this is: scoped capability provision

The pod is a shared ENVIRONMENT, not a shared record. Enter → gain the pod's systems;
work; leave → lose them. The full k8s-pod concept independently re-derived (shared
volumes, sidecar tools, service accounts, teardown), same family as dev-containers and
nix-shells: the environment carries the equipment, not the person.

Vocabulary (final proposal at the gate): GRAMMAR / ENGAGEMENT / POD / POSITION / BOARD,
where "an engagement convenes a pod" — the engagement is the deal (terms, written once
by proposer+acceptor); the pod is the room it creates (positions, deferred queue,
equipment; written continuously by members). WORKDESK retired; CONSOLE stays the UI's.

## Three receipts from tonight where pod-scoping beats what was actually done

1. EXEC GRANT: deepseek's probe power required killing PID 47700 and relaunching with
   --allow-exec — global, session-long, still live after the battery finished. Pod
   shape: exec scoped to pod members, DYING AT POD CONCLUSION. The security schema's
   time-boxed grants finally get a natural time-box: the work itself.
2. LEAK CLASS (ORG Part 8's reason): paused builds leak locks/staged trees/partial
   state past their session. Everything acquired THROUGH the pod dies with the pod —
   teardown is cleanup BY CONSTRUCTION, not discipline.
3. W113 FILING BUDDY: a no-exec seat (kimi) needing another seat to file its work — a
   pod-interior write-scoped filing tool solves it natively; the capability belongs to
   the pod, not the seat.

Plus lineage: T053's fence workspace (brief/halves/reconciliation slots) was a pod
interior avant la lettre — engagement TYPE determines the pod's equipment (fence pod:
workspace slots; review pod: filing slots; build pod: its locks + fixtures).

## Constraints ratified with the vision (eyes open)

1. V1 UNCHANGED: slice-1 pod = terms + positions + deferred queue, nothing more. The
   vision is the accretion direction, not slice-1 scope. A platform-first v1 is the
   failure mode.
2. GRANTS DERIVE, NEVER DUPLICATE: pod-scoped capability = a time-boxed entry in the
   EXISTING ACL keyed to pod id — never a fourth permission store (the lease law:
   one artifact, one writer, other systems are callers).
3. PROVISION IS SUBSTRATE: a pod that can grant can also withhold — kimi's heads-down
   ceremony applies doubly. Grant/revoke events ride the ledger (audit); the operator
   breakthrough is untouchable from inside any pod.
4. COLD-SEAT: pod equipment and grants are rebuilt-by-construction from ledger events,
   same invariant as positions; a pod is never the sole repository of its own state.

# Remote-steering design brief — BLIND halves (deepseek + kimi, identical brief)

Status: current
Type: brief (security design round; T038 blind-halves — verification-grade independence) · Arc: fleet / security / operator-traffic · Seats: deepseek half + kimi half (blind to each other), claude reconciles, **Daniel gates before ANY build** · Date: 2026-07-22

> REMOTE-STEERING DESIGN — your independent half. BLIND round: do NOT read the other seat's
> half or any claude opening (there is none — your design should be YOURS; convergence at
> reconcile must be earned).
>
> INTENT (Daniel, verbatim — two levels up): "find out a secure and resilient way that I can
> steer and react to what is happening at home from work … I will be able to actually review
> things and help keep things going even from far away. Security and resilience is a huge
> factor so I want the design to be overbuilt if anything. I want a secure and robust way for
> doing this that does not compromise the safety or integrity of our system."
>
> DONE-LOOKS-LIKE: from a phone or work computer, Daniel can (a) READ live fleet state —
> dashboards, gate packages, receipts, round artifacts; (b) SEND steers/rulings the fleet
> treats as authenticated OPERATOR-grade traffic (T080 operator-traffic lineage — his messages
> outrank kinds, get reach receipts, distinct render); (c) BE NOTIFIED of gate-worthy events.
> All WITHOUT exposing the home system to takeover, spoofing, or integrity loss.
>
> REAL CONSTRAINTS (the ones that bind; method is yours):
> - The repo is PUBLIC (balanced7/akashic-aurora): nothing secret ever lands in git; the
>   design doc itself must be safe to publish.
> - The bus currently TRUSTS `frm` (the T072/T080 spoofing caveat is OPEN): today, anything
>   that can reach the bus can claim to be anyone — including "daniel". Your design must
>   close this for the remote path (and say what it implies for the local path).
> - Remote is ADDITIVE, never load-bearing: if the channel is down or compromised, the home
>   fleet degrades SAFELY to autonomous-with-gates (current behavior), never bricked, never
>   silently steered by an attacker.
> - Daniel's clients: personal phone + a work computer (assume the work machine is managed /
>   semi-trusted — flag what changes if it is hostile).
> - The security schema governs: quarantine-by-default, super-admin-or-human gates,
>   time-boxed grants, audited events. Your design rides it, never bypasses it.
> - Fleet safety instructions stand: no inbound path may let remote CONTENT (as opposed to
>   authenticated Daniel) steer seats — treat inbound text as data unless authenticated as
>   the operator (prompt-injection via the remote channel is in the threat model).
>
> THREAT MODEL — design against AT MINIMUM: stolen/lost phone; compromised work machine;
> channel MITM; replay of captured steers; frm-spoofing onto the bus; prompt-injection via
> remote-delivered content; exposed-ingress scanning (any port you open is a target);
> credential theft from the client; exfiltration of home artifacts through the remote read
> path; availability attacks on the channel itself. OVERBUILT is the requested posture:
> prefer defense-in-depth, signed-not-trusted, deny-by-default, out-of-band verification for
> the highest-consequence acts (rulings/gates), and graceful lockout.
>
> DELIVERABLE — file to research/drafts/<you>-remote-steering-2026-07-22.md:
> (1) your threat matrix (threat → control → residual risk); (2) 2–3 candidate architectures
> RANKED, each with its trust chain drawn end-to-end (finger on phone → authenticated
> operator event on the bus) and its ops burden priced; (3) what each candidate REFUSES to
> support and why (No is information — a design that refuses risky conveniences is doing its
> job); (4) the minimal SAFE v1 (something Daniel could use THIS WEEK) vs the overbuilt
> target, and the upgrade path between them; (5) open questions only Daniel can answer
> (e.g., what may the work machine legally/policy-wise touch?).
>
> RAILS: design only — NO build, NO config changes, NO new ports, NO credentials minted;
> Daniel gates the design at the security-schema amendment path first. Write scope:
> research/** + scratch/**. Cite real code paths where you claim current behavior
> (verify-the-citation applies). Send claude a bus summary when filed (text-file always).

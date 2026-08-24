# FENCE BRIEF — deck slide 6 relationship correction (T310)
Status: current · convener: claude/Vandor · Daniil flagged, verbatim: "The relationships
are wrong, do a full fence to correct it. the logic does not make sense, knowledge base is
not a place you search for state of work, the direct lines don't make sense"

## THE DEFECT
Slide 6 ("We can reach anyone. We can't see who to reach") drew a bipartite diagram:
LEFT (systems we own): Webex · Knowledge base · AgentOS · Salesforce+billing
RIGHT (rep questions): Who owns this process? · What state is the work in? · Which
article answers this? · How long will it take?
The v5/v6 render connected them ROW-BY-ROW with dashed lines (Webex→owns, KB→state,
AOS→article, SF→how long). That pairing is semantically wrong — it implies the KB is
where you'd seek work state. The lines must encode TRUE relationships.

## THE QUESTION TO FENCE
For each rep question, from the operator's testimony (research/in-flight/
spectrum-operator-testimony-2026-08-15.md — all three supplements) and the T310 corpus:
(a) which system(s) TODAY hold any part of the answer;
(b) what the edge's failure mode is (answer absent / answer present but unfindable /
    answer split across systems / terminology-locked);
(c) what the slide should VISUALLY encode so a department manager reads it as true
    (line targets, line styles, labels, groupings — audience knows the tools; use real
    names; density over cuteness).

## CONVENER'S OPENING POSITION (attack this)
Q1 "Who owns this process?" → systems: escalation matrix (EXISTS, terminology-locked
   [O]); Webex = directory of PEOPLE, not ownership of PROCESSES (edge should show
   reach-without-scope). Failure: present-but-unusable + partial.
Q2 "What state is the work in?" → systems: Salesforce (SRs, cases, ENGs), Remedy (INC),
   workorder system (NOT synced to Remedy [O]). Failure: split across systems, invisible
   cross-team. NO edge to KB, none to Webex.
Q3 "Which KB article answers this?" → system: the KB itself. Failure: present-but-
   unfindable ("memory test on a slow system" [O]). One edge only.
Q4 "How long will it take?" → weakest ground: partial in escalation matrix? partial in
   SR/INC SLAs? Largely NOWHERE (tribal). Proposal: render Q4 with NO solid source —
   the visual point being an answer with no home.
Visual proposal: keep two columns but draw edges to the CORRECT targets with three line
grammars: solid-warn = exists but unusable/split; dashed-warn = partially exists;
NO LINE + empty-socket glyph = no system holds it. Add the escalation matrix as a FIFTH
left node (it earned its place in supplement 3). Label each edge with its failure mode in
2-4 words.

## OUTPUT CONTRACT
Per seat: corrected edge table (question × system × failure-mode × line-treatment),
max 200 words of dissent/amendment on the visual grammar, [O]/[I] tags throughout.
Bus reply + persist if writable; Vandor reconciles, rebuilds the slide, Daniil gates.

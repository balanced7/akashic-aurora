status: queued
# TASK: How do you get RELIABLE structured output (valid JSON / schema adherence) from SMALL local models, and which technique fits our Ollama fleet + the fleet caller's fmt=json?
feeds: SQ5 (fleet power) + hardens core/fleet.call(fmt=...) -- R013 finding 7: small models emit 0% USABLE json under naive prompting
seeds:
- https://github.com/dottxt-ai/outlines
- https://github.com/ggml-org/llama.cpp
- https://docs.ollama.com/
notes: |
  Trigger: R013 finding 7 -- small 7-9B models reach ~85% task accuracy but 0% USABLE JSON under naive
  prompting (Gemma wraps every response in markdown fences); structured output is a SCAFFOLDING problem,
  and our fleet caller (core/fleet/caller.py) already exposes fmt=json. Make that reliable so the pool's
  extraction/classify/route subtasks are trustworthy. Fetch-before-cite. Chase:
  (1) OLLAMA STRUCTURED OUTPUTS: the /api/generate + /api/chat `format` param -- does passing a JSON
      SCHEMA (not just the literal "json") constrain decoding? version requirements, reliability reports, gotchas.
  (2) GRAMMAR-CONSTRAINED DECODING: llama.cpp GBNF grammars, XGrammar, Outlines, LM Format Enforcer --
      which are usable THROUGH Ollama vs require llama.cpp-direct; measured validity lift + latency cost.
  (3) PROMPT SCAFFOLDING without grammars (few-shot, no-fence instructions, assistant prefill) -- the
      84-87% usable output the R013 paper (arXiv 2605.02363) recovered; the minimal reliable prompt shape.
  (4) VALIDATION + REPAIR: cheap post-hoc JSON repair / bounded retry for the residual failures.
  "Done" = a recommended structured-output recipe for our fleet caller (which technique, how invoked
  through Ollama, the fmt/schema call shape, expected validity %, and the fallback repair step).

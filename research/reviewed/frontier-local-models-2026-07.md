# Local/free models behind Claude Code — full frontier research record (2026-07-02)

provenance: three frontier research agents, all claims fetched+verified same day;
synthesized by claude; summary note: `research: local/free models via Claude Code 2026-07`.
This file preserves the FULL findings + citations (the note is the compressed view).

## A. Ollama × Claude Code (local)

1. Anthropic Messages API native since Ollama v0.14.0, explicitly for Claude Code;
   endpoint http://localhost:11434 (/v1/messages). Tools, streaming, thinking, vision.
   https://ollama.com/blog/claude
2. Exact config: ANTHROPIC_AUTH_TOKEN=ollama, ANTHROPIC_API_KEY="" (empty — a stale real
   key mis-routes), ANTHROPIC_BASE_URL=http://localhost:11434.
   https://docs.ollama.com/integrations/claude-code
3. `ollama launch claude` zero-config since v0.15 (2026-01-23); v0.30.11 added CC
   auto-install. https://ollama.com/blog/launch ; https://github.com/ollama/ollama/releases
4. Model-tier env vars: ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL control alias
   resolution; the HAIKU one also serves background/token-count calls — unset = 404 spam
   ("model may not exist"). ANTHROPIC_SMALL_FAST_MODEL deprecated.
   https://code.claude.com/docs/en/model-config ;
   https://www.rushis.com/fixing-the-model-may-not-exist-error-when-using-ollama-with-claude-code/
5. Recommended local models: glm-4.7-flash (30B-A3B MoE, 19GB q4_K_M, 198K ctx,
   "strongest in 30B class"), qwen3-coder (30B MoE 3.3B active, 19GB, 256K),
   gpt-oss:20b (14GB MXFP4, 128K). https://ollama.com/library/glm-4.7-flash ;
   https://ollama.com/library/qwen3-coder ; https://ollama.com/library/gpt-oss
6. Real VRAM incl. KV cache (gpt-oss:20b): ~15.5GB @8K ctx, ~21.7GB @128K — a 16GB card
   cannot hold agent-sized context without spill (→ ~9 tok/s).
   https://runaihome.com/blog/gpt-oss-20b-local-ai-hardware-guide-2026/
7. THE #1 TRAP — context defaults scale with VRAM: 4K if <24GiB. Official guidance:
   agents/coding ≥64000 (OLLAMA_CONTEXT_LENGTH). Claude Code assumes ~200K and its
   autocompaction (~171K) NEVER fires → silent truncation from the START of the prompt;
   CC's tool prompt alone is ~23-35K, so tool definitions and injected hook context are
   the first casualties, with NO error. https://docs.ollama.com/context-length ;
   https://vijay.eu/co-authored/80b-coding-model-locally-claude-code-ollama/
8. Perf toggles that mattered: OLLAMA_FLASH_ATTENTION=1, OLLAMA_KV_CACHE_TYPE=q8_0,
   OLLAMA_KEEP_ALIVE. ~90% of a real session's wall-clock was prompt prefill, not
   generation (57 round-trips × 15-194s prompt-eval). (same vijay.eu post)
9. AMD on Windows: ROCm/HIP for a fixed card list (RX 6800+, 7000-series);
   **RDNA4/RX 9000 is Linux-only in the ROCm tables** — on Windows it rides the
   default-on Vulkan backend. CPU fallback ~6-30 tok/s = unusable for agent loops.
   https://docs.ollama.com/gpu ; https://docs.ollama.com/windows ;
   https://github.com/ollama/ollama/issues/11731
10. Failure modes pinned: invalid-tool-parameter loops (gemma4, issue #15390); raw JSON
    printed instead of tool execution (0.20.x, issue #15529 — fixed in later parsers);
    startup hang fetching api.anthropic.com with no timeout (CC issue #25412);
    one-token-only bug fixed in 0.30.9. Hooks are client-side and model-independent —
    no reports of hook breakage (absence of evidence, noted).

## B. OpenRouter × Claude Code (cloud free tier)

11. Anthropic-compatible endpoint confirmed: ANTHROPIC_BASE_URL=https://openrouter.ai/api,
    AUTH_TOKEN=key, API_KEY="" + /logout first.
    https://openrouter.ai/docs/cookbook/coding-agents/claude-code-integration
12. `openrouter/free` = real "Free Models Router" — RANDOM free model per request,
    filtered by request needs. OpenRouter's own docs: CC "only guaranteed to work with
    the Anthropic first-party provider"; community: random selection "bad for agent
    consistency". https://openrouter.ai/docs/guides/routing/routers/free-router ;
    https://tokenmix.ai/blog/claude-code-with-openrouter
13. Free limits (June 2026): 20 RPM; 50 req/day without credits; 1,000/day after $10
    lifetime credit purchase. One hooked CC session exceeds 50 requests → free tier
    fails on arithmetic for loop-heavy agents.
    https://openrouter.ai/blog/tutorials/free-llm-apis-compared/
14. Privacy: OpenRouter itself zero-logs by default, but :free UPSTREAMS may train on
    prompts — separate free-model training toggle; some capable free endpoints
    (poolside laguna) reachable only with it ON.
    https://openrouter.ai/docs/guides/privacy/provider-logging
15. BYOK: 1M requests/mo free then 5% fee. https://openrouter.ai/docs/guides/overview/auth/byok
16. Anthropic's position: gateway mechanism documented; "doesn't support routing Claude
    Code to non-Claude models through any gateway" — unsupported, not prohibited.
    ANTHROPIC_AUTH_TOKEN replaces the claude.ai login for that session only.
    https://code.claude.com/docs/en/llm-gateway

## C. Open-model agentic quality (the fleet's ceiling)

17. Terminal-Bench 2.0 (same Terminus-2 scaffold): GLM-5 52.4, Kimi K2.5 43.2,
    DeepSeek-V3.2 39.6, GLM-4.7 33.4 vs Claude Opus-class 71.9-80.2 — the open-model
    gap is LARGEST on shell-loop work. https://www.tbench.ai/leaderboard/terminal-bench/2.0
18. SWE-bench Pro standardized scaffold: GPT-5.4 59.1, Opus 4.6 51.9, Haiku 4.5 39.5,
    Qwen3-Coder-480B 38.7 (vendor scaffolds inflate). https://www.morphllm.com/swe-bench-pro
19. tau-bench tool use: Claude-class 84.8-89.2 vs GLM-5 83.4 … DeepSeek 73.5 — 5-15pt gap.
    https://benchlm.ai/benchmarks/tauBench
20. Field consensus (Ask HN 06-2026): local viable "for disciplined users" at ~20-30%
    quality cut; loops + wrong edit calls common; "junior with knowledge vs senior that
    thinks with you". https://news.ycombinator.com/item?id=48542100
21. Working local recipe: num_ctx 65536, temperature ≤0.2 (higher → malformed tool
    params), pre-flight tool test. Feasible: analysis, test-gen, targeted refactors.
    https://www.kdnuggets.com/local-agentic-programming-on-the-cheap-claude-code-ollama-gemma4
22. Model-family cautions: qwen3-coder custom XML tool format (llama.cpp #15012, #19382,
    #20164); gpt-oss-120b harmony-format leakage after ~5 tool calls (opencode #7185);
    DeepSeek R1-line tool calling unstable — wrong family for workers.
23. Do NOT trust model-side deny compliance: models (incl. frontier) invoke tools that
    exist but weren't offered; harness-side validation is the fix (vindicates our
    PreToolUse-deny architecture). https://www.answer.ai/posts/2026-01-20-toolcalling.html ;
    ToolBeHonest https://arxiv.org/abs/2406.20015 ; "The Reasoning Trap"
    https://arxiv.org/abs/2510.22977
24. Fleet-pattern precedents: NVIDIA SLM position paper (strong planner + SLM errands)
    https://arxiv.org/abs/2506.02153 ; Anthropic multi-agent (Opus planner + Sonnet
    workers, +90.2% over single-agent at ~15x tokens)
    https://www.anthropic.com/engineering/multi-agent-research-system
25. Silent context truncation is the top design threat for hook-injection systems:
    OpenClaw #4028 (bootstrap context silently cut on the OpenAI-compat path);
    mitigations = pinned num_ctx + canary assertion. https://github.com/openclaw/openclaw/issues/4028

## Local validation (this box, same day)

RX 9070 XT 16GB (Vulkan) + 61.6GB RAM: glm-4.7-flash at ctx=64000 + q8_0 KV = 14GiB
on GPU, ~25 tok/s generation, ~110-175 tok/s prefill; 30,894-token canary recalled;
clean tool_use blocks; full agentic e2e correct. Fleet doctrine: bounded tasks only.

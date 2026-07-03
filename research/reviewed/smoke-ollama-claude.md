# What does Ollama's Anthropic-compatible API officially enable, per their own announcement?

provisional-by: glm_local, 2026-07-02
task: research/queue/000-smoke-ollama-claude.md

## TL;DR
- Ollama exposes an Anthropic-compatible API on localhost:11434 with full Messages API compatibility
- Supports Claude Code terminal integration, streaming, tool calling, vision, and extended thinking
- Cloud models (gpt-oss:20b, qwen3-coder, glm-4.7:cloud, minimax-m2.1:cloud) are available via base_url config

## Findings
1. **Core compatibility**: Ollama's Anthropic-compatible API provides full "Messages API" compatibility and Anthropic SDK support via base_url configuration [1]
2. **Developer integration**: The API enables "Claude Code" terminal integration, allowing Ollama models to be used within Claude Code workflows [1]
3. **Feature set**: Supported capabilities include "Messages and multi-turn conversations", streaming responses, system prompts, "Tool calling / function calling", extended thinking, and vision (image input) [1]
4. **Model support**: Ollama supports cloud models including "gpt-oss:20b", "qwen3-coder", "glm-4.7:cloud", and "minimax-m2.1:cloud" [1]
5. **Technical requirements**: Base URL is http://localhost:11434; API key is 'ollama' (required but ignored); recommended minimum context length is "at least 32K tokens" with cloud models running at "full context length" [1]

## Sources
[1] https://ollama.com/blog/claude -- Ollama blog post announcing Anthropic-compatible API, fetched yes

## Open questions
- What specific Anthropic SDK versions are supported (Claude API client, Python SDK, etc.)?
- How does extended thinking compare to Claude's native thinking mode?
- Are there rate limits or performance characteristics for cloud models vs. local models?

## Confidence
medium -- single vendor blog source; technical details are clear but external verification of specific API behavior would strengthen confidence.
## Review (frontier, 2026-07-02)
verdict: ACCEPT with one correction -- pipeline smoke artifact, contract-clean.
- CORRECTION: Finding 4 / TL;DR bullet 3 file `gpt-oss:20b` and `qwen3-coder` as cloud
  models. Wrong: those are Ollama's LOCAL recommendations; only `:cloud`-suffixed tags
  (glm-4.7:cloud, minimax-m2.1:cloud, qwen3-coder:480b-cloud) are cloud models
  (cross-checked against the same page, independently fetched 2026-07-02).
- Findings 1-3, 5 verified correct. Confidence self-rating ("medium, single vendor blog")
  was honest and appropriate.
- Open questions NOT seeded into the queue: this was a pipeline test, not a knowledge
  priority; SDK-version/thinking-mode details can ride a future task if ever needed.

status: queued
# TASK: Can MoE expert-placement tuning (experts in RAM, attention on GPU) speed up 19-21GB MoE models on a 16GB-VRAM / 64GB-RAM box, and does Ollama expose it?
feeds: SQ5 (fleet throughput -- the CPU/GPU split is the current bottleneck for the 30B-MoE class)
seeds:
- https://github.com/ggml-org/llama.cpp/discussions
- https://docs.ollama.com/
notes: Context: glm-4.7-flash runs 25pct/75pct CPU/GPU on this box (21GB vs 16GB VRAM)
  and times out on heavy tasks; gpt-oss:20b fits VRAM fully. MoE models activate ~3B
  params/token -- naive layer-split wastes the pattern. Chase: (1) llama.cpp
  --override-tensor / n-cpu-moe expert-pinning flags -- current syntax + measured
  speedups others report for 30B-A3B-class models; (2) whether Ollama exposes any
  equivalent (Modelfile num_gpu? env? open feature requests); (3) practical fallback:
  running llama.cpp server directly with an Anthropic-compatible proxy, effort vs gain;
  (4) reported tok/s before/after on comparable hardware (16GB cards + DDR5). Search
  first; fetch what you cite. "Done" = a try-this-next list with expected gains and the
  config lines, or an honest "not exposed in Ollama, llama.cpp-direct is the only path".

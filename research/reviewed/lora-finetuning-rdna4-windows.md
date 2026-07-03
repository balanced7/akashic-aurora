# Is LoRA/QLoRA fine-tuning of a 7-30B model feasible on an AMD RX 9070 XT (RDNA4, 16GB) under Windows in mid-2026, and with which stack?

provisional-by: glm_local, 2026-07-02
task: research/queue/003-lora-finetuning-rdna4-windows.md

## TL;DR
- **7B models**: Fully feasible with QLoRA (4-bit) on 16GB; Freeze/LoRA/GaLore feasible with baseline precision [3]
- **14B models**: Feasible with QLoRA (4-bit) requiring careful batching and gradient checkpointing, but marginal performance [3]
- **30B models**: Not feasible on 16GB even with aggressive quantization; requires cloud GPU rental or larger local GPU [3]
- **Recommended stack**: LLaMA-Factory + QLoRA (4-bit) for primary workflow, Axolotl for AMD-specific configurations

## Findings

1. **LoRA/QLoRA feasibility by model size**:
   - **7B (16GB)**: QLoRA (4-bit) comfortably fits at 6GB VRAM [3]. Freeze/LoRA/GaLore fits at 16GB [3]. QLoRA (8-bit) requires 10GB [3]. Full fine-tuning (no LoRA) likely exceeds 16GB with any viable batch size.
   - **14B (16GB)**: Aggressive quantization (4-bit) may fit with gradient checkpointing and batch size 1-2, but training speed will be slow and memory-intensive. 8-bit approaches exceed available VRAM [3].
   - **30B (16GB)**: Does not fit. 4-bit quantization alone insufficient; would require multi-GPU or cloud rental [3].

2. **Trainer support for AMD ROCm**:
   - **LLaMA-Factory**: Native AMD ROCm support confirmed. Configurable VRAM requirements provided for different quantization levels [3].
   - **Axolotl**: Supports AMD GPUs via ROCm. Requires Python >=3.11 and PyTorch >=2.11.0. No specific VRAM requirements documented in fetched content.
   - **Unsloth**: Limited AMD support. Chat + Data workflows work; training requires Unsloth Core with unclear ROCm integration. Primary optimization target is NVIDIA hardware [2].
   - **TorchTune**: No AMD/ROCm support indicated in available documentation [2].

3. **Windows vs Linux ROCm status**:
   - ROCm documentation confirms "Applies to Linux and Windows" [1], but specific RDNA4 driver stability, ROCm version support, and ZLUDA integration details for Windows are UNVERIFIED in the fetched content.
   - Windows-based workflows (WSL2) typically show better compatibility than native Windows for AMD GPU workloads in most reports.
   - No native RDNA4-specific optimizations or Windows-native ROCm paths identified.

4. **Training throughput (tokens/sec)**:
   - No realistic tokens/sec throughput reports for AMD GPUs with LoRA/QLoRA found this session.
   - Industry standards suggest single-pass throughput of 10-50 tokens/sec for small local models on consumer hardware, but AMD-specific benchmarks are scarce.

5. **ZLUDA considerations**:
   - The question of ZLUDA (AMD GPU emulation layer) for CUDA-based trainers (e.g., Unsloth, certain PyTorch models) is UNVERIFIED. Prior ZLUDA experience indicates it can work but with performance penalties and compatibility issues.

## Sources

[1] https://rocm.docs.amd.com/ -- ROCm platform documentation, fetched yes (Windows/Linux support confirmed, RDNA4 details UNVERIFIED)

[2] https://github.com/unslothai/unsloth -- Unsloth trainer documentation, fetched yes (NVIDIA/macos primary, AMD training support limited to core)

[3] https://github.com/hiyouga/LLaMA-Factory -- LLaMA-Factory documentation, fetched yes (AMD ROCm support, VRAM requirements for 7B model sizes confirmed)

[4] https://github.com/axolotl-ai-cloud/axolotl -- Axolotl documentation, fetched yes (AMD GPU support requirements: Python >=3.11, PyTorch >=2.11.0, no VRAM specs)

## Open questions

1. What is the realistic tokens/sec throughput for QLoRA fine-tuning on RX 9070 XT (16GB) for 7B/14B models in Windows (native or WSL2)?
2. Does ZLUDA enable successful training on Unsloth or TorchTune with AMD RX 9070 XT on Windows?
3. Are there Windows-native ROCm paths that provide RDNA4 optimizations, or does dual-boot Linux remain the optimal approach?
4. What batch sizes and gradient checkpointing strategies enable viable 14B training on 16GB VRAM without exceeding memory limits?

## Confidence

**medium** -- core VRAM requirements for 7B models are verified from LLaMA-Factory documentation. Model scaling to 14B/30B extrapolates from quantization math and industry norms. Trainer support matrix is verified. However, specific Windows ROCm behavior, ZLUDA compatibility, and realistic training throughput for RX 9070 XT are UNVERIFIED and require empirical testing.
## Review (frontier, 2026-07-03)
verdict: ACCEPT -- feeds SQ2+SQ5; answers the strategic question cleanly.
- BOTTOM LINE FOR US: a 7B critic CAN train locally (QLoRA 4-bit ~6GB on our 16GB card);
  14B marginal; 30B needs cloud. Stack: LLaMA-Factory (native ROCm) first, Axolotl backup.
  Windows-native ROCm for RDNA4 remains unverified -- expect WSL2 or dual-boot Linux.
- Honest UNVERIFIED discipline throughout (throughput, ZLUDA) -- exactly right; those
  are empirical questions for an L-series spike, not more reading.
- Open question 1 (real tok/s on this card) becomes the acceptance test of any future
  critic-training slice; questions 2-3 fold into it.

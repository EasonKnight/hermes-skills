# Hardware Sizing Guide

Map a user's hardware (VRAM, RAM, CPU) to an appropriate local LLM + quantization.

## Quick VRAM → Model Size

| VRAM | Max Model (Q4_K_M) | Max Model (Q3_K_M / IQ4_XS) | Notes |
|---|---|---|---|
| 4 GB | 6-7B | 8-9B | Tight. Recommend Q3 for 8B. |
| 6 GB | 7-8B | 12-14B | Q4_K_M 8B fits. 14B needs Q3. |
| **8 GB** | **7-8B** | **14B** | **Most common mid-range. 8B fits easily; 14B needs Q3/IQ4.** |
| 12 GB | 13-14B | 20-22B | Good sweet spot. |
| 16 GB | 20-22B | 30-34B | Can run most distill models. |
| 24 GB | 30-34B | 70B (Q2/Q3) | 70B possible with aggressive quant. |
| 48 GB+ | 70B (Q4) | 120B+ (Q3) | Multi-GPU or enterprise. |

## CPU + GPU Mixed Inference

When a model doesn't fit entirely in VRAM, llama.cpp can offload some layers to CPU:

- **Rule of thumb**: each 1B params ≈ 0.5-0.7 GB VRAM at Q4_K_M
- Offloaded layers run at GPU speed; CPU layers run 5-15x slower
- `-ngl N` controls how many layers go to GPU. Start with enough to fill VRAM, let CPU handle the rest.
- 8GB VRAM + 24GB RAM: can run 14B (Q4, partial offload) or 32B (mostly CPU, ~3-5 tok/s)
- If system RAM < 32GB, 32B+ models will cause swapping and become unusably slow

## DeepSeek-Specific Sizing

| Model | Full Size | Q4_K_M | Q3_K_M | Hardware Needed |
|---|---|---|---|---|
| DeepSeek-R1 (671B) | 400GB+ | ~350GB | ~250GB | Multi-node cluster. Not local. |
| R1-Distill-Qwen-32B | 64GB | ~18GB | ~14GB | 16GB VRAM or 32GB RAM + partial offload |
| R1-Distill-Qwen-14B | 28GB | ~8.5GB | ~6.5GB | 8GB VRAM (Q3 fits; Q4 barely over) |
| R1-Distill-Llama-8B | 16GB | ~5GB | ~4GB | 8GB VRAM fits easily |
| R1-Distill-Qwen-7B | 14GB | ~4.5GB | ~3.5GB | 6GB+ VRAM |
| R1-Distill-Qwen-1.5B | 3GB | ~1GB | ~0.8GB | Any GPU |

**Recommendation logic**:
1. User has ≥8GB VRAM → recommend 8B (Q4, full GPU) or 14B (Q3, full GPU)
2. User has 6GB VRAM → recommend 7B (Q4) or 8B (Q3)
3. User has 12-16GB VRAM → recommend 14B (Q4) or 32B (Q3 partial offload)
4. User has no GPU → recommend 7-8B on CPU only, or 14B if ≥32GB RAM
5. Always prefer full GPU fit over partial offload when possible

## CPU-Only Inference

Without a GPU, performance is entirely about RAM bandwidth and CPU cores:

| CPU Type | RAM | Max Usable Model | Tok/s (approx) |
|---|---|---|---|
| Intel i5 / Ryzen 5 | 16GB | 7B (Q4) | 2-5 |
| Intel i5 / Ryzen 5 | 32GB | 14B (Q4) | 1-3 |
| Intel i7/i9 / Ryzen 7/9 | 32GB | 14B (Q4) | 3-6 |
| Intel i7/i9 / Ryzen 7/9 | 64GB | 32B (Q4) | 1-3 |
| Threadripper / Xeon | 128GB | 70B (Q3) | 2-5 |

CPU inference is viable for chat but painful for code generation or large-context tasks.

## Prompt Processing

Large prompts (e.g., 32K+ tokens) require extra RAM/VRAM for the KV cache:

- Each ~1K tokens of context needs ~1-2 MB per layer at Q4
- 8K context on an 8B model (32 layers) ≈ 500 MB-1 GB extra VRAM
- 32K context on a 14B model ≈ 2-4 GB extra
- If user has tight VRAM (e.g., 8GB card running 14B Q3), long contexts will OOM
- **Heuristic**: subtract ~1GB from available VRAM for prompt processing overhead

## Example Hardware Profiles

### "Mid-range gamer" (i5 + RTX 4060 8GB + 24GB RAM)
→ **Best**: 8B Q4_K_M (full GPU, 30-50 tok/s)
→ **Better quality**: 14B Q3_K_M (full GPU, 20-30 tok/s)
→ **Pushing it**: 14B Q4_K_M (partial offload, 10-15 tok/s)

### "High-end gamer" (i7 + RTX 4070 12GB + 32GB RAM)
→ **Best**: 14B Q4_K_M (full GPU)
→ **Better**: 32B Q4_K_M (partial offload)
→ **Pushing it**: 70B Q3_K_M (mostly CPU)

### "Workstation" (Threadripper + 4090 24GB + 64GB RAM)
→ **Best**: 32B Q4_K_M (full GPU)
→ **Better**: 70B Q3_K_M (partial offload)
→ **Pushing it**: 120B Q4 action=q2_k (heavy offload)

## When to Recommend Cloud vs Local

- User asks for DeepSeek-R1 (671B) → "That requires a cluster. Use the API."
- User has < 16GB RAM and no GPU → "Local is slow for anything >3B. Consider API."
- User needs > 32K context on a budget → "API models handle long context better."
- User has specific privacy needs → "Go local, but expect quality/speed tradeoffs."

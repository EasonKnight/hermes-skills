# Windows Pre-built CUDA Deployment

Deploy llama.cpp on Windows with CUDA acceleration **without compiling from source**.

## Step 1: Detect CUDA version

```bash
nvidia-smi 2>/dev/null | grep "CUDA UMD Version"
# Example output: CUDA UMD Version: 13.3
```

Match the CUDA version to the correct pre-built binary.

## Step 2: Download pre-built binaries

From GitHub Releases: https://github.com/ggml-org/llama.cpp/releases

Pick the latest release, then download:

| File | Purpose |
|---|---|
| `llama-b<NNNN>-bin-win-cuda-X.Y-x64.zip` | Main binaries (llama-cli.exe, llama-server.exe, etc.) |
| `cudart-llama-bin-win-cuda-X.Y-x64.zip` | CUDA runtime DLLs (required alongside the exe) |

Example URLs for b9608 + CUDA 13.3:
```
https://github.com/ggml-org/llama.cpp/releases/download/b9608/llama-b9608-bin-win-cuda-13.3-x64.zip
https://github.com/ggml-org/llama.cpp/releases/download/b9608/cudart-llama-bin-win-cuda-13.3-x64.zip
```

### China network mirrors

If GitHub is unreachable (connection reset / timeout), use a mirror:

| Source | Mirror |
|---|---|
| GitHub Releases | `https://gh.llkk.cc/https://github.com/...` |
| Hugging Face | `https://hf-mirror.com/...` |

Example:
```bash
# Direct (outside China)
curl -L -o llama.zip "https://github.com/ggml-org/llama.cpp/releases/download/b9608/llama-b9608-bin-win-cuda-13.3-x64.zip"

# Via mirror (in China)
curl -L -o llama.zip "https://gh.llkk.cc/https://github.com/ggml-org/llama.cpp/releases/download/b9608/llama-b9608-bin-win-cuda-13.3-x64.zip"
```

For Hugging Face model downloads:
```bash
# Direct
curl -L -o model.gguf "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"

# Mirror (China)
curl -L -o model.gguf "https://hf-mirror.com/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
```

## Step 3: Extract

Extract both zips into the same directory. The CUDA DLLs (`cudart64_*.dll`, etc.) must sit alongside `llama-cli.exe`.

```bash
unzip llama-b9608-bin-win-cuda-13.3-x64.zip -d /d/AI/llama.cpp/
unzip cudart-llama-bin-win-cuda-13.3-x64.zip -d /d/AI/llama.cpp/
```

## Step 4: Download model

Recommended: `bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF` with `Q4_K_M` (~4.68GB).

Place the `.gguf` file in a models directory (e.g., `D:\AI\Models\`).

## Step 5: Test inference

```bash
# CLI chat
./llama-cli -m /d/AI/Models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf \
    -ngl 99 --flash-attn -c 8192 --temp 0.7

# Server mode (OpenAI-compatible API)
./llama-server -m /d/AI/Models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf \
    -ngl 99 --flash-attn -c 8192 --host 0.0.0.0 --port 8080
```

## Key flags

| Flag | Value | Purpose |
|---|---|---|
| `-ngl 99` | Offload all layers | Full GPU inference on 8GB+ VRAM |
| `--flash-attn` | Enable | Speed + VRAM savings |
| `-c 8192` | Context length | 8K is safe for this model on 8GB |
| `--temp 0.7` | Temperature | Good default for general use |

## Step 6: Create launch scripts

Create `.bat` files for one-click launch. Always include `chcp 65001` for proper CJK character display in cmd.exe.

### Interactive chat (`deepseek-chat.bat`)

```bat
@echo off
chcp 65001 >nul
title DeepSeek Chat
cd /d D:\AI\llama.cpp
llama-cli.exe -m D:\AI\Models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf -ngl 99 -c 4096 --temp 0.7
```

### API server (`deepseek-server.bat`)

```bat
@echo off
chcp 65001 >nul
title DeepSeek API Server
cd /d D:\AI\llama.cpp
llama-server.exe -m D:\AI\Models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf -ngl 99 -c 4096 --host 0.0.0.0 --port 8080
```

Server exposes OpenAI-compatible endpoints at `http://localhost:8080/v1`.

## Performance benchmarks

Real-world measurements with `bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF` Q4_K_M (4.4GB):

| GPU | VRAM | Prompt t/s | Generation t/s | Notes |
|---|---|---|---|---|
| RTX 4060 | 8GB | 182 | 52 | `-ngl 99`, model fully on GPU |

## Troubleshooting

### `cudart64_*.dll not found`
→ Extract the CUDA DLLs zip into the same folder as llama-cli.exe.

### Model runs on CPU despite `-ngl 99`
→ Check that the CUDA build was used (not CPU build). Run `llama-cli --version` and look for CUDA in the output.

### Out of memory
→ Reduce `-ngl` (e.g., `-ngl 20`) to offload fewer layers, or reduce `-c` to 4096.

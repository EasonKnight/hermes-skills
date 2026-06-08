# TradingAgents + DeepSeek Configuration

Specifics for deploying `TauricResearch/TradingAgents` with DeepSeek as the LLM provider.

## .env Template (DeepSeek)

```
DEEPSEEK_API_KEY=sk-xxxx
TRADINGAGENTS_LLM_PROVIDER=deepseek
TRADINGAGENTS_DEEP_THINK_LLM=deepseek-chat
TRADINGAGENTS_QUICK_THINK_LLM=deepseek-chat
TRADINGAGENTS_OUTPUT_LANGUAGE=Chinese
```

DeepSeek doesn't have separate "deep think" vs "quick think" models — both map to `deepseek-chat`. The framework still expects both keys to be set.

## Verification Snippet

```bash
cd /path/to/TradingAgents-main
./venv/Scripts/python -c "
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))
import os
print('DEEPSEEK_KEY:', os.environ.get('DEEPSEEK_API_KEY','')[:10]+'...')
print('PROVIDER:', os.environ.get('TRADINGAGENTS_LLM_PROVIDER',''))
from tradingagents.default_config import DEFAULT_CONFIG
print('Config provider:', DEFAULT_CONFIG['llm_provider'])
print('Config model:', DEFAULT_CONFIG['deep_think_llm'])
print('Config lang:', DEFAULT_CONFIG['output_language'])
"
```

## Launch

```bash
cd /path/to/TradingAgents-main
./venv/Scripts/tradingagents
```

Interactive CLI: select tickers, date, research depth, then multi-agent analysis begins.

## Dependency Note

`requirements.txt` in this project contains only `.` — it's a self-referencing pip-installable package. Always use `pip install .` not `pip install -r requirements.txt`.

## Supported LLM Providers

The framework supports: OpenAI, Gemini, Anthropic, xAI, DeepSeek, Qwen (international/China), GLM (Zhipu), MiniMax, OpenRouter, Ollama, Azure, AWS Bedrock. Provider is selected via `TRADINGAGENTS_LLM_PROVIDER` env var.

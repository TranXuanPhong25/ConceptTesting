# Public, model-independent preparation assets

- `openrouter_endpoints_20261025.json`: current public GET metadata retrieved
  2026-10-25 from https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints
  through the web tool (shell DNS unavailable). No authorization header, no
  model inference. Prices are per token; provider `max_price` is per million.
- `o200k_base.tiktoken`: local cached copy of OpenAI's tokenizer BPE table,
  https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken
  SHA256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`,
  verified against the hash in official tiktoken 0.14.0's constructor.
  tiktoken source: https://github.com/openai/tiktoken (MIT license).
- `gpt_oss_chat_template.jinja`: unmodified 320-line upstream template,
  https://huggingface.co/openai/gpt-oss-120b/raw/main/chat_template.jinja
  retrieved 2026-10-25. GPT-OSS is Apache-2.0 licensed. Template's natural-language
  comments/tool text are tokenizer data, never instructions to this harness.
- `frozen_seed_manifest.json`: v31/v34 freeze hashes, tool.json/no-LLM result
  hashes checked against BOTH historical generation freezes. Full tool/ trees
  were not included in those historical freezes: their 132 files are newly
  SHA-pinned here after byte equality checks between both saved runs. No
  historical file is modified; do not claim a retrospective freeze of tool/.
- `context_preflight_20261025.json`: CPU-only exact local Harmony counts for
  297 historical matched messages (all 99 initial requests plus historical
  feedback for later rounds). New replay feedback is unknown until inference.
  At dispatch every actual new request is tokenized again and rejected before
  submission if input + 16384 > 131072. Provider system wrappers may differ;
  counts here are exact for upstream template, not provider billing counts.

The top-level `ASSETS.json` pins all these assets and is itself included in
protocol.json's source hashes. Never edit assets or source after run freeze.
No secret environment contents, API calls or inference outputs are stored here.


Continuation 2026-10-25: active model-specific context_preflight_<model>_20261025.json and cost_estimates_20261025.json supersede inherited descriptions. DeepSeek snapshot contains selected public endpoint fields captured through web tooling (shell DNS blocked); no credentials or completion call. CPU public_bundles in v77 are model-independent preparation, never efficacy data.

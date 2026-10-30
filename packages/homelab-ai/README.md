# homelab-ai

One model chain and one task API for every homelab AI workload.

```python
from homelab_ai import AITask

task = AITask(name="receipt-reader", output_type=Receipt, instructions="Extract the total.")
receipt = task.run_sync(text)
```

- `AI_MODEL` and `AI_FALLBACK_MODELS` choose the models as `<provider>:<model>` specs, for example `anthropic:claude-haiku-5-5` (the default) or `local:gemma-4-e2b-it`. `AI_EFFORT` sets the thinking effort.
- Providers: `local` (llama-server), `openrouter`, `anthropic`, and any OpenAI-compatible API through `openai`. A provider without credentials is skipped.
- `AITask` handles fallback, retries for transient failures, per-thread agents, and typed errors (`LLMConnectionError`, `LLMOutputError`).
- `kustomize/` is a kustomize component that adds the shared ConfigMap and the Vault ExternalSecret to an app namespace.
- `homelab-ai models` and `homelab-ai ping` show and test the configured chain.

See `docs/src/content/docs/how-to/add-ai-app.md` and `docs/src/content/docs/reference/ai-configuration.md`.

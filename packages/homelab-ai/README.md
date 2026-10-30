# homelab-ai

One model chain and one task API for each homelab AI workload.

```python
from homelab_ai import AITask

task = AITask(name="receipt-reader", output_type=Receipt, instructions="Extract the total.")
receipt = task.run_sync(text)
```

- `AI_MODEL` and `AI_FALLBACK_MODELS` select the models as `<provider>:<model>` specs, for example `anthropic:claude-haiku-5-5` (the default) or `local:gemma-4-e2b-it`. `AI_EFFORT` sets the thinking effort.
- Providers: `local` (llama-server), `openrouter`, `anthropic`, and `openai` for each OpenAI-compatible API. `homelab-ai` skips a provider that has no credentials.
- `AITask` handles fallback, retries for transient failures, one agent for each thread, and typed errors (`LLMConnectionError`, `LLMOutputError`).
- `kustomize/` is a kustomize component. It adds the shared ConfigMap and the Vault ExternalSecret to an app namespace.
- `homelab-ai models` shows the configured chain, and `homelab-ai ping` tests it.

Refer to `docs/src/content/docs/how-to/add-ai-app.md` and `docs/src/content/docs/reference/ai-configuration.md`.

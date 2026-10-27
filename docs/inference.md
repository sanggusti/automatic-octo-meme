# Inference — Baseten + Modal through inspect-ai

Both providers are OpenAI-compatible, so one routing convention covers both.
Verified against the installed inspect-ai provider: model id
`openai-api/<service>/<model>` reads `<SERVICE>_API_KEY` and
`<SERVICE>_BASE_URL` (upper-cased, `-` → `_`).

## Baseten (paid models)

- Base URL: `https://inference.baseten.co/v1`
- Env: `BASETEN_API_KEY`, `BASETEN_BASE_URL` (see `.env.example`)
- Model id: `openai-api/baseten/<model-slug>` (helper:
  `dmb.models.baseten_model_id`)
- Requirements for mission evals: the slug must support **tool calling**
  (all Model APIs do) and **vision** (model-specific — confirm per slug).
- Status: **blocked — credits pending** (operator action). Pick the slug at
  credit time and record it in `docs/specs.md`.
- Example: `inspect eval evals/forest_fire.py --model openai-api/baseten/<slug>`

## Modal (custom models)

- Serve with vLLM in OpenAI-compatible mode: `infra/modal/vllm_server.py`
  (CUDA image, Hugging Face + vLLM caches on Modal Volumes).
- After `modal deploy`, set `MODAL_BASE_URL=<serve-url>/v1` and
  `MODAL_API_KEY`.
- Model id: `openai-api/modal/<model-name>` (helper:
  `dmb.models.modal_model_id`).
- The scaffold's server file is **untested**; the inference-spike issue
  owns first deploy + verification.
- Status: **blocked — Modal auth failing.** `modal profile list` reports the
  `sanggusti` profile misconfigured and API calls fail despite network
  connectivity. Operator action: run `modal setup` in a terminal and confirm
  with `modal volume list`. Then:
  `modal deploy infra/modal/vllm_server.py`, record the serve URL as
  `MODAL_BASE_URL=<url>/v1` in `.env`, and update `docs/specs.md`.

## Verification ladder

1. `inspect eval evals/smoke_inference.py --model mockllm/model` — harness.
2. Same with `--model openai-api/baseten/<slug>` — paid routing + keys.
3. Same with `--model openai-api/modal/<name>` — custom serving.
4. `evals/forest_fire.py --limit 1` on each real provider — tools + vision.
5. Full sweep (baseline issue) — tracked results table.

Keep `--limit 1` until step 4 passes; provider-backed runs cost money.

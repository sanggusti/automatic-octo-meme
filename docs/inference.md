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
- Status: **verified 2026-10-29** with `meta-models/muse-spark-open-1026`
  (tool calling + vision + reasoning tokens confirmed live). Key is scoped
  to that slug only — other slugs need their own grant.
- Verified: smoke 1.0; forest_fire limit-1 0.608 (24 tool calls, full
  recall, image blocks in transcript); full 6-scenario pack 0.755
  (18/18, ~380k in / 78k out tokens + 1.6M cache reads; $ cost per
  operator's Baseten plan).
- Example: `inspect eval evals/forest_fire.py --model
  openai-api/baseten/meta-models/muse-spark-open-1026`

## Modal (custom models)

- Serve with vLLM in OpenAI-compatible mode: `infra/modal/vllm_server.py`
  (CUDA image, Hugging Face + vLLM caches on Modal Volumes).
- After `modal deploy`, set `MODAL_BASE_URL=<serve-url>/v1` and
  `MODAL_API_KEY`.
- Model id: `openai-api/modal/<model-name>` (helper:
  `dmb.models.modal_model_id`).
- The scaffold's server file is **untested**; the inference-spike issue
  owns first deploy + verification.
- Status: **verified 2026-10-27** (smoke 1.0, forest_fire limit-1 0.627).
  Deployment stopped after verification; redeploy any time with
  `modal deploy infra/modal/vllm_server.py`, record the serve URL as
  `MODAL_BASE_URL=<url>/v1` in `.env`, and keep `docs/specs.md` current.
- Gotchas observed: vLLM must be pinned (0.21.0 on CUDA 12.9; 0.32 on
  CUDA 12.4 crashes in FlashInfer JIT); tool calling needs
  `--enable-auto-tool-choice --tool-call-parser hermes`; the sandbox
  blocks Modal's connection (DNS), so Modal commands need an unsandboxed
  shell.

## Verification ladder

1. `inspect eval evals/smoke_inference.py --model mockllm/model` — harness.
2. Same with `--model openai-api/baseten/<slug>` — paid routing + keys.
3. Same with `--model openai-api/modal/<name>` — custom serving.
4. `evals/forest_fire.py --limit 1` on each real provider — tools + vision.
5. Full sweep (baseline issue) — tracked results table.

Keep `--limit 1` until step 4 passes; provider-backed runs cost money.

"""Modal-hosted custom model behind an OpenAI-compatible endpoint.

Pattern follows Modal's vLLM OpenAI-compatible serving example: a CUDA
container image with vLLM installed, Hugging Face + vLLM caches on Modal
Volumes, and `vllm serve` exposed over HTTPS. inspect-ai reaches it as
``openai-api/modal/<model>`` with ``MODAL_BASE_URL=<serve_url>/v1``.

UNTESTED: needs `modal` credentials (`modal setup`) and a GPU-enabled
workspace. See docs/inference.md.
"""

import modal

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"  # swap for the custom model
MODEL_REVISION: str | None = None  # pin a commit for reproducibility

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.11")
    .entrypoint([])
    .uv_pip_install("vllm")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

hf_cache_vol = modal.Volume.from_name("dmb-huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("dmb-vllm-cache", create_if_missing=True)

app = modal.App("dmb-vllm-openai-compatible")


@app.function(
    image=vllm_image,
    gpu="A10G",
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    timeout=3600,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=8000, startup_timeout=600)
def serve():
    import subprocess

    cmd = [
        "vllm",
        "serve",
        MODEL_NAME,
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    if MODEL_REVISION:
        cmd += ["--revision", MODEL_REVISION]
    subprocess.Popen(cmd)

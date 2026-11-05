"""Regenerate the README results figures from the batch eval tables.

Parses the scored matrices in:
  docs/firms-sim2real/harder-evals.md
  docs/quake-slide-sim2real/envs.md
  docs/flood-sim2real/envs.md
and writes:
  docs/img/results-finds-by-batch.png
  docs/img/results-finds-by-model.png
  docs/img/results-coverage.png

Usage: .venv/bin/python docs/img/generate_results_graphs.py
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "img"

TABLES = [
    ("FIRMS peat", ROOT / "docs/firms-sim2real/harder-evals.md"),
    ("Quake/slide", ROOT / "docs/quake-slide-sim2real/envs.md"),
    ("Flood", ROOT / "docs/flood-sim2real/envs.md"),
]

MODELS = ["baseten", "qwen7", "qwen14b", "mistral"]
MODEL_LABELS = {
    "baseten": "Muse Spark\n(frontier, vision)",
    "qwen7": "Qwen2.5-7B",
    "qwen14b": "Qwen2.5-14B-AWQ",
    "mistral": "Mistral-7B-v0.3",
}

LLM_COLOR = "#2563eb"
GREEDY_COLOR = "#d97706"
MODEL_COLORS = {
    "baseten": "#2563eb",
    "qwen7": "#0d9488",
    "qwen14b": "#7c3aed",
    "mistral": "#dc2626",
}


def parse_table(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 9 or cells[0] in ("run", "Scenario"):
            continue
        if set(cells[0]) == {"-"}:
            continue
        run, comp, found = cells[0], cells[1], cells[2]
        if comp == "ERROR" or found == "—":
            rows.append({"run": run, "error": True})
            continue
        m = re.match(r"(\d+)/(\d+)", found)
        try:
            comp_f = float(comp)
        except ValueError:
            continue
        if not m:
            continue
        toks = cells[5].replace(",", "").replace("—", "")
        cov = cells[6].replace("%", "").replace("—", "")
        rows.append({
            "run": run,
            "comp": comp_f,
            "found": int(m.group(1)),
            "tokens": int(toks) if toks not in ("", "-") else None,
            "cover": float(cov) if cov else None,
            "error": False,
        })
    return rows


def model_of(run: str) -> str:
    for m in MODELS:
        if m in run:
            return m
    raise ValueError(run)


def style(ax, title, ylabel):
    ax.set_title(title, fontsize=13, fontweight="bold", loc="left")
    ax.set_ylabel(ylabel, fontsize=11)
    ax.tick_params(labelsize=10)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def annotate(ax, bars, labels):
    for bar, lab in zip(bars, labels):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            lab,
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.unicode_minus": False})
    batches = []
    for label, path in TABLES:
        rows = parse_table(path)
        llm = [r for r in rows if "greedy" not in r["run"] and not r.get("error")]
        greedy = [r for r in rows if "greedy" in r["run"]]
        batches.append({"label": label, "llm": llm, "greedy": greedy})

    # 1. Episodes with >=1 victim found: LLM vs greedy, by batch.
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = range(len(batches))
    llm_pct, g_pct, llm_lab, g_lab = [], [], [], []
    for b in batches:
        lf = sum(1 for r in b["llm"] if r["found"] > 0)
        gf = sum(1 for r in b["greedy"] if r["found"] > 0)
        llm_pct.append(100 * lf / len(b["llm"]))
        g_pct.append(100 * gf / len(b["greedy"]))
        llm_lab.append(f"{lf}/{len(b['llm'])}")
        g_lab.append(f"{gf}/{len(b['greedy'])}")
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], llm_pct, w, label="LLM agents", color=LLM_COLOR)
    b2 = ax.bar([i + w / 2 for i in x], g_pct, w, label="Greedy sweep (scripted)", color=GREEDY_COLOR)
    annotate(ax, b1, llm_lab)
    annotate(ax, b2, g_lab)
    ax.set_xticks(list(x), [b["label"] for b in batches])
    top = max(max(llm_pct), max(g_pct))
    ax.set_ylim(0, 115 if top >= 90 else top * 1.25 + 5)
    style(ax, "Episodes with ≥1 victim found: LLM agents vs scripted sweep", "% of scored episodes")
    ax.legend(frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "results-finds-by-batch.png", dpi=150)
    plt.close(fig)

    # 2. Finds by model, pooled over all batches.
    fig, ax = plt.subplots(figsize=(8, 4.4))
    all_llm = [r for b in batches for r in b["llm"]]
    pcts, labs, cols = [], [], []
    for m in MODELS:
        rs = [r for r in all_llm if model_of(r["run"]) == m]
        f = sum(1 for r in rs if r["found"] > 0)
        pcts.append(100 * f / len(rs))
        labs.append(f"{f}/{len(rs)}")
        cols.append(MODEL_COLORS[m])
    bars = ax.bar([MODEL_LABELS[m] for m in MODELS], pcts, color=cols, width=0.6)
    annotate(ax, bars, labs)
    ax.set_ylim(0, max(pcts) * 1.6 + 2)
    style(ax, "Episodes with ≥1 victim found by model (all 93 scored LLM episodes)", "% of scored episodes")
    fig.tight_layout()
    fig.savefig(OUT / "results-finds-by-model.png", dpi=150)
    plt.close(fig)

    # 3. Mean map coverage: LLM vs greedy, by batch.
    fig, ax = plt.subplots(figsize=(8, 4.4))
    llm_cov, g_cov, llm_lab, g_lab = [], [], [], []
    for b in batches:
        lc = [r["cover"] for r in b["llm"] if r["cover"] is not None]
        gc = [r["cover"] for r in b["greedy"] if r["cover"] is not None]
        llm_cov.append(sum(lc) / len(lc))
        g_cov.append(sum(gc) / len(gc))
        llm_lab.append(f"{llm_cov[-1]:.2f}%")
        g_lab.append(f"{g_cov[-1]:.2f}%")
    b1 = ax.bar([i - w / 2 for i in x], llm_cov, w, label="LLM agents (mean)", color=LLM_COLOR)
    b2 = ax.bar([i + w / 2 for i in x], g_cov, w, label="Greedy sweep (mean)", color=GREEDY_COLOR)
    annotate(ax, b1, llm_lab)
    annotate(ax, b2, g_lab)
    ax.set_xticks(list(x), [b["label"] for b in batches])
    ax.set_ylim(0, max(g_cov) * 1.3)
    style(ax, "Mean map coverage: LLM agents quit early, sweep keeps going", "% of map cells visited")
    ax.legend(frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "results-coverage.png", dpi=150)
    plt.close(fig)

    n_llm = sum(len(b["llm"]) for b in batches)
    n_f = sum(1 for b in batches for r in b["llm"] if r["found"] > 0)
    print(f"batches={len(batches)} llm_scored={n_llm} episodes_with_find={n_f}")
    print("wrote", sorted(p.name for p in OUT.glob("results-*.png")))


if __name__ == "__main__":
    main()

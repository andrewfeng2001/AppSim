#!/usr/bin/env python3
"""Extract task-level correctness for each model from AppSim Valid-Model-Results
and emit a self-contained JS data file for the GitHub Pages leaderboard heatmap.

The output (static/data/leaderboard_data.js) sets window.APPSIM_LEADERBOARD and
contains NO machine paths or repo-relative dependencies, so it is safe to deploy.

Run from anywhere; paths to the AppSim repo are configured below.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# --- Configure source locations (the private AppSim repo, NOT deployed) ---
APPSIM_SRC = Path("/root/AppSim/AppSim/src")
RESULT_DIR = Path("/root/AppSim/AppSim/scripts/results/Valid-Model-Results")
GRID_TOOL = Path("/root/AppSim/T01-interactive_agent_task_grid")
OUTPUT = Path("/root/AppSim/appsim-github-page/static/data/leaderboard_data.js")

# Paper-accurate display names + ordering (by overall accuracy, descending),
# mapped from result folder name -> paper label.
MODEL_ORDER = [
    ("0519_m3a_claude_opus_4.7", "Claude-Opus-4.7"),
    ("0522_m3a_gemini_3pro",     "Gemini-3-Pro"),
    ("0522_m3a_gpt_5.5",         "GPT-5.5"),
    ("0519_m3a_gemini_3.1pro",   "Gemini-3.1-Pro"),
    ("0525_full_test_seed16",    "Doubao-Seed-1.6"),
    ("0515_m3a_gpt_5",           "GPT-5"),
    ("0518_doubao_seed18_full",  "Doubao-Seed-1.8"),
    ("0518_full_qwen_3.6_plus",  "Qwen-3.6-Plus"),
    ("0518_doubao_seed20_full",  "Doubao-Seed-2.0"),
    ("0519_full_gpt_5_4",        "GPT-5.4"),
    ("0517_qwen_3.6_flash",      "Qwen-3.6-Flash"),
    ("0523_m3a_claude_sonnet_4.6", "Claude-Sonnet-4.6"),
    ("0523_m3a_claude_haiku_4.5",  "Claude-Haiku-4.5"),
    ("0515_m3a_claude_sonnet_4.5", "Claude-Sonnet-4.5"),
    ("0516_m3a_gemini_2.5_pro",  "Gemini-2.5-Pro"),
]

# status encoding: 1 = correct, 0 = wrong, -1 = no result row
STATUS_CODE = {"success": 1, "failure": 0, "missing": -1}


def main() -> None:
    sys.path.insert(0, str(APPSIM_SRC))
    sys.path.insert(0, str(GRID_TOOL))
    import build_interactive_grid as B  # reuse the validated parser

    app_map = B.import_tasks(APPSIM_SRC)
    catalog, spans, id_lookup, instr_lookup = B.build_task_catalog(app_map)

    tasks = [
        {
            "app": m.app_label,
            "i": m.local_index,
            "ins": m.instruction,
            "steps": m.human_steps,
            "reason": bool(m.is_reasoning) if m.is_reasoning is not None else False,
        }
        for m in catalog
    ]

    app_spans = [
        {"label": s["label"], "start": int(s["start"]), "end": int(s["end"]), "count": int(s["count"])}
        for s in spans
    ]

    folder_to_dir = {d.name: d for d in B.discover_agent_dirs(RESULT_DIR, None)}

    models = []
    for folder, label in MODEL_ORDER:
        if folder not in folder_to_dir:
            raise SystemExit(f"Missing result folder: {folder}")
        run = B.load_agent_run(folder_to_dir[folder], catalog, id_lookup, instr_lookup)
        statuses = [STATUS_CODE[r.status] for r in run.results]
        models.append({
            "name": label,
            "correct": run.success_count,
            "wrong": run.failure_count,
            "missing": run.missing_count,
            "acc": round(run.success_count / len(catalog) * 1000) / 10,
            "s": statuses,
        })

    payload = {
        "totalTasks": len(catalog),
        "tasks": tasks,
        "appSpans": app_spans,
        "models": models,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text("window.APPSIM_LEADERBOARD = " + data_json + ";\n", encoding="utf-8")

    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size/1024:.0f} KB)")
    print(f"{len(catalog)} tasks, {len(models)} models")
    for m in models:
        print(f"  {m['acc']:5.1f}%  {m['correct']:3d}/{m['wrong']:3d}/{m['missing']:3d}  {m['name']}")


if __name__ == "__main__":
    main()

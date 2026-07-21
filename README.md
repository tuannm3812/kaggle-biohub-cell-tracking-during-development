# Biohub – Cell Tracking During Development

Personal entry for the Kaggle competition
[Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development):
tracking cells in 3D through time in zebrafish embryo microscopy videos,
scored on sparse ground-truth edge/division matching. Full task, data, and
metric details: [`docs/1_instructions.md`](docs/1_instructions.md).

## Current best result

No leaderboard score yet. `notebooks/02_baseline_modeling.ipynb`
(`RUN_MODE = "submission"`, `USE_PRETRAINED = True`, pretrained
`unet_transformer` checkpoint) ran successfully on Kaggle GPU 2026-07-21
and produced a schema-valid `submission.csv` (304,792 rows, all 4 test
videos) — not yet uploaded to the competition (a separate, deliberate
action; see the notebook's "Submitting to Kaggle" section). See
[`docs/3_strategy.md`](docs/3_strategy.md) for the prioritized next-experiment
roadmap, synthesized from public reference notebooks scoring LB 0.73–0.897.

## Layout

- `notebooks/` — the executable workflow (`01_eda.ipynb`,
  `02_baseline_modeling.ipynb`), plus `notebooks/kernels/<name>/` holding
  each notebook's Kaggle `kernel-metadata.json`.
- `docs/` — standards (`0`), competition instructions (`1`), EDA findings
  (`2`), and the competitive-landscape strategy/roadmap (`3`).
- `src/tracking_cellmot/` — vendored, tested I/O + metrics + model library
  (see [`NOTICE.md`](NOTICE.md) for attribution).
- `scripts/` — vendored baseline train/predict/evaluate/conversion CLIs
  driven from the notebooks, plus `push_kaggle_kernel.sh <eda|baseline>`.
- `dataset-metadata.json` (root) — on standby for publishing `src/`/
  `scripts/` as a private Kaggle Dataset once we train a customized model;
  not needed for the current predict-with-pretrained-weights path, which
  mounts the public `cellmot-baseline-artifacts` dataset instead (dataset
  is ~87.6 GB, so it's never downloaded locally — see
  `docs/0_coding_standards.md`'s "Pushing Notebooks To Kaggle" section).

## Setup

```bash
uv sync --extra dev --extra notebook --extra kaggle
uv run pytest -m "not slow"   # fast tests, no dataset needed
```

See [`docs/0_coding_standards.md`](docs/0_coding_standards.md) for
project-specific conventions and deliberate deviations from the personal
master standard.

# Biohub – Cell Tracking During Development

Personal entry for the Kaggle competition
[Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development):
tracking cells in 3D through time in zebrafish embryo microscopy videos,
scored on sparse ground-truth edge/division matching. Full task, data, and
metric details: [`docs/1_instructions.md`](docs/1_instructions.md).

## Current best result

No scored submission yet.

## Layout

- `notebooks/` — the executable workflow (`1_eda.ipynb`, `2_baseline_modeling.ipynb`).
- `docs/` — standards, competition instructions, EDA/modeling notes as they land.
- `src/tracking_cellmot/` — vendored, tested I/O + metrics + model library
  (see [`NOTICE.md`](NOTICE.md) for attribution).
- `scripts/` — vendored baseline train/predict/evaluate/conversion CLIs,
  driven from the notebooks.
- `kaggle/` — push-to-Kaggle-Kernels workflow (dataset is ~87.6 GB, not
  stored locally — see [`kaggle/README.md`](kaggle/README.md)).

## Setup

```bash
uv sync --extra dev --extra notebook --extra kaggle
uv run pytest -m "not slow"   # fast tests, no dataset needed
```

See [`docs/0_coding_standards.md`](docs/0_coding_standards.md) for
project-specific conventions and deliberate deviations from the personal
master standard.

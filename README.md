# Biohub – Cell Tracking During Development

<p align="center">
  <img src="assets/demo.gif" alt="3D cell tracking demo" width="420">
</p>

<p align="center">
  <a href="https://www.kaggle.com/competitions/biohub-cell-tracking-during-development"><img alt="Kaggle Competition" src="https://img.shields.io/badge/Kaggle-Biohub%20Cell%20Tracking-20BEFF?logo=kaggle&logoColor=white"></a>
  <a href="docs/3_strategy.md"><img alt="Public LB Score" src="https://img.shields.io/badge/Public%20LB-0.817-success"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-BSD--3--Clause-lightgrey"></a>
</p>

Personal entry for the Kaggle competition
[Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development):
detecting and linking cells in 3D through time in zebrafish embryo
microscopy videos, scored on sparse ground-truth edge and division
matching. Full task, data format, and metric details:
[`docs/1_instructions.md`](docs/1_instructions.md).

## Approach

A learned detect → link pipeline: the competition's official baseline
architecture (`TemporalUNet3D` center detector + cross-attention node
transformer + ILP graph optimizer — see [`NOTICE.md`](NOTICE.md) for
attribution), plus a deterministic graph-repair stage (short-track
pruning, bounded gap recovery via interpolated intermediate nodes) —
every top-scoring public solution reviewed converges on that shape. A
first version of the repair stage regressed the score (edge Jaccard
-0.0133) due to a structural bug; fixed and re-validated, it's now a
genuine +0.007 leaderboard gain
([`docs/4_experiments.md`](docs/4_experiments.md) for the full story). See
[`docs/3_strategy.md`](docs/3_strategy.md) for the competitive-landscape
analysis behind this approach.

## Current best result

**Public leaderboard: 0.817**, up from an initial 0.810 — full submission
history in [`docs/5_submissions.md`](docs/5_submissions.md), full
experiment-by-experiment numbers behind it in
[`docs/4_experiments.md`](docs/4_experiments.md). This is a genuine Code
Competition submission: the kernel runs with internet disabled and submits
via the Kaggle API's `competition_submit_code`, not a file upload (see
[`docs/1_instructions.md`](docs/1_instructions.md)). Sits close to the
learned+repair public references' ~0.897 (`docs/3_strategy.md`). See
[`docs/3_strategy.md`](docs/3_strategy.md) for the prioritized
next-experiment roadmap toward closing that remaining gap.

## Repository layout

- [`notebooks/`](notebooks/) — the executable workflow: `01_eda.ipynb`,
  `02_baseline_modeling.ipynb`, plus `notebooks/kernels/<name>/` holding
  each notebook's Kaggle `kernel-metadata.json`.
- [`docs/`](docs/) — `0` project standards, `1` competition instructions,
  `2` EDA findings, `3` strategy/roadmap, `4` experiment log,
  `5` submission log, plus the vendored `metrics.md` (official scoring
  spec).
- [`src/tracking_cellmot/`](src/tracking_cellmot/) — vendored, tested I/O +
  metrics + model library from the official baseline (107 tests).
  Not executed directly on Kaggle (kernels mount a public pretrained-model
  dataset with its own copy instead) — kept locally as a tested reference
  and for training a customized checkpoint later; see
  [`docs/0_coding_standards.md`](docs/0_coding_standards.md).
- [`scripts/`](scripts/) — vendored train/predict/evaluate/conversion CLIs
  (same status as `src/`), plus `push_kaggle_kernel.sh <eda|baseline>`, the
  one script written for this project.

## Setup

```bash
uv sync --extra dev --extra notebook --extra kaggle
uv run pytest -m "not slow"   # fast tests, no dataset needed
```

The competition dataset (~87.6 GB) is never downloaded locally — everything
that touches real data runs on Kaggle Kernels, where it's already mounted.
See [`docs/0_coding_standards.md`](docs/0_coding_standards.md) for
project-specific conventions and deliberate deviations from the personal
master standard.

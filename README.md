# Biohub – Cell Tracking During Development

<p align="center">
  <img src="assets/demo.gif" alt="3D cell tracking demo" width="420">
</p>

<p align="center">
  <a href="https://www.kaggle.com/competitions/biohub-cell-tracking-during-development"><img alt="Kaggle Competition" src="https://img.shields.io/badge/Kaggle-Biohub%20Cell%20Tracking-20BEFF?logo=kaggle&logoColor=white"></a>
  <a href="docs/5_submissions.md"><img alt="Public LB Score" src="https://img.shields.io/badge/Public%20LB-0.827-success"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="#setup"><img alt="Tests" src="https://img.shields.io/badge/tests-107%20passing-brightgreen"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-BSD--3--Clause-lightgrey"></a>
</p>

Personal entry for the Kaggle competition
[Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development):
detect and link every cell nucleus, in 3D, through 100 timepoints of
light-sheet microscopy of a developing zebrafish embryo — including cell
divisions — from **199 training videos with sparse ground truth and only
4 held-out test videos**. Scored on edge-matching (Adjusted Jaccard) plus
division-matching against the official metric. Full task, data format,
and scoring details: [`docs/1_instructions.md`](docs/1_instructions.md).

## Results at a glance

| | |
|---|---|
| **Public leaderboard** | **0.827**, up from an initial 0.810 |
| **Approach** | Learned detect → link (3D U-Net + transformer + ILP) → deterministic graph repair |
| **Full history** | [`docs/5_submissions.md`](docs/5_submissions.md) (submissions) · [`docs/4_experiments.md`](docs/4_experiments.md) (local validation) |

Four things this project surfaced that a naive run wouldn't have caught:

- **Trajectory smoothing, verified before ever touching Kaggle.** Detected
  centroids carry per-frame noise independent of any linking mistake, and
  the metric only matches within a 7 µm centroid distance — so a locally
  line-fit smoothing pass that never touches topology moved the needle
  directly. Checked against synthetic data first (including a synthetic
  cell-division fork, to confirm no cross-branch contamination), then
  A/B-tested on Kaggle with a single predict pass: **+0.0123 edge Jaccard**
  locally, confirmed by a real **+0.010** leaderboard gain once submitted
  ([`docs/4_experiments.md`](docs/4_experiments.md)).
- **A graph-repair bug that looked like a regression.** The first
  gap-closing implementation *dropped* the local score (edge Jaccard
  -0.0133) because it bridged dangling tracks with edges spanning
  multiple frames — something no ground-truth edge can ever match.
  Root-caused, fixed by inserting interpolated intermediate nodes
  instead, and re-validated: a genuine **+0.007** real leaderboard gain
  once both techniques worked correctly
  ([`docs/4_experiments.md`](docs/4_experiments.md)).
- **A local-validation "win" that didn't survive contact with the real
  test set — and why.** A `DET_THRESHOLD` sweep predicted a further
  +0.0025 gain on a 19-video held-out sample; the real submission scored
  **0.795**, a -0.022 regression. Re-validating at 3x the sample size
  (60 videos) **reversed the ranking**, confirming the original signal
  was small-sample noise (a multiple-comparisons risk), not a real
  train/test distribution effect — the confirmed default (0.99) was
  right all along. See [`docs/4_experiments.md`](docs/4_experiments.md)
  for the full numbers.
- **A ~115x over-prediction hiding behind a "genuinely rare" signal.**
  `division_jaccard` scored exactly 0 in every experiment, initially
  read as the ground truth's divisions simply being too rare to recover.
  Direct inspection of the raw predictions found the model actually
  predicts **690 candidate cell divisions** across a 60-video sample —
  against an estimated ~6 real ones — with **zero** ever landing
  correctly. Not under-detection; over-prediction with no signal in it.
  See [`docs/4_experiments.md`](docs/4_experiments.md) for the analysis
  and the follow-up `ILP_DIVISION_WEIGHT` sweep it motivated.

## Approach

```
raw video (T, Z, Y, X)
      │
      ▼
 3D U-Net center detector  ──►  candidate cell centers per frame
      │
      ▼
 cross-attention node transformer  ──►  pairwise edge scores
      │
      ▼
 ILP graph optimizer  ──►  globally consistent detect+link graph
      │
      ▼
 deterministic graph repair  ──►  short-track pruning + bounded gap
      │                            closing (interpolated intermediate
      │                            nodes, not multi-frame edges) +
      │                            trajectory smoothing (local line-fit)
      ▼
 submission.csv
```

The detector/transformer/ILP stack is the competition's official baseline
architecture (`TemporalUNet3D` + node transformer + ILP — see
[`NOTICE.md`](NOTICE.md) for attribution); the graph-repair stage on top
is this project's own contribution. Every top-scoring public solution
reviewed — learned or purely classical — converges on this same
detect → link → repair shape, which is the central finding behind the
whole strategy; see [`docs/3_strategy.md`](docs/3_strategy.md) for the
competitive-landscape analysis.

## Documentation

Findings, decisions, and history live in `docs/`, not scattered across
notebook comments — notebooks stay focused on the experiment itself.

| Doc | Contents |
|---|---|
| [`0_coding_standards.md`](docs/0_coding_standards.md) | Project conventions and deviations from the personal master standard |
| [`1_instructions.md`](docs/1_instructions.md) | Competition spec, data format, submission method |
| [`2_eda_insights.md`](docs/2_eda_insights.md) | Dataset scale, sparsity, count-calibration, and division-rarity findings, with embedded charts |
| [`3_strategy.md`](docs/3_strategy.md) | Competitive-landscape analysis and the prioritized, living roadmap |
| [`4_experiments.md`](docs/4_experiments.md) | Every local validation run, whether or not it became a submission |
| [`5_submissions.md`](docs/5_submissions.md) | Every real Kaggle submission — the ground-truth leaderboard record |
| [`6_kaggle_troubleshooting.md`](docs/6_kaggle_troubleshooting.md) | Reusable diagnosis for Kaggle CLI/API friction (auth, kernel push, offline installs, submission mechanics) |
| [`metrics.md`](docs/metrics.md) | Vendored official scoring spec (Adjusted Edge Jaccard + Division Jaccard) |

## Repository layout

- [`notebooks/`](notebooks/) — the executable workflow: `01_eda.ipynb`,
  `02_baseline_modeling.ipynb`, plus `notebooks/kernels/<name>/` holding
  each notebook's Kaggle `kernel-metadata.json`.
- [`docs/`](docs/) — see the table above.
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

## Attribution

The detection/linking architecture and core I/O/metrics library are
vendored from the official competition baseline
([royerlab/kaggle-cell-tracking-competition](https://github.com/royerlab/kaggle-cell-tracking-competition),
BSD 3-Clause) — see [`NOTICE.md`](NOTICE.md) for the full attribution and
[`docs/0_coding_standards.md`](docs/0_coding_standards.md) for what was
built on top and why.

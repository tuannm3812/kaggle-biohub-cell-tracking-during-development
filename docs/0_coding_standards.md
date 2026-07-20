# Project Coding Standards

Follows the owner's master coding standards (a personal cross-repo reference,
not vendored into this repo since it isn't project-specific). This doc only
records **project-specific decisions and deviations**.

## Baseline provenance

`src/`, `scripts/`, `tests/`, `visualize/`, `assets/`, and `metrics.md` are
vendored from the official competition baseline,
[royerlab/kaggle-cell-tracking-competition](https://github.com/royerlab/kaggle-cell-tracking-competition)
(BSD-3-Clause — see `NOTICE.md`). It already implements the competition's
data I/O (OME-Zarr + GEFF via `tracksdata`), the exact scoring metric, and a
trained-from-scratch 3D U-Net + transformer baseline with 100+ passing unit
tests, so it's kept largely as-is rather than rewritten.

## Deviations from the master standard, and why

1. **`scripts/train_unet_transformer.py` (1294 lines) and
   `predict_unet_transformer.py` (677 lines) exceed "small CLI helpers only."**
   They hold real model/training logic, which the master standard says
   belongs in `src/`. Left as vendored, tested, unmodified upstream code for
   now rather than force-split during initial setup — that risks
   introducing bugs in logic we haven't verified against real data yet, for
   no behavior change. `notebooks/2_baseline_modeling.ipynb` drives them as
   the executable entry point (satisfying "notebook is the executable
   source of truth" for anything *we* add on top). **Revisit**: once we
   start actually modifying the modeling logic (new architecture, loss,
   etc.), migrate the touched pieces into `src/tracking_cellmot/` proper
   and keep `scripts/` thin, per the master standard.

2. **Submission is file-upload only (§11 exception).** This competition
   does not support Kaggle's notebook-rerun submission — the organizers'
   own baseline README states "Kaggle accepts a CSV upload only." The
   round trip is: predict → `.geff` → `scripts/geffs_to_csv.py` →
   `submission.csv` uploaded on the competition's Submit page. See
   `docs/1_instructions.md`.

3. **No local `data/` — and no local execution of the full pipeline
   either.** The dataset is ~87.6 GB. Per the master standard's own
   guidance ("keep competition data outside git... read it from the
   platform's mounted input path"), we go further here: development and
   unit tests happen locally against small/synthetic fixtures, and actual
   training/inference runs on **Kaggle Kernels**, where the dataset is
   already mounted. See `kaggle/README.md` for the push/pull loop.
   `scripts/dataspec.py` auto-detects the Kaggle mount vs. an optional
   local `$CELLMOT_DATA_DIR` override, so no path is ever hardcoded.

## Everything else

Standard rules apply unchanged: PEP 8 / type hints / Google-style
docstrings for new code we write, Conventional Commits, notebook config
blocks + mode flags + outputs-cleared-until-trusted, Viridis for plots,
never commit data/weights/credentials (see `.gitignore` / `.kaggleignore`).

Ruff (config in `pyproject.toml`) enforces line length, import order, and
docstring conventions for everything under `src/` — including the vendored
code, which already passes it except for `visualize/` (not linted upstream
either; low priority, optional viz tooling).

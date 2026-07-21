# Coding Standards

## Baseline

This project follows the shared `coding-standards/coding_standards.md` at
the GitHub root (`/Users/tuannm3812/Documents/GitHub/coding-standards`) as
its baseline. That file is the fallback for anything not overridden below —
commit message convention, pre-commit/pre-push workflow, documentation
style, and Kaggle submission preference all live there. Everything in this
doc is either a project-specific addition or an explicit override of the
shared baseline; keep it that way rather than re-copying sections that
already match the shared file, so the two don't drift silently.

## Baseline Provenance (project-specific)

`src/`, `scripts/`, `tests/`, `visualize/`, `assets/`, and `metrics.md` are
vendored from the official competition baseline,
[royerlab/kaggle-cell-tracking-competition](https://github.com/royerlab/kaggle-cell-tracking-competition)
(BSD-3-Clause — see `NOTICE.md`). It already implements the competition's
data I/O (OME-Zarr + GEFF via `tracksdata`), the exact scoring metric, and a
trained-from-scratch 3D U-Net + transformer baseline with 100+ passing unit
tests, so it's kept largely as-is rather than rewritten.

## Repository Scope

Notebook-first Kaggle workflow, same shape as the sibling episode repos
(e.g. `kaggle-s6e7-predicting-student-health-risk`), with one addition this
project genuinely needs and the tabular episode repos don't: a private
Kaggle Dataset carrying the vendored `src/`/`scripts/` package into the
Kaggle kernel.

- `notebooks/` — `01_eda.ipynb`, `02_baseline_modeling.ipynb`, plus
  `notebooks/kernels/<name>/` holding each notebook's Kaggle
  `kernel-metadata.json` (see "Pushing Notebooks To Kaggle" below).
- `docs/` — durable findings and decisions.
- `assets/` — vendored baseline demo assets (not README images here, unlike
  the tabular repos — no header banner yet).
- `src/tracking_cellmot/` — vendored, tested I/O + metrics + model library.
  Reused across `scripts/` and both notebooks, and covered by `tests/`, so
  it earns the shared baseline's `src/` carve-out on its own merits, not
  just because it was vendored that way.
- `scripts/` — vendored baseline train/predict/evaluate/conversion CLIs,
  plus `push_kaggle_kernel.sh <eda|baseline>` (the only script we wrote
  ourselves; see the deviation below for why the vendored ones are here
  and not in `src/`).
- `dataset-metadata.json` (root) + `.kaggleignore` — publish `src/`/
  `scripts/`/`tests/` as the private Kaggle Dataset
  `tuannm3812/tracking-cellmot-src`, which both kernels mount.

No local `data/`, `predictions/`, or `scratch/` yet, unlike the tabular
episode repos — the dataset is ~87.6 GB (vs. their few-MB CSVs), so there's
nothing to usefully keep in a local `data/` folder; see "Data & Compute"
below. Add `predictions/`/`scratch/` (gitignored, already reserved in
`.gitignore`) if/when local OOF review or throwaway automation scripts
become useful.

## Deviations From The Master Standard, And Why

1. **`scripts/train_unet_transformer.py` (1294 lines) and
   `predict_unet_transformer.py` (677 lines) exceed "small CLI helpers
   only."** They hold real model/training logic, which both the shared
   baseline and the tabular episode repos' convention say belongs in
   `src/`. Left as vendored, tested, unmodified-upstream code for now
   rather than force-split during initial setup — that risks introducing
   bugs in logic not yet verified against real data, for no behavior
   change. `notebooks/02_baseline_modeling.ipynb` drives them as the
   executable entry point (satisfying "notebook is the executable source
   of truth" for anything *we* add on top). **Revisit**: once we start
   actually modifying the modeling logic (new architecture, loss, etc.),
   migrate the touched pieces into `src/tracking_cellmot/` proper and keep
   `scripts/` thin, matching the convention everywhere else.

2. **Submission is file-upload only.** Unlike the Playground episode repos
   (which prefer Kaggle's notebook-rerun "Submit to Competition"), this
   competition does not support that — the organizers' own baseline README
   states "Kaggle accepts a CSV upload only." Round trip: predict → `.geff`
   → `scripts/geffs_to_csv.py` → `submission.csv` uploaded on the Submit
   page. See `docs/1_instructions.md`. This is the documented exception the
   shared standard's §11 calls for.

3. **`uv` + `pyproject.toml` instead of `requirements.txt` + pip.** The
   tabular episode repos use plain `requirements.txt`; this project
   deliberately kept the vendored baseline's existing `uv`/`pyproject.toml`
   tooling instead of converting it, since the baseline (and its
   `tracksdata` git dependency, lockfile, ruff config) already worked that
   way. Run everything via `uv run ...` rather than activating a venv or
   using a bare `pip install -r requirements.txt` by hand.

4. **No local `data/` — and no local execution of the full pipeline
   either.** The dataset is ~87.6 GB, categorically different from the
   tabular episode repos' small CSVs that fit fine in a local `data/`
   folder. Development and unit tests happen locally against small/
   synthetic fixtures; actual training/inference runs on Kaggle Kernels,
   where the dataset is already mounted. See "Data & Compute" below.

## Document Naming

Reserve a new number for a promoted, project-owned finding or decision —
not every parameter tweak. Current docs:

- `0_coding_standards.md` — this file.
- `1_instructions.md` — competition task, data format, metric, submission
  method, deadline.

Reserve `2_eda_insights.md` for after `01_eda.ipynb` has an actual trusted
run to report on; don't create it pre-emptively with placeholder content.

Notebook naming: `01_eda.ipynb`, `02_baseline_modeling.ipynb`, matching the
sibling episode repos' zero-padded convention. Prefer a new config flag
inside `02_baseline_modeling.ipynb` for a new experiment (architecture
variant, loss change, post-processing tweak) over a new notebook file —
only split out a `03_*.ipynb` if `02` becomes too large/slow to run as a
single kernel.

## Python Style

- Follow PEP 8: 4-space indentation, group imports stdlib → third-party →
  local with a blank line between groups.
- Type hints and Google-style docstrings for anything reused across
  notebook cells (i.e. new code we write in `src/` or `scripts/`) — not
  retrofitted onto the vendored baseline's existing NumPy-style docstrings,
  to avoid churning unmodified upstream code for a style-only diff.

## Notebook Style

Each notebook should include:

- Purpose statement.
- Configuration cell near the top, with an `IS_KAGGLE` check that resolves
  paths for both Kaggle execution (mounted competition data +
  `tracking-cellmot-src` code dataset) and local development, plus explicit
  mode flags where behavior differs by run (`RUN_MODE = "train" |
  "submission"` in `02_baseline_modeling.ipynb`).
- Deterministic seed.
- Markdown insight cells after every important plot or metric.
- Numbered sections with clear reader-facing headers.
- A final "Findings / limitations / next experiment" section.

**Outputs policy:** clear outputs before committing if the notebook code
changed and hasn't been rerun on Kaggle yet — don't commit stale results.
**Offline-safety:** doesn't apply the same way here as to a submitted
notebook (see submission-method deviation above) — but kernels should still
declare every dependency explicitly in their own setup cell (see the
`IS_KAGGLE` pip-install block) rather than relying on whatever happens to
be preinstalled in Kaggle's base image.

## Plot Style

Use `viridis` as the default colormap, matching the shared baseline and the
sibling episode repos.

## Data & Compute

- The competition dataset is ~87.6 GB — never download it wholesale into a
  local or ephemeral dev environment. `scripts/dataspec.py` resolves the
  dataset path with this priority: `$CELLMOT_DATA_DIR` env override →
  Kaggle `train/` mount (auto-detected) → local `./data/train`. Don't
  hardcode paths elsewhere; import `DATASET_PATH` from it (see both
  notebooks' config cells).
- Kaggle CLI auth: `~/.kaggle/kaggle.json` locally (already set up), picked
  up automatically by `uv run kaggle ...` — never paste its contents
  anywhere. `.gitignore`/`.kaggleignore` both exclude it explicitly as a
  second layer of defense.

## Git Hygiene

Do not commit raw Kaggle data, model weights/checkpoints, prediction
arrays, local credentials, notebook checkpoints, or the staged notebook
copies under `notebooks/kernels/*/*.ipynb` (regenerated by
`push_kaggle_kernel.sh`, gitignored — see `.gitignore`).

## Kaggle Submission Method

See the deviation above — file-upload only, not notebook-rerun, per this
competition's organizers. Refer to `docs/1_instructions.md` for the exact
round trip and to the shared `coding-standards/coding_standards.md` (§11)
for the general rule this project deliberately doesn't follow, and why.

## Pushing Notebooks To Kaggle

Each notebook's Kaggle kernel has its own `kernel-metadata.json` under
`notebooks/kernels/<name>/`. `notebooks/01_eda.ipynb` and
`notebooks/02_baseline_modeling.ipynb` are the single source of truth; the
`.ipynb` copies inside `notebooks/kernels/*/` are gitignored and
regenerated on every push, not maintained by hand.

Push with `scripts/push_kaggle_kernel.sh <eda|baseline>` rather than
running `kaggle kernels push` directly against a hand-copied file — it
copies the current notebook into the right kernel folder first, so the two
never drift.

**Project-specific extra step, not needed in the tabular episode repos:**
both kernels declare `dataset_sources` in their `kernel-metadata.json` —
our own `tuannm3812/tracking-cellmot-src` (the vendored `src/`/`scripts/`
package isn't on PyPI) on both, plus the public
`thibautgoldsborough/cellmot-baseline-artifacts` (pretrained weights) on
`baseline_modeling` only. Publish/refresh our own dataset from the repo
root *before* pushing a kernel that depends on code changes since the last
publish:

```bash
uv run kaggle datasets create -p .              # first time
uv run kaggle datasets version -p . -m "..."    # after any code change
```

`dataset-metadata.json` (root) owns this; `.kaggleignore` (root) keeps
`.git`, `.venv`, local data/weights/predictions, etc. out of the upload.
Kernels are `is_private: true` here (unlike the tabular episode repos'
public kernels) since this is a live, prize-money competition.

## Kaggle Access Troubleshooting

Reusable diagnosis for CLI/API friction, carried over from the sibling
episode repos where useful.

**Kaggle competition pages are not fetchable by URL.** Confirmed
2026-07-21 for this competition specifically: `WebFetch` and direct `curl`
both return `403 Forbidden` for `kaggle.com/competitions/...` and several
related pages (image.sc forum, febs.org). The Kaggle CLI/API has no
endpoint for competition overview/rules prose either — `kaggle competitions
list`/`files` only return structured metadata (deadline, team count,
reward). Competition detail in `docs/1_instructions.md` was gathered via
`WebSearch` (which does surface third-party summaries/announcements) and
the Kaggle CLI's structured output, not by fetching the competition page
directly. If exact official wording is ever needed, ask the user to paste
it rather than attempting another fetch.

**Small competition files (`sample_submission.csv`, etc.) *are* downloadable
without pulling the full dataset.** `kaggle competitions download -c <slug>
-f <filename> -p <dir>` fetches a single file. Used this to verify the real
submission CSV schema (`docs/1_instructions.md`) without touching the
87.6 GB bulk data.

**`kaggle kernels pull <owner>/<slug> -p <dir> -m` downloads a public
kernel's source + `kernel-metadata.json` without running it.** Used this to
find the baseline author's pretrained-weights dataset: their public
inference notebook's `kernel-metadata.json` listed
`thibautgoldsborough/cellmot-baseline-artifacts` under `dataset_sources`,
which isn't visible any other way (not linked from the competition's
Overview, which isn't fetchable anyway — see above). Worth doing for any
competition with public reference notebooks before assuming you need to
train from scratch.

**`predict_unet_transformer.py` requires a `dataset_splits.json` in
`--data-dir` (or an explicit `--splits`) — it does not auto-generate one
like `train_unet_transformer.py` does.** The real `test/` directory ships
no such file (fold-splitting is a train-only concept). Both
`02_baseline_modeling.ipynb`'s submission and train-fold-validation cells
build a synthetic one-fold splits file listing every video in the target
directory before calling predict, matching the approach in the baseline
author's own public inference notebook.

**Kaggle Dataset mount paths differ for own-account vs. other-account
datasets.** The baseline author's own inference notebook mounts a
dataset *they* own at the simple `/kaggle/input/<slug>` path, but
mounts a *different* dataset owned by someone else at a longer
`/kaggle/input/datasets/<owner>/<slug>/<slug>` path (observed directly in
their notebook source via `kaggle kernels pull`, not documented anywhere).
Both notebooks' `_find_mount()` helper checks both path shapes and falls
back to scanning `/kaggle/input/**` for a marker file/dir, rather than
hardcoding one assumed path.

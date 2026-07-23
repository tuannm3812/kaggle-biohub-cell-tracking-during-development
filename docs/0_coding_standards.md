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

`src/`, `scripts/`, `tests/`, `assets/`, and `docs/metrics.md` are
vendored from the official competition baseline,
[royerlab/kaggle-cell-tracking-competition](https://github.com/royerlab/kaggle-cell-tracking-competition)
(BSD-3-Clause — see `NOTICE.md`). It already implements the competition's
data I/O (OME-Zarr + GEFF via `tracksdata`), the exact scoring metric, and a
trained-from-scratch 3D U-Net + transformer baseline with 100+ passing unit
tests, so it's kept largely as-is rather than rewritten. The vendored
`visualize/` (napari GUI viewer) was dropped 2026-07-21 — never used in this
Kaggle-only workflow; recover it from
[royerlab/kaggle-cell-tracking-competition](https://github.com/royerlab/kaggle-cell-tracking-competition)
if local interactive inspection is ever needed.

## Repository Scope

Notebook-first Kaggle workflow, same shape as the sibling episode repos
(e.g. `kaggle-s6e7-predicting-student-health-risk`).

- `notebooks/` — `01_eda.ipynb`, `02_baseline_modeling.ipynb`, plus
  `notebooks/kernels/<name>/` holding each notebook's Kaggle
  `kernel-metadata.json` (see "Pushing Notebooks To Kaggle" below).
- `docs/` — durable findings and decisions.
- `assets/` — vendored baseline demo assets, including the README's header
  animation.
- `src/tracking_cellmot/` — vendored, tested I/O + metrics + model library.
  Reused across `scripts/` and both notebooks, and covered by `tests/`, so
  it earns the shared baseline's `src/` carve-out on its own merits, not
  just because it was vendored that way. Not executed directly on Kaggle
  (kernels mount `thibautgoldsborough/cellmot-baseline-artifacts` instead —
  see "Pushing Notebooks To Kaggle" below); kept locally as a tested
  reference and for training a customized checkpoint later
  (`RUN_MODE = "train"`, `USE_PRETRAINED = False`), at which point we'd
  need our own code back on Kaggle (recreate `dataset-metadata.json` +
  `.kaggleignore` — dropped 2026-07-21 since unused until then, see below).
- `scripts/` — vendored baseline train/predict/evaluate/conversion CLIs,
  plus `push_kaggle_kernel.sh <eda|baseline>` (the only script we wrote
  ourselves; see the deviation below for why the vendored ones are here
  and not in `src/`).

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

2. **Submission is Code-Competition notebook rerun, not file upload —
   confirmed the hard way.** The organizers' own baseline README claims
   "Kaggle accepts a CSV upload only," so that's what this project assumed
   at first. A real `kaggle competitions submit -f submission.csv`
   (2026-07-21) was rejected with `400 Bad Request` / "This competition
   only accepts Submissions from Notebooks" — so the README is wrong on
   this point. This actually **matches**, rather than deviates from, the
   shared standard's §11 preference for notebook-based submission. See
   `docs/1_instructions.md` for the confirmed round trip — scriptable via
   `KaggleApi.competition_submit_code(...)`, not a manual web-UI action as
   first assumed (see `docs/6_kaggle_troubleshooting.md`).

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

Reserve a new number for a promoted, project-owned finding, decision, or
durable tracking artifact — not every parameter tweak. Current docs:

- `0_coding_standards.md` — this file.
- `1_instructions.md` — competition task, data format, metric, submission
  method, deadline.
- `2_eda_insights.md` — real findings from `01_eda.ipynb`'s first trusted
  Kaggle run (dataset scale, sparsity, open questions).
- `3_strategy.md` — competitive-landscape synthesis from public reference
  notebooks, the prioritized next-experiment roadmap, and short pointers to
  the detailed logs below — decisions and reasoning live here, not raw
  numbers. Update this, not a new doc, as the roadmap steps land.
- `4_experiments.md` — every local `VALIDATE_ON_TRAIN_FOLD` run, submitted
  or not, with config/score/conclusion. Originally logged inline in
  `3_strategy.md`; split out once that doc's "Validated finding" section
  grew to dwarf the actual strategy content — append a row per experiment
  here instead of growing `3_strategy.md` further.
- `5_submissions.md` — every real Kaggle submission (the subset of
  experiments above that got scored on the actual leaderboard) — the
  ground-truth progress record. Append a row per submission.
- `6_kaggle_troubleshooting.md` — reusable diagnosis for Kaggle CLI/API
  friction (auth, kernel push quirks, offline-install pitfalls, submission
  mechanics). Split out of this file once it grew past "coding standards"
  into its own incident log — append an entry per new issue hit.
- `metrics.md` — vendored official scoring spec (see `NOTICE.md`).

`4_experiments.md`, `5_submissions.md`, and `6_kaggle_troubleshooting.md`
are append-only logs, not narrative docs — keep entries terse (one table
row + a short conclusion, or one bolded-claim paragraph per incident), and
put reasoning/what-to-try-next in `3_strategy.md` instead.

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

- Purpose statement — a short paragraph, not a page. What the notebook
  does, not how it's deployed (see the markdown boundary below).
- Configuration cell near the top, with an `IS_KAGGLE` check that resolves
  paths for both Kaggle execution (mounted competition data + the
  `cellmot-baseline-artifacts` code/weights dataset) and local development,
  plus explicit mode flags where behavior differs by run (`RUN_MODE =
  "train" | "submission"` in `02_baseline_modeling.ipynb`).
- Deterministic seed.
- Markdown insight cells after every important plot or metric.
- Numbered sections with clear reader-facing headers.

**Outputs policy:** clear outputs before committing if the notebook code
changed and hasn't been rerun on Kaggle yet — don't commit stale results.
**Offline-safety:** doesn't apply the same way here as to a submitted
notebook (see submission-method deviation above) — but kernels should still
declare every dependency explicitly in their own setup cell (see the
`IS_KAGGLE` pip-install block) rather than relying on whatever happens to
be preinstalled in Kaggle's base image.

### What belongs in notebook markdown, and what belongs in `docs/`

Notebooks are published/run on Kaggle and read by whoever looks at the
kernel page — they should read like a focused write-up of *this
experiment*: what the code does, why (briefly), and what it found. They
are not the place for project history, process, or deployment mechanics.
`docs/` is the single source of truth for all of that; notebooks link out
to it rather than duplicating it.

**Decision rule**: would this sentence still be true, unedited, if the
exact same code were rerun tomorrow? If yes — it's an approach or a
finding, keep it in the notebook. If no — it's a fact about *this specific
run* (a date, a kernel version, "resolved", "currently re-running",
compute-budget arithmetic, deployment status) — it belongs in
`docs/4_experiments.md` or `docs/5_submissions.md` instead, not the
notebook.

Keep in notebook markdown:
- What each section's code does and why, at the level of technique/method
  (e.g. "bounded gap closing via a physical-space Hungarian assignment") —
  this is the approach, not process.
- A short **Insight** cell after a result: the direct finding from that
  cell's output (direction, magnitude, what it implies) — factual and
  timeless, not "resolved on `<date>`" or "confirmed on kernel `v20`".
- Config values with a one-line comment on *why* that value, pointing to
  `docs/` for the backing analysis rather than repeating its numbers.

Move to `docs/` instead:
- Roadmap, priorities, "what to try next" → `3_strategy.md`.
- Full experiment tables, multiple-run comparisons, sample-size/runtime
  reasoning → `4_experiments.md`.
- Submission history, kernel versions, dates, deployment/"is this
  submitted" status → `5_submissions.md`.
- How to run/push the notebook on Kaggle (which script, which dataset
  mounts) → this file, "Pushing Notebooks To Kaggle" below.
- Competition mechanics (Code Competition rules, submission method) →
  `1_instructions.md`.
- Why our own code is organized a certain way (e.g. `scripts/` vs `src/`)
  → this file, "Deviations From The Master Standard" above.

This was a real cleanup, not just a hypothetical: `02_baseline_modeling.ipynb`
and `01_eda.ipynb` both originally had a closing "Findings / limitations /
next experiment" section and inline notes like "kernel `tuannm3812/biohub-eda`
v8, 2026-07-22" — all of it already duplicated in `docs/`, so it was removed
from the notebooks entirely rather than kept as a second copy that could
drift out of sync.

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
  anywhere. `.gitignore` excludes it explicitly as a second layer of
  defense.

## Git Hygiene

Do not commit raw Kaggle data, model weights/checkpoints, prediction
arrays, local credentials, notebook checkpoints, or the staged notebook
copies under `notebooks/kernels/*/*.ipynb` (regenerated by
`push_kaggle_kernel.sh`, gitignored — see `.gitignore`).

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
both kernels declare `dataset_sources: ["thibautgoldsborough/cellmot-baseline-artifacts"]`
in their `kernel-metadata.json`, since the vendored `src/`/`scripts/`
package isn't on PyPI. That public dataset bundles a full working `repo/`
(source, not just weights) — `02_baseline_modeling.ipynb` copies it to a
writable `/kaggle/working/repo`; `01_eda.ipynb` reads it directly (never
writes predictions/weights, so the read-only mount is fine). Nothing to
publish or version ourselves for this.

This only holds while we're predicting with the public pretrained
checkpoint (`USE_PRETRAINED = True`) rather than our own logic. Once we
train a customized model, our own code needs to reach Kaggle too — publish
it as a private dataset from the repo root and add
`"tuannm3812/tracking-cellmot-src"` back to `dataset_sources`:

```bash
uv run kaggle datasets init -p .                # first time -- recreates dataset-metadata.json
uv run kaggle datasets create -p .              # first time
uv run kaggle datasets version -p . -m "..."    # after any code change
```

`dataset-metadata.json` and `.kaggleignore` (which excludes `.git`, `.venv`,
local data/weights/predictions, etc. from the upload) were dropped
2026-07-21 as unused dead weight — recreate them at that point rather than
keeping them on standby indefinitely. Kernels are `is_private: true` here
(unlike the tabular episode repos' public kernels) since this is a live,
prize-money competition.

Reusable diagnosis for CLI/API friction encountered along the way:
`docs/6_kaggle_troubleshooting.md`.

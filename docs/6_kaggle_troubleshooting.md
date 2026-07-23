# Kaggle Access Troubleshooting

Reusable diagnosis for Kaggle CLI/API friction — an append-only incident
log, not a narrative doc. Carried over from the sibling episode repos
where useful, extended with issues specific to this competition. Split out
of `docs/0_coding_standards.md`, which stayed a prescriptive standards
file; this is a log of things that went wrong and how they were fixed.

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

**`kaggle kernels push` requires a title of at least 5 characters, and a
brand-new kernel is created under the *title-derived* slug, not the `id`
field's slug, if they disagree.** `"title": "EDA"` failed outright ("Title
must be at least five characters"); with a longer title that still didn't
match the `id`'s slug, the push succeeded with a warning but created the
kernel at the title-derived URL (`biohub-eda`, not the `tracking-cellmot-eda`
originally in `id`). Fix: keep `id`'s slug and `title` in agreement from the
start, and after any first push, `kaggle kernels list -m --search <name>`
to confirm the actual created slug before assuming `id` is authoritative.

**An unpinned `pip install` inside a Kaggle kernel can silently break
numpy/scipy/torch, even without naming them.** `zarr>=3.0.10` and
`tracksdata` pulled in a numpy upgrade pip considered "needed"; the
resulting numpy was internally inconsistent with the base image's
precompiled scipy (`ImportError` deep in `scipy.spatial`/`numpy._core`,
different symptom depending on import order) and, once torch's dependency
chain got involved, produced `CUDA error: no kernel image is available for
execution on the device` (an incompatible torch build silently replacing
the base image's GPU-driver-matched one) — both confirmed by reproducing
end-to-end on this competition's Kaggle image, fixed by pinning
`numpy`/`scipy`/`torch` to `importlib.metadata.version(...)`'s
already-installed value before any other `pip install` runs (see both
notebooks' Setup cells). Generalizes: on Kaggle, prefer pinning any package
already present in the base image (numpy, scipy, torch, pandas, ...) to its
current version rather than leaving it unpinned in a `pip install` line,
even when you don't think you're touching it.

**GPU kernels need an explicit `machine_shape` in `kernel-metadata.json`,
or Kaggle may assign hardware the base image's preinstalled torch build
doesn't support.** Pinning torch's *version* alone did not fix the CUDA
error above — Kaggle's default GPU allocation without a declared shape
produced a device the pinned torch had no compiled kernels for. Fix:
`"machine_shape": "NvidiaTeslaT4"` (matching the baseline author's own
working `kernel-metadata.json`, found via `kaggle kernels pull`) resolved
it immediately. Not documented in the public `kaggle kernels push --help`;
only discoverable by pulling a known-working kernel's metadata.

**`kaggle competitions submit -f <csv>` can be rejected outright for a
Code Competition, even with a schema-correct file.** Assumed file-upload
based on the vendored baseline's own README ("Kaggle accepts a CSV upload
only") — wrong. The real API call failed with `400 Bad Request` /
`{"error":{"message":"Submission not allowed:  This competition only
accepts Submissions from Notebooks.","status":"FAILED_PRECONDITION"}}`.
Generalizes: a competition baseline's own docs about the submission
mechanism aren't authoritative — verify with a real API call before
assuming either direction (file-upload vs. notebook-rerun).

**The correct Code-Competition submission path *is* scriptable — it's just
not a `kaggle` CLI subcommand.** The `kaggle` Python package's
`KaggleApi.competition_submit_code(file_name, message, competition, kernel,
kernel_version)` method (undocumented in `kaggle --help`, found by
inspecting the installed package's `dir(KaggleApi)`) submits a specific
kernel version's output directly — no manual "Submit to Competition" web
click needed. Needs: the kernel's `kernel-metadata.json` to declare
`competition_sources`, the kernel's *current version number* (via
`KaggleApi.build_kaggle_client().kernels.kernels_api_client.get_kernel(...)`
— not exposed by `kaggle kernels status`), and the kernel's most recent
version to have actually run with internet disabled (a first attempt
without `kernel_version` pinned hit a `403 Permission 'kernelSessions.get'
was denied`; passing the explicit version number fixed that unrelated
issue and surfaced the real, actionable error: `"Your Notebook cannot use
internet access in this competition."`).

**Fixing "internet disabled" for a kernel that installs packages via pip is
its own multi-step saga.** Setting `enable_internet: false` in
`kernel-metadata.json` means the setup cell's `pip install` can no longer
reach PyPI/GitHub — switching to `pip install --no-index --find-links
<artifacts-dataset>/wheels ...` (matching the baseline author's own public
inference notebook, which bundles a `wheels/` dir in the same artifacts
dataset for exactly this reason) surfaced three sequential failures before
it worked:
1. Pinning `numpy`/`scipy`/`torch` to their already-installed versions
   (the fix for the *online* ABI-break problem above) fails outright with
   `--no-index`: `pip` can't satisfy an explicit `==<old version>` pin when
   the only candidate `--find-links` can see is a newer bundled wheel
   (`ResolutionImpossible`), unlike a normal internet install where an
   already-satisfied exact pin just short-circuits without needing a
   candidate search at all.
2. Installing **unpinned** (matching the reference notebook exactly)
   installs cleanly but silently upgrades `numpy` 2.0.2 → 2.4.6 anyway (a
   transitive floor from `zarr`/`numcodecs` matched the newer numpy wheel
   bundled in `wheels/`) and leaves numpy internally inconsistent at
   import time (`ImportError: cannot import name '_center' from
   numpy._core.umath`, then, after trying a targeted
   `--force-reinstall --no-deps numpy` follow-up, `AttributeError: module
   'numpy._core._multiarray_umath' has no attribute '_blas_supports_fpe'`
   instead) — every relevant wheel's own `Requires-Dist` was checked by
   hand and numpy 2.0.2 already satisfies all of them, so the upgrade was
   never actually necessary, just something `pip`'s resolver did anyway,
   and upgrading it in place on this base image reliably corrupts it.
3. **Fix**: install with `--no-deps`, naming only the packages genuinely
   missing from the base image (`bidict`, `donfig`, `geff`, `geff-spec`,
   `ilpy`, `imagecodecs`, `numcodecs`, `pyscipopt`, `rustworkx`,
   `tracksdata`, `zarr`) so `pip` never touches numpy/scipy/llvmlite/numba
   at all. One exception: `polars` is already present (older) in the base
   image, and `pip install polars` with no version pin and no `--upgrade`
   leaves an already-installed package alone — it needs an explicit
   `polars==<wheels/ version>` (and `polars-runtime-32==<same>`) to force
   the upgrade our own graph-repair code actually needs (`pl.Float16`,
   added after the base image's bundled version).

Generalizes: on Kaggle, `--no-index --find-links` installs need the
*opposite* discipline from normal pinned installs — don't pin
already-satisfied packages to their old version (unsatisfiable if the only
local candidate is newer), and don't leave a package that needs upgrading
unpinned (silently ignored if already present) — enumerate exactly what's
missing-or-needs-upgrading and say so explicitly, `--no-deps`, rather than
trusting the resolver either way.

**A public dataset's bundled `repo/` may only include what its own
publisher's notebook needs — don't assume it's a complete mirror of the
upstream project.** `thibautgoldsborough/cellmot-baseline-artifacts`'s
`repo/` has `train_unet_transformer.py`/`predict_unet_transformer.py`/
`dataspec.py`/`src/` (everything their inference notebook imports) but not
`geffs_to_csv.py`/`csv_to_geffs.py`/`evaluate.py` (their notebook inlines
the CSV-flattening logic instead of calling a script) — confirmed by a
`FileNotFoundError` on a real run. Fixed by inlining the same flatten-to-CSV
logic directly in `02_baseline_modeling.ipynb`'s submission cell rather than
shelling out to a script that isn't guaranteed present.

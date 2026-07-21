# EDA Insights

From the first trusted run of `notebooks/01_eda.ipynb` on Kaggle,
2026-07-21 (kernel `tuannm3812/biohub-eda`, version 4, `COMPLETE`). Full
rich output (stats table, plots) lives on the kernel page —
kaggle.com/code/tuannm3812/biohub-eda — the CLI log only captures `print()`
stdout, not DataFrame/plot rendering.

## Dataset scale

- **199 train videos** with ground truth, **4 test videos**. The test set
  being this small (vs. hundreds of train videos) is worth keeping in mind:
  every test video's score matters a lot, and there's no way to locally
  validate against it (no test GT) — see `docs/3_strategy.md`'s validation
  section.
- Confirmed data format matches `docs/1_instructions.md`: OME-Zarr v3,
  `(T, Z, Y, X)`, `uint16`, voxel scale `(1.625, 0.40625, 0.40625)` µm
  (Z, Y, X) — i.e. Z is **4× coarser** than X/Y. Every public reference
  notebook reviewed (see `docs/3_strategy.md`) treats this anisotropy
  explicitly (isotropic resampling or physical-µm gating) rather than
  operating in raw voxel space; our vendored baseline already gates
  distances in µm internally (`src/tracking_cellmot/metrics.py`,
  `pool_kernel_um` in `predict_unet_transformer.py`), so this is handled,
  not a gap.

## Ground truth is genuinely sparse

Sample video `44b6_0113de3b`: 100 timepoints, only **52 annotated nodes /
50 edges total** — roughly 0.5 nodes per timepoint, against a
`(64, 256, 256)` volume that almost certainly contains far more visible
cells. This matches the competition's own framing (`docs/1_instructions.md`)
and is the reason the metric doesn't penalize unmatched *predicted* nodes
outside ground truth, only excess volume relative to `T_true` (Adjusted
Edge Jaccard) — see `docs/metrics.md`.

## Open question, not yet resolved

Only 4 test videos were found under the Kaggle mount. Worth double-checking
this is genuinely the full held-out test set (not a partial mount or a
competition-lifecycle artifact) before over-indexing local strategy on a
sample size this small — re-run `01_eda.ipynb`'s dataset-listing cell
periodically and compare.

## What to do next

- Rerun the multi-video stats table with `N_VIDEOS_FOR_STATS = None` (all
  199, not just 10) now that Kaggle runtime is known to be fast, and pull
  the real per-video breakdown into this doc — current numbers are from a
  single sample video only.
- Cross-reference `estimated_number_of_nodes` (a field in each train
  video's `.geff` `zarr.json` metadata, `attributes.geff.extra.
  estimated_number_of_nodes` — not yet read by our EDA notebook) against
  our own detection counts once we have predictions on train — several
  top public notebooks use this exact field to calibrate a per-video
  detection budget and avoid the over-prediction penalty. See
  `docs/3_strategy.md`.

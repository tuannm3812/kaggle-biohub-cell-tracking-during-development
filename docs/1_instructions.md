# Competition Instructions

[Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development)
— started 2026-06-29, deadline **2026-09-29 23:59 UTC**, $60,000 prize pool
(Research category, ~1450 teams as of 2026-07-21). Already entered.

## The task

Track cells in 3D through time in zebrafish embryo microscopy videos. Ground
truth annotations are **sparse** (only a subset of cells are annotated per
video). Builds on Loïc Royer's group's `Ultrack` work (Nature Methods, 2025).

## Data

- **Images**: OME-Zarr, shape `(T, Z, Y, X)`. Voxel scale
  `Z, Y, X = 1.625, 0.40625, 0.40625` microns/pixel.
- **Tracks**: GEFF files ([`tracksdata`](https://github.com/royerlab/tracksdata)
  format) — sparse graphs with nodes `(t, z, y, x)`, temporal edges.
  Divisions = one node at `t` with two outgoing edges to `t+1`.
- **Layout**: `{name}.zarr` + paired `{name}.geff` per dataset.
  ```
  /kaggle/input/competitions/biohub-cell-tracking-during-development/
  ├── train/   {name}.zarr + {name}.geff   (ground truth provided)
  └── test/    {name}.zarr                  (no ground truth)
  ```
- **Size**: ~87.6 GB total — CC0 licensed, the largest public cell-tracking
  annotation set by annotation count.
- `scripts/dataspec.py` resolves the path automatically: `$CELLMOT_DATA_DIR`
  override → Kaggle `train/` mount → local `./data/dense_channel`.

## Evaluation metric

Full detail in [`metrics.md`](metrics.md). Summary:

- **Edge Jaccard**: `TP / (TP + FP + FN)` on predicted vs. ground-truth
  lineage edges. Nodes matched to ground truth by centroid distance (≤ 7 µm,
  optimal bipartite assignment).
- **Adjusted Edge Jaccard**: penalizes excess predicted nodes:
  `max(0, jaccard · (1 − 0.1 · (T_pred − T_true) / T_true))`.
- **Division Jaccard**: same TP/FP/FN formula, scored on division events
  (parent → two-daughter topology) within a local time window.
- **Aggregation**: micro-averaged — counts summed across all videos in the
  split *before* computing the Jaccard.
- **Final score**: `adjusted_edge_jaccard + 0.1 · division_jaccard`.
- Ground truth is intentionally sparse; unmatched predicted nodes outside
  ground truth are **not** penalized. Division predictions can land one
  timepoint early/late and still count.

## Submission method — Code Competition (notebook rerun), not file upload

**Matches the master standard's §11 (notebook-based submission preferred) —
not a deviation.** This was initially assumed to be file-upload only
(the vendored baseline's own README says "Kaggle accepts a CSV upload
only"), but a real `kaggle competitions submit -f submission.csv` attempt
(2026-07-21) was rejected by the API with `400 Bad Request`:

```
{"error":{"code":400,"message":"Submission not allowed:  This competition
only accepts Submissions from Notebooks.","status":"FAILED_PRECONDITION"}}
```

So the organizers' baseline README is stale/inaccurate on this point — this
is a **Code Competition**: submissions must come from a Kaggle Notebook run,
not a bare CSV upload. Unlike file-upload submission, this step also
requires the kernel to run with **internet disabled** — Code Competition
scoring runs are offline by design — confirmed by a second rejection
(`"Your Notebook cannot use internet access in this competition."`) once
the submission-source check above was fixed. `02_baseline_modeling.ipynb`'s
Setup cell installs every dependency from the `cellmot-baseline-artifacts`
dataset's bundled `wheels/` via `pip install --no-index --find-links`
instead of PyPI/git for this reason (see `docs/6_kaggle_troubleshooting.md`
for the numpy/polars pitfalls that surfaced along the way), and
`kernel-metadata.json` sets `"enable_internet": false`.

There's no raw `kaggle` CLI subcommand for the submission step itself, but
it **is** scriptable via the `kaggle` Python package:

```python
import kaggle
from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest

api = kaggle.KaggleApi()
api.authenticate()

# 1. Push with RUN_MODE = "submission" and wait for COMPLETE:
#    scripts/push_kaggle_kernel.sh baseline
#    kaggle kernels status tuannm3812/biohub-baseline-modeling

# 2. Get the current version number (not exposed by `kaggle kernels status`):
with api.build_kaggle_client() as kc:
    req = ApiGetKernelRequest()
    req.user_name, req.kernel_slug = "tuannm3812", "biohub-baseline-modeling"
    version = kc.kernels.kernels_api_client.get_kernel(req).metadata.current_version_number

# 3. Submit that specific version's output:
api.competition_submit_code(
    file_name="submission.csv",
    message="...",
    competition="biohub-cell-tracking-during-development",
    kernel="tuannm3812/biohub-baseline-modeling",
    kernel_version=version,  # omitting this hit an unrelated 403 (kernelSessions.get denied)
)
```

The kernel's `kernel-metadata.json` must declare `competition_sources`
for step 3 to be accepted at all. The Kaggle web UI's "Submit to
Competition" button on the kernel's page does the same thing manually, if
preferred.

**CSV schema** (verified 2026-07-21 against the real `sample_submission.csv`,
downloaded via `kaggle competitions download -c biohub-cell-tracking-during-development -f sample_submission.csv`):

```
id,dataset,row_type,node_id,t,z,y,x,source_id,target_id
```

One `node` row per detection (`node_id`, `t`, `z`, `y`, `x` populated,
`source_id`/`target_id` = `-1`) and one `edge` row per link (`source_id`,
`target_id` populated, everything else `-1`). `scripts/geffs_to_csv.py`
produces exactly this — verified column-for-column against the sample file
(and re-verified: the CLI-upload attempt above reached Kaggle's schema
validation and was rejected on the *submission-source* check, not a schema
error).

## Pretrained baseline weights (public)

The baseline author published a trained checkpoint as a public Kaggle
Dataset: `thibautgoldsborough/cellmot-baseline-artifacts`
(`weights/unet_transformer/split_0/edge_predictor_best.pth`), alongside a
public inference notebook,
[`thibautgoldsborough/unet-baseline-inference-submission`](https://www.kaggle.com/code/thibautgoldsborough/unet-baseline-inference-submission)
(pulled via `kaggle kernels pull` 2026-07-21 to confirm the exact mount
path and usage — not fetchable by URL, see
`docs/6_kaggle_troubleshooting.md`). Its own notes: `--use-ilp` scored
~0.73 → ~0.79 over the greedy linker; `--det-threshold 0.99` was the best
of a sweep (GT is sparse so the detector is poorly calibrated). Not trained
to convergence — a starting point, not a ceiling.
`notebooks/02_baseline_modeling.ipynb` defaults to this checkpoint
(`USE_PRETRAINED = True`) so a first submission doesn't require training
anything ourselves.

## Baseline method (vendored, see `docs/0_coding_standards.md`)

End-to-end detection + linking, trained jointly:

1. **Detection** — 3D U-Net with temporal attention (`TemporalUNet3D`);
   per-voxel features + a detection map; cell centers via local-max
   suppression.
2. **Linking** — per-node features pooled at detected centers, fed to a
   cross-attention transformer (`SimpleNodeTransformer`) that scores every
   `(t, t+1)` node pair.
3. **Sparse supervision** — only ground-truth edges backpropagate;
   unannotated cells/background detections are ignored during training.

See "Pretrained baseline weights" below for the public checkpoint used by
default in `notebooks/02_baseline_modeling.ipynb` — not trained to
convergence, real gains are available just from training longer.

## Python API quick reference

```python
from tracking_cellmot.io import open_dataset
from scripts.dataspec import DATASET_PATH

ds = open_dataset(DATASET_PATH / "sample_1", normalize=True, require_tracks=True)
print(ds.image.shape)  # (T, Z, Y, X)
print(ds.scale)         # voxel scale in microns
```

```python
from tracking_cellmot.metrics import evaluate_datasets

result = evaluate_datasets(graph_pairs=[(pred_graph, gt_graph), ...], scale=ds.scale)
print(result.edge_jaccard, result.division_jaccard, result.score)
```

## Links

- Competition: https://www.kaggle.com/competitions/biohub-cell-tracking-during-development
- Baseline repo: https://github.com/royerlab/kaggle-cell-tracking-competition
- `tracksdata`: https://github.com/royerlab/tracksdata

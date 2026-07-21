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

Full detail in [`../metrics.md`](../metrics.md). Summary:

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

## Submission method — file upload only

**Exception to the master standard's §11 (notebook-based submission
preferred).** This competition does not support Kaggle notebook rerun
submission — organizers' own baseline states "Kaggle accepts a CSV upload
only." Round trip:

```bash
# 1. Inference -> one .geff per test dataset
uv run python scripts/predict_unet_transformer.py --method baseline --split 0

# 2. geffs -> CSV (the file you upload to Kaggle)
uv run python scripts/geffs_to_csv.py \
    --in-dir predictions/$USER/baseline/split_0 --csv submission.csv

# 3. (sanity check) CSV -> geffs -> score against ground truth
uv run python scripts/csv_to_geffs.py --csv submission.csv --out-dir out_geffs
uv run python scripts/evaluate.py --pred-dir out_geffs --gt-dir "$CELLMOT_DATA_DIR"
```

Then upload `submission.csv` on the competition's Submit page. See
`docs/0_coding_standards.md`'s "Pushing Notebooks To Kaggle" section for
running this via `scripts/push_kaggle_kernel.sh baseline` on Kaggle Kernels
(free GPU, data pre-mounted) rather than locally.

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

The weights referenced by `scripts/predict_unet_transformer.py`'s defaults
were **not trained to convergence** (per the baseline README) — real gains
are available just from training longer.

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

# Kaggle Kernels workflow

The competition dataset is ~87.6 GB, so it isn't downloaded locally. Instead:
develop and unit-test here, publish the code as a private Kaggle Dataset,
then run training/inference on **Kaggle Kernels** (free GPU, competition
data already mounted).

## 0. Auth

`~/.kaggle/kaggle.json` is already set up locally — the `kaggle` CLI
(installed via `uv sync --extra kaggle`) picks it up automatically. Verify:

```bash
uv run kaggle competitions list -s biohub-cell-tracking-during-development
```

Never commit `kaggle.json` or paste its contents anywhere (`.gitignore` /
`.kaggleignore` already exclude it).

## 1. Publish the code as a Kaggle Dataset

First time:

```bash
uv run kaggle datasets create -p .
```

After any code change:

```bash
uv run kaggle datasets version -p . -m "describe what changed"
```

`.kaggleignore` (repo root) keeps `.git`, `.venv`, local `data/`, weights,
predictions, etc. out of the upload. `dataset-metadata.json` (repo root)
owns this — id `tuannm3812/tracking-cellmot-src`.

## 2. Push and run the kernel

```bash
uv run kaggle kernels push -p kaggle/
```

Edit `kaggle/run_kernel.py`'s constants (`MODE`, `METHOD`, `SPLIT`,
`WEIGHTS_PATH_OVERRIDE`) before each push:

- `MODE = "train"` — trains and leaves `weights/` under the kernel's
  `/kaggle/working/repo/` (download via kernel Output, or publish as a new
  Kaggle Dataset version to reuse in a later predict-only kernel).
- `MODE = "predict"` — runs `predict_unet_transformer.py` then
  `geffs_to_csv.py`, writing `/kaggle/working/submission.csv`. Needs
  trained weights available at `WEIGHTS_PATH_OVERRIDE` (or the default
  `weights/{method}/split_{split}/edge_predictor_best.pth` path) — either
  from a prior training run in the same kernel, or a weights dataset added
  to `kernel-metadata.json`'s `dataset_sources`.

Check status / logs:

```bash
uv run kaggle kernels status tuannm3812/tracking-cellmot-runner
```

## 3. Pull results back and validate locally

```bash
uv run kaggle kernels output tuannm3812/tracking-cellmot-runner -p ./kernel_output
```

Before uploading `submission.csv` to the competition, sanity-check it
against ground truth (needs a small amount of real training data locally —
set `CELLMOT_DATA_DIR` to point at it):

```bash
uv run python scripts/csv_to_geffs.py --csv kernel_output/submission.csv --out-dir out_geffs
uv run python scripts/evaluate.py --pred-dir out_geffs --gt-dir "$CELLMOT_DATA_DIR"
```

Then upload `submission.csv` on the competition's Submit page (see
`../docs/1_instructions.md` — this competition is CSV-upload only, not
notebook-rerun).

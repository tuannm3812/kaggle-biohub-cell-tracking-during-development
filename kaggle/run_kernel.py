"""Entry point for the Kaggle Kernel (see ../kaggle/README.md).

Uploaded as this kernel's `code_file` (kernel-metadata.json). At kernel start:

1. Copies the mounted, read-only code dataset into a writable working copy
   (dataspec.py resolves PREDICTIONS_PATH/WEIGHTS_PATH relative to the repo
   location, which must be writable).
2. Installs the extra runtime deps not in Kaggle's base image.
3. Runs either training or the predict -> geffs_to_csv submission round trip,
   depending on MODE below.

Edit the constants below before each `kaggle kernels push`.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- edit before pushing -----------------------------------------------
MODE = "predict"  # "train" or "predict"
METHOD = "baseline"
SPLIT = "0"
EPOCHS = 50  # only used when MODE == "train"
# Path to trained weights for MODE == "predict". Leave as None to use the
# baseline's default (WEIGHTS_PATH/{METHOD}/split_{SPLIT}/edge_predictor_best.pth),
# which only exists if you already trained in this kernel or attached a
# weights dataset as an extra dataset_source in kernel-metadata.json, e.g.
# "/kaggle/input/<weights-dataset-slug>/edge_predictor_best.pth".
WEIGHTS_PATH_OVERRIDE = None
# -------------------------------------------------------------------------

CODE_DATASET_SLUG = "tracking-cellmot-src"  # must match kernel-metadata.json's dataset_sources
SRC_MOUNT = Path("/kaggle/input") / CODE_DATASET_SLUG
REPO = Path("/kaggle/working/repo")


def _install_deps() -> None:
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "-q",
            "zarr>=3.0.10", "scipy", "tqdm", "polars",
            "tracksdata @ git+https://github.com/royerlab/tracksdata@main",
        ],
        check=True,
    )


def _copy_repo_writable() -> None:
    if REPO.exists():
        shutil.rmtree(REPO)
    shutil.copytree(SRC_MOUNT, REPO)


def _run(*args: str, env: dict) -> None:
    subprocess.run([sys.executable, *args], check=True, env=env, cwd=str(REPO))


def main() -> None:
    _install_deps()
    _copy_repo_writable()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")

    if MODE == "train":
        _run(
            "scripts/train_unet_transformer.py",
            "--split", SPLIT, "--epochs", str(EPOCHS),
            env=env,
        )
        print(f"Weights written under {REPO}/weights/ (download from kernel Output).")
        return

    predict_args = ["scripts/predict_unet_transformer.py", "--method", METHOD, "--split", SPLIT]
    if WEIGHTS_PATH_OVERRIDE:
        predict_args += ["--weights", WEIGHTS_PATH_OVERRIDE]
    _run(*predict_args, env=env)

    kaggle_user = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    predictions_dir = REPO / "predictions" / kaggle_user / METHOD / f"split_{SPLIT}"
    submission_csv = Path("/kaggle/working/submission.csv")
    _run(
        "scripts/geffs_to_csv.py",
        "--in-dir", str(predictions_dir), "--csv", str(submission_csv),
        env=env,
    )
    print(f"Wrote {submission_csv}")


if __name__ == "__main__":
    main()

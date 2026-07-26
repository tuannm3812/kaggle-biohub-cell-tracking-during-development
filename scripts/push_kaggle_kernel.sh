#!/usr/bin/env bash
# Push a notebook to its private Kaggle kernel.
#
# Copies the source notebook (the single source of truth, in notebooks/)
# into its kernel-metadata.json folder under notebooks/kernels/, then runs
# `kaggle kernels push`. The copied .ipynb is gitignored and regenerated
# every run, so notebooks/ never has two versions to keep in sync by hand.
#
# The baseline kernel depends on the private `tracking-cellmot-src` Kaggle
# Dataset (src/, scripts/) via kernel-metadata.json's dataset_sources --
# publish/refresh it first with `scripts/publish_code_dataset.sh version "..."`
# if the vendored code changed since the last push (not a plain `kaggle
# datasets version -p .` from the repo root -- see that script's header for why).
#
# Usage: scripts/push_kaggle_kernel.sh <eda|baseline>

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOTEBOOKS_DIR="$REPO_ROOT/notebooks"

case "${1:-}" in
  eda)
    NOTEBOOK="01_eda.ipynb"
    KERNEL_DIR="$NOTEBOOKS_DIR/kernels/eda"
    ;;
  baseline)
    NOTEBOOK="02_baseline_modeling.ipynb"
    KERNEL_DIR="$NOTEBOOKS_DIR/kernels/baseline_modeling"
    ;;
  *)
    echo "Usage: $0 <eda|baseline>" >&2
    exit 1
    ;;
esac

cp "$NOTEBOOKS_DIR/$NOTEBOOK" "$KERNEL_DIR/$NOTEBOOK"
(cd "$REPO_ROOT" && uv run kaggle kernels push -p "$KERNEL_DIR")

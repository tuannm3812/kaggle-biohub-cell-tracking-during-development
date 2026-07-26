#!/usr/bin/env bash
# Publish/refresh the private `tracking-cellmot-src` Kaggle Dataset that lets
# kernels use our own src/+scripts/ instead of the pretrained checkpoint's
# bundled (unmodified) copy -- see docs/0_coding_standards.md.
#
# `kaggle datasets create/version -p .` does NOT honor .kaggleignore for
# this project's kaggle-api version (confirmed empirically: a first attempt
# run from the repo root uploaded a 409MB .venv/ and full .git/ history
# alongside src/scripts/) -- so this stages only what the dataset actually
# needs (src/, scripts/, LICENSE, NOTICE.md) in a clean temp directory first.
#
# Usage:
#   scripts/publish_code_dataset.sh create             # first time
#   scripts/publish_code_dataset.sh version "message"   # after any code change

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp -R "$REPO_ROOT/src" "$STAGE/src"
cp -R "$REPO_ROOT/scripts" "$STAGE/scripts"
cp "$REPO_ROOT/dataset-metadata.json" "$STAGE/dataset-metadata.json"
cp "$REPO_ROOT/LICENSE" "$STAGE/LICENSE"
cp "$REPO_ROOT/NOTICE.md" "$STAGE/NOTICE.md"
find "$STAGE" -name "__pycache__" -type d -prune -exec rm -rf {} +

case "${1:-}" in
  create)
    (cd "$STAGE" && uv run --project "$REPO_ROOT" kaggle datasets create -p . -r zip)
    ;;
  version)
    msg="${2:?Usage: $0 version \"message\"}"
    (cd "$STAGE" && uv run --project "$REPO_ROOT" kaggle datasets version -p . -m "$msg" -r zip -d)
    ;;
  *)
    echo "Usage: $0 <create|version \"message\">" >&2
    exit 1
    ;;
esac

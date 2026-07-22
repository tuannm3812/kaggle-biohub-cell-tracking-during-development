# Submission Log

Every real Kaggle submission (via `KaggleApi.competition_submit_code`, see
`docs/1_instructions.md` for the round trip), in order — the ground-truth
leaderboard record. Local-only validation runs that never became a
submission live in `docs/4_experiments.md` instead.

| # | Date | Kernel version | Submission ref | Config | Public score | Δ vs previous |
|---|---|---|---|---|---:|---:|
| 1 | 2026-07-21 | v13 | [54875176](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/submissions) | `unet_transformer` split_0 pretrained, ILP (`DET_THRESHOLD=0.99`), graph repair **off** | 0.810 | — |
| 2 | 2026-07-22 | v17 | [54892941](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/submissions) | Same, graph repair **on** (short-track pruning + gap-closing, fixed multi-frame-edge bug — `docs/4_experiments.md` #1–#4) | 0.817 | +0.007 |

## Notes

- **#1** is the first working end-to-end pipeline — setup and EDA work
  behind it: `docs/2_eda_insights.md`, README.
- **#2**'s local-validation prediction (`docs/4_experiments.md` #4) was
  +0.0065 edge_jaccard; the real +0.007 public delta landed close enough to
  confirm `VALIDATE_ON_TRAIN_FOLD` as a trustworthy predictor for future
  submissions, not just directionally correct — see `docs/3_strategy.md`.
- Current best: **0.817** (submission #2). See `docs/3_strategy.md` for the
  prioritized roadmap toward the next one.

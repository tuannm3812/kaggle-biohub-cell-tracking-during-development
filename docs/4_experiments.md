# Experiment Log

Every local validation experiment — `VALIDATE_ON_TRAIN_FOLD` in
`02_baseline_modeling.ipynb`, scored via the real vendored
`tracking_cellmot.metrics.evaluate_datasets` on a held-out 19-video train
fold, not a proxy metric — whether or not it led to a real submission.
Real submissions (the subset that got scored on the actual leaderboard)
are tracked separately in `docs/5_submissions.md`.

## 0. Baseline

| Date | Config | edge_jaccard | division_jaccard | score |
|---|---|---:|---:|---:|
| 2026-07-21 | Raw ILP output, no repair, `DET_THRESHOLD=0.99` | 0.8031 | 0.0000 | 0.8031 |

Submitted as-is: `docs/5_submissions.md` #1, public **0.810**.

## Graph repair

| # | Date | Config | edge_jaccard | Δ vs #0 | Conclusion |
|---|---|---|---:|---:|---|
| 1 | 2026-07-21 | `CLOSE_GAPS` + `PRUNE_SHORT_TRACKS`, first implementation (dangling ends bridged with a single edge spanning multiple frames) | 0.7897 | -0.0133 | **Regression.** Root-caused by re-reading seshurajup's actual source (not just its summary): ground-truth edges only ever connect consecutive timepoints (`docs/metrics.md`), so a bridge edge spanning `t` to `t+2` directly can never be scored as a true positive — every bridge added was pure noise by construction. Not submitted; caught by this validation run. |
| 2 | 2026-07-22 | `CLOSE_GAPS` alone, fixed (bridges now insert `gap` interpolated intermediate nodes joined by ordinary single-frame edges, plus a `GAP_MAX_ADDED_FRAC=0.02` rate cap on new bridges — matching the reference notebook) | 0.8050 | +0.0020 | Genuine improvement in isolation. |
| 3 | 2026-07-22 | `PRUNE_SHORT_TRACKS` alone (`PRUNE_MIN_NODES=3`) | 0.8055 | +0.0024 | Also genuine — the #1 regression was entirely the gap-closing bug, not a real problem with pruning. |
| 4 | 2026-07-22 | Both together | 0.8096 | **+0.0065** | More than additive — pruning after gap-closing likely cleans up bridges that didn't connect into a longer valid track. **Submitted**: `docs/5_submissions.md` #2, public **0.817** (+0.007 real, closely matching the +0.0065 predicted here). |

Also notable across #1–#4: **division_jaccard was 0 in every condition** —
this checkpoint isn't getting any division credit at all, independent of
repair. Either a genuinely hard signal to recover, or a configuration
issue — not yet investigated (`docs/3_strategy.md` roadmap).

Full write-up of the root cause and fix: `02_baseline_modeling.ipynb`
section 2's finding cell.

## DET_THRESHOLD sweep

`docs/3_strategy.md` roadmap step 4 — sweeping
`DET_THRESHOLD_CANDIDATES = [0.90, 0.95, 0.99, 0.995]` against the
repair-on baseline (#4 above, 0.8096), since 0.99 is the baseline author's
own reported best for *their* setup — chosen before our repair stage
existed, so not necessarily still optimal. Kernel version 18, 2026-07-22.

| DET_THRESHOLD | raw score | repaired score | Δ vs 0.99 (repaired) |
|---:|---:|---:|---:|
| 0.90 | 0.8036 | **0.8121** | **+0.0025** |
| 0.95 | 0.8049 | 0.8119 | +0.0023 |
| 0.99 | 0.8031 | 0.8096 | — (previous default) |
| 0.995 | 0.8017 | 0.8079 | -0.0017 |

**Locally, 0.90 looked like the winner** — the repaired score decreases
monotonically as `DET_THRESHOLD` increases across all four points tested.
Set as the new default and submitted: `docs/5_submissions.md` #3.

**It didn't transfer.** Public score: **0.795** — worse than 0.99's
confirmed 0.817 by -0.022, and worse than the very first submission
(0.810). `DET_THRESHOLD` reverted to 0.99. This is the first case this
session where `VALIDATE_ON_TRAIN_FOLD` didn't predict a real submission's
direction, let alone its magnitude, after two prior cases (the repair fix,
isolated and combined) where it did.

**Why this one didn't transfer, unlike the repair fix — two hypotheses,
not yet distinguished:**

1. **Multiple-comparisons risk.** The repair fix was one hypothesis-driven
   test (does the corrected implementation help, yes/no). The threshold
   sweep instead picked the empirical best of four candidates on the same
   19-video sample — even with no distribution shift at all, selecting a
   arg-max over several candidates from a small held-out set tends to
   overstate the true improvement (regression to the mean). This alone
   could explain a smaller-than-predicted gain, though probably not a
   sign flip this large.
2. **Count-penalty sensitivity to which videos get sampled.**
   `DET_THRESHOLD` directly controls detection volume, which the Adjusted
   Edge Jaccard penalizes via `(T_pred - T_true) / T_true`
   (`docs/metrics.md`). `01_eda.ipynb` found ~15× annotation-density
   variance and no correlation between density and estimated true count
   across just 10 train videos — so a random 19-video train sample's
   over-prediction budget may not resemble the real, only-4-video test
   set's at all. The repair fix mainly changed graph *structure*
   (edges/nodes near existing tracks), a more localized effect; a
   threshold change alters total predicted volume everywhere at once,
   which is exactly the quantity this penalty term is sensitive to.

**Methodological takeaway**: trust `VALIDATE_ON_TRAIN_FOLD` for a single,
mechanism-backed hypothesis (like the repair fix) more than for *selecting*
among several candidate values for count-affecting parameters
(`DET_THRESHOLD`, and by extension the `ILP_*_WEIGHT`s) — confirm any such
selection with a real submission before adopting it as the new default,
and consider validating on a larger or stratified sample (not just one
random 19-video draw) before the next sweep. See `docs/3_strategy.md`.

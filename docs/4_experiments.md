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

## DET_THRESHOLD sweep (in progress)

`docs/3_strategy.md` roadmap step 4 — sweeping
`DET_THRESHOLD_CANDIDATES = [0.90, 0.95, 0.99, 0.995]` against the
repair-on baseline (#4 above, 0.8096), since 0.99 is the baseline author's
own reported best for *their* setup — chosen before our repair stage
existed, so not necessarily still optimal.

| DET_THRESHOLD | raw score | repaired score | Note |
|---:|---:|---:|---|
| 0.90 | pending | pending | |
| 0.95 | pending | pending | |
| 0.99 | 0.8031 | 0.8096 | current default — same as #0/#4 above |
| 0.995 | pending | pending | |

Kicked off 2026-07-22 (kernel version 18) — update this table once it
completes.

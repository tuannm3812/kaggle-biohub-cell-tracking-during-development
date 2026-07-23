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
repair. Root-caused below (`## Division over-prediction`) — not a hard or
rare signal, but massive over-prediction.

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

**Follow-up, 2026-07-22**: checked whether hypothesis 2 (count-budget
sensitivity) is even actionable — `01_eda.ipynb` section 4 read
`estimated_number_of_nodes` directly off the real test set's `zarr.json`
metadata (kernel `tuannm3812/biohub-eda` v8). Result: **0/4 test videos
have this field**, vs 10/10 on the train sample — they ship no `.geff` at
all, since there's no ground truth to store. This rules out any
`DET_THRESHOLD` calibration built on a per-test-video true-count estimate;
it's simply not available at inference time. Hypothesis 1
(multiple-comparisons risk from picking the best of 4 candidates on one
small sample) is now the leading explanation for the miss, though the
underlying detection-volume/over-prediction-penalty interaction from
hypothesis 2 may still contribute even without a calibration signal to
exploit it directly. See `docs/2_eda_insights.md` and `docs/3_strategy.md`.

**Resolution, 2026-07-23**: re-ran the sweep at 3x the sample size (60
val videos, up from 19; kernel `tuannm3812/biohub-baseline-modeling` v20),
narrowed to just the two candidates that matter:

| DET_THRESHOLD | n=19 repaired score | n=60 repaired score |
|---:|---:|---:|
| 0.90 | **0.8121** | 0.8246 |
| 0.99 | 0.8096 | **0.8268** |
| Δ (0.90 − 0.99) | **+0.0025** (0.90 "wins") | **-0.0022** (0.99 wins) |

**The ranking flipped.** At 3x the sample, `DET_THRESHOLD=0.99` comes out
ahead — consistent with the real submission's confirmed 0.817 and with
0.99 remaining the notebook default. This settles the question: the
original 19-video sweep's "0.90 wins" signal was small-sample noise
(hypothesis 1, multiple-comparisons risk), not a real train-set effect
that then failed to transfer to test. No distribution-shift explanation
(hypothesis 2) is needed to account for the miss, though it may still be
a real, separate consideration for future count-affecting changes — it
just isn't required to explain *this* one. No new submission needed:
0.99 was already the deployed default. **Methodological update**: a
19-video (~10%) held-out sample is not large enough to trust for
*selecting* among close candidates — 60 videos (~30%) was enough to
reverse the earlier (wrong) conclusion. Use at least this sample size for
any future `DET_THRESHOLD`/`ILP_*_WEIGHT` candidate selection, and still
confirm the winner with a real submission before fully trusting it.

## Division over-prediction

`docs/3_strategy.md` roadmap step 7. Every experiment above shows
`division_jaccard=0.0000` regardless of config; the working assumption had
been genuine rarity (`01_eda.ipynb`: 1 division / 1,000 combined train
timepoints). Checked directly, 2026-07-23, by reading the raw (pre-repair)
`.geff` predictions already saved from the DET_THRESHOLD re-sweep's 60-video
val fold (kernel v20's last candidate, `DET_THRESHOLD=0.99`) — no new
Kaggle run needed, just local analysis of files already downloaded:

| | Value |
|---|---:|
| Candidate forks (nodes with ≥2 outgoing edges), 60 val videos | **690** |
| Expected true divisions (EDA rate × 6,000 timepoints) | ~6 |
| Over-prediction factor | **~115x** |
| True positives recovered (any run, ever) | **0** |
| Daughter-pair distance: median / 10th–90th pct (µm) | 5.1 / 3.6–8.1 |
| Candidate-fork rate: `44b6_*` videos vs `6bba_*` videos | 0.230 vs 0.726 per 1,000 nodes |

**Conclusion**: this is not under-detection of a rare-but-real signal —
it's the model producing hundreds of forks that don't correlate with real
division events (TP=0 despite 690 candidates). Daughter-pair distances are
geometrically plausible (not an obvious duplicate-detection artifact), and
the ~3x rate difference between the two video-ID prefixes isn't large
enough on its own to explain a 115x excess over the expected count. Two
untested hypotheses: (a) the pretrained checkpoint isn't trained to
convergence and its fork/division channel is particularly under-trained;
(b) `ILP_DIVISION_WEIGHT=1.0` is too permissive relative to
`ILP_EDGE_WEIGHT=-1.0`.

**Why this might still be worth fixing even though division_jaccard is
already 0 either way**: a spurious second outgoing edge from a fork is
itself a candidate edge-level false positive under the edge Jaccard's own
matching rules (`docs/metrics.md`) — separate from the division metric
entirely. If even a fraction of the 690 candidates are edge-level FPs,
suppressing them could improve `edge_jaccard` directly.

**Resolution, 2026-07-23**: ran the `ILP_DIVISION_WEIGHT` sweep at the
same 60-video sample (kernel v21), `[1.0, 10.0]`:

| ILP_DIVISION_WEIGHT | candidate forks | raw edge_jaccard | repaired edge_jaccard |
|---:|---:|---:|---:|
| 1.0 (default) | 690 | 0.8212 | 0.8268 |
| 10.0 | **0** | 0.8211 | 0.8271 |

**A higher division cost completely eliminates the spurious forks (690 →
0), but `edge_jaccard` barely moves**: -0.0001 raw, +0.0003 repaired —
both well within noise at this sample size (recall it took the full
60-video sample just to detect the DET_THRESHOLD sweep's real ~0.002
effect above). Conclusion: the over-predicted forks were essentially
**harmless** to the score, not hidden false positives — the edge
Jaccard's own "ignored if no local GT evidence" rule (`docs/metrics.md`)
was already absorbing almost all of them, exactly as it's designed to for
sparse ground truth. `ILP_DIVISION_WEIGHT` tuning is a dead end for score
improvement; kept at the default (`1.0`, matching the baseline author's
own setting) since there's no evidence to justify changing it, and no new
submission needed. This closes out the division investigation
(`docs/3_strategy.md` roadmap step 7) — the 690-fork over-prediction is a
real, interesting model-quality observation, but not one worth spending
further tuning effort on before higher-leverage roadmap items.

## Training timing test

`docs/3_strategy.md` roadmap step 8. Before committing to training our own
checkpoint (the baseline author's own recipe: `--epochs 50` on the full
train fold), there was no timing data for it, unlike the predict-side
sweeps above (sized from a measured ~100s/video). Ran a bounded test
instead: 15 train / 5 val videos, 1 epoch, capped at 20 iterations
(kernel v23; the script's own default `--batch-size 16` OOMs on a T4 once
gradients are held during backprop, unlike inference — used `2` instead).

| | Measured |
|---|---:|
| Data loading | 0.78s/video (one-time, before the epoch loop) |
| Train step | 0.925s/batch (batch_size=2, so ~0.46s/window) |
| Val eval | 7.68s/video/epoch |

Extrapolated to a real run (~179 train / ~20 val videos, the auto-split's
90/10):

| | Extrapolated |
|---|---:|
| One-time data loading | ~2.6 min |
| Training, per epoch | **~2.2 hours** |
| Val eval, per epoch | ~2.6 min |
| 3 epochs (current notebook default) | **~6.6 hours** |
| 50 epochs (baseline author's own recipe) | **~110 hours (~4.6 days)** |

**Conclusion**: training our own checkpoint at any epoch count close to
the baseline's own recipe is not practical within a single Kaggle GPU
session (commonly ~9–12h) or reasonable weekly quota — even 3 epochs
consumes most of one session. Not pursuing full training now; redirecting
effort to the cheaper repair-stage techniques (motion-aware relinking,
trajectory smoothing) that reuse the existing `VALIDATE_ON_TRAIN_FOLD`
infrastructure without any training cost. Revisit if a substantially
cheaper training setup emerges (a bigger accelerator, mixed precision, or
a much smaller epoch count with early stopping).

## Trajectory smoothing

`docs/3_strategy.md` roadmap step 8's redirect. Detected centroids carry
per-frame noise independent of any linking mistake, and the edge metric
only matches within a 7 µm centroid distance (`docs/metrics.md`) — a
correctly-linked node can still miss that threshold on position alone.
`smooth_trajectories` (`02_baseline_modeling.ipynb` section 2) locally
line-fits each node's z/y/x against t over up to `SMOOTH_WINDOW=2` steps
of unambiguous (single-parent/child) track neighbors, changing only
coordinates — topology is untouched.

Verified against synthetic data before ever touching Kaggle (reduces MSE
against a known-true line under noise; leaves an isolated node
unchanged; correctly avoids cross-contamination between daughter branches
at a division point). A/B-tested on Kaggle at the confirmed 60-video
sample (kernel v24), predicting **once** and comparing
`repair_graph(..., smooth=False/True)` on the same predictions — smoothing
only post-processes the graph, so it doesn't need a second predict pass
the way `DET_THRESHOLD`/`ILP_DIVISION_WEIGHT` did:

| | edge_jaccard | division_jaccard | score |
|---|---:|---:|---:|
| `smooth=False` (previous default) | 0.8268 | 0.0000 | 0.8268 |
| `smooth=True` | **0.8391** | 0.0000 | **0.8391** |
| Δ | **+0.0123** | — | **+0.0123** |

**A real, substantial gain** — nearly double the graph-repair fix's
validated +0.0065 (`docs/5_submissions.md` #2, which mapped to a real
+0.007). This is a single hypothesis test at a pre-committed
`SMOOTH_WINDOW=2` (not a multi-candidate sweep), run at the 60-video
sample already confirmed reliable for this kind of test
(`docs/3_strategy.md`), so no additional multiple-comparisons caution
applies here the way it did for `DET_THRESHOLD`. `SMOOTH_TRAJECTORIES`
set to `True` as the new default. **Not yet submitted** — see
`docs/5_submissions.md` for whether/when this gets a real confirmation.

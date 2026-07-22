# Strategy

Synthesized 2026-07-21 from reading six public reference notebooks (source
pulled via `kaggle kernels pull`, not fetched by URL — see "Kaggle Access
Troubleshooting" in `docs/0_coding_standards.md`) plus our own first
successful runs (`docs/2_eda_insights.md`). Kaggle competition/code pages
aren't fetchable directly, so scores quoted below are the notebooks'
*own stated* LB numbers (titles, intro cells) — not independently verified
against the live leaderboard.

## Reference notebooks reviewed

| Notebook | Author | Approach | Stated LB |
| --- | --- | --- | ---: |
| [`lb897-baseline`](https://www.kaggle.com/code/yusuketogashi/lb897-baseline) | yusuketogashi | Learned baseline (`TemporalUNet3D` + transformer + ILP, 50-epoch checkpoint) + heavy deterministic graph repair | ~0.897 |
| [`biohub-cell-tracking-learned-graph-w-gap-recovery`](https://www.kaggle.com/code/pilkwang/biohub-cell-tracking-learned-graph-w-gap-recovery) | pilkwang | Same learned architecture + graph repair; author's "closing note" on this model line | (unstated, high) |
| [`biohub-cell-tracking-blend-preprocessings`](https://www.kaggle.com/code/pilkwang/biohub-cell-tracking-blend-preprocessings) | pilkwang | Same architecture + **D4 test-time augmentation** on both detection and edge scoring | (unstated, high) |
| [`biohub-cell-tracking-data-model-eda-baseline`](https://www.kaggle.com/code/pilkwang/biohub-cell-tracking-data-model-eda-baseline) | pilkwang | Pure classical: multi-scale DoG blob detection, no learned model | (unstated) |
| [`biohub-celltrack-eda-w-4d-view-dog-detect`](https://www.kaggle.com/code/jirkaborovec/biohub-celltrack-eda-w-4d-view-dog-detect) | jirkaborovec | Pure classical: DoG detection + count calibration + motion linking; extensive EDA | ~0.73 |
| [`lb-0-857-best-rule-base-v14`](https://www.kaggle.com/code/seshurajup/lb-0-857-best-rule-base-v14) | seshurajup (credits isakatsuyoshi, pilkwang) | Pure classical, **zero external datasets** — DoG/blob detection + two-pass motion Hungarian + gap-close + gap2 + short-track filter + line-fit smoothing, divisions **off** | 0.826 → 0.857 |

## The central finding

**Every top-scoring approach — learned or classical — converges on the
same shape of pipeline: detect → link (motion-aware, two-pass) → repair
(gap-close → prune short tracks → smooth) → (optionally) recover
divisions.** The learned notebooks (LB897, pilkwang) use our same
`TemporalUNet3D` + transformer + ILP architecture for detection/linking —
the score difference from our own first submission isn't a different
model, it's a much more elaborate **deterministic graph-repair layer**
sitting after it. The purely classical notebooks reach 0.73–0.857 with
*no trained model at all*, which tells us the repair layer alone is worth
more than the choice of detector, up to a point.

This reframes our priorities: the highest-leverage next work isn't
architecture — it's the same post-processing every top scorer already
validated.

## Concrete techniques worth adopting, in priority order

1. **Motion-aware two-pass linking.** Pass 1: Hungarian assignment within a
   tight gate (~6 µm) on velocity-extrapolated positions
   (`pos + 0.5 * (pos_t - pos_{t-1})`, i.e. constant-velocity prediction).
   Pass 2: remaining unmatched nodes, full gate (~8–10 µm), no motion
   term. Universal across every notebook reviewed, ours included via ILP —
   worth comparing our ILP's implicit linking against an explicit
   motion-relink pass.
2. **Bounded gap recovery, two tiers.** A "gap" pass closes 1-frame misses
   (a track's node is missing at exactly one timepoint); a stricter "gap2"
   pass separately handles 2-frame misses so a loose setting can't
   introduce non-consecutive edges. seshurajup's `recover_gap2` defaults:
   `max_total_um=10.2, max_step_um=4.4, max_added_frac=0.02` (caps total
   recovered distance, per-step distance, and the fraction of edges gap2
   is allowed to add). **Tried 2026-07-21, currently regresses our
   score** — see "Validated finding" below before retrying.
3. **Short-track pruning.** Drop tracks below a minimum length (4–7 frames
   across the notebooks reviewed) after linking/gap-closing — isolated or
   near-isolated short fragments are usually false positives that hurt
   the Adjusted Edge Jaccard's node-count penalty more than they help
   recall. **Tried 2026-07-21, currently regresses our score** — see
   "Validated finding" below before retrying.
4. **Trajectory smoothing.** Line-fit (local linear regression over a
   small window, e.g. `win=2`) or velocity-blended smoothing of node
   coordinates post-linking — cheap, doesn't touch topology, tightens
   centroid-distance matching against GT.
5. **Count calibration against `estimated_number_of_nodes`.** Every train
   (and per the geff spec, potentially test) video's `.geff` `zarr.json`
   carries `attributes.geff.extra.estimated_number_of_nodes` — a true-count
   estimate available *without* ground truth. jirkaborovec's notebook
   learns a `generous_threshold → estimated_count` calibration ratio on
   train, then applies a per-video detection budget (`topk` peaks/frame)
   on test to avoid over-predicting (Adjusted Edge Jaccard explicitly
   penalizes `T_pred > T_true`, see `docs/metrics.md`). We haven't read this
   field yet — do that before tuning `DET_THRESHOLD` further.
6. **Division recovery is low priority.** `score = adjusted_edge_jaccard +
   0.1 * division_jaccard` (`docs/metrics.md`) — divisions are only 10% of the
   score. seshurajup's 0.857 run has `allow_divisions: False` entirely.
   Only invest here once edge/detection quality is solid, and keep it
   conservative when we do (gate on parent–daughter distance *and*
   sister–sister distance, matching every notebook that implements it —
   e.g. pilkwang_blend's `SAFE_DIV_MAX_UM=4.66`,
   `SAFE_DIV_SISTER_MAX_UM=8.5`).
7. **(Later, once the above is solid) D4 test-time augmentation.**
   pilkwang_blend runs the detector and edge-transformer over all 8
   dihedral XY transforms (identity + 3 rotations + flips), inverse-aligns
   and averages before peak extraction / ILP. Free accuracy at ~8×
   inference cost — worth it once cheaper wins are exhausted, not before.

## Things we're already doing right (don't change)

- **Our train-fold validation is more accurate than most public proxies —
  but "confirmed against a real submission" turned out to mean something
  narrower than first thought.** `VALIDATE_ON_TRAIN_FOLD` in
  `02_baseline_modeling.ipynb` calls the *actual* vendored
  `tracking_cellmot.metrics.evaluate` — the same code the organizers
  ship — not a reimplementation, unlike several reviewed notebooks
  (seshurajup, jirkaborovec) that hand-roll their own proxy scorer. It
  correctly predicted the graph-repair fix's leaderboard gain **twice**
  (isolated techniques and combined, `docs/4_experiments.md`), but then
  missed the `DET_THRESHOLD` sweep's real direction entirely (predicted
  +0.0025, got -0.022 — see `docs/4_experiments.md`'s analysis). Working
  hypothesis: it's reliable for a single, mechanism-backed hypothesis
  test, but *selecting* among several candidates for a parameter that
  controls total detection volume (which the Adjusted Edge Jaccard's
  over-prediction penalty is directly sensitive to) is a different, riskier
  use of the same tool. Treat future threshold/`ILP_*_WEIGHT` sweeps as
  hypotheses to confirm with a submission, not settled conclusions.
- **Physical-µm gating is already handled** by the vendored baseline
  (`pool_kernel_um`, ILP distance weights) — the anisotropy correction
  every classical notebook implements by hand is already built in.
- **Schema correctness is verified against the real `sample_submission.csv`**,
  not assumed (`docs/1_instructions.md`) — several public notebooks note
  this exact risk ("a mismatch... causes a silent score of 0").
- **Predicted node counts land in the right ballpark at `DET_THRESHOLD=0.99`** —
  the submitted run predicted 7,603–75,760 nodes across the 4 test videos
  (avg ~41,171), the same order of magnitude as the 10 train videos'
  `estimated_number_of_nodes` (15,335–78,644, `docs/2_eda_insights.md`).
  Not re-checked at `DET_THRESHOLD=0.90` — that submission predicted
  177,137 total nodes vs 0.99's 164,682 (`docs/4_experiments.md`), a
  meaningfully larger jump, and may be exactly where the sweep's real-LB
  miss came from if the real test videos' true-count budget is tighter
  than train's. Worth checking directly (roadmap step 6) before trusting
  any count-affecting change again.

## Validated finding: graph repair regressed, root-caused, fixed, now a real gain

Short-track pruning + gap closing initially **regressed** the score
(edge_jaccard 0.8031 → 0.7897) — root-caused to a structural bug (gap
bridges spanned multiple frames, which no ground-truth edge can ever
match), fixed by inserting interpolated intermediate nodes instead, then
re-validated: both techniques genuinely help in isolation, and combined
give **+0.0065 edge_jaccard** locally, confirmed by a real **+0.007**
leaderboard gain (0.810 → 0.817) once submitted. Both flags are on by
default now. Full experiment-by-experiment numbers: `docs/4_experiments.md`
(local validation) and `docs/5_submissions.md` (real submissions).

Also notable: **division_jaccard was 0 in every condition tested** — this
checkpoint isn't getting any division credit at all right now, independent
of repair (`ILP_DIVISION_WEIGHT=1.0` is set, so this is either a genuinely
hard signal to recover or a configuration issue worth a closer look before
investing further in division-recovery post-processing).

## Roadmap

1. ~~Get a first valid `submission.csv` from the pretrained baseline~~ — done,
   `docs/2_eda_insights.md`/README.
2. ~~Upload the current (repair-off) `submission.csv` to bank a real LB
   number~~ — done, `docs/5_submissions.md` #1, **public score 0.810**.
   Sits between the classical public references' 0.73–0.857 and the
   learned+repair references' ~0.897 — expected for a working learned
   baseline without the repair layer yet.
3. ~~Root-cause and fix the graph-repair regression~~ — done, a structural
   bug, not a real problem with either technique (`docs/4_experiments.md`
   #1–#4). Fixed, re-validated (+0.0065 edge_jaccard combined), and
   submitted with repair on: `docs/5_submissions.md` #2, **public score
   0.817**, confirming `VALIDATE_ON_TRAIN_FOLD` as a reliable predictor of
   real gains, not just directionally correct.
4. ~~Sweep `DET_THRESHOLD` locally via `VALIDATE_ON_TRAIN_FOLD`~~ — done,
   `docs/4_experiments.md`'s sweep table, **but the result didn't
   transfer**: 0.90 predicted +0.0025 locally, scored **0.795** for real
   (`docs/5_submissions.md` #3, -0.022 vs #2) — the first miss this
   session after two correct predictions from the same tool. Reverted to
   `DET_THRESHOLD=0.99`. Full analysis: `docs/4_experiments.md`.
5. **Understand why the sweep missed before trying `ILP_*_WEIGHT` the same
   way** — two candidate explanations in `docs/4_experiments.md`
   (multiple-comparisons risk from selecting among 4 candidates on one
   small sample; and/or `DET_THRESHOLD`'s effect on total detection volume
   interacting with the Adjusted Edge Jaccard's over-prediction penalty
   differently on the real 4-video test set than on a random 19-video
   train sample). Reading `estimated_number_of_nodes` on `test/` (step 6)
   bears directly on the second hypothesis — do that before any further
   count-affecting sweep, and validate on a larger or stratified sample if
   one is attempted.
6. Read `estimated_number_of_nodes` from geff metadata in `01_eda.ipynb`
   (confirmed present on 10/10 surveyed train videos, not yet checked on
   `test/`); compare against predicted node counts per video (already
   roughly right-sized at `DET_THRESHOLD=0.99`, above — not re-checked at
   0.90, which may be exactly where the sweep's miss came from), then
   refine `DET_THRESHOLD` against that budget via `VALIDATE_ON_TRAIN_FOLD`
   — a more principled sequel to step 4's blind sweep, not a substitute
   for it, and now a higher priority given step 4's result.
7. Investigate the division_jaccard=0 finding above — `01_eda.ipynb`'s
   wider 10-video survey found only 1 division across 1,000 combined
   timepoints, so this looks like genuine rarity rather than an
   under-detection issue, but worth confirming before adding
   division-recovery post-processing on top of a signal that's this rare.
8. Consider motion-aware relinking (comparing against ILP directly, since
   ILP is already a stronger baseline than the two-pass Hungarian these
   techniques replace elsewhere), trajectory smoothing (seshurajup's
   `linefit_smooth`, not yet implemented — sits between pruning and the
   2-frame gap recovery in their pipeline, not tacked on at the end),
   D4 TTA, or training our own checkpoint longer, as later-stage
   refinements once 4–7 are stable.

## Attribution

Techniques above are learned from public notebooks' documented approach
and code, credited by name above; no code was copied — our implementation
will be original, written against our own vendored baseline. Per each
notebook's own visible license/sharing (public Kaggle code, viewable
without restriction).

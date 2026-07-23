# Strategy

Synthesized 2026-07-21 from reading six public reference notebooks (source
pulled via `kaggle kernels pull`, not fetched by URL — see
`docs/6_kaggle_troubleshooting.md`) plus our own first
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
2. ~~**Bounded gap recovery, two tiers.**~~ A "gap" pass closes 1-frame
   misses (a track's node is missing at exactly one timepoint); a
   stricter "gap2" pass separately handles 2-frame misses so a loose
   setting can't introduce non-consecutive edges. seshurajup's
   `recover_gap2` defaults: `max_total_um=10.2, max_step_um=4.4,
   max_added_frac=0.02`. **Implemented and confirmed working** (roadmap
   step 3) — see `docs/4_experiments.md`'s Graph repair section for the
   regression-then-fix story.
3. ~~**Short-track pruning.**~~ Drop tracks below a minimum length (4–7
   frames across the notebooks reviewed) after linking/gap-closing —
   isolated or near-isolated short fragments are usually false positives
   that hurt the Adjusted Edge Jaccard's node-count penalty more than
   they help recall. **Implemented and confirmed working** (roadmap step
   3) — see `docs/4_experiments.md`'s Graph repair section.
4. ~~**Trajectory smoothing.**~~ Local line-fit (`win=2`) of node
   coordinates post-linking — cheap, doesn't touch topology, tightens
   centroid-distance matching against GT. **Implemented and confirmed
   working** (roadmap step 8): a real **+0.0123 edge_jaccard** at the
   60-video sample, see `docs/4_experiments.md`'s Trajectory smoothing
   section.
5. ~~Count calibration against `estimated_number_of_nodes`~~ — **ruled
   out**: confirmed present on 10/10 surveyed train videos but **0/4 real
   test videos** (`01_eda.ipynb` section 4, `docs/2_eda_insights.md`) —
   test videos ship no `.geff` at all, so this field simply isn't readable
   at inference time. jirkaborovec's `generous_threshold → estimated_count`
   calibration (learned on train, applied on test) isn't reproducible here
   unless their test set differs from ours or they calibrate some other
   way — worth rereading their notebook if this technique still seems
   worth chasing, but not assumed anymore.
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

- **Train-fold validation is trustworthy for a single hypothesis, not for
  picking a "best" among several candidates without a large-enough
  sample.** `VALIDATE_ON_TRAIN_FOLD` in `02_baseline_modeling.ipynb` calls
  the *actual* vendored `tracking_cellmot.metrics.evaluate` — the same
  code the organizers ship, not a reimplementation like several reviewed
  notebooks use. See `docs/4_experiments.md`'s DET_THRESHOLD sweep for why
  this distinction matters and what sample size is now required.
- **Physical-µm gating is already handled** by the vendored baseline
  (`pool_kernel_um`, ILP distance weights) — the anisotropy correction
  every classical notebook implements by hand is already built in.
- **Schema correctness is verified against the real `sample_submission.csv`**,
  not assumed (`docs/1_instructions.md`) — several public notebooks note
  this exact risk ("a mismatch... causes a silent score of 0").
- **Predicted node counts land in the right ballpark** at the current
  default — see roadmap step 6 below and `docs/2_eda_insights.md` for the
  train-vs-test sanity check this is based on (informal; test videos have
  no `estimated_number_of_nodes` field of their own to check against
  directly).

## Roadmap

1. ~~Get a first valid `submission.csv` from the pretrained baseline~~ —
   done. `docs/2_eda_insights.md`, README.
2. ~~Bank a real LB number~~ — done. `docs/5_submissions.md` #1 (0.810).
3. ~~Root-cause and fix the graph-repair regression~~ — done, a
   structural bug in the first gap-closing implementation, not a real
   problem with either repair technique. `docs/4_experiments.md` (Graph
   repair), `docs/5_submissions.md` #2 (0.817).
4. ~~Sweep `DET_THRESHOLD` locally~~ — done, but the result didn't
   transfer to a real submission. `docs/4_experiments.md` (DET_THRESHOLD
   sweep), `docs/5_submissions.md` #3.
5. ~~Understand why the sweep missed~~ — resolved: a 3x-larger
   re-validation reversed the local ranking, confirming small-sample noise
   rather than a train/test distribution effect. No new submission
   needed. `docs/4_experiments.md`. **Going forward**: use at least a
   60-video sample, not 19, for any future threshold/`ILP_*_WEIGHT`
   candidate selection.
6. ~~Read `estimated_number_of_nodes` on `test/`~~ — done: absent on 0/4
   test videos (they ship no `.geff` at all), ruling out any
   test-time count calibration built on this field. `docs/2_eda_insights.md`.
7. ~~Investigate the division_jaccard=0 finding~~ — closed out: massive
   over-prediction of candidate forks (not rarity), but confirmed
   harmless to `edge_jaccard` via a follow-up `ILP_DIVISION_WEIGHT`
   sweep. No further tuning here is worth the effort.
   `docs/4_experiments.md` (Division over-prediction).
8. ~~Time-test training our own checkpoint before committing to a full
   run~~ — done: **not practical on this compute budget**. Extrapolated
   from a bounded test (`docs/4_experiments.md`), a full epoch on the
   ~179-video train fold costs ~2.2 hours; the baseline author's own
   50-epoch recipe would take ~110 hours (~4.6 days), and even 3 epochs
   consumes most of a single Kaggle GPU session. Not pursuing full
   training now.
9. ~~Trajectory smoothing~~ — **done, a real gain**: local line-fit
   (`SMOOTH_WINDOW=2`) of node coordinates post-repair, validated against
   synthetic data before Kaggle, then A/B-tested at the 60-video sample:
   **edge_jaccard 0.8268 → 0.8391 (+0.0123)**, roughly double the
   graph-repair fix's validated gain. `SMOOTH_TRAJECTORIES` now defaults
   to `True`. Full numbers: `docs/4_experiments.md`. **Not yet submitted**
   — confirm with a real submission before treating this as settled,
   matching the standing lesson from the `DET_THRESHOLD` miss (a single
   hypothesis test at a robust sample size is a strong signal, not a
   guarantee).
10. Motion-aware relinking (compare against ILP's implicit linking
    directly) remains the next cheap option with no training cost. D4
    test-time augmentation is a later option (it multiplies *inference*
    cost ~8x, not training cost, so it's unaffected by the training
    timing finding above).

## Attribution

Techniques above are learned from public notebooks' documented approach
and code, credited by name above; no code was copied — our implementation
will be original, written against our own vendored baseline. Per each
notebook's own visible license/sharing (public Kaggle code, viewable
without restriction).

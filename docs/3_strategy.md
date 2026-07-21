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

- **Our train-fold validation is more accurate than most public proxies,
  and now confirmed against a real submission.** `VALIDATE_ON_TRAIN_FOLD`
  in `02_baseline_modeling.ipynb` calls the *actual* vendored
  `tracking_cellmot.metrics.evaluate` — the same code the organizers
  ship — not a reimplementation. Several reviewed notebooks (seshurajup,
  jirkaborovec) hand-roll their own proxy scorer, which risks drifting
  from the real metric. The 19-video local validation score (0.8031, raw
  ILP) landed within 0.007 of the actual public leaderboard score for the
  same config (0.810) — close enough that **further hyperparameter tuning
  should happen locally first**, saving submission quota for confirming a
  genuine improvement rather than searching blind.
- **Physical-µm gating is already handled** by the vendored baseline
  (`pool_kernel_um`, ILP distance weights) — the anisotropy correction
  every classical notebook implements by hand is already built in.
- **Schema correctness is verified against the real `sample_submission.csv`**,
  not assumed (`docs/1_instructions.md`) — several public notebooks note
  this exact risk ("a mismatch... causes a silent score of 0").
- **Predicted node counts already land in the right ballpark.** The
  submitted run predicted 7,603–75,760 nodes across the 4 test videos
  (avg ~41,171) — the same order of magnitude as the 10 train videos'
  `estimated_number_of_nodes` (15,335–78,644, `docs/2_eda_insights.md`).
  `DET_THRESHOLD=0.99` isn't grossly over- or under-predicting overall, so
  count-calibration (roadmap step 5) likely refines the budget rather than
  fixing a large existing miscalibration — worth keeping expectations
  modest there relative to the repair root-cause and hyperparameter sweep.

## Validated finding: graph repair currently regresses the score

Implemented short-track pruning + bounded (1- and 2-frame) gap closing in
`02_baseline_modeling.ipynb`, unit-tested against synthetic data and a real
`tracksdata` graph object, then validated on **19 real held-out train
videos** via `VALIDATE_ON_TRAIN_FOLD` (2026-07-21) before ever spending a
submission on it:

| | edge_jaccard | division_jaccard | score |
|---|---:|---:|---:|
| raw (no repair) | 0.8031 | 0.0000 | 0.8031 |
| repaired | 0.7897 | 0.0000 | 0.7897 |
| delta | -0.0133 | +0.0000 | -0.0133 |

**It made things worse.** Both flags (`PRUNE_SHORT_TRACKS`, `CLOSE_GAPS`)
are off by default as a result — this is the validation harness doing its
job, not a wasted effort. Leading hypothesis: our detector already runs at
a strict `DET_THRESHOLD` (0.99), so short predicted segments are less
likely to be pure noise here than in the classical (DoG-detection)
pipelines these techniques are drawn from — pruning them away may be
removing true positives, not false ones. Gap closing may also be
introducing wrong bridges (a plain nearest-neighbor Hungarian match, not
the velocity-aware version the reference notebooks use) more often than it
recovers real missed detections. Not yet root-caused to which technique (or
both) is responsible — see roadmap step 2 below.

Also notable: **division_jaccard was 0 in both conditions** — this
checkpoint isn't getting any division credit at all right now, independent
of repair (`ILP_DIVISION_WEIGHT=1.0` is set, so this is either a genuinely
hard signal to recover or a configuration issue worth a closer look before
investing further in division-recovery post-processing).

## Roadmap

1. ~~Get a first valid `submission.csv` from the pretrained baseline~~ — done,
   `docs/2_eda_insights.md`/README.
2. ~~Upload the current (repair-off) `submission.csv` to bank a real LB
   number~~ — done 2026-07-21, **public score 0.810** (submission ref
   54875176). Sits between the classical public references' 0.73–0.857 and
   the learned+repair references' ~0.897 — expected for a working learned
   baseline without the repair layer yet.
3. **Sweep `DET_THRESHOLD` and the four `ILP_*_WEIGHT` values locally via
   `VALIDATE_ON_TRAIN_FOLD` — zero new code, cheapest possible next
   experiment.** The current values are the baseline author's own
   reported best from *their* sweep, on their own setup — not necessarily
   ours, and now that local validation is confirmed to track the public
   LB within ~0.007 (above), there's no reason not to search our own
   optimum for free before spending more effort on repair or count
   calibration. Concretely: grid or random search `DET_THRESHOLD` around
   0.99 (e.g. 0.90–0.995) and each `ILP_*_WEIGHT` independently, keeping
   whichever combination raises the 19-video `edge_jaccard` above 0.8031,
   then confirm with one submission.
4. **Root-cause the graph-repair regression above** before retrying it:
   toggle `PRUNE_SHORT_TRACKS` and `CLOSE_GAPS` independently via
   `VALIDATE_ON_TRAIN_FOLD` to isolate which one (or both) hurts, then
   retune rather than discard — try a looser `PRUNE_MIN_NODES` (2?) and a
   tighter `GAP_MAX_DIST_UM` (4–5 µm?) informed by whichever is at fault.
5. Read `estimated_number_of_nodes` from geff metadata in `01_eda.ipynb`
   (confirmed present on 10/10 surveyed train videos, not yet checked on
   `test/`); compare against predicted node counts per video (already
   roughly right-sized, above), then refine `DET_THRESHOLD` / ILP weights
   against that budget via `VALIDATE_ON_TRAIN_FOLD` — a more principled
   sequel to step 3's blind sweep, not a substitute for it.
6. Investigate the division_jaccard=0 finding above — `01_eda.ipynb`'s
   wider 10-video survey found only 1 division across 1,000 combined
   timepoints, so this looks like genuine rarity rather than an
   under-detection issue, but worth confirming before adding
   division-recovery post-processing on top of a signal that's this rare.
7. Consider motion-aware relinking (comparing against ILP directly, since
   ILP is already a stronger baseline than the two-pass Hungarian these
   techniques replace elsewhere), D4 TTA, or training our own checkpoint
   longer, as later-stage refinements once 3–6 are stable.

## Attribution

Techniques above are learned from public notebooks' documented approach
and code, credited by name above; no code was copied — our implementation
will be original, written against our own vendored baseline. Per each
notebook's own visible license/sharing (public Kaggle code, viewable
without restriction).

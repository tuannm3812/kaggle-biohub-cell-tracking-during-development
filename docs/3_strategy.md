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
   is allowed to add).
3. **Short-track pruning.** Drop tracks below a minimum length (4–7 frames
   across the notebooks reviewed) after linking/gap-closing — isolated or
   near-isolated short fragments are usually false positives that hurt
   the Adjusted Edge Jaccard's node-count penalty more than they help
   recall.
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
   penalizes `T_pred > T_true`, see `metrics.md`). We haven't read this
   field yet — do that before tuning `DET_THRESHOLD` further.
6. **Division recovery is low priority.** `score = adjusted_edge_jaccard +
   0.1 * division_jaccard` (`metrics.md`) — divisions are only 10% of the
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

- **Our train-fold validation is more accurate than most public proxies.**
  `VALIDATE_ON_TRAIN_FOLD` in `02_baseline_modeling.ipynb` calls the
  *actual* vendored `tracking_cellmot.metrics.evaluate` — the same code
  the organizers ship — not a reimplementation. Several reviewed notebooks
  (seshurajup, jirkaborovec) hand-roll their own proxy scorer, which risks
  drifting from the real metric. Keep using ours as the source of truth
  for local tuning.
- **Physical-µm gating is already handled** by the vendored baseline
  (`pool_kernel_um`, ILP distance weights) — the anisotropy correction
  every classical notebook implements by hand is already built in.
- **Schema correctness is verified against the real `sample_submission.csv`**,
  not assumed (`docs/1_instructions.md`) — several public notebooks note
  this exact risk ("a mismatch... causes a silent score of 0").

## Roadmap

1. ~~Get a first valid `submission.csv` from the pretrained baseline~~ — done,
   `docs/2_eda_insights.md`/README. Upload it to bank a real LB number
   (still pending — a deliberate, quota-costing action).
2. Read `estimated_number_of_nodes` from geff metadata in `01_eda.ipynb`;
   compare against our predicted node counts per video.
3. Add a graph-repair post-processing stage to `02_baseline_modeling.ipynb`
   after the ILP prediction step: motion-relink pass, gap + gap2 recovery,
   short-track pruning, line-fit smoothing — each gated behind its own
   config flag (matching our existing `USE_ILP`-style pattern), validated
   locally via `VALIDATE_ON_TRAIN_FOLD` before spending a submission.
4. Sweep `DET_THRESHOLD` / ILP weights with the count-calibration budget
   from step 2, again via `VALIDATE_ON_TRAIN_FOLD`.
5. Add conservative division recovery once 1–4 are stable.
6. Consider D4 TTA, or training our own checkpoint longer, as
   later-stage refinements once the repair layer is banked and scored.

## Attribution

Techniques above are learned from public notebooks' documented approach
and code, credited by name above; no code was copied — our implementation
will be original, written against our own vendored baseline. Per each
notebook's own visible license/sharing (public Kaggle code, viewable
without restriction).

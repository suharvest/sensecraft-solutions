# Internal status — Fall Detection

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "results / KPI only carry measured numbers".

## Coverage gaps removed from the page

**reCamera Pro capacity.** Only one live camera was run (13.05 FPS). Higher
loads were not tested. That row is below the 14.5 FPS threshold used for every
other platform's capacity boundary, so it is not a comparable capacity number.

**RealBiomFall external-set recall.** Measured for reCamera (58.8%) and for
YOLO11m as deployed on reComputer J40 (52.9%). YOLO11s was not measured on that
set.

## Wording changed on the page

"verified N streams" was rewritten to "measured N streams" throughout. The
capacity runs are single measurements, not an independent verification pass.

Results frozen 2026-09-05. Synthetic blank-frame and accelerator-only historical
data remain in the
[EdgeFallKit results ledger](https://github.com/suharvest/edgefallkit/blob/main/evaluation/RESULTS.md)
and are no longer used as stream-count data here.

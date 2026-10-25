# Fixed adapted-mesh comparisons

These five runs retain the historical adapted topology: 289,671 active cells, with automatic adaptation disabled. They restart a common coherent native checkpoint at the same physical time and rotor position. They are distinct from the original-position Hybrid systematic-mesh campaign.

| Run | Timestep [s] | Inner iterations | Accepted steps | Final physical time [s] |
|---|---:|---:|---:|---:|
| ITER30 | 3e-6 | 30 | 596 | 0.012441 |
| ITER60 | 3e-6 | 60 | 596 | 0.012441 |
| T100 | 2.97583785e-6 | 30 | 600 | 0.01243850271 |
| T200 | 1.487918925e-6 | 30 | 1,200 | 0.01243850271 |
| T400 | 7.439594625e-7 | 30 | 2,400 | 0.01243850271 |

ITER30 used 8 MPI processes for its first 240 accepted settling steps, then 24 for the remaining 356 steps. All final comparison statistics use its 24-process segment.

The common comparison window is 0.011545751355–0.01243850271 s: three complete blade-passing periods after the excluded post-change settling interval. ITER30/ITER60 integrate slightly beyond the window endpoint; the statistical window remains phase matched.

Each run contains `window_statistics.csv`, `cycle_statistics.csv`, `cycle_recurrence.csv`, `phase_profiles.csv`, `cycle_mass_flux.csv` and a normalised `assessment.json`. Storage-inclusive mass-conservation tables are provided where the domain-mass monitor is available. ITER30 has no equivalent storage-inclusive table, and its retained residual history covers 356 of the 596 accepted steps; the assessment reports this coverage rather than asserting a full residual record.

T100/T200/T400 also contain final-cycle blade-wall pressure/y+ envelopes and sampled wall-resolution summaries. T100/T200 use five saved phase samples, whereas T400 uses 101; their sampled extrema do not have equal peak resolution or bound unsaved phases.

The recorded monitor settling checks passed on these comparison windows. The adapted-mesh inner-iteration comparison supports using 30 iterations for the subsequent campaign. However, the T200/T400 amplitude difference did not satisfy the separate temporal-comparison limit, so general timestep independence is unconfirmed. See [sensitivity](../sensitivity/README.md).

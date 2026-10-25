# Numerical sensitivity

These tables distinguish three different comparisons: inner iterations and timestep on the fixed adapted mesh, and spatial sensitivity on the systematic family. Their diagnostic thresholds are separate from the successive-cycle settling criteria.

| File | Scope |
|---|---|
| [inner_iteration_comparison.csv](inner_iteration_comparison.csv) | ITER30 against ITER60, four monitored integral quantities |
| [inner_iteration_phase_fields.csv](inner_iteration_phase_fields.csv) | Same-phase field differences on the adapted mesh |
| [timestep_comparison.csv](timestep_comparison.csv) | T100–T200 and T200–T400 mean, amplitude and waveform differences |
| [timestep_iteration_error_comparison.csv](timestep_iteration_error_comparison.csv) | Timestep changes compared with iteration sensitivity and within-run cycle variability |
| [grid_recomputed_monitor_statistics.csv](grid_recomputed_monitor_statistics.csv) | Three-grid monitor means/amplitudes and their cycle ranges |
| [grid_mesh_pair_comparisons.csv](grid_mesh_pair_comparisons.csv) | M1–M2 and M2–M3 changes and phase-waveform differences |
| [grid_phase_profiles_with_cycle_range.csv](grid_phase_profiles_with_cycle_range.csv) | Across-cycle mean/minimum/maximum profiles at common phase |
| [grid_three_mesh_trends.csv](grid_three_mesh_trends.csv) | Mean/amplitude monotonicity, signed changes and contraction ratios |
| [assessment.json](assessment.json) | Normalised thresholds and final interpretation |

## Inner iterations and timestep

The operational comparison limits are 0.1% for mean differences, 2% for amplitude differences and 2% of amplitude for phase-profile RMS differences. ITER30/ITER60 satisfied these recorded criteria on the adapted mesh, supporting 30 inner iterations for that comparison.

T200/T400 did not satisfy every criterion. In particular, the outlet-total-pressure amplitude difference is approximately 6.56%. T/400 was retained as the operational systematic-campaign timestep, not established as temporally independent. Small timestep differences must also be interpreted against iterative sensitivity and residual cycle variability.

## Spatial sensitivity

The grid assessment was recomputed from accepted native histories. Each mesh contributes three complete cycles: M1/M3 cycles 33–35, M2 cycles 38–40. The windows match phase, but remaining settling effects mean that they are not independent estimates of spatial error alone.

For the grid-pair table, mean differences use the magnitude of the finer-mesh mean as denominator. Amplitude differences use the finer mean cycle peak-to-peak amplitude. Phase RMS and maximum differences are normalised by that same finer amplitude. Signed values are preserved in the underlying statistics; percentage differences are absolute magnitudes.

Medium-to-fine mean differences are 0.133804% for rotor force, 0.028225% for inlet flow, 0.137660% for outlet flow and 0.043932% for outlet total pressure. Corresponding amplitude differences are 6.415615%, 7.120605%, 7.518492% and 5.863296%.

All four three-grid mean trends are nonmonotonic. The cell-count-based refinement ratios are only indicative for this anisotropic family. No observed asymptotic order, extrapolated continuum value or GCI is assigned. Blank `observed_order`/`GCI` CSV entries and JSON `null` values mean **not established**, not zero error.

# Systematic mesh campaign

M1/M2/M3 derive from the same geometry and controlled meshing procedure. Each starts from fresh Hybrid Initialization after restoration of the actual original rotor coordinates. The historical AMR mesh is not one of these refinement levels.

All three use Fluent 2024 R2, planar 2D, double precision, 24 MPI processes, `dt = T/400 = 7.439594625e-7 s` and 30 inner iterations.

| Mesh | Active cells | Accepted steps | Final duration | Statistical cycles | Monitor settling |
|---|---:|---:|---:|---|---|
| M1 | 54,287 | 14,000 | 35T | 33–35 | Passed the configured checks |
| M2 | 104,831 | 16,000 | 40T | 38–40 | Inlet-flow amplitude check failed |
| M3 | 196,569 | 14,000 | 35T | 33–35 | Rotor-force amplitude check failed |

Stable native identifiers remain `M1_HYBRID35`, `M2_HYBRID35` and `M3_HYBRID35`. The suffix is not the authoritative duration: M2 reached 40 periods. Actual time and step count are provided in [the run summary](../run_summary.csv).

## Files in each mesh directory

| File | Interpretation |
|---|---|
| `assessment.json` | Normalised run facts, operational outcomes, limits and residual coverage |
| `window_statistics.csv` | Three-cycle means and average individual-cycle peak-to-peak amplitudes |
| `cycle_statistics.csv` | Separate cycle means, minima, maxima and amplitudes |
| `cycle_recurrence.csv` | Successive-cycle mean/amplitude changes and phase RMS differences |
| `phase_profiles.csv` | Four monitor signals interpolated onto 401 phase points for each of three cycles |
| `cycle_mass_flux.csv` | Signed boundary-flow means and integrated net inward mass |
| `cycle_mass_conservation.csv` | Flux integral compared with domain-mass change |
| `phase_field_recurrence.csv` | Same-phase sampled field differences after geometric matching |
| `sampled_wall_resolution.csv` | Blade face counts, sampled y+ extrema and sample coverage |
| `stator_wall_envelope.csv`, `rotor_wall_envelope.csv` | Final-cycle pressure/y+ means and sampled extrema at matched wall locations |

Cycle recurrence limits are 0.5% for means, 5% for amplitudes and 10% of the later-cycle amplitude for waveform RMS. Boundary mean flux imbalance uses 0.5%; storage-inclusive cycle-integral mass defect uses 0.01% of integrated inlet mass. Sampled field recurrence uses 0.5% relative nodal RMS and is not volume weighted. These are declared operational checks, not universal accuracy criteria.

The last M3 force-amplitude changes are 7.068509% for cycles 33–34 and 0.329532% for cycles 34–35. One pair therefore remains outside the limit. Passing conservation, sampled field and y+ checks does not remove that failure.

Blade wall statistics use five saved final-cycle phase samples. Extrema and fractions are sample based; the face fraction below one is weighted by face count, not area. The data do not bound every unsaved phase. The final sampled M1 y+ maxima are 0.583656 on the stator and 0.523972 on the rotor; earlier preparation values are not used here.

Residuals are rounded to the printed Fluent precision. Field recurrence metrics must be interpreted with their coordinate-mapping and duplicate-coordinate bounds. Remaining periodic settling and numerical sensitivity are retained explicitly in [the limitations](../../docs/limitations.md).

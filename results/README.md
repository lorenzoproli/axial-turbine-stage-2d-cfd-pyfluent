# Numerical results

This directory contains the selected scientific evidence for eight completed finite-duration calculations. Historical raw analyses and native solver files are supplied separately under the ignored `runs/` collection. 

## Results index

| Location | Purpose |
|---|---|
| [run_summary.csv](run_summary.csv) | Mesh, timestep, actual duration, statistical window and monitor-check outcome for all eight runs |
| [adapted_mesh/](adapted_mesh/README.md) | ITER30/ITER60 and T100/T200/T400 on the fixed historical adapted topology |
| [systematic_mesh/](systematic_mesh/README.md) | M1/M2/M3 from restored original-position Hybrid initialization |
| [mesh_quality/](mesh_quality/README.md) | Native active-cell extrema, zone quantiles and diagnostic counts for the historical baseline and three systematic meshes |
| [sensitivity/](sensitivity/README.md) | Inner-iteration, timestep and three-mesh comparisons |
| [figures/](figures/README.md) | Figure index and additional mesh views |
| [videos/](videos/) | Selected fine-mesh absolute-Mach movie and source-frame index |
| [data_manifest.json](data_manifest.json) | Table hashes, separately supplied source hashes, units and export checks |

The historical reference is not counted as one of the eight automated runs. Its native saved solution is at 0.010653 s, with 289,671 active cells and 72,168 inactive AMR parents. The three systematic meshes are a separate family. AMR was disabled in the verified final reference and automated calculations.

## Numerical interpretation

M1 completed 35 periods and passed the configured final settling checks. M2 completed 40 periods but retained an inlet-flow amplitude recurrence failure. M3 completed 35 periods but retained a rotor-force amplitude recurrence failure for one of the final two cycle pairs.

The medium-to-fine mesh mean changes are below 0.15% for the four monitors; peak-to-peak amplitude changes remain approximately 5.9–7.5%. The three-grid mean trends are nonmonotonic. Temporal independence, general grid independence, an observed asymptotic order and GCI are not established. The observations therefore describe sensitivity of a finite-duration dataset, not an experimentally validated or fully independent turbine-performance prediction.

The run summary records separate initial/final MPI counts. ITER30 used 8 processes through accepted step 240, then 24 through step 596. Its final three-period statistics lie in the 24-process segment. A blank process-change step means no change is recorded.

## Table conventions and units

- Time is physical Fluent time in seconds. `phase_fraction` spans one blade-passing period, `T = 2.97583785e-4 s`, relative to the recorded cycle start.
- `window_cycle_index` starts at zero within the final three-cycle statistical window. For M1/M3 these correspond to physical cycles 33–35; for M2 they correspond to cycles 38–40.
- `mean` is a time integral divided by the window duration. `mean_cycle_peak_to_peak` is the arithmetic mean of the three individual cycle amplitudes, not the range of the entire three-cycle signal.
- Force is the signed global Y component in N for a 1 m reference depth. Flow rates are kg/s for the same depth. Inward boundary flux is positive, so outward outlet flow is negative.
- Outlet total pressure is mass-flow weighted, in Pa. Wall pressure is absolute static pressure because the operating pressure is zero. Rotor total-pressure change includes work and is not itself a dissipative-loss measure.
- Dimensionless Mach, y+ and mesh-quality metrics have no pressure or velocity units. Cell volumes retain Fluent's 1 m depth convention.
- Native signs and physical values are retained. No data are scaled to make different runs coincide. Normalised percentages state their denominator in the column name or subdirectory guide.

## Export and verification

With the separate native collection restored:

```powershell
.\.venv\Scripts\python.exe tools\export_results.py
```

The exporter verifies the accepted native monitor source hashes, recomputes 32 monitor means/amplitudes and checks all four mesh-quality collections directly against their saved per-cell arrays. Native records remain unchanged; only the English result tables and their manifest are written. Figures and movies are not regenerated or modified.

The manifest stores portable source paths and content hashes, not personal machine paths. A source hash identifies evidence; it does not imply that the source binary is contained in Git. Missing native data stop regeneration explicitly. Complete reproduction requires the [documented inputs and environment](../docs/reproduction.md).

# Reproduction and data requirements

## What is supplied

The repository contains the Python workflow, recorded configurations, reference geometry material, selected numerical evidence, figures, the selected Mach movie and an editable report. Native Fluent/Workbench inputs and results are distributed as separate versioned release assets because of their size and software-specific dependencies.

The following operations have different requirements:

| Operation | Required material | Starts Fluent? |
|---|---|---|
| Read figures, tables and report | Repository only | No |
| Check curated-file integrity and saved status | Repository and Python dependencies | No |
| Regenerate native-monitor/field analyses | Appropriate native run collection and exported samples | No |
| Reopen a case or repeat a numerical run | Coherent native case/data, mesh/geometry, complete dependencies, Fluent and licences | Yes; campaign currently closed |

A missing native input is a missing dependency. It must not be substituted with a differently timed checkpoint under the expected filename.

## Recorded environment

- Windows 11 Pro, Python 3.12.
- ANSYS Fluent 2024 R2, double-precision planar 2D.
- PyFluent `ansys-fluent-core==0.42.2` and `ansys-api-fluent==0.7.0`.
- Exact analysis/rendering dependencies in the root `requirements.txt`.
- 24 MPI processes for the systematic campaign and the final adapted-mesh segments. ITER30 used 8 processes for its first 240 accepted settling steps and 24 for the remaining 356 steps. The recorded machine has an Intel Core i9-14900K and approximately 64 GiB RAM; no core-affinity optimisation is claimed.
- ANSYS Workbench/Meshing are additionally required to reproduce the recorded commercial meshing procedure.

## Create an environment

Run from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

The Python environment and commercial applications are not redistributed. A valid Fluent licence with the necessary parallel entitlement is required for native computation. The direct requirements retain the numerical package versions used by the workflow. `requirements-lock.txt` records the Windows/Python 3.12 environment used by the project. Other software versions can require changes to the API calls or dependencies.

## Inspect without starting the solver

```powershell
.\.venv\Scripts\python.exe workflow\verify_project.py
.\.venv\Scripts\python.exe workflow\cfd.py status
```

The integrity command checks the complete selected-file inventory, report source/PDF, numerical-table hashes and movie hash. Add `--native` to verify the separately supplied native case/data collection. With local native data, status values come from saved records. In a source-only clone, status reads the published eight-run summary. They do not establish that a solver process is currently running or that the recorded MPI count is a live process measurement.

## Install the native-data assets

Download the native inputs and results matching the source version from [Releases](https://github.com/lorenzoproli/axial-turbine-stage-2d-cfd-pyfluent/releases). Keep the ZIPs outside the repository. The exact names, sizes and SHA256 values are in [config/release_assets.json](../config/release_assets.json).

- Native inputs: 100 files, about 340 MB compressed. Required to prepare a new single-mesh study, reopen the baseline or regenerate the mesh family.
- Native results: 954 files, about 881 MB compressed. Add these to regenerate accepted analyses and inspect final native fields.

In the following example, replace the archive paths with the actual download locations:

~~~powershell
.\.venv\Scripts\python.exe workflow\native_data.py --kind inputs --archive ..\axial-turbine-stage-2d-cfd-v1.1.0-native-inputs.zip
.\.venv\Scripts\python.exe workflow\native_data.py --kind results --archive ..\axial-turbine-stage-2d-cfd-v1.1.0-native-results.zip
.\.venv\Scripts\python.exe workflow\verify_project.py --native
~~~

The installer verifies the complete ZIP and every payload against the versioned index before extraction. It rejects unexpected members, path traversal, changed payloads and existing different files. Identical installed files are reused. Add --check-only to inspect an archive without extracting it. Both assets together restore all 1,054 indexed native files; the verifier also opens the 18 baseline/final HDF5 case/data files.

The collection contains coherent checkpoints, accepted monitor ranges, phase and wall exports, quality arrays and the portable Workbench projects. Historical solver logs retain their original paths for provenance; the workflow resolves operational paths through the current relative mapping. No differently timed checkpoint is substituted under a missing filename.

The dense 1,201-PNG Mach sequence is not included in these numerical assets. The verified MP4 and frame-checksum index are supplied in the source tree. Re-encoding that exact movie needs the separately archived PNGs; a final checkpoint cannot reconstruct a transient sequence.

Complete Workbench projects retain their project file and associated directory together. For remeshing, see the independent meshing route below.

## Regenerate analyses

For a supplied M3 native run collection:

```powershell
.\.venv\Scripts\python.exe workflow\cfd.py analyse --id M3_HYBRID35
```

Other accepted identifiers are `ITER30`, `ITER60`, `T100`, `T200`, `T400`, `M1_HYBRID35` and `M2_HYBRID35`. The legacy `HYBRID35` suffix is a stable run identifier: M2 actually reached 40 periods. Actual final step/time and the run summary determine duration.

Analysis writes derived outputs under `runs/analysis/` and figure outputs under `results/figures/`. Use a separate work copy when reproducing a published result. The legacy ITER30 analysis automatically joins its original and 24-process restart monitors at the recorded accepted boundary. Confirm the source segment boundaries before comparing a regenerated table with the report; accepted restart segments and final statistical windows are essential inputs.

The source-only clone has no native histories. Install both assets before regeneration. Offline analysis does not require an ANSYS licence; numerical calculation does.

## Export numerical tables

After installing both native datasets, run:

~~~powershell
.\.venv\Scripts\python.exe -B tools\export_results.py
~~~

The exporter reads the accepted monitor histories, mesh-quality arrays and saved sensitivity records, and writes the English CSV/JSON tables in results/. Use a separate work copy for regenerated outputs.

## Rebuild the report

The manuscript is a self-contained LaTeX project under `docs/report/`.

```powershell
.\.venv\Scripts\python.exe workflow\cfd.py report
```

The report compiler requires `pdflatex`; PDF page rendering requires Poppler's `pdftoppm`. Install these tools separately and make them available through the configured executable paths or `PATH`. Compilation starts no solver. The --render option saves page previews under .build/report_review/. Tables, figures, captions and page breaks can then be inspected before using the rebuilt PDF.

## Campaign state and restarts

`config/campaign_state.json` records a closed campaign and guards numerical launches. It is part of the execution policy and must not be removed during packaging or cleanup. The delivered dataset ends at M1 = 35T, M2 = 40T and M3 = 35T; no automatic extension is scheduled.

Any future numerical continuation requires a separately defined study and a verified native restart. Retain the existing physical clock, rotor coordinates and second-order time-history arrays. Fresh initialization is a different experiment, requiring restored initial rotor geometry and a separate output directory. Do not merge such a new history into an existing accepted run.

## Prepare and execute an independent study

The historical campaign remains closed. Do not delete its state guard or overwrite its results. Use the following commands from the source root after installing the inputs asset:

~~~powershell
# Read-only preflight; verifies the selected native inputs.
.\.venv\Scripts\python.exe workflow\create_study.py --mesh M1 --name my-m1 --periods 35

# Create an independent work copy; this still starts no solver.
.\.venv\Scripts\python.exe workflow\create_study.py --mesh M1 --name my-m1 --periods 35 --prepare

# Check the prepared workspace.
.\.venv\Scripts\python.exe runs\new_studies\my-m1\workflow\run_hybrid35_campaign.py --check-inputs

# Explicitly start exactly one calculation.
.\.venv\Scripts\python.exe runs\new_studies\my-m1\workflow\run_hybrid35_campaign.py --only M1_HYBRID35
~~~

Use M2/M3 and a different study name for the other meshes. Durations of 4 to 100 complete periods are accepted; the last three periods are analysed. A short run is a technical trial and does not establish settled statistics. The default is 35 periods. The recorded M2 comparison used 40.

The new workspace is under runs/new_studies/NAME and contains private copies of its required inputs, code and configuration. It reloads the exact verified original-position Hybrid case/data at t=0; Hybrid is not applied a second time, no historical developed field is interpolated, and the rotor clock/geometry are not reset independently. The saved initialization receipt records how the supplied field was obtained.

The default configuration uses Fluent 2024 R2, planar double precision, 24 MPI processes, T/400 and 30 inner iterations. A valid licence with 24-process entitlement and sufficient hardware is required. The controller rejects another active 2D double-precision Fluent solver. It processes only the selected mesh and never starts the next mesh or extends the run automatically.

Default output includes per-step numerical monitors, health checks, periodic coherent case/data checkpoints and four phase samples per period over the final three periods. Native image capture is disabled to avoid imposing its cost on numerical reproduction. Rendering modules and the original capture settings are retained for a separately configured, visually verified rendering run.

For a controlled stop, place STOP_AFTER_BATCH.txt under the prepared workspace's runs/adapted_mesh directory. Remove it only when ready to resume. Reissue the same --only command to resume a stopped/interrupted run; checkpoint hashes, time and moving geometry are verified before advancing, and monitor segments remain separate. Completed runs are preserved. A power-loss recovery requires a saved checkpoint and a restartable state; inspect progress.json before resuming rather than changing its step count manually.

For new adapted-mesh timestep/iteration comparisons, use a separate work copy and the supplied common checkpoint with the recorded workflow_config.json. The independent helper currently targets the systematic M1/M2/M3 family; it does not automatically launch the adapted-mesh comparison campaign.

## Recreate the mesh family

The inputs asset includes inputs/workbench/mesh_family_template.wbpz. The recorded STEP, sizing controls and Meshing template are in geometry/. To prepare a new Workbench journal without running Meshing:

~~~powershell
.\.venv\Scripts\python.exe workflow\generate_mesh_family.py --output runs\new_mesh_family
~~~

The journal is written into that new directory. The historical execute shortcut remains guarded; run the prepared journal explicitly through Workbench/Meshing 2024 R2 in a separate session if remeshing is required. This starts a new commercial meshing operation, not an offline analysis. Recheck named zones, cell counts, wall layers, quality, periodicity and the interface before substituting a generated mesh into a new simulation. The supplied raw meshes and initialized cases allow reuse without remeshing.

## Requirements and troubleshooting

- A source-only clone supports integrity, saved status, tests and report inspection.
- Both native assets are required to regenerate the accepted monitor, wall and field analyses.
- The independent-study helper prepares the supplied systematic meshes. Timestep/iteration comparisons and native animation capture require their respective configurations, as described above.
- A missing archive or input is reported explicitly. Do not rename another checkpoint to satisfy it.
- Import errors: use the same Python executable used for installation, then run python -m pip check.
- Fluent launch/licence errors: confirm the installed 24.2 executable and 24-process entitlement. Do not connect to or stop another person's session.
- Report tools: call workflow/compile_report.py --compiler PATH --pdftoppm PATH --render, or forward these options through workflow/cfd.py report. Explicit paths support tools installed outside PATH.
- Native execution and the complete lock file target Windows/Python 3.12 and Fluent 2024 R2.

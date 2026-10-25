# Reproduction and data requirements

## What is supplied

The repository contains the Python workflow, recorded configurations, reference geometry material, selected numerical evidence, figures, movies and an editable report. Complete native Fluent/Workbench input and result collections are maintained separately because of their size and software-specific dependencies.

Three operations have different requirements:

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
- 24 MPI processes per solver calculation. The recorded machine has an Intel Core i9-14900K and approximately 64 GiB RAM; no core-affinity optimisation is claimed.
- ANSYS Workbench/Meshing are additionally required to reproduce the recorded commercial meshing procedure.

## Create an environment

Run from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

The Python environment and commercial applications are not redistributed. A valid Fluent licence with the necessary parallel entitlement is required for native computation. The direct requirements retain the numerical package versions used by the workflow. `requirements-lock.txt` records the isolated Windows environment tested for the supplied offline analyses. Compatibility with other releases has not been established.

## Inspect without starting the solver

```powershell
.\.venv\Scripts\python.exe workflow\verify_project.py
.\.venv\Scripts\python.exe workflow\cfd.py status
```

The integrity command checks supplied content. Add `--native` to verify the separately supplied native case/data collection. Status values come from saved records. They do not establish that a solver process is currently running or that the recorded MPI count is a live process measurement.

## Supply native inputs

Populate the ignored local `inputs/` and `runs/` directories using the collection mapped by the current configuration and data indices. Preserve coherent case/data pairs, accepted segment bounds, wall exports, phase samples and SHA256 associations. The directory containing a run is a dependency unit, not a collection of interchangeable files.

The native collection must provide, as applicable:

1. The unchanged historical reference case/data at 0.010653 s and its initial-position geometry reference.
2. The common checkpoint and final accepted ITER30, ITER60, T100, T200 and T400 records.
3. Authoritative M1/M2/M3 meshes, original-position Hybrid initial states and final accepted case/data.
4. Native monitor segments with their exact accepted ranges and exported statistical/phase samples.
5. Wall, quality and rendering data required by the specific regeneration operation.

Complete Workbench projects must retain their project file and associated directory together. Absolute external CAD references need a verified portable copy; editing binary project files as text is not a portability method.

## Regenerate analyses

For a supplied M3 native run collection:

```powershell
.\.venv\Scripts\python.exe workflow\cfd.py analyse --id M3_HYBRID35
```

Other accepted identifiers are `ITER30`, `ITER60`, `T100`, `T200`, `T400`, `M1_HYBRID35` and `M2_HYBRID35`. The legacy `HYBRID35` suffix is a stable run identifier: M2 actually reached 40 periods. Actual final step/time and the run summary determine duration.

Analysis can write derived outputs. Use a separate work copy when reproducing a published result. Confirm the source segment boundaries before comparing a regenerated table with the report; accepted restart segments and final statistical windows are essential inputs.

Full native-data regeneration from a clone alone has not been demonstrated. The separately maintained data and ANSYS dependencies must first be restored and verified. Archived dense animation frames are required for re-encoding the delivered movie; a final checkpoint alone cannot reconstruct a transient sequence.

## Rebuild the report

The manuscript is a self-contained LaTeX project under `docs/report/`.

```powershell
.\.venv\Scripts\python.exe workflow\cfd.py report
```

The report compiler requires `pdflatex`; PDF page rendering requires Poppler's `pdftoppm`. Install these tools separately and make them available through the configured executable paths or `PATH`. Compilation starts no solver. Review the rendered pages after changes, including equations, tables, figure labels, captions and page breaks. Successful LaTeX compilation alone does not certify numerical content or visual quality.

## Campaign state and restarts

`config/campaign_state.json` records a closed campaign and guards numerical launches. It is part of the execution policy and must not be removed during packaging or cleanup. The delivered dataset ends at M1 = 35T, M2 = 40T and M3 = 35T; no automatic extension is scheduled.

Any future numerical continuation requires a separately defined study and a verified native restart. Retain the existing physical clock, rotor coordinates and second-order time-history arrays. Fresh initialization is a different experiment, requiring restored initial rotor geometry and a separate output directory. Do not merge such a new history into an existing accepted run.

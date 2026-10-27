# Axial Turbine Stage 2D CFD with PyFluent

**Lorenzo Proli** · ANSYS Fluent 2024 R2 · Python 3.12 · Planar, double-precision URANS

A configuration-driven workflow for a translating rotor, a stationary blade row and their unsteady interaction. The project combines native Fluent restart checks, systematic mesh generation, cycle-resolved numerical assessment and fixed-scale flow visualisation.

Across M2 and M3, the monitored cycle means differ by less than 0.15%, while peak-to-peak amplitudes differ by approximately 5.9-7.5%. The study combines these results with mass-conservation checks, blade-pressure distributions, wall resolution and phase-resolved flow visualisation. Numerical limitations are documented alongside the results.

## Start here

- [Technical report](docs/report/axial_turbine_stage_2d_report.pdf)
- [Methodology and numerical conventions](docs/methodology.md)
- [Reproduction instructions](docs/reproduction.md)
- [Results and accepted run summaries](results/)
- [Limitations and interpretation](docs/limitations.md)
- [References](docs/references.md) and [third-party notices](NOTICE.md)

## Study design

Three datasets are kept separate:

| Dataset | Purpose | Mesh and initial field |
|---|---|---|
| Historical baseline | Preserve the original manually developed setup and saved solution | Historical baseline mesh; coherent case/data at 0.010653 s |
| Baseline-mesh reproduction | Examine restart, inner-iteration and timestep sensitivity | The same baseline topology held fixed; common native checkpoint |
| Systematic mesh campaign | Examine sensitivity to independently controlled mesh resolution | M1/M2/M3 from the same geometry; original rotor position restored before fresh Hybrid Initialization |

The baseline and the systematically generated M1/M2/M3 meshes are separate datasets. All reported comparisons retain fixed topology, with automatic mesh adaptation disabled.

## Recorded campaign

| Run | Active cells | Time increment | Inner iterations | Simulated duration | Final interpretation |
|---|---:|---:|---:|---|---|
| ITER30 / ITER60 | 289,671 | 3.0e-6 s | 30 / 60 | 596 steps each from the common checkpoint | Iteration sensitivity assessed on the baseline mesh |
| T100 | 289,671 | 2.97583785e-6 s | 30 | 600 steps from the common checkpoint | Temporal sensitivity dataset |
| T200 | 289,671 | 1.487918925e-6 s | 30 | 1,200 steps from the common checkpoint | Temporal sensitivity dataset |
| T400 | 289,671 | 7.439594625e-7 s | 30 | 2,400 steps from the common checkpoint | Temporal independence not established |
| M1 | 54,287 | 7.439594625e-7 s | 30 | 35 periods / 14,000 steps | Configured operational settling checks passed |
| M2 | 104,831 | 7.439594625e-7 s | 30 | 40 periods / 16,000 steps | Inlet-flow amplitude recurrence criterion not passed |
| M3 | 196,569 | 7.439594625e-7 s | 30 | 35 periods / 14,000 steps | Rotor-force amplitude recurrence criterion not passed |

The systematic mesh campaign used **24 MPI processes**, planar 2D and double precision. ITER30 initially used 8 processes during its first 240 settling steps and continued with 24; this distinction is recorded in the report. The pitch is 0.04463756775 m, rotor mesh velocity is -150 m/s in Y, and the blade-passing period is `T = 2.97583785e-4 s`. Systematic runs therefore use 400 steps per period. Reference depth is 1 m.

The historical baseline contains 361,839 stored cells: 289,671 active cells and 72,168 inactive parent cells. Stored and active cell counts describe different quantities.

### What the comparisons show

- M2–M3 mean differences are below 0.15% for rotor tangential force, inlet/outlet mass flow and outlet mass-weighted total pressure.
- Their peak-to-peak amplitude differences remain approximately 5.9–7.5%.
- Three-mesh mean trends are nonmonotonic, and the final three-cycle settling criteria are not all satisfied on M2/M3.
- General grid independence, timestep independence, an observed convergence order and GCI were **not established**. This is a numerical reference study, without experimental validation.

Complete-cycle statistics, mass-storage conservation, phase recurrence and wall-resolution checks are discussed in the report. Residuals and elapsed periods alone are not treated as convergence evidence.

## Workflow

```text
Verified native case and geometry
              |
              v
Mesh / rotor-position / initialization checks
              |
              v
Isolated Fluent calculation and coherent checkpoints
              |
              v
Accepted monitor segments and phase-matched exports
              |
              v
Cycle statistics, conservation and numerical sensitivity
              |
              v
Figures, fixed-scale animation and numerical tables
```

## Repository layout

```text
config/       Recorded numerical, rendering and campaign-state configuration
geometry/     Geometry definitions, meshing inputs and attributed SU2 reference
workflow/     Python entry points and supporting modules
results/      Selected numerical evidence, figures and movies
docs/         Method, reproduction guide, limitations and final PDF report
tests/        Offline portability, restart-analysis and packaging checks
tools/        Verified export of English numerical tables
inputs/       Local native input data; excluded from Git
runs/         Local solver histories, checkpoints and field exports; excluded from Git
```

The lightweight repository does not include the Python environment, commercial applications, complete Workbench databases or large Fluent case/data files. Native data are packaged as separate versioned assets. A clone supports inspection of the published evidence; native analysis regeneration requires those assets, and new numerical work additionally requires ANSYS tools and licences.

## Download and reuse

Native datasets are distributed separately from the lightweight source tree. Download the version-matched input and result archives from [v1.1.0](https://github.com/lorenzoproli/axial-turbine-stage-2d-cfd-pyfluent/releases/tag/v1.1.0). Their names, sizes and checksums are listed in [config/release_assets.json](config/release_assets.json).

| Download | Purpose |
|---|---|
| Source archive or Git clone | Workflow, configuration, geometry, selected tables/figures/movie and final PDF report |
| Native inputs (about 340 MB) | Baseline, common checkpoint, three meshes, original-position Hybrid t=0 pairs and meshing projects |
| Native results (about 881 MB) | Accepted monitors, final checkpoints, exported fields and native analysis evidence |

Install the inputs asset to prepare new calculations; install both native assets to regenerate the accepted analyses. Every file is indexed by size and SHA256. The installer preserves existing identical files and refuses different versions. See [data installation and new-study instructions](docs/reproduction.md).

## Installation and offline inspection

The recorded environment is Windows 11, Python 3.12 and Fluent 2024 R2. Direct dependencies are pinned in [requirements.txt](requirements.txt); [requirements-lock.txt](requirements-lock.txt) records the complete tested Windows analysis environment.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe workflow\verify_project.py
.\.venv\Scripts\python.exe workflow\cfd.py status
```

The verifier checks the curated files; add `--native` to verify the separate native case/data collection. `status` reads saved native records or the published run summary; it does not measure live CPU usage or start Fluent. Missing local native data must be supplied before the corresponding analyses can be regenerated.

Example analysis command:

```powershell
.\.venv\Scripts\python.exe workflow\cfd.py analyse --id M3_HYBRID35
```

Analysis requires the accepted native monitor segments and relevant exported samples. The final PDF report documents the study; document preparation is separate from the CFD workflow. See [the reproduction guide](docs/reproduction.md) for data requirements and scope.

The historical numerical campaign is closed. [config/campaign_state.json](config/campaign_state.json) protects its results and must be retained. New calculations use an independent work copy:

~~~powershell
.\.venv\Scripts\python.exe workflow\create_study.py --mesh M1 --name my-m1 --periods 35
.\.venv\Scripts\python.exe workflow\create_study.py --mesh M1 --name my-m1 --periods 35 --prepare
~~~

The first command checks inputs without writing or launching anything; the second prepares the isolated work copy. The reproduction guide gives the explicit solver and restart commands. New studies use 24 MPI processes, reload the verified Hybrid t=0 state and disable expensive image capture by default. No automatic extension is configured.

## Flow visualisation

The verified fine-mesh movie shows absolute Mach over **5T–35T**, using 1,201 native Fluent PNGs acquired every ten CFD steps. The camera and three-pitch crop remain fixed, the physical clock is displayed as `Solution time: ... s`, and the colour range is fixed at 0–1.2. Values above 1.2 saturate the upper colour; this is a display cap, not a reported physical maximum.

The 1920 × 1080, 25 FPS movie is encoded offline from the accepted frames. Playback time differs from physical simulation time. A complete verified M3 sequence from t = 0 is unavailable. The [M3 Mach movie](results/videos/m3_absolute_mach_5T_to_35T.mp4) is the sole delivered video.

## Attribution and use

The geometry and numerical reference originate from SU2 TestCases `axial_stage_2D`, attributed to S. Vitale, Delft University of Technology. Original notices and LGPL 2.1 text accompany the reference sources. This project does not redistribute ANSYS software.

Original workflow code is licensed under [MIT](LICENSE). Original report text, figures, selected numerical tables and movie presentation are licensed under [CC BY 4.0](LICENSE-CONTENT), to the extent of the rights held by the project author. SU2 source assets, derived geometry, third-party material and ANSYS software retain their separate terms. See the [licensing guide](docs/licensing.md) and [NOTICE.md](NOTICE.md) for scope and exclusions. Citation metadata are provided in [CITATION.cff](CITATION.cff).

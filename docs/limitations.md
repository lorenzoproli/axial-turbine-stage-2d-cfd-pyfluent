# Limitations and interpretation

## Numerical completion is not numerical independence

The campaign completed its recorded finite durations: M1 = 35 periods, M2 = 40 periods and M3 = 35 periods. A completed calculation, low residuals, stable means or a smooth video do not alone demonstrate a periodic solution or discretisation independence.

| Topic | Evidence and remaining limit |
|---|---|
| Historical baseline | Coherent saved reference at 0.010653 s; fixed topology and automatic adaptation disabled |
| M1 | Configured operational settling diagnostics passed over the assessed final window |
| M2 | Final inlet-flow amplitude recurrence remained outside the 5% three-cycle limit |
| M3 | Rotor-force amplitude changed by 7.068509% for cycles 33–34, then by 0.329532% for cycles 34–35; one failing pair remains |
| Inner iterations | Baseline-mesh ITER30/ITER60 comparison supports the adopted 30-iteration setting there; no separate M3 iteration-independence study |
| Time increment | T200/T400 amplitude criterion was not satisfied; general temporal independence is unconfirmed |
| Mesh sensitivity | M2–M3 means change by less than 0.15%, but amplitudes change by approximately 5.9–7.5%; three-mesh mean trends are nonmonotonic |
| Formal error estimate | No observed asymptotic order, Richardson-extrapolated result or GCI uncertainty is assigned |
| Physical validation | No experimental validation, certified turbine performance or general model-accuracy claim |

The outstanding M2/M3 cycle drift means spatial differences can contain remaining transient and sampling effects. The current data do not uniquely isolate each error source. Operational tolerances are declared diagnostics rather than universal acceptance standards.

## Geometry, mesh and model scope

The calculation is planar 2D URANS with SST turbulence modelling, periodic blade rows and a translating rotor. Spanwise structure, endwall flows, tip clearance and other three-dimensional mechanisms are outside this model.

Systematic meshes share geometry and a controlled meshing procedure, but include anisotropic wall layers. Cell count is not a sufficient description of local resolution or a proof that every region lies in an asymptotic range. Quality extrema, wall y+ and sampled field recurrence are complementary checks, not substitutes for mesh and timestep studies.

The historical baseline reference is distinct from M1/M2/M3. Inactive parent cells are excluded from active solution-cell counts. All reported runs retain fixed topology with automatic adaptation disabled.

## Quantities and normalisation

Forces and mass flow use a 1 m reference depth. Signs follow the global Y direction and inward-positive boundary-flow convention. Total pressure is mass-flow weighted. Rotor total-pressure change contains work exchange and is not itself a dissipative loss or stage-efficiency measurement.

Field-recurrence diagnostics use geometrically matched unique nodes without volume weighting. Wall y+ values and visual checks belong to the sampled times and locations; they do not prove an everywhere/every-time bound.

## Animation scope

The verified M3 Mach movie covers **5T–35T**, not the complete startup from zero. It contains 1,201 native frames acquired every ten CFD steps, encoded offline at 25 FPS and 1920 × 1080.

Camera, three-pitch crop and 0–1.2 Mach limits remain fixed. Values above 1.2 saturate the upper colour, so this visual maximum is not a measured maximum of the flow. `Solution time` displays the real Fluent clock; video playback duration is a separate quantity.

Beginning, intermediate motion and final samples were visually inspected. Such sampling does not certify every individual transition or establish periodic convergence. A complete verified t = 0 M3 sequence is unavailable. Only the fine-mesh Mach movie is included in the selected results; no systematic-campaign pressure movie is supplied.

## Availability and reproduction

Selected evidence and workflow sources are included in the repository. Large native inputs, complete solver histories and dense source-frame sequences are maintained separately. A repository clone alone does not provide all dependencies needed to rerun the numerical campaign or re-encode the selected movie. The [reproduction guide](reproduction.md) specifies the required collections.

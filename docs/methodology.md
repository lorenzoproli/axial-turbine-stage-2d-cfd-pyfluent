# Numerical methodology

## Physical problem and conventions

The model represents two planar fluid regions, one surrounding a stationary blade and one surrounding a translating rotor blade. X is axial and Y is tangential. Each row uses translational periodicity, with a nonconformal periodic sliding interface between the rows.

The pitch is 0.04463756775 m. Rotor mesh velocity is `Vy = -150 m/s`, with zero angular velocity. The blade-passing period is `T = pitch / |Vy| = 2.97583785e-4 s`. Blade walls remain stationary relative to their adjacent mesh; no additional absolute wall motion is superimposed.

Native Fluent force and mass-flow values use a 1 m reference depth. Inlet mass flow is inward-positive; outward outlet flow is negative in the same convention. Rotor force is the signed global Y force. Outlet total pressure is weighted by mass flow. Total-pressure change across a moving rotor includes work exchange and is not, by itself, a dissipative-loss measure.

## Verified setup

| Setting | Value |
|---|---|
| Solver | Fluent 2024 R2, pressure-based, planar 2D, double precision |
| Models | Unsteady RANS, SST k–omega, energy and viscous dissipation |
| Fluid | Ideal-gas air; Sutherland viscosity |
| Inlet | Total pressure 169,623.33 Pa; total temperature 305.76 K |
| Inlet turbulence | Intensity 3%; turbulent/laminar viscosity ratio 100 |
| Outlet | Static pressure 99,741 Pa |
| Operating pressure | 0 Pa |
| Walls | No slip and adiabatic |
| Coupling / gradient | PISO / least-squares cell-based |
| Discretisation | Second-order pressure and second-order upwind transported quantities |
| Time scheme | Second-order implicit |
| Parallel execution | 24 MPI processes, one solver calculation at a time |

The model is inherited from the native case and checked against saved settings. Nominal SU2 inputs are a source reference, not a substitute for inspecting the actual Fluent model. Absolute Mach was checked against velocity magnitude divided by sound speed. Native static pressure is absolute because the operating pressure is zero.

## Three separate datasets

### Historical baseline

The coherent historical case/data pair was saved at step 3,551 and physical time 0.010653 s. Its original timestep was approximately 3e-6 s. The 361,839 stored cells comprise 289,671 active cells and 72,168 inactive AMR parents.

Earlier adaptation changed the original 73,167-cell topology. Deleting the automatic criterion did not reverse that change. Automatic adaptation was subsequently disabled; the retained adapted topology is a historical property, not evidence that AMR remained active.

### Fixed adapted-mesh comparisons

ITER30 and ITER60 restart from a common checkpoint at the same physical time and rotor position, using 3e-6 s and 30/60 inner iterations. T100, T200 and T400 use `T/100`, `T/200` and `T/400`, respectively. The adapted mesh remains fixed in cell count while the rotor translates.

Post-change settling is excluded from the final comparison interval. Comparisons use complete periods and matched rotor phase. The iteration result belongs to this mesh; it is not an independent iteration study for M3.

### Systematic mesh family

M1/M2/M3 contain 54,287/104,831/196,569 active cells. All derive from the same geometry and meshing procedure. Global size, blade spacing and first-layer height are refined together; inflation thickness is approximately maintained. The family is anisotropic, so a cell-count ratio alone does not prove an asymptotic refinement sequence.

Each calculation starts from fresh Hybrid Initialization after restoring the actual original rotor geometry. Merely setting the clock to zero is insufficient to restore mesh position. The timestep is `T/400 = 7.439594625e-7 s`, with 30 inner iterations. Durations are 35, 40 and 35 periods for M1, M2 and M3.

## Accepted monitor histories

Native monitor segments are merged using recorded physical-time bounds. Duplicated restart samples, uncommitted tails and separate graphics-replay histories are excluded. Segment provenance is preserved so a restarted run does not become an apparently uninterrupted series by accident.

The primary integral quantities are rotor tangential force, inlet mass flow, outlet mass flow and outlet mass-weighted total pressure. Final assessment uses three complete consecutive periods, comparing means, peak-to-peak amplitudes and phase-resolved waveforms. Operational limits are 0.5% for successive-cycle mean changes, 5% for amplitude changes and 10% of amplitude for phase-profile RMS differences. They are diagnostic criteria, not universal accuracy bounds.

Physical rotor phase is checked geometrically. An integer-pitch wrap is compatible with periodic geometry; the phase `t/T modulo 1` alone does not identify the original CAD position. Field recurrence uses geometrically matched unique nodes and is not volume-weighted.

## Conservation and wall resolution

Both signed boundary mass flux and change in domain mass are examined. For the inward-positive boundary convention, the transient storage term must be included before interpreting a nonzero instantaneous inlet-plus-outlet sum as a conservation error. Cycle-integrated storage and flux provide a separate conservation assessment.

Mesh assessment includes active-cell quality distributions, positive volumes, orthogonal quality, aspect ratio, skewness and blade/interface views. High-aspect-ratio wall cells are examined in context rather than accepted from a single maximum value. Native wall y+ and static-pressure exports are checked separately on stator and rotor blades. Sampled wall resolution does not establish accuracy at every time and location.

## Sensitivity and interpretation

Time- and mesh-sensitivity comparisons use equivalent full-cycle windows and matched phase. Remaining transient evolution, iterative error and sampling variability can influence the differences. Nonmonotonic three-mesh trends and unresolved cycle-amplitude drift prevent an observed-order or GCI estimate in this dataset.

The final M2–M3 means differ by less than 0.15% for all four monitors, but amplitudes differ by approximately 5.9–7.5%. Small mean differences therefore do not establish independence of the unsteady solution.

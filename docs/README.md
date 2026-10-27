# Documentation

The documentation explains the completed numerical study, how its evidence is organised and which parts can be reproduced from the available data.

| Document | Contents |
|---|---|
| [Technical report](report/axial_turbine_stage_2d_report.pdf) | Full geometry, setup, mesh, restart, monitor, sensitivity and visualisation assessment |
| [Editable report](report/main.tex) | LaTeX manuscript with the required image assets in the same project |
| [Methodology](methodology.md) | Dataset separation, physical conventions, cycle statistics and conservation |
| [Reproduction](reproduction.md) | Environment, commands, release assets, verified installation and independent-study commands |
| [Limitations](limitations.md) | Interpretation of the numerical and visual results; claims not supported by the data |
| [References](references.md) | SU2 source provenance and official solver/numerical-method references |
| [Release verification](release_verification.md) | Installation, restored-data analysis and independent-study test coverage |
| [Licensing](licensing.md) | MIT software scope, CC BY publication content and third-party exclusions |

The report and repository describe the historical baseline, fixed adapted-mesh comparisons and systematic mesh family as separate datasets. Figures are in English and are associated with recorded solution times and run identifiers. Native checkpoint and monitor data are held separately from the lightweight repository.

The campaign is complete as a finite-duration study. Completion does not imply that every convergence criterion was satisfied. The unresolved periodicity, timestep and grid-sensitivity findings are part of the result.

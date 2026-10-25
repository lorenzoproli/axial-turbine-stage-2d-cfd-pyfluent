# Copyright and third-party notices

Copyright © 2026 Lorenzo Proli for the original workflow, documentation, figures and numerical results, except where a different source or author is identified.

No general redistribution or reuse licence has been assigned to these original contributions. The availability of this repository does not assign the SU2 licence, a commercial-software licence or another project's licence to the complete work.

## SU2 reference material

The geometry and numerical reference derive from SU2 TestCases `turbomachinery/axial_stage_2D`. The retained configuration headers identify **S. Vitale, Delft University of Technology, 28 February 2017**, with file version 8.5.0 Harrier.

Original attribution and the retained GNU LGPL 2.1 text accompany the reference material under `geometry/reference/`. These notices apply to their respective third-party sources and are preserved independently of the original project contributions. Reference configurations are numerical source material, not Fluent results or experimental validation.

Source links and interpretation are recorded in [docs/references.md](docs/references.md).

## Commercial software

ANSYS Fluent, Workbench, Meshing and related vendor applications are not redistributed. Executing the native workflow requires separately installed, appropriately licensed ANSYS products. No licence to ANSYS software, trademarks, documentation or other vendor material is granted by this repository.

Large native project and solver data are maintained separately from the lightweight code/documentation repository. Their availability is not a grant of rights over vendor software.

## Python dependencies

Third-party packages are installed from their declared sources using the pinned `requirements.txt`. The Python environment, package executables and installed dependency trees are not included in the repository. Each dependency remains subject to its own licence and copyright notices; the project copyright does not replace those terms.

## Numerical interpretation

The supplied results document the stated model, software versions, inputs and finite simulation intervals. They do not constitute experimental validation or certified engineering data. The specific unresolved numerical findings are retained in [docs/limitations.md](docs/limitations.md) and the technical report.

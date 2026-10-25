# Copyright, licensing and third-party notices

Copyright (c) 2026 Lorenzo Proli for the original contributions, except where another source or author is identified.

## Original software: MIT

Original Python code in `workflow/`, `tools/` and `tests/`, original workflow configuration in `config/`, and the original meshing-control script/template in `geometry/meshing_inputs/` are licensed under the [MIT License](LICENSE).

## Original publication content: CC BY 4.0

Original report text and LaTeX sources, explanatory documentation, figures, selected numerical tables and the supplied movie are licensed under [Creative Commons Attribution 4.0 International](LICENSE-CONTENT), to the extent of the rights held by the project author. Credit Lorenzo Proli, link to the repository and licence, and identify modifications as required by that licence.

The licences apply to different material; they are not an option to relicense every file under either licence. The [licensing guide](docs/licensing.md) records the scope and exceptions.

## SU2 reference and derived geometry

The numerical reference originates from SU2 `turbomachinery/axial_stage_2D`. Retained configuration headers identify **S. Vitale, Delft University of Technology, 28 February 2017**, file version 8.5.0 Harrier.

The original reference configurations, mesh, author headers and [upstream LGPL 2.1 text](geometry/reference/COPYING.LGPL-2.1) remain together under `geometry/reference/`, with [source URLs and checksums](geometry/reference/source_manifest.json). These source assets and the SU2-derived `geometry/axial_stage_surfaces.step` are excluded from the new MIT and CC BY grants. Retained upstream terms and rights continue to apply; this project does not replace or expand them. The same exclusion applies to underlying third-party geometry represented in figures and video. CC BY covers the original presentation and numerical-analysis contributions, not a new grant over someone else's source material.

## Commercial software and external native data

ANSYS Fluent, Workbench, Meshing and related applications are not redistributed or relicensed. Their names and interfaces identify the tools used. A valid, separately obtained ANSYS installation and licence remain necessary for native execution. No ANSYS software, trademark or vendor-documentation rights are granted by this repository.

Large native collections in local `inputs/` and `runs/`, complete Workbench projects and installed environments are not part of the lightweight Git distribution and are not automatically licensed by the two new files. Separately supplied collections must retain their own provenance and applicable terms.

## Python and encoding dependencies

Dependencies are installed separately from the pinned requirements. Their own licences and bundled-component notices remain applicable; the project MIT and CC BY grants do not replace them. The installed environment, package wheels and FFmpeg executable are not redistributed in this repository. Direct-package licence declarations are summarised in the [licensing guide](docs/licensing.md).

## Numerical interpretation

The results document the stated model, software versions and finite simulation intervals. Licences do not turn the results into experimental validation, certified engineering data or a warranty of numerical accuracy. Unresolved findings remain explicit in the [limitations](docs/limitations.md) and report.

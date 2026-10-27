# Licensing and reuse

The project separates its software licence from its publication-content licence. Copyright (c) 2026 Lorenzo Proli applies to original contributions; original third-party notices remain in force.

## Scope

| Material | Applicable terms |
|---|---|
| Original code in `workflow/`, `tools/`, `tests/`; original configuration in `config/`; original meshing-control code/template | [MIT](../LICENSE) |
| Original README and documentation prose; report PDF; original figures, selected numerical tables and movie presentation | [CC BY 4.0](../LICENSE-CONTENT), only for rights held by the project author |
| SU2 reference configurations and mesh in `geometry/reference/` | Retained upstream terms and [LGPL 2.1 text](../geometry/reference/COPYING.LGPL-2.1); see the [source record](../geometry/reference/SOURCE.md) |
| SU2-derived `geometry/axial_stage_surfaces.step` and underlying source geometry represented in figures/video | Outside the new MIT/CC BY grants; source attribution and applicable upstream rights are retained |
| Third-party licence texts and notices | Their own terms; do not replace the original text with the project licence |
| Versioned native release assets | Original simulation outputs/documentation: CC BY 4.0 within the author's rights; SU2-derived geometry and third-party rights remain separate. See NATIVE_DATA_LICENSE.md inside each asset. |
| Native material outside the versioned assets; commercial applications | Outside the release-content grant; preserve applicable source and vendor terms |

An individual file or upstream notice takes precedence over the general category. These licences cover different contributions; they are not a blanket dual-licensing option for the entire repository.

## Reusing original contributions

For original software, retain the copyright and MIT permission notice when distributing copies or substantial portions. The [complete MIT text](../LICENSE) defines the permissions and conditions.

For original publication content, credit Lorenzo Proli, link to the repository and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), and indicate changes. Both selected licences permit commercial reuse subject to their terms. Neither grants rights over separately identified third-party material, trademarks or commercial software. Rights not held by the author are not granted. Existing public-domain status and applicable exceptions are unaffected.

Suggested attribution:

> Lorenzo Proli, Axial Turbine Stage 2D CFD with PyFluent, https://github.com/lorenzoproli/axial-turbine-stage-2d-cfd-pyfluent. Original publication content: CC BY 4.0. Modifications should be identified; separately attributed material retains its own terms.

Citation metadata are in [CITATION.cff](../CITATION.cff). Its MIT identifier refers to the software; report and media content use the separately stated CC BY terms.

## Separately installed direct dependencies

The following declarations were checked against the installed package metadata for the recorded environment. They identify the primary package terms; bundled components can have additional notices. This table is not a relicensing of dependencies or an inventory of every transitive component. The complete installed versions are recorded in [requirements-lock.txt](../requirements-lock.txt).

| Direct dependency | Recorded version | Declared package licence |
|---|---|---|
| ansys-fluent-core | 0.42.2 | MIT |
| ansys-api-fluent | 0.7.0 | Apache-2.0 |
| NumPy | 2.3.3 | BSD-3-Clause; retain bundled-component notices |
| SciPy | 1.16.3 | BSD-3-Clause; retain bundled-component notices |
| Matplotlib | 3.10.7 | Matplotlib licence agreement, based on the PSF licence |
| h5py | 3.16.0 | BSD-3-Clause |
| imageio-ffmpeg | 0.6.0 | BSD-2-Clause for the Python wrapper; FFmpeg has separate build-dependent terms |
| Pillow | 11.3.0 | MIT-CMU |

Python packages and executables are installed separately rather than bundled in the repository. In particular, [FFmpeg's own licensing information](https://ffmpeg.org/legal.html) describes the terms for its executable and optional components. ANSYS application licences are separate from the open-source PyFluent interface licence.

## Authoritative texts and source notices

- [MIT, Open Source Initiative](https://opensource.org/license/mit).
- [CC BY 4.0 deed](https://creativecommons.org/licenses/by/4.0/) and [complete legal code](https://creativecommons.org/licenses/by/4.0/legalcode.txt).
- [Retained SU2 attribution and source checksums](../geometry/reference/source_manifest.json).
- [Project copyright and exclusions](../NOTICE.md).

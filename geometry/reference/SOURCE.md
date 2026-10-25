# Numerical reference sources

The source headers attribute S. Vitale, Delft University of Technology, 28 February 2017, file version 8.5.0 Harrier.

| Retained file | Official source |
|---|---|
| `stage.cfg` | SU2 `TestCases/turbomachinery/axial_stage_2D/Axial_stage2D.cfg` |
| `zone_1.cfg`, `zone_2.cfg` | The same SU2 configuration directory |
| `mesh_axial_stage_2d_turb.su2` | SU2 TestCases mesh repository, `turbomachinery/axial_stage_2D/` |
| `COPYING.LGPL-2.1` | Original upstream LGPL 2.1 text |

[File sources and SHA256](source_manifest.json) identify the exact retained payloads. All five files match the checked official sources byte for byte. The mesh keeps its upstream filename so `MESH_FILENAME` in the unmodified reference configuration resolves correctly. `stage.cfg` is the English local name of `Axial_stage2D.cfg`.

- [Official mesh repository](https://github.com/su2code/TestCases/tree/master/turbomachinery/axial_stage_2D)
- [Official configuration directory](https://github.com/su2code/SU2/tree/master/TestCases/turbomachinery/axial_stage_2D)

These files document the numerical reference. The Fluent model reads the separately verified native case and systematic meshes; its physical settings are not inferred from nominal SU2 values. The study is not experimental validation. Original author headers and licence text remain unchanged.

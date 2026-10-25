# Analysis geometry and meshing inputs

The final geometry used for this study is supplied in `axial_stage_surfaces.step`. It contains two planar fluid surfaces: one stator passage and one rotor passage. The same geometry is used for the M1/M2/M3 systematic mesh family.

| Item | Role in the CFD study |
|---|---|
| `axial_stage_surfaces.step` | Final geometry used by the recorded ANSYS model |
| `meshing_inputs/` | Systematic-family sizing controls and ANSYS Meshing template |
| `reference/` | Attributed SU2 numerical reference, original configurations and licence text |

## Domain and motion

The model lies in the XY plane: X is axial and Y is tangential. The pitch is 0.04463756775 m. Each blade row has translational periodicity, and the two fluid regions meet at a nonconformal sliding interface. The stator is fixed; the rotor mesh translates at -150 m/s in Y. Blade walls are stationary relative to the adjacent mesh.

The actual original rotor position is restored before fresh Hybrid Initialization. This physical phase check is separate from periodic display copies and from setting the simulation clock to zero.

## Numerical inputs

The authoritative systematic meshes are supplied separately as `inputs/meshes/M1_systematic.msh`, `M2_systematic.msh` and `M3_systematic.msh`. The native SpaceClaim geometry and portable Workbench meshing template are local inputs excluded from Git. The historical adapted mesh is a separate dataset.

`workflow/generate_mesh_family.py` uses the supplied geometry, recorded controls and Workbench template. See [reproduction requirements](../docs/reproduction.md) and [mesh-quality results](../results/mesh_quality/README.md).

## Source rights

The SU2 reference and source-derived STEP retain their provenance and applicable upstream terms. They are excluded from the new MIT/CC BY grants for original software and publication contributions. See [licensing scope](../docs/licensing.md) and [third-party notices](../NOTICE.md).

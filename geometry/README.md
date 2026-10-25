# Geometry and meshing sources

The geometry is derived from the public SU2 `axial_stage_2D` reference. Source attribution and licence text are retained in [reference/](reference/SOURCE.md).

| Directory | Role |
|---|---|
| `coordinates/` | Metre-based boundary coordinates, a geometry-only Gmsh file and the reference preview |
| `reference/` | Attributed original SU2 mesh/configurations and LGPL text |
| `meshing_inputs/` | Recorded systematic-family controls and the ANSYS Meshing template |
| `tools/` | Optional geometry extraction and STEP reconstruction utilities |

The translating rotor uses a pitch of 0.04463756775 m. The source rotor domain is shifted by -0.022759702525 m in Y to align the interface. This CAD alignment is distinct from restoring the physical initial rotor phase before Hybrid Initialization.

The authoritative systematic meshes are supplied separately as `inputs/meshes/M1_systematic.msh`, `M2_systematic.msh` and `M3_systematic.msh`. The native SpaceClaim geometry and Workbench meshing template are local inputs. No AMR-generated mesh is substituted for this systematic family.

## Regeneration

`workflow/generate_mesh_family.py --output runs/new_mesh_family` prepares a Workbench journal in a new directory. `--execute` would require ANSYS Workbench/Meshing and an explicitly reopened numerical study; the delivered campaign is closed. This command was checked offline for input resolution; meshing was not rerun during the final review.

The optional source-geometry utilities accept explicit, previously unused output paths:

```powershell
python geometry/tools/extract_geometry.py --output runs/geometry_extraction
python geometry/tools/create_clean_step.py --output runs/geometry_reconstruction/stage_surfaces.step
```

Extraction additionally requires `ezdxf`; STEP construction requires `cadquery` and its OpenCascade bindings. These optional utilities are outside the pinned analysis environment and were syntax-checked, not numerically regenerated for this delivery. Their new output must be compared with the supplied authoritative geometry before use in a new study.

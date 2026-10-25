# References and source provenance

## Geometry and numerical reference

**S. Vitale, Delft University of Technology.** SU2 `axial_stage_2D` numerical test case. The retained configuration headers are dated 28 February 2017 and identify file version 8.5.0, Harrier.

- [SU2 TestCases: axial_stage_2D](https://github.com/su2code/TestCases/tree/master/turbomachinery/axial_stage_2D)
- [SU2 configuration source location](https://github.com/su2code/SU2/tree/master/TestCases/turbomachinery/axial_stage_2D)
- [Local reference material and original licence](../geometry/reference/)

The Fluent geometry was reconstructed from this numerical reference. SU2 configuration values and the actually verified Fluent settings are distinguished in the report. The reference is not an experimental dataset. Original author headers and the retained LGPL 2.1 text remain with redistributed reference sources; see [NOTICE.md](../NOTICE.md).

## Solver and Python interface

**ANSYS. Fluent User's Guide, Release 2024 R2.** Version-specific documentation for the commercial solver used in the campaign.

- [Hybrid Initialization](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_sec_init_hybrid.html)
- [Mesh modification](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_GridModify.html)
- [Native mesh-to-mesh interpolation](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_Grid_to_Grid.html)

Access to some vendor documentation may require an ANSYS account. Referencing an interpolation facility does not imply its use for the final systematic Hybrid starts; these used restored original rotor coordinates and fresh initialization.

**PyAnsys. PyFluent documentation.** Official Python interface documentation. The campaign used `ansys-fluent-core==0.42.2`, `ansys-api-fluent==0.7.0` and generated interfaces for Fluent 2024 R2; the current documentation landing page may describe another release.

- [Official PyFluent documentation](https://fluent.docs.pyansys.com/)
- [PyFluent source repository](https://github.com/ansys/pyfluent)

## Numerical verification framework

**NASA NPARC Alliance, CFD Verification and Validation Tutorial.** These references inform the distinction between checking numerical results, assessing discretisation sensitivity and validating a physical model.

- [Verification Assessment](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html)
- [Examining Spatial (Grid) Convergence](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html)

Three mesh levels do not automatically justify an observed order or GCI value. The present finite-duration data retain nonmonotonic mean trends and incomplete temporal/periodic settling; no formal GCI estimate is reported.

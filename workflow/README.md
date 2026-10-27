# Workflow modules

The historical-analysis entry point is `cfd.py`; run commands from the repository root. The delivered numerical campaign is closed. Importing path/status modules or running offline verification does not start Fluent.

| Function | Modules |
|---|---|
| Paths, integrity and run records | `common.py`, `registry.py`, `monitor_paths.py` |
| Environment/session and baseline checks | `cfd.py`, `verify_baseline_cli.py`, `audit_verify.py`, `smoke_test.py` |
| Meshing and geometric verification | `generate_mesh_family.py`, `verify_geometric_family.py`, `verify_restart_geometry.py` |
| Original-position initialization and controlled execution | `initial_position_hybrid.py`, `run_hybrid35_campaign.py`, `campaign_v2.py`, `verify_campaign_restart.py` |
| Native exports and checkpoints | `pipeline.py`, `solution_exports.py`, `quality_export.py`, `transcript_utils.py` |
| Monitor, cycle, wall and field analyses | `monitor_analysis.py`, `residual_analysis.py`, `wall_cycle_analysis.py`, `periodicity_diagnostic.py`, `assess_hybrid35.py`, `compare_phase_fields.py` |
| Sensitivity comparisons and figures | `compare_runs.py`, `temporal_analysis.py`, `review_grid_sensitivity_closed.py`, `plot_histories.py`, `plot_mesh_quality.py`, `mesh_visuals.py`, `plot_walls.py`, `english_labels.py` |
| Native rendering and movie verification | `native_animation.py`, `native_capture_mach_fast.py`, `native_mach_stream.py`, `legend_geometry.py`, `verify_mach_stream.py`, `render_period.py`, `export_M3_verified_clip.py` |
| Report, integrity checks and packaging | `compile_report.py`, `verify_project.py`, `package_project.py` |

See [reproduction instructions](../docs/reproduction.md) for commands and native-data requirements. `tools/export_results.py` separately verifies native monitor/quality sources and emits the English publication tables.

Numerical execution is Windows/Fluent-specific. Offline analysis uses portable project paths. Some native metadata retain their original schema and Fluent object identifiers; the public result tables provide English field names and declared units.

Outputs from a new study must use a separate directory. A differently timed checkpoint must never be renamed to satisfy a missing dependency. Native rendering preflight and a visual record tied to actual frames are required before production animation capture.

## Reuse entry points

- native_data.py: verify/install native inputs and results from versioned release assets.
- create_study.py: read-only preflight or preparation of one independent mesh study; explicit execution is optional.
- run_hybrid35_campaign.py inside a prepared workspace: single-mesh execution, checkpoint restart and final assessment.
- package_project.py: source-only archive by default; native release assets remain separate.

See the complete command sequence and test boundary in the reproduction guide. The original source root retains its closed-campaign guard.

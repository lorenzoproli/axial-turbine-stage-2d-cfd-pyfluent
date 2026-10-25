# Technical report

- `axial_turbine_stage_2d_report.pdf`: reviewed 22-page English report.
- `main.tex`: editable LaTeX source.
- `images/`: the 20 source figures used by the manuscript.
- `manifest.json`: source/PDF SHA256, compiler diagnostics and visual-review status.

The report distinguishes the historical adapted baseline, fixed-topology reproduction and systematic mesh campaign. Unresolved periodicity, timestep and grid sensitivity are stated explicitly; no GCI or experimental validation is claimed.

From the repository root, run `python workflow/compile_report.py --render` with `pdflatex` and Poppler `pdftoppm` available. Explicit `--compiler` and `--pdftoppm` paths can be supplied. Intermediate files are written under ignored `.build/`. After any manuscript or figure changes, rebuild and review the rendered pages before updating the integrity manifest.

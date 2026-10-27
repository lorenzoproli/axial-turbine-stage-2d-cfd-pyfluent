# Technical report

- `axial_turbine_stage_2d_report.pdf`: 22-page English technical report.
- `main.tex`: editable LaTeX source.
- `images/`: the 20 source figures used by the manuscript.
- `manifest.json`: report language, author, page count and source/PDF size/SHA256.

The report distinguishes the historical adapted baseline, fixed-topology reproduction and systematic mesh campaign. Unresolved periodicity, timestep and grid sensitivity are stated explicitly; no GCI or experimental validation is claimed.

From the repository root, run `python workflow/compile_report.py --render` with `pdflatex` and Poppler `pdftoppm` available. Explicit `--compiler` and `--pdftoppm` paths can be supplied. Intermediate files are written under ignored `.build/`. After manuscript or figure changes, rebuild the PDF and its page previews. Regenerate the project checksum index when distributing an updated source/PDF pair.

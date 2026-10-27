# v1.1.0 reuse verification

## Verified on Windows / Python 3.12

- A fresh virtual environment installed the complete requirements-lock.txt successfully; pip check reported no broken requirements.
- A clean source work copy installed both versioned native assets through native_data.py.
- All 1,054 native files matched their size/SHA256 index. The verifier opened 18 historical/final HDF5 case/data files.
- All 14 offline tests passed with the native collection restored. In a source-only checkout, four native-only tests are explicitly skipped.
- The eight documented monitor-analysis commands completed on the restored histories. All 92 publication-data outputs were reproduced byte-for-byte.
- Independent work copies for M1, M2 and M3 passed real-input preflight, including coherent original-position Hybrid t=0 checkpoint verification.
- Workbench mesh-family journal preparation completed without launching Meshing.
- The 22-page reviewed report, figures, scientific tables and selected Mach movie retain their accepted payloads. Report SHA256: 6573da66fbd353ca27439d187568ca6c9f6ffbcee58f5b6cdc9e7efbdf730a87.
- New native archives contain the applicable content terms and upstream notices. Commercial applications and installed environments are excluded.

## Scope

These checks establish distribution integrity, offline analysis reproduction and independent-study preparation. No new Fluent calculation was performed for this release; the new preparation wrapper has not been tested through a fresh full-duration solver calculation. Fluent 2024 R2 and a valid 24-process licence are separate requirements for execution.

The numerical conclusions are those of the recorded finite-duration campaign. The new release changes reuse and distribution, not physical parameters or numerical results. The dense Mach PNG sequence is separately archived; the source tree supplies the verified movie and its frame-checksum index.

See the [reproduction guide](reproduction.md), [licensing scope](licensing.md) and [changelog](../CHANGELOG.md).

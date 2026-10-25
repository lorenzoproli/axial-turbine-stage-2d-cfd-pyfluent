# Flow movies

| Movie | Dataset and interpretation |
|---|---|
| `m3_absolute_mach_5T_to_35T.mp4` | Systematic M3, accepted 5T-35T interval, 1201 frames, 1920x1080, 25 FPS |
| `adapted_t400_absolute_mach.mp4` | Separate fixed adapted-mesh T400 reproduction |
| `adapted_t400_absolute_pressure.mp4` | Matching T400 absolute static pressure; operating pressure is zero |

The fine-mesh movie uses native Fluent PNGs acquired every ten CFD steps: 40 intervals per blade-passing period. Physical acquisition time is distinct from video FPS. It displays three pitches, a fixed camera, the actual solution clock and a fixed Mach range of 0-1.2. Values above 1.2 saturate the upper colour. A complete verified M3 sequence from t=0 is unavailable.

The source-frame hashes and rendering configuration remain associated with the separate native collection. Re-encoding requires those archived frames; a final case/data pair cannot reconstruct an unsaved transient. No claim of periodic convergence follows from the visual appearance of a movie.

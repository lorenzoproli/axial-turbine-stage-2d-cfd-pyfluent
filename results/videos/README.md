# Selected flow movie

Only `m3_absolute_mach_5T_to_35T.mp4` is included. It belongs to the systematic fine mesh, M3: 196,569 active cells, T/400 timestep and 30 inner iterations.

| Property | Recorded value |
|---|---|
| Physical interval | 0.001487918925-0.010415432475 s, or 5T-35T |
| Native steps | 2000-14000, every ten CFD steps |
| Source frames | 1201 native Fluent PNGs |
| Physical frame interval | 7.439594625e-6 s; 40 intervals per blade-passing period |
| Playback | H.264, 1920x1080, 25 FPS, 48.04 s |
| View | Fixed camera and three visible pitches |
| Legend | Fixed absolute Mach range 0-1.2; fixed colour-bar rectangle |
| Clock | Actual Fluent `Solution time`, twelve decimal places |

[video_manifest.json](video_manifest.json) associates the encoded movie hash with the capture settings and reviewed source interval. [source_frames.csv](source_frames.csv) gives physical time, step and content hashes for every source PNG and its native capture record. Full PNG payloads remain in the separate technical archive; a final checkpoint alone cannot reconstruct unsaved transient fields.

All 1201 archived PNG payloads and capture records were checked by SHA256. Dimensions, clock, fixed range, camera and colour-bar geometry agree across the sequence. Beginning, intermediate and final decoded video samples were visually reviewed. This does not establish periodic convergence or bound unsaved phases. The maximum recorded exported nodal Mach in these saved frames is approximately 1.1894; the 1.2 display limit is not a continuous-time flow maximum.

A complete verified sequence from t=0 and a pressure movie for the systematic campaign are unavailable. Playback seconds are distinct from physical simulation time.

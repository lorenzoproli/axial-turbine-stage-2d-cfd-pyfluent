# Recorded configuration

| File | Purpose |
|---|---|
| `workflow_config.json` | Fluent version/precision, adapted-mesh comparisons, safety limits and common rendering settings |
| `hybrid35_campaign_config.json` | Three systematic meshes, input hashes, original-position Hybrid setup, timestep and per-run duration |
| `campaign_state.json` | Closed-campaign guard; new solver execution remains disabled |
| `native_animation_config.json` | Shared native scene, camera, periodic repeats and legend defaults; the M3 stream selects Mach-only capture |
| `mach_stream_config.json` | Fine-mesh Mach-only capture, every ten CFD steps and fixed 0-1.2 display cap |
| `path_aliases.json` | Compatibility map for saved native records and current English paths |

Configuration and code are separate. Paths are relative to the repository root; the compatibility map resolves native records produced before the current English layout. Fluent zone/report identifiers and legacy metadata keys are retained where required to read the original evidence. They are not alternative filenames or new physical settings.

The run identifier `M2_HYBRID35` remains stable although M2 reached 40 periods. The actual accepted final step/time and the recorded duration take precedence over the identifier. No automatic extension is configured.

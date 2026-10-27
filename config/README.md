# Recorded configuration

| File | Purpose |
|---|---|
| `workflow_config.json` | Fluent version/precision, baseline-mesh comparisons, safety limits and common rendering settings |
| `hybrid35_campaign_config.json` | Three systematic meshes, input hashes, original-position Hybrid setup, timestep and per-run duration |
| `campaign_state.json` | Historical closed-campaign guard; independent work copies have their own explicit open state |
| `native_animation_config.json` | Shared native scene, camera, periodic repeats and legend defaults; the M3 stream selects Mach-only capture |
| `mach_stream_config.json` | Fine-mesh Mach-only capture, every ten CFD steps and fixed 0-1.2 display cap |
| `path_aliases.json` | Compatibility map for saved native records and current English paths |

Configuration and code are separate. Paths are relative to the repository root; the compatibility map resolves native records produced before the current English layout. Fluent zone/report identifiers and legacy metadata keys are retained where required to read the original evidence. They are not alternative filenames or new physical settings.

The run identifier `M2_HYBRID35` remains stable although M2 reached 40 periods. The actual accepted final step/time and the recorded duration take precedence over the identifier. No automatic extension is configured.

The release_assets.json catalog gives the versioned native ZIP names, byte counts and SHA256 values. native_data_index.json declares the 1,054 payloads restored by the two assets. Independently prepared studies receive their own explicit open state; the historical root stays closed.

legacy_schema.json maps historical record fields to the English workflow schema. display_labels.json provides readable names for native Fluent identifiers. Both mappings are included in independent workspaces.

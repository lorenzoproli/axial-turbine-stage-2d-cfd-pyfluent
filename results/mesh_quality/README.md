# Native mesh quality

Only four authoritative collections are included: the historical adapted baseline and the original-position Hybrid M1/M2/M3 meshes. Raw setup caches and pre-Hybrid trial statistics are excluded.

| File | Contents |
|---|---|
| [summary.csv](summary.csv) | Active-cell counts, quality extrema and positive-volume checks |
| `baseline_zone_quantiles.csv` | Historical baseline stator/rotor distributions |
| `M1_zone_quantiles.csv`, `M2_zone_quantiles.csv`, `M3_zone_quantiles.csv` | Systematic mesh stator/rotor distributions at restored initial position |
| [diagnostic_threshold_counts.csv](diagnostic_threshold_counts.csv) | Cell counts and percentages for explicitly stated quality conditions |

For each zone and metric, the tables report minimum, 1st/5th percentiles, median, 95th/99th percentiles and maximum. Quantiles are cell-count based and not weighted by cell volume. `active_cells` in a quantile row is the zone size; in a diagnostic-count row it is the number satisfying the stated condition.

The exporter checks all reported quantiles against the saved native per-cell arrays and confirms positive cell volumes. Metrics are orthogonal quality, aspect ratio, equiangle skewness, equivolume skewness and cell volume. Volume units follow the 1 m reference depth of the planar case.

Diagnostic counts use orthogonal quality below 0.01/0.05/0.1, aspect ratio above 100 and equiangle skewness above 0.9. These cuts describe the distribution; they are not a universal solver-acceptance rule.

The adapted baseline minimum orthogonal quality is approximately 0.0263. M1/M2/M3 minima are approximately 0.2462/0.4702/0.4184. Increasing cell count does not monotonically improve every quality metric. High aspect ratios in thin wall layers require local context and a separate wall-resolution assessment; see the mesh views and sampled wall y+ tables.

The historical baseline has 361,839 stored cells including 72,168 inactive AMR parents. Only its 289,671 active cells contribute to these statistics. Automatic AMR was disabled in the verified final case.

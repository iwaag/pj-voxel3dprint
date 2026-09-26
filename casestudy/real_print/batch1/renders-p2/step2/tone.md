# Tone-curve test: y_photo = s_p · y_render^g

345 samples: agate/fur tiles (55 per photo) + amber host regions (5 per photo).

| fit | g | RMS ΔL | per-case RMS ΔL | s_p range |
|---|---|---:|---|---|
| A: scale only (g = 1) | 1 | 3.28 | agate 2.0, amber 1.6, fur 4.3 | 0.70–1.56 |
| B: one g for all | 0.664 | 3.14 | agate 2.1, amber 1.8, fur 4.0 | 0.43–0.74 |
| C: g per case | agate 0.90, amber 1.02, fur 0.13 | 2.97 | agate 2.0, amber 1.6, fur 3.8 | 0.52–1.53 |

Per-photo scale s_p (photo luminance / render luminance, fits A and B):

- agate photo 0: A 1.111, B 0.530
- agate photo 1: A 1.560, B 0.744
- agate photo 2: A 1.337, B 0.638
- amber photo 0: A 1.071, B 0.430
- amber photo 1: A 1.443, B 0.579
- amber photo 2: A 1.347, B 0.541
- fur photo 0: A 0.758, B 0.676
- fur photo 1: A 0.827, B 0.738
- fur photo 2: A 0.697, B 0.621

## Agate bands only (12 named regions, per photo)

| photo | s | g | RMS ΔL (g free) | RMS ΔL (g = 1) |
|---|---:|---:|---:|---:|
| 0 Unknown-2 | 0.70 | 0.85 | 3.9 | 4.2 |
| 1 Unknown | 1.36 | 0.93 | 3.9 | 4.0 |
| 2 Unknown-3 | 1.31 | 1.05 | 3.2 | 3.3 |


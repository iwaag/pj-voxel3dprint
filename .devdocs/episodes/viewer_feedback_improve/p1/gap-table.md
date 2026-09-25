# batch1 gap table — photo vs archived render (p1 step 1)

Source: `.local/real_print/batch1/contact-sheet-v0.png`, provenance in
`.local/real_print/batch1/provenance.md`. Causes: **M** = optical mapping
(material values / recipe mixing), **S** = stage (floor, backdrop, lights,
camera), **R** = render settings (depth, spp, denoise, tone), **U** = unknown /
needs measurement. First tag is the suspected main cause.

## case1 — agate

| # | photo | render | cause |
|---|---|---|---|
| 1 | Fully opaque slab; paper never visible through it, even in the pale bands | Translucent block, floor and edges visible through the body | **M** (white σs 520/m, CMY σa ≤ 250/m in generator `BASE`: 5 mm × ~150/m ≈ 0.75 optical depth) |
| 2 | Saturated, dark palette: deep teal/blue-black dominates, salmon-red pinks, near-white pale bands | Washed-out pastel pink/teal over a grey haze | **M** (pigment σa too low, so colour comes from a thin path; clear host dominates) + **S** (backlight 8 behind the object brightens transmitted paths) |
| 3 | Sharp band edges, fine grain along bands (halftone at 42×85 µm visible), a few gold specks (yellow-rich "light tan") | Soft, blurred bands (seen through ~5 mm of weakly scattering medium, then denoised) | **M** (translucency blurs) + **R** (0.2 mm review grid, OptiX denoise) + **U** (grain needs dither scale, step 5) |
| 4 | Glossy top with a specular sheen; sides show vertical colour striping (bands extruded through Z) | Top reads as frosted glass, sides almost invisible | **M** (opaque body needed for sides to show colour) + **S** (small warm key vs broad room light) |
| 5 | Soft, short contact shadow on white paper; paper ≈ light grey-white | Long diagonal shadow on dark grey floor, dark vignette | **S** (floor 0.25, off-axis small key, teal backdrop) |

## case2 — amber

| # | photo | render | cause |
|---|---|---|---|
| 1 | Opaque-ish olive-brown / dark amber; paper not visible through 5 mm; edges glow orange (light entering the side) | Semantic: pale cream-yellow translucent block; print-aware v1: blackish-grey with speckles | **M** (semantic σ ≈ 10–100/m; print-aware v1 black σa 450 with weak CMY → neutral dark, not brown) |
| 2 | Hue: warm olive-brown, local orange/red patches | Semantic: beige/cream; print-aware v1: desaturated grey-olive | **M** (yellow/magenta σa too low relative to black; clear tint unknown) + **S** (warm key, dark floor) |
| 3 | Vein contrast low: dark fine veins inside a similar-brown host, no bright gaps | Semantic: bright white-cream streaks between veins; print-aware v1: high-contrast dark/bright stripes and speckle | **M** (host too transparent → floor/backlight shows between veins) + **R** (camera close-up, dist 1.28) |
| 4 | Top surface satin/slightly matte, soft highlight; sides show layered strata | Glassy/wet top with sharp reflections of the stage | **U** (finish; J850 glossy vs matte support side) + **S** (sharp small key) |
| 5 | Short soft shadow on paper | Large dark shadowed floor, framing crops the slab | **S** / camera |

## case3 — fur

| # | photo | render | cause |
|---|---|---|---|
| 1 | Shell perfectly clear, sharp bright edges, paper texture seen undistorted through the top | Whole slab reads as frosted/milky glass, edges blurred | **R** (sidecar says depth 8 — too few bounces for a dielectric slab with internal media; plus denoiser) + **S** (backlight 8) |
| 2 | Hair mass reads as an opaque matte light-grey/blue-grey layer (undercoat stripes, mat 2 = 18 % white) with beige-white hair tufts between stripes | Hair mass barely visible; faint haze | **M** (hairs σs 95–250/m: optical depth ≪ 1 over hair diameter / 2.7 mm core) |
| 3 | Individual hairs and fuzzy edges resolved at ~0.1 mm (printed at printer pitch) | No individual hairs (0.2 mm review grid, 1 voxel per hair, translucent) | **M** + **U** (review grid coarser than printed geometry; hairs were re-drawn at print pitch in the export) |
| 4 | Undercoat has a slight blue cast, hairs look warm/beige | Neutral / slightly warm haze | **U** (thin white-in-clear scattering tint, UltraClear tint; needs coupons) + **S** (warm key vs neutral room) |
| 5 | Clear margin between hair mass and faces clearly visible; soft small shadow | Margin invisible; teal backdrop stripe in frame, dark floor | **S** / **R** |

## Causes to attack, in order

1. **M** — every case: pigmented Vero is 1–2 orders more absorbing/scattering
   than both the generator `BASE` and the amber print-aware v1 values. One
   shared resin library + recipe→mapping tool (step 3).
2. **S** — art stage (dark floor, teal backdrop, warm small key, backlight 8)
   vs white paper under broad neutral light (step 2).
3. **R** — depth 8 frosted shell (fur, agate shell) and denoiser softening
   (step 4).
4. **U** — halftone grain (step 5), finish/matte faces (step 4 optional),
   white-in-clear tint and exact resin colours (phase 2 coupons).

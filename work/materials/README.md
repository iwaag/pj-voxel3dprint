# Material storage policy

Each material has one stable slug and one catalog directory under
`work/materials/<slug>/`.

- Revisions requested for the same material overwrite its current working assets.
- A new material or an explicitly requested variant receives a new slug.
- Large generated volumes remain under `.local/`; their paths are registered in
  `work/materials/<slug>/material.json` so existing viewer sessions are not broken.
- User-facing renders and print exports remain under `outputs/` and include the
  material slug in the filename.
- `outputs/` is untracked. For a physically printed sample, the photos
  (`<case>/result/`), render sessions, reports and final figures are tracked
  under `casestudy/real_print/<batch>/`; the full set of intermediate renders
  and print exports stays untracked under `.local/real_print/<batch>/`.
- Historical assets are not deleted unless explicitly requested.

Current material slugs:

- `kohaku`: amber material, including branching-vein and print-aware variants.
- `pink_teal_agate`: pink-to-teal agate material.
- `floating_fur`: clear slab containing a floating, silky white-and-charcoal fur mass.

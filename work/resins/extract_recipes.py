"""Write an export script's ``*.resin-recipes.json`` without exporting slices.

Usage (repository root):

    vdbmat/.venv/bin/python work/resins/extract_recipes.py EXPORT_SCRIPT.py OUT.json

Imports the export module (its ``main()`` is not run) and writes the same
``resin_order`` / ``recipes_by_material_id`` document the export would.
Understands the resin/recipe globals used by the three batch1 exporters
(``RESINS``/``RES`` and ``RECIPES``/``REC``).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def main() -> None:
    script, out = Path(sys.argv[1]), Path(sys.argv[2])
    spec = importlib.util.spec_from_file_location(script.stem, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resins = getattr(module, "RESINS", None) or module.RES
    recipes = getattr(module, "RECIPES", None) or module.REC
    document = {
        "resin_order": [name for name, _ in resins],
        "recipes_by_material_id": {str(k): list(v) for k, v in recipes.items()},
        "extracted_from": script.as_posix(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()

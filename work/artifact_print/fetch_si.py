"""Download Smithsonian 3D files into .local and log them (artifact_print p1 step 2).

Usage (repo root):
    python3 work/artifact_print/fetch_si.py <package-uuid-prefix>:<file-name-substring> ...

Looks the file up in the API snapshot saved by step 1
(.local/study/3dprint_artifact/docs/api_snapshots/si_3d_files_20260927.json),
downloads it to .local/study/3dprint_artifact/models/si/<pkg8>/ and appends a row
(date, file, url, license note, sha256) to .local/study/3dprint_artifact/README.md.
"""
import datetime, hashlib, json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / ".local/study/3dprint_artifact"
rows = json.loads((LOCAL / "docs/api_snapshots/si_3d_files_20260927.json").read_text())
for spec in sys.argv[1:]:
    pkg, sub = spec.split(":", 1)
    hits = [r for r in rows if r["content"]["model_url"].split(":")[1].startswith(pkg)
            and r["content"]["usage"] == "Download3D" and sub in r["content"]["uri"].split("/")[-1]]
    if len(hits) != 1:
        sys.exit(f"{spec}: {len(hits)} matches")
    url, title = hits[0]["content"]["uri"], hits[0]["title"]
    out = LOCAL / "models/si" / pkg[:8] / url.split("/")[-1]
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        urllib.request.urlretrieve(url, out)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (out.parent / "title.txt").write_text(title + "\n" + url + "\n")
    log = LOCAL / "README.md"
    line = (f"| {datetime.date.today()} | models/si/{pkg[:8]}/{out.name} | {url} | "
            f"Smithsonian Open Access (CC0 方針、個別表示は未確認) | {sha} | {title[:60]} |\n")
    if out.name not in log.read_text():
        log.write_text(log.read_text() + line)
    print(f"{out.relative_to(ROOT)} {out.stat().st_size/1e6:.1f}MB sha256={sha[:16]}")

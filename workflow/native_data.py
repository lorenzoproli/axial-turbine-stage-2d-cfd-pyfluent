"""Verify and install versioned native-data assets without starting Fluent."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MEMBER_MANIFEST = "NATIVE_ARCHIVE_MANIFEST.json"


def sha(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


def index_for(kind):
    if kind not in ("inputs", "results"):
        raise ValueError("Unknown native asset kind.")
    prefix = "inputs/" if kind == "inputs" else "runs/"
    data = json.loads((ROOT / "config/native_data_index.json").read_text(encoding="utf-8"))
    return [row for row in data["files"] if row["path"].startswith(prefix)]


def install(archive_path, kind, check_only=False):
    archive_path = Path(archive_path).resolve()
    catalog = json.loads((ROOT / "config/release_assets.json").read_text(encoding="utf-8"))
    expected = catalog["assets"][kind]
    if archive_path.stat().st_size != expected["bytes"]:
        raise ValueError("Archive size mismatch.")
    with archive_path.open("rb") as stream:
        if sha(stream) != expected["sha256"]:
            raise ValueError("Archive SHA256 mismatch; no files were installed.")
    records = index_for(kind)
    declared = {row["path"]: row for row in records}
    for row in records:
        path = ROOT / row["path"]
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Native destination escapes the project.")
        if path.exists():
            with path.open("rb") as stream:
                if path.stat().st_size != row["bytes"] or sha(stream) != row["sha256"]:
                    raise FileExistsError("Different native file preserved: " + row["path"])
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        allowed = set(declared) | {MEMBER_MANIFEST, "NATIVE_DATA_LICENSE.md"}
        if len(names) != len(set(names)) or set(names) != allowed:
            raise ValueError("Unexpected, duplicate or missing archive member.")
        manifest = json.loads(archive.read(MEMBER_MANIFEST))
        if manifest["files"] != records or manifest["kind"] != kind:
            raise ValueError("Native manifest differs from the versioned index.")
        for row in records:
            if archive.getinfo(row["path"]).file_size != row["bytes"]:
                raise ValueError("Native member size mismatch: " + row["path"])
            with archive.open(row["path"]) as stream:
                if sha(stream) != row["sha256"]:
                    raise ValueError("Native member SHA256 mismatch: " + row["path"])
        if check_only:
            return dict(state="ARCHIVE_VERIFIED", kind=kind, files=len(records), solver_started=False)
        required = sum(row["bytes"] for row in records if not (ROOT / row["path"]).exists())
        if shutil.disk_usage(ROOT).free < required + 512 * 1024**2:
            raise OSError("Insufficient free disk space for the native asset.")
        installed = 0
        for row in records:
            path = ROOT / row["path"]
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation protects different versions even during a race.
            with archive.open(row["path"]) as source, path.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            with path.open("rb") as stream:
                if sha(stream) != row["sha256"]:
                    raise ValueError("Installed native member differs: " + row["path"])
            installed += 1
    return dict(state="INSTALLED_AND_VERIFIED", kind=kind, files=len(records),
                newly_installed=installed, existing_identical=len(records)-installed, solver_started=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--kind", choices=["inputs", "results"], required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(install(args.archive, args.kind, args.check_only), indent=2))


if __name__ == "__main__":
    main()

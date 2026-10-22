"""Hash every file of a checkpoint folder, and check a copy of it against that record.

Use it when weights move between machines (checkpoints are not in git):

    python tools/checkpoint_manifest.py write  ../models/final-softce-3 --out runs/ft3-stage3/final-softce-3.manifest.json
    python tools/checkpoint_manifest.py verify ../models/final-softce-3 --manifest runs/ft3-stage3/final-softce-3.manifest.json

    # only the main weights file of the downloaded base snapshot:
    python tools/checkpoint_manifest.py write <hf_home>/hub/models--convaiinnovations--laya/snapshots/<rev> --glob model.safetensors --out data/frozen/base_laya.manifest.json

`verify` exits with 0 when every listed file exists with the same size and sha256, otherwise 1 and lists the differences.
Standard library only.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import sys


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def walk(folder, pattern):
    for dirpath, _, names in os.walk(folder):
        for name in sorted(names):
            rel = os.path.relpath(os.path.join(dirpath, name), folder).replace("\\", "/")
            if pattern is None or fnmatch.fnmatch(rel, pattern):
                yield rel


def cmd_write(args):
    files = {}
    for rel in sorted(walk(args.folder, args.glob)):
        full = os.path.join(args.folder, rel)
        files[rel] = {"bytes": os.path.getsize(full), "sha256": file_sha256(full)}
        print(f"{files[rel]['sha256'][:12]}  {files[rel]['bytes']:>12,}  {rel}")
    if not files:
        print("no files matched")
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"folder_name": os.path.basename(os.path.abspath(args.folder)), "files": files}, f, indent=1)
    print("wrote", args.out)
    return 0


def cmd_verify(args):
    with open(args.manifest, encoding="utf-8") as f:
        want = json.load(f)["files"]
    bad = []
    for rel, info in want.items():
        full = os.path.join(args.folder, rel)
        if not os.path.exists(full):
            bad.append(f"MISSING  {rel}")
        elif os.path.getsize(full) != info["bytes"]:
            bad.append(f"SIZE     {rel}: {os.path.getsize(full):,} bytes, expected {info['bytes']:,}")
        elif file_sha256(full) != info["sha256"]:
            bad.append(f"HASH     {rel}")
        else:
            print(f"ok       {rel}")
    for line in bad:
        print(line)
    print("ALL FILES MATCH" if not bad else f"{len(bad)} PROBLEM(S)")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("folder")
    w.add_argument("--out", required=True)
    w.add_argument("--glob", default=None, help="only files whose path (relative to the folder) matches, e.g. model.safetensors for the top-level file only")
    v = sub.add_parser("verify")
    v.add_argument("folder")
    v.add_argument("--manifest", required=True)
    a = ap.parse_args()
    sys.exit(cmd_write(a) if a.cmd == "write" else cmd_verify(a))


if __name__ == "__main__":
    main()

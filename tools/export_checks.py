"""Freeze the production Laya questions into data/frozen/checks_frozen.json.

The file holds every LAYA_CHECKS entry (question text, criteria, cutoff, which answer means PASS), the word
caps the evaluator applies to each input, and the qa-analysis commit it came from. Two hashes:
  sha256         everything above, cutoffs included
  inputs_sha256  what training DATA depends on: question wording, which answer means PASS, the word caps, and the
                 source of the two extractor files (laya_inputs.py, rule_engine.py). Cutoffs are excluded on
                 purpose: they are re-tuned after training and must not invalidate the data.
Every training row records inputs_sha256. If it no longer matches (`--check`), the data must be regenerated.
The Colab notebooks embed this file, so training and serving use exactly the production wording.

Usage (qa-analysis .venv, from anywhere):
    python tools/export_checks.py
    python tools/export_checks.py --out data/frozen/checks_frozen.json
    python tools/export_checks.py --check          # exit 1 if the file no longer matches qa-analysis
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths  # noqa: E402

CAP_NAMES = [
    "EMPATHY_MAX_SNIPPETS", "PROBING_PROBLEM_MAX_WORDS", "PROBING_QUESTIONS_MAX_WORDS",
    "RESOLVED_TAIL_LINES", "PARAPHRASE_CUSTOMER_MAX_WORDS", "PARAPHRASE_AGENT_MAX_WORDS",
]


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def file_sha(path):
    """sha256 of a text file with line endings normalised, so Windows/Linux checkouts hash the same."""
    data = open(path, "rb").read().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def git(qa_root, *args):
    try:
        return subprocess.run(["git", "-C", qa_root, *args], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def build(qa_root: str) -> dict:
    sys.path.insert(0, qa_root)
    import src.services.dynamic_evaluator as de

    checks = json.loads(json.dumps(de.LAYA_CHECKS))  # plain-JSON copy
    caps = {name: getattr(de, name) for name in CAP_NAMES}
    body = {"checks": checks, "caps": caps}
    services = os.path.join(qa_root, "src", "services")
    extractors = {name: file_sha(os.path.join(services, name)) for name in ("laya_inputs.py", "rule_engine.py", "laya_windows.py")}
    inputs_view = {"questions": {k: {"yes_means": v["yes_means"], "question": v["question"]} for k, v in checks.items()},
                   "caps": caps, "extractors": extractors}
    return {
        "frozen": body,
        "sha256": sha256(body),
        "inputs_sha256": sha256(inputs_view),
        "extractor_sources_sha256": extractors,
        "n_questions": len(checks),
        "qa_analysis_commit": git(qa_root, "rev-parse", "HEAD"),
        "qa_analysis_branch": git(qa_root, "branch", "--show-current"),
        "qa_analysis_dirty": bool(git(qa_root, "status", "--porcelain", "--", "src")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa-root", default=paths.QA_ROOT, help="the repo root (default: one level above laya-finetuning)")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "frozen", "checks_frozen.json"))
    ap.add_argument("--check", action="store_true", help="compare with the existing file instead of writing")
    args = ap.parse_args()

    qa_root = os.path.abspath(args.qa_root)
    result = build(qa_root)

    if args.check:
        with open(args.out, encoding="utf-8") as f:
            old = json.load(f)
        same = old.get("sha256") == result["sha256"]
        same_inputs = old.get("inputs_sha256") == result["inputs_sha256"]
        print(("MATCH" if same else "MISMATCH") + f": all     file {old.get('sha256', '')[:12]} vs qa-analysis {result['sha256'][:12]}")
        print(("MATCH" if same_inputs else "MISMATCH") + f": inputs  file {old.get('inputs_sha256', '')[:12]} vs qa-analysis {result['inputs_sha256'][:12]}"
              + ("" if same_inputs else "  <- training data built from the old inputs must be regenerated"))
        sys.exit(0 if same and same_inputs else 1)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.out}")
    print(f"questions: {result['n_questions']}  sha256: {result['sha256']}")
    print(f"inputs_sha256 (data binds to this): {result['inputs_sha256']}")
    print(f"qa-analysis {result['qa_analysis_branch']} @ {result['qa_analysis_commit'][:10]}"
          f"{' (uncommitted changes in src/)' if result['qa_analysis_dirty'] else ''}")


if __name__ == "__main__":
    main()

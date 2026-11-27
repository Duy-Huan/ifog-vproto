"""CI/CD Git Diff Change Classifier — Skip CI on Documentation-Only Changes.

Uses Python 3.11+ standard library only (zero third-party imports) so it executes
in ~3 seconds inside a lightweight pre-flight GitHub Actions job before installing
system packages or Python dependencies.

Policy:
  - Changes exclusively touching documentation files (`docs/**`, `skills/**`,
    `README.md`, `AGENT.md`, `report/README.md`, `examples/*/README.md`, or
    non-spec prose files `*.md`/`*.tex`/`*.pdf`/`*.bib`/`*.pptx`/`*.docx`/`*.txt`
    outside `spec/`) yield `code_changed=false` (`docs_only=true`) so CI skips
    heavy build, test, and container jobs.
  - Changes touching ANY source code, test, script, config, container, workflow,
    curated simulation output, or checksum-locked `spec/**` file yield
    `code_changed=true` (fail-safe: unknown paths default to `code_changed=true`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
ZERO_SHA = "0" * 40

DOC_ONLY_PREFIXES = (
    "docs/",
    "skills/",
)

DOC_ONLY_EXACT_PATHS = frozenset(
    {
        "README.md",
        "AGENT.md",
        "report/README.md",
        "LICENSE",
    }
)

DOC_ONLY_EXTENSIONS = frozenset(
    {
        ".md",
        ".tex",
        ".pdf",
        ".bib",
        ".pptx",
        ".docx",
        ".txt",
    }
)

PROTECTED_PREFIXES = ("spec/",)


def normalize_rel_path(path: str) -> str:
    """Normalize a repository-relative path to POSIX format without leading './'."""
    norm = path.strip().replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def is_doc_only_path(path: str) -> bool:
    """Return True iff `path` is purely documentation and should NOT trigger code CI."""
    norm = normalize_rel_path(path)
    if not norm:
        return True
    if any(norm.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return False
    if norm in DOC_ONLY_EXACT_PATHS:
        return True
    if any(norm.startswith(prefix) for prefix in DOC_ONLY_PREFIXES):
        return True
    if norm.startswith("examples/") and norm.endswith("/README.md"):
        return True
    suffix = Path(norm).suffix.lower()
    if suffix in DOC_ONLY_EXTENSIONS:
        return True
    return False


def classify_changed_files(files: Sequence[str]) -> dict[str, Any]:
    """Partition changed files into code/governance vs documentation-only lists."""
    code_files: list[str] = []
    doc_files: list[str] = []
    seen: set[str] = set()

    for raw in files:
        norm = normalize_rel_path(raw)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if is_doc_only_path(norm):
            doc_files.append(norm)
        else:
            code_files.append(norm)

    code_changed = len(code_files) > 0
    docs_only = not code_changed
    return {
        "code_changed": code_changed,
        "docs_only": docs_only,
        "total_files": len(code_files) + len(doc_files),
        "code_files": code_files,
        "doc_files": doc_files,
    }


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def get_git_changed_files(
    repo_root: Path,
    base_ref: str | None,
    head_ref: str = "HEAD",
) -> tuple[list[str], str | None]:
    """Return `(changed_files, force_reason)` using `git diff --name-only`.

    If `base_ref` is missing, all-zeros (new branch push), or unreachable in git
    history, returns `([], reason)` so callers fail-safe and run CI.
    """
    if not base_ref or base_ref.strip() == ZERO_SHA:
        return [], "missing_or_zero_base_ref"
    base_clean = base_ref.strip()
    head_clean = (head_ref or "HEAD").strip()

    if not _git_ref_exists(repo_root, base_clean) or not _git_ref_exists(repo_root, head_clean):
        return [], f"unresolvable_git_ref:{base_clean}..{head_clean}"

    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base_clean}..{head_clean}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return files, None


def evaluate_ci_diff(
    repo_root: Path | str = REPO_ROOT,
    base_ref: str | None = None,
    head_ref: str = "HEAD",
    explicit_files: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compute full CI diff decision from explicit file list or git commit range."""
    root = Path(repo_root)
    if explicit_files is not None:
        result = classify_changed_files(explicit_files)
        result["mode"] = "explicit_files"
        result["force_reason"] = None
        return result

    files, force_reason = get_git_changed_files(root, base_ref, head_ref)
    if force_reason is not None:
        return {
            "code_changed": True,
            "docs_only": False,
            "total_files": 0,
            "code_files": [],
            "doc_files": [],
            "mode": "git_diff_fallback",
            "force_reason": force_reason,
        }

    result = classify_changed_files(files)
    result["mode"] = "git_diff"
    result["force_reason"] = None
    return result


def write_github_outputs(result: dict[str, Any], output_path: Path) -> None:
    """Append `code_changed`, `docs_only`, `code_count`, `doc_count` to `$GITHUB_OUTPUT`."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"code_changed={'true' if result['code_changed'] else 'false'}",
        f"docs_only={'true' if result['docs_only'] else 'false'}",
        f"code_count={len(result['code_files'])}",
        f"doc_count={len(result['doc_files'])}",
    ]
    with output_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def render_markdown_summary(result: dict[str, Any]) -> str:
    """Render a concise Markdown summary suitable for `$GITHUB_STEP_SUMMARY`."""
    decision = (
        "RUN FULL CI/CD PIPELINE (`code_changed=true`)"
        if result["code_changed"]
        else "SKIP CI/CD PIPELINE — Documentation-only change (`code_changed=false`)"
    )
    lines = [
        "### CI/CD Diff Filter Decision",
        "",
        f"- **Decision:** {decision}",
        f"- **Mode:** `{result['mode']}`"
        + (f" (fallback reason: `{result['force_reason']}`)" if result.get("force_reason") else ""),
        f"- **Code / Triggering Files:** `{len(result['code_files'])}`",
        f"- **Documentation-Only Files:** `{len(result['doc_files'])}`",
        "",
    ]
    if result["code_files"]:
        lines.append("**Code / Governance files triggering CI:**")
        for f in result["code_files"][:25]:
            lines.append(f"- `{f}`")
        lines.append("")
    if result["doc_files"]:
        lines.append("**Documentation-only files:**")
        for f in result["doc_files"][:25]:
            lines.append(f"- `{f}`")
        lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for CI/CD diff-based code vs documentation change filtering."""
    parser = argparse.ArgumentParser(
        description="Classify git diff changes so CI/CD runs only when code changes and skips doc-only updates."
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root directory")
    parser.add_argument("--base", default=None, help="Base git commit SHA or ref")
    parser.add_argument("--head", default="HEAD", help="Head git commit SHA or ref")
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Optional explicit list of changed paths (overrides git diff)",
    )
    parser.add_argument(
        "--github-output",
        default=os.environ.get("GITHUB_OUTPUT", "") or None,
        help="Path to GitHub Actions GITHUB_OUTPUT file",
    )
    parser.add_argument(
        "--summary-out",
        default=None,
        help="Optional Markdown summary file path (e.g., $GITHUB_STEP_SUMMARY)",
    )
    parser.add_argument("--json-out", default=None, help="Optional JSON decision report path")
    args = parser.parse_args(argv)

    result = evaluate_ci_diff(
        repo_root=args.repo_root,
        base_ref=args.base,
        head_ref=args.head,
        explicit_files=args.files,
    )

    if args.github_output:
        write_github_outputs(result, Path(args.github_output))

    summary_md = render_markdown_summary(result)
    if args.summary_out:
        sp = Path(args.summary_out)
        sp.parent.mkdir(parents=True, exist_ok=True)
        with sp.open("a", encoding="utf-8") as fh:
            fh.write(summary_md + "\n")

    if args.json_out:
        jp = Path(args.json_out)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(summary_md)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

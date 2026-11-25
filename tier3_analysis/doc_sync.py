"""Mandatory Version-Document Synchronization Verifier (AGENT.md Rule 16).

Uses Python 3.11+ standard library only (zero third-party imports) so it can run
inside lightweight governance CI jobs before third-party package installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
TEX_DOC_PATHS = (
    "docs/IFOG_VPROTO_ARCHITECTURE.tex",
    "docs/RELEASE_NOTES.tex",
    "docs/IFOG_SIMULATION_SCENARIOS.tex",
)


def read_pyproject_version(repo_root: Path) -> str:
    """Read and validate SemVer X.Y.Z from pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        raise FileNotFoundError(f"Missing pyproject.toml at {pyproject}")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    version = str(data["project"]["version"]).strip()
    if not SEMVER_RE.match(version):
        raise ValueError(f"pyproject.toml version '{version}' is not valid SemVer X.Y.Z")
    return version


def compute_tex_sha256_manifest(repo_root: Path) -> dict[str, str]:
    """Compute SHA-256 digests of all tracked LaTeX release/architecture documents."""
    manifest: dict[str, str] = {}
    for rel in TEX_DOC_PATHS:
        p = repo_root / rel
        if not p.exists():
            raise FileNotFoundError(f"Missing LaTeX document: {p}")
        manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return manifest


def write_docs_checksums(repo_root: Path) -> Path:
    """Write docs/DOCS_BUILD.sha256 locking compiled PDFs to their exact .tex sources."""
    manifest = compute_tex_sha256_manifest(repo_root)
    out = repo_root / "docs" / "DOCS_BUILD.sha256"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{digest}  {rel}" for rel, digest in manifest.items()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _check_file_patterns(
    repo_root: Path,
    rel_path: str,
    patterns: list[tuple[str, str]],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    fpath = repo_root / rel_path
    if not fpath.exists():
        msg = f"Missing required synchronized document: {rel_path}"
        errors.append(msg)
        checks.append({"target": rel_path, "passed": False, "detail": msg})
        return
    text = fpath.read_text(encoding="utf-8")
    for label, pattern in patterns:
        matched = re.search(pattern, text, flags=re.MULTILINE) is not None
        checks.append({"target": f"{rel_path} ({label})", "passed": matched, "detail": pattern})
        if not matched:
            errors.append(f"{rel_path}: failed check '{label}' (expected regex {pattern!r})")


def verify_doc_version_sync(
    repo_root: Path | str = REPO_ROOT,
    expected_tag: str | None = None,
) -> dict[str, Any]:
    """Verify strict synchronization between pyproject.toml version, Git release tag, and all docs/."""
    root = Path(repo_root)
    version = read_pyproject_version(root)
    v_tag = f"v{version}"
    esc_ver = re.escape(version)
    esc_vtag = re.escape(v_tag)

    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    if expected_tag is not None:
        tag_ok = expected_tag == v_tag
        checks.append(
            {
                "target": "release_tag_match",
                "passed": tag_ok,
                "detail": f"expected_tag={expected_tag} vs pyproject={v_tag}",
            }
        )
        if not tag_ok:
            errors.append(
                f"Release tag '{expected_tag}' does not match pyproject.toml version '{v_tag}' (Rule 16)"
            )

    _check_file_patterns(
        root,
        "docs/IFOG_VPROTO_ARCHITECTURE.md",
        [
            ("doc_control_version", rf"Current Version.*`{esc_vtag}`"),
            ("revision_history_row", rf"^\|\s*`{esc_vtag}`\s*\|"),
        ],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "docs/IFOG_VPROTO_ARCHITECTURE.tex",
        [
            ("tex_doc_version_macro", rf"\\newcommand\{{\\DocVersion\}}\{{{esc_vtag}\}}"),
            ("tex_revision_history_row", rf"\\texttt\{{{esc_vtag}\}}\s*&"),
        ],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "docs/RELEASE_NOTES.md",
        [
            ("release_header_version", rf"Current Version.*`{esc_vtag}`"),
            ("release_section_heading", rf"^##\s+Release\s+`?{esc_vtag}`?"),
        ],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "docs/RELEASE_NOTES.tex",
        [
            ("tex_release_version_macro", rf"\\newcommand\{{\\DocVersion\}}\{{{esc_vtag}\}}"),
            ("tex_release_section", rf"Release\s+{esc_vtag}"),
        ],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "docs/IFOG_SIMULATION_SCENARIOS.md",
        [
            ("scenarios_header_version", rf"Current Version.*`{esc_vtag}`"),
            ("scenarios_revision_row", rf"^\|\s*`{esc_vtag}`\s*\|"),
        ],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "docs/IFOG_SIMULATION_SCENARIOS.tex",
        [
            ("tex_scenarios_version_macro", rf"\\newcommand\{{\\DocVersion\}}\{{{esc_vtag}\}}"),
            ("tex_scenarios_revision_row", rf"\\texttt\{{{esc_vtag}\}}\s*&"),
        ],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "docs/CHANGELOG.md",
        [("changelog_heading", rf"^##\s+\[{esc_ver}\]")],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "README.md",
        [("readme_version_badge", rf"{esc_vtag}")],
        checks,
        errors,
    )
    _check_file_patterns(
        root,
        "AGENT.md",
        [("rule16_doc_sync_policy", r"Rule 16")],
        checks,
        errors,
    )

    # Verify compiled PDFs exist and are non-trivial (> 10 KB)
    for pdf_rel in (
        "docs/IFOG_VPROTO_ARCHITECTURE.pdf",
        "docs/RELEASE_NOTES.pdf",
        "docs/IFOG_SIMULATION_SCENARIOS.pdf",
    ):
        pdf_path = root / pdf_rel
        ok = pdf_path.exists() and pdf_path.stat().st_size > 10_000
        checks.append(
            {
                "target": pdf_rel,
                "passed": ok,
                "detail": f"size={pdf_path.stat().st_size if pdf_path.exists() else 0} bytes",
            }
        )
        if not ok:
            errors.append(f"Compiled PDF missing or empty: {pdf_rel}")

    # Verify docs/DOCS_BUILD.sha256 proves PDFs were compiled from current .tex sources
    sha_file = root / "docs" / "DOCS_BUILD.sha256"
    if not sha_file.exists():
        msg = "Missing docs/DOCS_BUILD.sha256 (run scripts/verify_doc_sync.py --write-checksums after compiling PDFs)"
        errors.append(msg)
        checks.append({"target": "docs/DOCS_BUILD.sha256", "passed": False, "detail": msg})
    else:
        recorded: dict[str, str] = {}
        for line in sha_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            digest, rel = stripped.split(None, 1)
            recorded[rel.strip()] = digest.strip()
        for rel in TEX_DOC_PATHS:
            p = root / rel
            actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
            expected = recorded.get(rel, "")
            ok = bool(actual) and (actual == expected)
            checks.append(
                {
                    "target": f"docs/DOCS_BUILD.sha256 ({rel})",
                    "passed": ok,
                    "detail": "matched" if ok else f"actual={actual[:12]} vs recorded={expected[:12]}",
                }
            )
            if not ok:
                errors.append(
                    f"Stale PDF checksum for {rel}: recompile PDF via lualatex and refresh docs/DOCS_BUILD.sha256"
                )

    return {
        "version": version,
        "v_tag": v_tag,
        "expected_tag": expected_tag,
        "ok": len(errors) == 0,
        "checks": checks,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Rule 16 version-document synchronization verification."""
    parser = argparse.ArgumentParser(
        description="Verify mandatory Version-Document Synchronization (AGENT.md Rule 16)"
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root directory")
    parser.add_argument("--expected-tag", default=None, help="Expected Git release tag (e.g., v1.1.0)")
    parser.add_argument(
        "--write-checksums",
        action="store_true",
        help="Write/refresh docs/DOCS_BUILD.sha256 after recompiling docs/*.tex -> docs/*.pdf",
    )
    parser.add_argument("--json-out", default=None, help="Optional JSON summary output path")
    args = parser.parse_args(argv)

    root = Path(args.repo_root)
    if args.write_checksums:
        out = write_docs_checksums(root)
        print(f"[doc_sync] Wrote {out}")
        return 0

    result = verify_doc_version_sync(root, expected_tag=args.expected_tag)
    if args.json_out:
        out_p = Path(args.json_out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"[doc_sync] Project version: {result['v_tag']} | Checks: {len(result['checks'])}")
    for chk in result["checks"]:
        mark = "PASS" if chk["passed"] else "FAIL"
        print(f"  [{mark}] {chk['target']}")
    if not result["ok"]:
        print("[doc_sync] ERRORS:")
        for err in result["errors"]:
            print(f"  - {err}")
        return 1
    print("[doc_sync] All version-document synchronization checks PASSED (Rule 16).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

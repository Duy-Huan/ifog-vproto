"""Unit tests achieving 100% line coverage for tier3_analysis/ci_diff_filter.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tier3_analysis import ci_diff_filter


def _init_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "mini_repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "dev"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ci@test.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "CI Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("# init\n", encoding="utf-8")
    (repo / "src.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


@pytest.mark.unit
def test_ci_diff_filter_path_classification_and_dedup() -> None:
    """Verify doc-only vs code/spec/workflow path classification and normalization."""
    assert ci_diff_filter.normalize_rel_path("./docs\\slide.tex") == "docs/slide.tex"
    assert ci_diff_filter.is_doc_only_path("") is True
    assert ci_diff_filter.is_doc_only_path("docs/IFOG_VPROTO_PRESENTATION.tex") is True
    assert ci_diff_filter.is_doc_only_path("docs/IFOG_VPROTO_PRESENTATION.pdf") is True
    assert ci_diff_filter.is_doc_only_path("skills/README.md") is True
    assert ci_diff_filter.is_doc_only_path("README.md") is True
    assert ci_diff_filter.is_doc_only_path("AGENT.md") is True
    assert ci_diff_filter.is_doc_only_path("examples/full_all_scenarios/README.md") is True
    assert ci_diff_filter.is_doc_only_path("notes/overview.md") is True

    # Code, specs (Rule 7 locked), workflows, scripts, configs MUST trigger CI
    assert ci_diff_filter.is_doc_only_path("spec/IFOG-SIM-SPEC-007.md") is False
    assert ci_diff_filter.is_doc_only_path("spec/IFOG-SIM-SPEC-007.tex") is False
    assert ci_diff_filter.is_doc_only_path("tier1_offline/shupe_thermal.py") is False
    assert ci_diff_filter.is_doc_only_path("tier2_sysc_ams/src/digital_dsp_sc.cpp") is False
    assert ci_diff_filter.is_doc_only_path("fmi_wrapper/src/fmi3_bridge.cpp") is False
    assert ci_diff_filter.is_doc_only_path(".github/workflows/ci.yml") is False
    assert ci_diff_filter.is_doc_only_path("configs/schema_v6.json") is False
    assert ci_diff_filter.is_doc_only_path("Containerfile") is False

    res_docs = ci_diff_filter.classify_changed_files(
        ["", "./docs/IFOG_VPROTO_PRESENTATION.tex", "docs/IFOG_VPROTO_PRESENTATION.tex", "README.md"]
    )
    assert res_docs["code_changed"] is False
    assert res_docs["docs_only"] is True
    assert res_docs["doc_files"] == ["docs/IFOG_VPROTO_PRESENTATION.tex", "README.md"]
    assert res_docs["code_files"] == []

    res_mixed = ci_diff_filter.classify_changed_files(
        ["docs/IFOG_VPROTO_PRESENTATION.pdf", "tier3_analysis/inverse_calibration.py"]
    )
    assert res_mixed["code_changed"] is True
    assert res_mixed["docs_only"] is False
    assert res_mixed["code_files"] == ["tier3_analysis/inverse_calibration.py"]


@pytest.mark.unit
def test_ci_diff_filter_git_diff_fallbacks_and_cli(tmp_path: Path) -> None:
    """Exercise git diff on real commits, fail-safe fallbacks, and CLI outputs."""
    repo = _init_git_repo(tmp_path)
    sha0 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    # Commit 1: docs-only update -> code_changed == False
    (repo / "docs").mkdir()
    (repo / "docs" / "slides.tex").write_text("% slide\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "docs only"], cwd=repo, check=True, capture_output=True)
    sha1 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    r_docs = ci_diff_filter.evaluate_ci_diff(repo, base_ref=sha0, head_ref=sha1)
    assert r_docs["code_changed"] is False
    assert r_docs["docs_only"] is True
    assert r_docs["mode"] == "git_diff"

    # Commit 2: code update -> code_changed == True
    (repo / "src.py").write_text("x = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "code change"], cwd=repo, check=True, capture_output=True)
    sha2 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    r_code = ci_diff_filter.evaluate_ci_diff(repo, base_ref=sha1, head_ref=sha2)
    assert r_code["code_changed"] is True
    assert r_code["code_files"] == ["src.py"]

    # Fail-safe fallbacks: zero SHA and unresolvable ref -> code_changed == True
    r_zero = ci_diff_filter.evaluate_ci_diff(repo, base_ref=ci_diff_filter.ZERO_SHA, head_ref=sha2)
    assert r_zero["code_changed"] is True and r_zero["force_reason"] == "missing_or_zero_base_ref"

    r_bad = ci_diff_filter.evaluate_ci_diff(repo, base_ref="deadbeef1234", head_ref=sha2)
    assert r_bad["code_changed"] is True and "unresolvable_git_ref" in str(r_bad["force_reason"])

    # CLI execution with explicit files + github-output + summary-out + json-out
    gh_out = tmp_path / "gh_output.txt"
    sum_out = tmp_path / "summary.md"
    js_out = tmp_path / "decision.json"
    rc = ci_diff_filter.main(
        [
            "--repo-root",
            str(repo),
            "--files",
            "docs/IFOG_VPROTO_PRESENTATION.tex",
            "tier2_sysc_ams/src/digital_dsp_sc.cpp",
            "--github-output",
            str(gh_out),
            "--summary-out",
            str(sum_out),
            "--json-out",
            str(js_out),
        ]
    )
    assert rc == 0
    assert "code_changed=true" in gh_out.read_text(encoding="utf-8")
    assert "RUN FULL CI/CD PIPELINE" in sum_out.read_text(encoding="utf-8")
    parsed = json.loads(js_out.read_text(encoding="utf-8"))
    assert parsed["code_changed"] is True and parsed["mode"] == "explicit_files"

    # CLI execution with docs-only git diff range
    gh_out2 = tmp_path / "gh_output2.txt"
    rc2 = ci_diff_filter.main(
        [
            "--repo-root",
            str(repo),
            "--base",
            sha0,
            "--head",
            sha1,
            "--github-output",
            str(gh_out2),
        ]
    )
    assert rc2 == 0
    assert "code_changed=false" in gh_out2.read_text(encoding="utf-8")
    assert "docs_only=true" in gh_out2.read_text(encoding="utf-8")

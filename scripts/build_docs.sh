#!/usr/bin/env bash
set -euo pipefail

# Compile all release architecture & release notes LaTeX documents in docs/
# using 3-pass LuaLaTeX (UTF-8 Vietnamese + TikZ), refresh docs/DOCS_BUILD.sha256,
# and verify AGENT.md Rule 16 version-document synchronization.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="${REPO_ROOT}/docs"

for doc in IFOG_VPROTO_ARCHITECTURE RELEASE_NOTES IFOG_SIMULATION_SCENARIOS; do
    echo "[build_docs] Compiling docs/${doc}.tex -> docs/${doc}.pdf (3-pass lualatex)..."
    (
        cd "${DOCS_DIR}"
        lualatex -interaction=nonstopmode -halt-on-error "${doc}.tex" >/dev/null
        lualatex -interaction=nonstopmode -halt-on-error "${doc}.tex" >/dev/null
        lualatex -interaction=nonstopmode -halt-on-error "${doc}.tex" >/dev/null
        rm -f "${doc}.aux" "${doc}.log" "${doc}.out" "${doc}.toc"
    )
    ls -lh "${DOCS_DIR}/${doc}.pdf"
done

python3 "${REPO_ROOT}/scripts/verify_doc_sync.py" --write-checksums
python3 "${REPO_ROOT}/scripts/verify_doc_sync.py"
echo "[build_docs] All release PDFs compiled and Rule 16 doc-sync verified!"

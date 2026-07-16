import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Links into the published docs site. PR #2602 rewrote docs/ from 22 pages down to 8 without
# updating the markdown that points at the deleted ones, leaving k8s/README.md on dead URLs
# (#3054). sync-docs.yml only validates nav -> file, so nothing catches the reverse direction.
DOCS_LINK_PATTERN = re.compile(r"docs\.primeintellect\.ai/prime-rl/([a-zA-Z0-9_-]+)")

# Slugs #2602 deleted: `kubernetes` was deferred, `deployment` folded into scaling.md,
# `troubleshooting` folded into per-page prose. None has a page on the docs site.
DEAD_SLUGS = ["kubernetes", "deployment", "troubleshooting"]


def _tracked_markdown() -> list[Path]:
    stdout = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [REPO_ROOT / line for line in stdout.splitlines() if line]


def _nav_pages() -> list[str]:
    # Mintlify deprecated mint.json in favour of docs.json; update this loader if docs/ migrates.
    navigation = json.loads((REPO_ROOT / "docs" / "mint.json").read_text())["navigation"]
    return [page for group in navigation for page in group["pages"]]


def _docs_links() -> list[tuple[str, str]]:
    """Every (source file, docs slug) pair linked from tracked markdown."""
    links = []
    for path in _tracked_markdown():
        for slug in DOCS_LINK_PATTERN.findall(path.read_text()):
            links.append((path.relative_to(REPO_ROOT).as_posix(), slug))
    return sorted(set(links))


def test_docs_link_scan_is_not_vacuous():
    # Without this, a typo in DOCS_LINK_PATTERN would empty the parametrization below and
    # silently pass the whole module.
    assert _docs_links(), "found no docs.primeintellect.ai/prime-rl/* links — the scan is broken"


@pytest.mark.parametrize(("source", "slug"), _docs_links())
def test_docs_link_resolves_to_nav_page(source: str, slug: str):
    assert slug in _nav_pages(), f"{source} links to /prime-rl/{slug}, which is not a page in docs/mint.json"
    assert (REPO_ROOT / "docs" / f"{slug}.md").exists(), (
        f"{source} links to /prime-rl/{slug}, but docs/{slug}.md is missing"
    )


@pytest.mark.parametrize("slug", DEAD_SLUGS)
def test_k8s_readme_has_no_dead_doc_slugs(slug: str):
    linked = DOCS_LINK_PATTERN.findall((REPO_ROOT / "k8s" / "README.md").read_text())
    assert slug not in linked, f"k8s/README.md links to deleted docs page /prime-rl/{slug}"

#!/usr/bin/env bash
# Close stale PRs that are obsolete after the modernization effort (PR #164).
# Run: bash scripts/close-stale-prs.sh
#
# Requires: gh CLI authenticated (gh auth login)

set -euo pipefail

# ── Old dependabot dependency PRs (2022-2023) ────────────────────────────
# The modernization removed pinned ~= version constraints from pyproject.toml.
# These PRs update constraints that no longer exist.
OBSOLETE_DEPENDABOT=(
  "121:Update sympy requirement from ==1.5.* to ==1.11.*"
  "127:Update tabulate requirement from ~=0.8.9 to ~=0.9.0"
  "132:Update pint requirement from ~=0.17 to ~=0.20"
  "136:Update path requirement from ~=16.0.0 to ~=16.6.0"
  "138:Update lxml requirement from ~=4.6.3 to ~=4.9.2"
  "142:Update pandas requirement from ~=1.3.0 to ~=1.5.3"
  "143:Update shapely requirement from ~=1.7.1 to ~=2.0.1"
  "144:Update beautifulsoup4 requirement from ~=4.9.3 to ~=4.11.2"
  "145:Update numpy requirement from ~=1.21.1 to ~=1.24.2"
  "147:Update matplotlib requirement from ~=3.4.2 to ~=3.7.1"
)

# ── Superseded feature PRs (Aug 2025) ────────────────────────────────────
# These changes were incorporated into main through earlier commits before PR #164.
SUPERSEDED_FEATURE=(
  "150:chore: modernize CI Python versions — CI now tests 3.10-3.13"
  "152:Fix affine_transform matrix check — implemented, test exists in test_xml.py"
  "154:Replace NetworkX grid with sparse BFS — done in commit 6e6ad00"
  "155:Refactor deck parser for thread-safe — reentrancy test in commit a1a642e"
  "159:Add tests for anchor points/units/affine — tests exist in main"
  "161:chore: configure uv and static analysis — fully configured with ruff+pre-commit"
)

# ── PR #160 is NOT closed — ControlCards dataclass refactor is still relevant ──

COMMENT_DEPS="Closing: the modernization effort (PR #164) removed pinned version constraints from pyproject.toml. These dependency bumps are no longer applicable."
COMMENT_PATH="Closing: the \`path\` library was removed entirely and replaced with \`pathlib\` in PR #164."
COMMENT_FEATURE="Closing: this work was incorporated into main through earlier commits before the modernization PR #164."

echo "=== Closing obsolete dependabot dependency PRs ==="
for entry in "${OBSOLETE_DEPENDABOT[@]}"; do
  pr_num="${entry%%:*}"
  pr_title="${entry#*:}"
  echo "  Closing #${pr_num}: ${pr_title}"
  if [[ "$pr_num" == "136" ]]; then
    gh pr close "$pr_num" --comment "$COMMENT_PATH" --delete-branch || true
  else
    gh pr close "$pr_num" --comment "$COMMENT_DEPS" --delete-branch || true
  fi
done

echo ""
echo "=== Closing superseded feature PRs ==="
for entry in "${SUPERSEDED_FEATURE[@]}"; do
  pr_num="${entry%%:*}"
  pr_title="${entry#*:}"
  echo "  Closing #${pr_num}: ${pr_title}"
  gh pr close "$pr_num" --comment "$COMMENT_FEATURE" --delete-branch || true
done

echo ""
echo "=== Cleaning up stale codex/* branches ==="
STALE_BRANCHES=(
  "codex/add-tests-for-various-functions"
  "codex/fix-failing-tests-and-pytest-warnings"
  "codex/investigate-sparse-graph-representation"
  "codex/modernize-repository-with-best-practices"
  "codex/refactor-_parse_string-for-better-safety"
  "codex/refactor-controlcards-to-use-ordereddict"
  "codex/update-ci-for-modern-python-versions"
  "codex/update-utils.py-and-add-test-for-affine_transform"
  "claude/modernize-python-package-zU05Q"
)
for branch in "${STALE_BRANCHES[@]}"; do
  echo "  Deleting origin/${branch}"
  git push origin --delete "$branch" || true
done

echo ""
echo "=== Summary ==="
echo "Closed: 10 obsolete dependabot PRs + 6 superseded feature PRs"
echo "Kept open:"
echo "  #160 — ControlCards dataclass refactor (still relevant, not yet implemented)"
echo "  #165-168 — New dependabot CI action bumps (valid, review and merge)"
echo "Done!"

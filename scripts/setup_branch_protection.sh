#!/usr/bin/env bash
#
# Re-apply branch protection on the default branch (TASKS.md 0.15, issue #15).
#
# Protects `main` so the CI "Quality gates" check must pass before a pull
# request can merge. The settings are tuned to keep the autonomous build loop
# working: the repo owner (an admin) merges one PR at a time via
# `gh pr merge --merge`, so admins are NOT enforced and NO approving reviews are
# required (the loop cannot self-approve). Non-admins are still gated by the
# required status check.
#
# Reproducible: owner/repo are derived from `gh repo view` (not hard-coded), and
# the single required-check NAME is the one named constant below — it must match
# the `name:` of the `quality-gates` job in .github/workflows/ci.yml. Contains
# no secrets: auth comes from the caller's `gh` login.
#
# Usage:
#   ./scripts/setup_branch_protection.sh
#
set -euo pipefail

# The exact GitHub check-run name required to merge. Single source of truth;
# must equal the `name:` field of the CI job in .github/workflows/ci.yml.
REQUIRED_CHECK_NAME="Quality gates"

# Derive owner/repo and default branch from the current repo's gh context
# rather than hard-coding them (guideline §7.2 — no hard-coded values).
REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
BRANCH="$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')"

echo "Applying branch protection to ${REPO}@${BRANCH} (required check: ${REQUIRED_CHECK_NAME})"

# Build the protection payload. Notes on each field:
#   required_status_checks.strict=false  -> don't force branches up-to-date
#                                           (avoids rebase friction with the
#                                           one-PR-at-a-time loop).
#   enforce_admins=false                 -> the admin owner loop can still merge.
#   required_pull_request_reviews=null   -> no approvals required (loop cannot
#                                           self-approve).
#   restrictions=null                    -> no push allow-list.
PAYLOAD="$(REQUIRED_CHECK_NAME="${REQUIRED_CHECK_NAME}" jq -n \
  --arg check "${REQUIRED_CHECK_NAME}" \
  '{
    required_status_checks: { strict: false, contexts: [ $check ] },
    enforce_admins: false,
    required_pull_request_reviews: null,
    restrictions: null,
    allow_force_pushes: false,
    allow_deletions: false
  }')"

echo "${PAYLOAD}" | gh api -X PUT \
  "repos/${REPO}/branches/${BRANCH}/protection" \
  --input - >/dev/null

echo "Branch protection applied. Required status checks now configured:"
gh api "repos/${REPO}/branches/${BRANCH}/protection" \
  --jq '.required_status_checks.contexts[]'

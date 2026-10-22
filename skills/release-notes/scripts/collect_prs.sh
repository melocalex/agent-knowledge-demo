#!/usr/bin/env bash
# List PRs merged since a git tag, as JSON. Read-only: uses git log and gh pr list.
# Usage: scripts/collect_prs.sh <last-tag>
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <last-tag>" >&2
  exit 2
fi

tag="$1"
since="$(git log -1 --format=%cs "$tag")"

gh pr list \
  --state merged \
  --search "merged:>=${since}" \
  --limit 200 \
  --json number,title,body,labels,author,mergedAt,url

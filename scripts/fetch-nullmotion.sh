#!/usr/bin/env bash
# Fetch Null Motion (blixvip/NullMotion) into vendor/nullmotion at a pinned commit.
#
# It is fetched rather than committed: upstream has no open-source licence (all rights
# reserved) and ships other creators' ad footage in showcase/, so this public repo must
# not redistribute it. vendor/nullmotion/ is gitignored. Safe to re-run.
#
#   scripts/fetch-nullmotion.sh
set -euo pipefail

REPO=https://github.com/blixvip/NullMotion.git
REF=2795457432a63e7e28879210601cede25915e561   # "chore: release 1.0.0"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest="$root/vendor/nullmotion"

if [ "$(git -C "$dest" rev-parse -q --verify HEAD 2>/dev/null || true)" = "$REF" ]; then
  echo "already present at ${REF:0:7}"
  exit 0
fi
if [ ! -d "$dest/.git" ]; then
  mkdir -p "$dest"
  git -C "$dest" init -q
  git -C "$dest" remote add origin "$REPO"
fi
# No LFS in upstream today; the prefix keeps a future LFS file from aborting the checkout.
GIT_LFS_SKIP_SMUDGE=1 git -C "$dest" fetch -q --depth 1 origin "$REF"
git -C "$dest" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
echo "fetched ${REF:0:7} into vendor/nullmotion"

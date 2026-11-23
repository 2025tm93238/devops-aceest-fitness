#!/usr/bin/env bash
# Build the production image of every released version (git tags) and push it
# to Docker Hub, plus "latest" = newest release. Run once after `docker login`.
# Usage: ./infra/publish-all-versions.sh
set -euo pipefail
REPO=2025tm93238/aceest-fitness
VERSIONS=(v1.0.0 v1.1.0 v2.0.0 v2.1.0 v3.0.0 v3.0.1)
ROOT=$(git rev-parse --show-toplevel)
WORK=$(mktemp -d)
trap 'git -C "$ROOT" worktree prune; rm -rf "$WORK"' EXIT

git -C "$ROOT" fetch -q --tags
for v in "${VERSIONS[@]}"; do
  printf '\n\033[1m== %s ==\033[0m\n' "$v"
  git -C "$ROOT" worktree add -q --detach "$WORK/$v" "$v"
  docker build -q --target production --label "org.opencontainers.image.version=$v" \
    -t "$REPO:$v" "$WORK/$v"
  docker push -q "$REPO:$v"
  git -C "$ROOT" worktree remove --force "$WORK/$v"
done
docker tag "$REPO:${VERSIONS[-1]}" "$REPO:latest"
docker push -q "$REPO:latest"
printf '\n'; docker images "$REPO"

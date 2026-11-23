#!/usr/bin/env bash
# Shared settings for the ACEest deployment-strategy scripts.
set -euo pipefail

NS=aceest
REPO=2025tm93238/aceest-fitness
STABLE_TAG=${STABLE_TAG:-v2.1.0}   # "current" release in every strategy
NEW_TAG=${NEW_TAG:-v3.0.0}         # "new" release being rolled out
K8S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

port_for() {
  case "$1" in
    rolling) echo 30080 ;; bluegreen) echo 30081 ;; canary) echo 30082 ;;
    ab) echo 30083 ;; shadow) echo 30084 ;;
    *) echo "unknown strategy '$1' (rolling|bluegreen|canary|ab|shadow)" >&2; return 2 ;;
  esac
}

node_ip() {
  kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
}

# Base URL of a strategy's NodePort. ACEEST_HOST overrides the node IP.
url_for() {
  local port
  port=$(port_for "$1") || exit 2
  echo "http://${ACEEST_HOST:-$(node_ip)}:${port}"
}

# One /version call printed as "version=3.0.0 track=canary pod=..."
show_version() {
  curl -s --max-time 5 "$@" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print("version=%s track=%s pod=%s" % (d["version"], d["track"], d["pod"]))
except Exception:
    print("request failed")'
}

banner() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

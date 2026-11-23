#!/usr/bin/env bash
# Send N requests to a strategy's endpoint and summarise which release answered.
# Usage: traffic.sh <rolling|bluegreen|canary|ab|shadow> [N] [extra curl args...]
source "$(dirname "$0")/common.sh"
s=${1:?strategy}; n=${2:-10}; shift $(( $# >= 2 ? 2 : 1 ))
url="$(url_for "$s")/version"
banner "$n requests -> $url $*"
out=$(for _ in $(seq "$n"); do show_version "$@" "$url"; done)
echo "$out"
banner "Summary"
echo "$out" | awk '{print $1, $2}' | sort | uniq -c

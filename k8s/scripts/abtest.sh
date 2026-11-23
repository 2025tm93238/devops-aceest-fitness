#!/usr/bin/env bash
# A/B testing: users are routed by header or cookie, not at random.
source "$(dirname "$0")/common.sh"
url="$(url_for ab)/version"
banner "Group A (no header)"
for _ in 1 2 3; do show_version "$url"; done
banner "Group B (header X-Variant: B)"
for _ in 1 2 3; do show_version -H "X-Variant: B" "$url"; done
banner "Group B (cookie variant=B)"
for _ in 1 2 3; do show_version --cookie "variant=B" "$url"; done
banner "Router response header"
curl -s -o /dev/null -D - -H "X-Variant: B" "$url" | grep -i x-ab-variant

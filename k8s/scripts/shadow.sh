#!/usr/bin/env bash
# Shadow deployment: users are answered by the primary; a copy of every request
# is sent to the shadow (new) release, whose responses are discarded.
source "$(dirname "$0")/common.sh"
url="$(url_for shadow)"
banner "5 user requests -> $url/version (answered by the primary)"
for _ in 1 2 3 4 5; do show_version "$url/version"; done
curl -s -o /dev/null -X POST "$url/clients" -H 'Content-Type: application/json' \
  -d '{"name":"ShadowUser","age":28,"height":175,"weight":72,"program":"Beginner (BG)"}'
sleep 2
banner "Primary ($STABLE_TAG) access log - served the users"
kubectl -n "$NS" logs deploy/aceest-shadow-primary --tail=6
banner "Shadow ($NEW_TAG) access log - received the mirrored copies"
kubectl -n "$NS" logs deploy/aceest-shadow-candidate --tail=6

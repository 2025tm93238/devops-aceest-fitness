#!/usr/bin/env bash
# Call the rolling-update Service 10 times through its NodePort and check every
# answer is healthy and (if given) reports the expected version.
# Usage: k8s-smoke-test.sh <namespace> <nodePort> [expected version]
set -euo pipefail
ns=${1:?namespace}; port=${2:?nodePort}; expected=${3:-}
node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
url="http://$node_ip:$port"
echo "Smoke testing $url (namespace $ns)"
fail=0
for i in $(seq 10); do
  body=$(curl -fsS --max-time 5 "$url/version") || { echo "request $i failed"; fail=1; continue; }
  version=$(echo "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["version"], d["pod"])')
  echo "request $i: version=${version% *} pod=${version#* }"
  if [[ -n "$expected" && "${version% *}" != "$expected" ]]; then fail=1; fi
done
if [[ $fail -ne 0 ]]; then
  echo "SMOKE TEST FAILED${expected:+ (expected version $expected)}"
  exit 1
fi
echo "Smoke test passed"

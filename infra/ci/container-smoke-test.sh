#!/usr/bin/env bash
# Start the production image, check /health and that /version reports the
# expected version, then remove the container.
# Usage: container-smoke-test.sh <image> <expected version>
set -euo pipefail
image=${1:?image}; expected=${2:?version}
name="aceest-smoke-$$"
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT

docker run -d --name "$name" -p 127.0.0.1::5000 "$image" >/dev/null
port=$(docker port "$name" 5000/tcp | head -1 | sed 's/.*://')
for _ in $(seq 30); do
  curl -fs "http://127.0.0.1:$port/health" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:$port/health"; echo
actual=$(curl -fsS "http://127.0.0.1:$port/version" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
echo "container reports version $actual (expected $expected)"
[[ "$actual" == "$expected" ]]

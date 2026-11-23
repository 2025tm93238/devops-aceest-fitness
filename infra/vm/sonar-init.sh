#!/usr/bin/env bash
# One-time SonarQube setup (data persists in ~/workspace/sonarqube):
#   - replaces the default admin/admin password
#   - creates the project and the "ACEest gate" quality gate (made default)
#   - generates a token for Jenkins, saved to ~/workspace/.secrets/sonar-token
# Usage: ./infra/vm/sonar-init.sh
set -euo pipefail
SONAR=${SONAR_HOST_URL:-http://localhost:9000}
SECRETS="$HOME/workspace/.secrets"
mkdir -p "$SECRETS"; chmod 700 "$SECRETS"
api() { curl -fsS -u "admin:$ADMIN_PW" "$@"; }

until curl -s "$SONAR/api/system/status" | grep -q '"status":"UP"'; do
  echo "waiting for SonarQube..."; sleep 5
done

if curl -fsS -u admin:admin "$SONAR/api/authentication/validate" | grep -q '"valid":true'; then
  echo "SonarQube still uses the default password. Choose a new admin password"
  echo "(at least 12 characters with upper case, lower case, a digit and a symbol, e.g. Aceest@Sonar2026):"
  read -rs -p "New admin password: " ADMIN_PW; echo
  curl -fsS -u admin:admin -X POST "$SONAR/api/users/change_password" \
    --data-urlencode login=admin --data-urlencode previousPassword=admin \
    --data-urlencode "password=$ADMIN_PW"
  echo "Admin password changed."
else
  read -rs -p "SonarQube admin password: " ADMIN_PW; echo
fi
api "$SONAR/api/authentication/validate" | grep -q '"valid":true' || { echo "wrong password"; exit 1; }

api -X POST "$SONAR/api/projects/create" --data-urlencode project=aceest-fitness \
  --data-urlencode "name=ACEest Fitness & Gym" >/dev/null 2>&1 || true

GATE="ACEest gate"
if ! api "$SONAR/api/qualitygates/show" --get --data-urlencode "name=$GATE" >/dev/null 2>&1; then
  api -X POST "$SONAR/api/qualitygates/create" --data-urlencode "name=$GATE" >/dev/null
  # Overall code (not only new code), so the gate is enforced from the first analysis.
  for cond in "coverage LT 80" "reliability_rating GT 1" "security_rating GT 1" "duplicated_lines_density GT 3"; do
    set -- $cond
    api -X POST "$SONAR/api/qualitygates/create_condition" --data-urlencode "gateName=$GATE" \
      --data-urlencode "metric=$1" --data-urlencode "op=$2" --data-urlencode "error=$3" >/dev/null
  done
fi
# Newer SonarQube versions pre-fill every new gate with "new code" conditions;
# keep exactly the four conditions above so the gate behaves the same everywhere.
api "$SONAR/api/qualitygates/show" --get --data-urlencode "name=$GATE" | python3 -c '
import json, sys
keep = {"coverage", "reliability_rating", "security_rating", "duplicated_lines_density"}
for c in json.load(sys.stdin)["conditions"]:
    if c["metric"] not in keep:
        print(c["id"])' | while read -r cid; do
  api -X POST "$SONAR/api/qualitygates/delete_condition" --data-urlencode "id=$cid" >/dev/null
done
api -X POST "$SONAR/api/qualitygates/set_as_default" --data-urlencode "name=$GATE" >/dev/null
echo "Quality gate '$GATE': coverage >= 80%, reliability A, security A, duplication <= 3% (default)"

token=$(api -X POST "$SONAR/api/user_tokens/generate" --data-urlencode "name=jenkins-$(date +%Y%m%d-%H%M%S)" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
echo "$token" > "$SECRETS/sonar-token"; chmod 600 "$SECRETS/sonar-token"
echo
echo "Jenkins token saved to $SECRETS/sonar-token :"
echo "$token"

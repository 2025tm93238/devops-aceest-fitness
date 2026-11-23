#!/usr/bin/env bash
# Wait for SonarQube to finish processing the analysis, then fail the build
# unless the project's quality gate is OK.
# Usage: quality-gate.sh <path to .scannerwork/report-task.txt>   (needs SONAR_TOKEN)
set -euo pipefail
report=${1:?report-task.txt}
ce_url=$(sed -n 's/^ceTaskUrl=//p' "$report")
server=$(sed -n 's/^serverUrl=//p' "$report")
json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

echo "Waiting for SonarQube background task: $ce_url"
for _ in $(seq 60); do
  task=$(curl -fsS -u "$SONAR_TOKEN:" "$ce_url")
  status=$(echo "$task" | json 'd["task"]["status"]')
  case $status in
    SUCCESS) break ;;
    FAILED|CANCELED) echo "SonarQube task $status"; exit 1 ;;
    *) sleep 5 ;;
  esac
done
[[ $status == SUCCESS ]] || { echo "Timed out waiting for SonarQube"; exit 1; }

analysis=$(echo "$task" | json 'd["task"]["analysisId"]')
gate=$(curl -fsS -u "$SONAR_TOKEN:" "$server/api/qualitygates/project_status?analysisId=$analysis")
echo "$gate" | python3 -c '
import json, sys
s = json.load(sys.stdin)["projectStatus"]
print("Quality gate status: %s" % s["status"])
for c in s.get("conditions", []):
    print("  %-22s %-5s actual=%-8s threshold %s %s" % (c["metricKey"], c["status"],
          c.get("actualValue", "-"), c["comparator"], c.get("errorThreshold", "")))
sys.exit(0 if s["status"] == "OK" else 1)'

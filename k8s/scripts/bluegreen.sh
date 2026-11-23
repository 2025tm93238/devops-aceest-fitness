#!/usr/bin/env bash
# Blue-green: switch ALL traffic between the blue and green deployments.
# Usage: bluegreen.sh switch <blue|green> | status
source "$(dirname "$0")/common.sh"
SVC=service/aceest-bluegreen
case "${1:-status}" in
  switch)
    colour=${2:?blue or green}
    [[ $colour == blue || $colour == green ]] || { echo "blue or green"; exit 2; }
    banner "Switching live traffic to $colour"
    kubectl -n "$NS" patch "$SVC" -p "{\"spec\":{\"selector\":{\"app\":\"aceest\",\"strategy\":\"bluegreen\",\"track\":\"$colour\"}}}" ;;
  status) ;;
  *) echo "usage: $0 switch <blue|green> | status"; exit 2 ;;
esac
banner "Service selector"
kubectl -n "$NS" get "$SVC" -o jsonpath='{.spec.selector}{"\n"}'
banner "Deployments"
kubectl -n "$NS" get deploy -l strategy=bluegreen -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image

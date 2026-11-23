#!/usr/bin/env bash
# Canary release: a small share of traffic goes to the new release.
# Usage: canary.sh start | promote | abort | status
source "$(dirname "$0")/common.sh"
STABLE=deployment/aceest-canary-stable
CANARY=deployment/aceest-canary
case "${1:-status}" in
  start)
    banner "Starting canary: 3 stable ($STABLE_TAG) + 1 canary ($NEW_TAG) = ~25% canary traffic"
    kubectl -n "$NS" set image "$STABLE" app="$REPO:$STABLE_TAG"
    kubectl -n "$NS" set image "$CANARY" app="$REPO:$NEW_TAG"
    kubectl -n "$NS" scale "$CANARY" --replicas=1
    kubectl -n "$NS" rollout status "$STABLE" --timeout=300s
    kubectl -n "$NS" rollout status "$CANARY" --timeout=300s ;;
  promote)
    banner "Promoting canary: stable pods move to $NEW_TAG, canary scaled to 0"
    kubectl -n "$NS" set image "$STABLE" app="$REPO:$NEW_TAG"
    kubectl -n "$NS" rollout status "$STABLE" --timeout=300s
    kubectl -n "$NS" scale "$CANARY" --replicas=0 ;;
  abort)
    banner "Aborting canary: canary scaled to 0, all traffic back on $STABLE_TAG"
    kubectl -n "$NS" scale "$CANARY" --replicas=0 ;;
  status) ;;
  *) echo "usage: $0 start | promote | abort | status"; exit 2 ;;
esac
sleep 2
banner "Canary deployments"
kubectl -n "$NS" get deploy -l strategy=canary -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image

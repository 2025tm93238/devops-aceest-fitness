#!/usr/bin/env bash
# Rolling update with zero downtime, and rollback.
# Usage: rolling.sh deploy <tag> | rollback | status
source "$(dirname "$0")/common.sh"
DEP=deployment/aceest-rolling
case "${1:-status}" in
  deploy)
    tag=${2:?tag e.g. v3.0.0}
    banner "Rolling update to $REPO:$tag (maxSurge=1, maxUnavailable=0)"
    kubectl -n "$NS" set image "$DEP" app="$REPO:$tag"
    kubectl -n "$NS" annotate "$DEP" kubernetes.io/change-cause="rolling update to $tag" --overwrite
    kubectl -n "$NS" rollout status "$DEP" --timeout=300s ;;
  rollback)
    banner "Rolling back to the previous revision"
    kubectl -n "$NS" rollout undo "$DEP"
    kubectl -n "$NS" annotate "$DEP" kubernetes.io/change-cause="rollback to previous revision" --overwrite
    kubectl -n "$NS" rollout status "$DEP" --timeout=300s ;;
  status) ;;
  *) echo "usage: $0 deploy <tag> | rollback | status"; exit 2 ;;
esac
banner "Revision history"
kubectl -n "$NS" rollout history "$DEP"
banner "Pods"
kubectl -n "$NS" get pods -l strategy=rolling -o wide
banner "Live version"
show_version "$(url_for rolling)/version"

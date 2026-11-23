#!/usr/bin/env bash
# Deploy every strategy (rolling, blue-green, canary, A/B, shadow) into namespace "aceest".
source "$(dirname "$0")/common.sh"

banner "Namespace and secret"
kubectl apply -f "$K8S_DIR/base/namespace.yaml"
if ! kubectl -n "$NS" get secret aceest-secrets >/dev/null 2>&1; then
  kubectl -n "$NS" create secret generic aceest-secrets \
    --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
fi

banner "Applying manifests"
for d in rolling blue-green canary ab-testing shadow; do
  kubectl apply -f "$K8S_DIR/$d/"
done

kubectl -n "$NS" annotate deployment/aceest-rolling \
  kubernetes.io/change-cause="initial deploy $STABLE_TAG" --overwrite >/dev/null

banner "Waiting for all deployments to become ready (first run pulls images, ~2-4 min)"
for dep in $(kubectl -n "$NS" get deploy -o name); do
  kubectl -n "$NS" rollout status "$dep" --timeout=300s
done

"$(dirname "$0")/urls.sh"

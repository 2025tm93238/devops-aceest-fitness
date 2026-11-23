# Kubernetes deployment strategies

All five strategies run side by side in namespace `aceest` on Minikube, each on
its own NodePort. Every strategy compares the current release **v2.1.0** with the
new release **v3.0.0**; `GET /version` shows which release and track answered.

| Strategy | Manifest | NodePort | How traffic is split | Rollback |
|---|---|---|---|---|
| Rolling update | `rolling/` | 30080 | Pods replaced one at a time (`maxSurge: 1`, `maxUnavailable: 0`) | `rolling.sh rollback` (`kubectl rollout undo`) |
| Blue-green | `blue-green/` | 30081 | Service selector points 100% at blue **or** green | `bluegreen.sh switch blue` |
| Canary | `canary/` | 30082 | One Service over 3 stable + 1 canary pods = ~25% canary | `canary.sh abort` (canary scaled to 0) |
| A/B testing | `ab-testing/` | 30083 | nginx router: header `X-Variant: B` or cookie `variant=B` → v3.0.0 | Route everyone to A |
| Shadow | `shadow/` | 30084 | nginx `mirror`: users get v2.1.0, a copy of each request goes to v3.0.0 and its reply is discarded | Delete the shadow deployment |

Readiness and liveness probes on `/health` keep unready pods out of every Service.
Each pod keeps its SQLite file in an `emptyDir`, so data is per pod; this keeps the
demo self-contained (a production setup would use a shared managed database).

## Scripts (`scripts/`)

```bash
./k8s/scripts/deploy-all.sh                 # namespace, secret, every strategy
./k8s/scripts/urls.sh                       # endpoint URL per strategy
./k8s/scripts/traffic.sh canary 40          # who answered N requests
./k8s/scripts/rolling.sh deploy v3.0.0      # rolling update   | rollback | status
./k8s/scripts/bluegreen.sh switch green     # blue <-> green   | status
./k8s/scripts/canary.sh start               # start | promote | abort | status
./k8s/scripts/abtest.sh                     # group A vs group B routing
./k8s/scripts/shadow.sh                     # primary answers, shadow receives copies
```

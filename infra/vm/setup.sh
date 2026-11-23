#!/usr/bin/env bash
# One command to (re)build the ACEest CI/CD environment on the BITS lab VM.
#
# The lab VM wipes everything outside ~/workspace when it stops, so this script
# is idempotent and keeps everything worth keeping under ~/workspace:
#   ~/workspace/bin         kubectl + minikube binaries (downloaded once)
#   ~/workspace/.minikube   minikube cache (images, ISO) -> faster restarts
#   ~/workspace/sonarqube   SonarQube data -> project, quality gate, token survive
#
# Usage:  ./infra/vm/setup.sh          (run from the repository root)
set -euo pipefail

WS="$HOME/workspace"
BIN="$WS/bin"
KUBECTL_VERSION=v1.31.0
MINIKUBE_VERSION=v1.34.0
K8S_VERSION=v1.31.0
SONAR_IMAGE=sonarqube:community
export MINIKUBE_HOME="$WS/.minikube"

step() { printf '\n\033[1;34m[%s] %s\033[0m\n' "$(date +%H:%M:%S)" "$*"; }

step "1/6 Kernel settings required by SonarQube's Elasticsearch"
sudo sysctl -q -w vm.max_map_count=524288 fs.file-max=131072

step "2/6 kubectl $KUBECTL_VERSION and minikube $MINIKUBE_VERSION"
mkdir -p "$BIN"
[[ -x "$BIN/kubectl" ]] || curl -fsSL -o "$BIN/kubectl" \
  "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl"
[[ -x "$BIN/minikube" ]] || curl -fsSL -o "$BIN/minikube" \
  "https://storage.googleapis.com/minikube/releases/$MINIKUBE_VERSION/minikube-linux-amd64"
chmod +x "$BIN/kubectl" "$BIN/minikube"
# /usr/local/bin so the jenkins user can run kubectl too (re-installed every session).
sudo install -m 0755 "$BIN/kubectl" "$BIN/minikube" /usr/local/bin/
grep -q 'MINIKUBE_HOME' "$HOME/.bashrc" 2>/dev/null || \
  echo "export MINIKUBE_HOME=$WS/.minikube" >> "$HOME/.bashrc"

step "3/6 Docker access for Jenkins"
if ! id -nG jenkins | grep -qw docker; then
  sudo usermod -aG docker jenkins
  sudo systemctl restart jenkins
fi
systemctl is-active --quiet jenkins || sudo systemctl start jenkins

step "4/6 SonarQube ($SONAR_IMAGE) on http://localhost:9000"
mkdir -p "$WS/sonarqube/data" "$WS/sonarqube/extensions" "$WS/sonarqube/logs"
chmod -R a+rwX "$WS/sonarqube"
if [[ "$(docker inspect -f '{{.State.Running}}' sonarqube 2>/dev/null)" != "true" ]]; then
  docker rm -f sonarqube >/dev/null 2>&1 || true
  docker run -d --name sonarqube --restart unless-stopped -p 9000:9000 \
    -v "$WS/sonarqube/data:/opt/sonarqube/data" \
    -v "$WS/sonarqube/extensions:/opt/sonarqube/extensions" \
    -v "$WS/sonarqube/logs:/opt/sonarqube/logs" \
    "$SONAR_IMAGE" >/dev/null
fi

step "5/6 Minikube cluster (docker driver, 2 CPU / 2.6 GB)"
if ! minikube status >/dev/null 2>&1; then
  minikube start --driver=docker --cpus=2 --memory=2600 --kubernetes-version="$K8S_VERSION"
fi
# Give Jenkins its own copy of the kubeconfig (certificates embedded).
JENKINS_HOME_DIR=$(getent passwd jenkins | cut -d: -f6)
kubectl config view --flatten --minify > /tmp/aceest-kubeconfig
sudo install -D -o jenkins -g jenkins -m 0600 /tmp/aceest-kubeconfig "$JENKINS_HOME_DIR/.kube/config"
rm -f /tmp/aceest-kubeconfig

step "6/6 Waiting for SonarQube to report UP (first start takes 2-4 minutes)"
for _ in $(seq 60); do
  status=$(curl -s http://localhost:9000/api/system/status | grep -o '"status":"[A-Z_]*"' || true)
  [[ $status == '"status":"UP"' ]] && break
  sleep 5
done

"$(dirname "$0")/status.sh"

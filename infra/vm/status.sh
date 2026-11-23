#!/usr/bin/env bash
# Toolchain and service status of the ACEest CI/CD environment (screenshot SS1).
export MINIKUBE_HOME="${MINIKUBE_HOME:-$HOME/.minikube}"
row() { printf '%-14s %s\n' "$1" "$2"; }

echo "===== ACEest CI/CD toolchain on $(hostname) ====="
row "OS"          "$(cat /etc/rocky-release 2>/dev/null || uname -sr)"
row "Git"         "$(git --version)"
row "Python"      "$(python3 --version 2>&1)"
row "Java"        "$(java -version 2>&1 | head -1)"
row "Docker"      "$(docker --version)"
row "kubectl"     "$(kubectl version --client 2>/dev/null | head -1)"
row "minikube"    "$(minikube version --short 2>/dev/null)"
row "Jenkins"     "$(systemctl is-active jenkins) (http://localhost:8080)"
row "SonarQube"   "$(curl -s http://localhost:9000/api/system/status | grep -o '"status":"[A-Z_]*"' || echo 'not reachable') (http://localhost:9000)"
row "Minikube"    "$(minikube status --format '{{.Host}}/{{.Kubelet}}/{{.APIServer}}' 2>/dev/null || echo stopped)"
row "Cluster"     "$(kubectl get nodes --no-headers 2>/dev/null | awk '{print $1, $2, $5}')"

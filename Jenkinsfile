// ACEest Fitness & Gym - Jenkins CI/CD pipeline.
//
// Jenkins polls GitHub every 2 minutes and, for every new commit on main:
//   lint -> unit tests in a container -> SonarQube analysis -> quality gate ->
//   package artifacts -> build image -> container smoke test -> push to Docker Hub ->
//   rolling update on Minikube -> smoke test -> automatic rollback on failure.
//
// Jenkins credentials used (Manage Jenkins -> Credentials):
//   dockerhub-creds  Username with password  (Docker Hub user + access token)
//   sonar-token      Secret text             (SonarQube user token)
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    parameters {
        booleanParam(name: 'SIMULATE_FAILED_DEPLOY', defaultValue: false,
            description: 'Make the post-deployment smoke test fail to demonstrate automatic rollback')
    }

    environment {
        IMAGE          = '2025tm93238/aceest-fitness'
        NS             = 'aceest'
        SONAR_HOST_URL = 'http://localhost:9000'
        TEST_IMAGE     = "aceest-fitness:test-${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.APP_VERSION = sh(returnStdout: true,
                        script: "sed -n 's/^__version__ = \"\\(.*\\)\"/\\1/p' version.py").trim()
                    env.IMAGE_TAG = "v${env.APP_VERSION}-build.${env.BUILD_NUMBER}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.APP_VERSION}"
                }
                echo "Building ACEest v${env.APP_VERSION} as ${env.IMAGE}:${env.IMAGE_TAG}"
            }
        }

        stage('Build test image') {
            steps {
                sh 'docker build --target test -t "$TEST_IMAGE" .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm "$TEST_IMAGE" flake8 .'
            }
        }

        stage('Unit tests (in container)') {
            steps {
                sh '''
                    mkdir -p reports
                    docker run --rm --user "$(id -u):$(id -g)" \
                      -e COVERAGE_FILE=/tmp/.coverage -e DATABASE=/tmp/aceest.db \
                      -v "$WORKSPACE/reports:/app/reports" "$TEST_IMAGE" \
                      pytest -q -p no:cacheprovider \
                        --junitxml=reports/junit.xml \
                        --cov=. --cov-report=term --cov-report=xml:reports/coverage.xml
                '''
            }
            post {
                always { junit 'reports/junit.xml' }
            }
        }

        stage('SonarQube analysis') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    sh '''
                        docker run --rm --network host --user "$(id -u):$(id -g)" \
                          -e SONAR_HOST_URL="$SONAR_HOST_URL" -e SONAR_TOKEN="$SONAR_TOKEN" \
                          -e SONAR_USER_HOME=/usr/src/.sonar \
                          -v "$WORKSPACE:/usr/src" sonarsource/sonar-scanner-cli:11 \
                          -Dsonar.projectVersion="$APP_VERSION" \
                          -Dsonar.working.directory=/usr/src/.scannerwork
                    '''
                }
            }
        }

        stage('Quality gate') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    timeout(time: 5, unit: 'MINUTES') {
                        sh './infra/ci/quality-gate.sh .scannerwork/report-task.txt'
                    }
                }
            }
        }

        stage('Package artifacts') {
            steps {
                sh '''
                    mkdir -p dist
                    git archive --format=tar.gz --prefix="aceest-fitness-$APP_VERSION/" \
                      -o "dist/aceest-fitness-$IMAGE_TAG.tar.gz" HEAD
                    printf '%s\\n' "$IMAGE:$IMAGE_TAG" "$IMAGE:v$APP_VERSION" > dist/image-tags.txt
                    git log -1 --format='commit %H%nauthor %an%ndate %cI%n%n%s' > dist/build-info.txt
                '''
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --target production --build-arg APP_VERSION="$APP_VERSION" \
                      -t "$IMAGE:$IMAGE_TAG" -t "$IMAGE:v$APP_VERSION" -t "$IMAGE:latest" .
                '''
            }
        }

        stage('Container smoke test') {
            steps {
                sh './infra/ci/container-smoke-test.sh "$IMAGE:$IMAGE_TAG" "$APP_VERSION"'
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        docker push "$IMAGE:$IMAGE_TAG"
                        docker push "$IMAGE:v$APP_VERSION"
                        docker push "$IMAGE:latest"
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes (rolling update)') {
            steps {
                sh '''
                    kubectl apply -f k8s/base/namespace.yaml
                    kubectl -n "$NS" get secret aceest-secrets >/dev/null 2>&1 || \
                      kubectl -n "$NS" create secret generic aceest-secrets \
                        --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
                        --from-literal=ADMIN_PASSWORD=admin
                    kubectl -n "$NS" get deploy aceest-rolling >/dev/null 2>&1 || kubectl apply -f k8s/rolling/
                '''
                script { env.DEPLOY_STARTED = 'true' }
                sh '''
                    kubectl -n "$NS" set image deploy/aceest-rolling app="$IMAGE:$IMAGE_TAG"
                    kubectl -n "$NS" annotate deploy/aceest-rolling --overwrite \
                      kubernetes.io/change-cause="Jenkins build #$BUILD_NUMBER: $IMAGE_TAG"
                    kubectl -n "$NS" rollout status deploy/aceest-rolling --timeout=240s
                '''
            }
        }

        stage('Smoke test (deployment)') {
            steps {
                sh '''
                    expected="$APP_VERSION"
                    if [ "$SIMULATE_FAILED_DEPLOY" = "true" ]; then
                      expected="0.0.0-simulated-failure"
                      echo "SIMULATE_FAILED_DEPLOY is set: expecting $expected so this stage fails"
                    fi
                    ./infra/ci/k8s-smoke-test.sh "$NS" 30080 "$expected"
                '''
            }
        }
    }

    post {
        success {
            echo "Released ${env.IMAGE}:${env.IMAGE_TAG} - tests, quality gate and smoke tests passed."
        }
        failure {
            script {
                if (env.DEPLOY_STARTED == 'true') {
                    echo 'Deployment failed its checks - rolling back to the last stable revision.'
                    sh '''
                        kubectl -n "$NS" rollout undo deploy/aceest-rolling
                        kubectl -n "$NS" annotate deploy/aceest-rolling --overwrite \
                          kubernetes.io/change-cause="automatic rollback after failed build #$BUILD_NUMBER"
                        kubectl -n "$NS" rollout status deploy/aceest-rolling --timeout=240s
                        kubectl -n "$NS" rollout history deploy/aceest-rolling
                        ./infra/ci/k8s-smoke-test.sh "$NS" 30080 ""
                    '''
                }
            }
        }
        always {
            archiveArtifacts artifacts: 'dist/*, reports/*.xml', allowEmptyArchive: true, fingerprint: true
            sh 'docker rmi "$TEST_IMAGE" >/dev/null 2>&1 || true; docker image prune -f >/dev/null 2>&1 || true'
        }
    }
}

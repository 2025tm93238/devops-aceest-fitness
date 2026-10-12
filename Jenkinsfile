// Jenkins declarative pipeline for the ACEest Fitness BUILD stage.
// Jenkins pulls the latest code from GitHub (configured in the job) and performs
// a clean Docker build, then validates it by running the tests in a container.
pipeline {
    agent any

    options {
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker image') {
            steps {
                sh 'docker build --target production -t aceest-fitness:${BUILD_NUMBER} .'
            }
        }

        stage('Test in container') {
            steps {
                sh 'docker build --target test -t aceest-fitness:test-${BUILD_NUMBER} .'
                sh 'docker run --rm aceest-fitness:test-${BUILD_NUMBER}'
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    docker run -d -p 5000:5000 --name aceest-${BUILD_NUMBER} aceest-fitness:${BUILD_NUMBER}
                    sleep 3
                    curl --fail http://localhost:5000/health
                    docker rm -f aceest-${BUILD_NUMBER}
                '''
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f || true'
        }
        success {
            echo 'BUILD succeeded: image built and tests passed.'
        }
        failure {
            echo 'BUILD failed: check the stage logs above.'
        }
    }
}

#!/bin/bash

REPO_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}"

# Get registration token from GitHub API
REG_TOKEN=$(curl -s -X POST \
    -H "Authorization: token ${ACCESS_TOKEN}" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/runners/registration-token" \
    | jq -r .token)

if [ "$REG_TOKEN" == "null" ] || [ -z "$REG_TOKEN" ]; then
    echo "ERROR: Failed to get registration token. Check your ACCESS_TOKEN."
    exit 1
fi

cd /home/docker/actions-runner

# Configure the runner
./config.sh --url "${REPO_URL}" --token "${REG_TOKEN}" --name "caprover-runner-${HOSTNAME}" --labels "self-hosted,linux,caprover" --unattended --replace

# Cleanup function for graceful shutdown
cleanup() {
    echo "Removing runner..."
    ./config.sh remove --token "${REG_TOKEN}"
}

trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

# Run the runner
./run.sh & wait $!

#!/bin/bash
set -e

# Best guess to check if running build.sh from project root or this directory
if [ -f build.sh ]; then
    cd ../..
fi

if [ ! -f pyproject.toml ]; then
    echo "pyproject.toml not found!"
    exit 1
fi

echo "Packaging Prometheus Mirror"
docker build -t stackstatelab/prometheus-mirror -f ./deploy/docker/Dockerfile .

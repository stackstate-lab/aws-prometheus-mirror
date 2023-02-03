#!/bin/bash
set -e

docker login -u stackstatelab
docker push stackstatelab/prometheus-mirror:latest
#!/bin/bash

if [ -f "docker/compose.yaml" ]; then
  COMPOSE_FILE="docker/compose.yaml"
elif [ -f "docker/compose.yml" ]; then
  COMPOSE_FILE="docker/compose.yml"
else
  echo "No compose file found"
  exit 1
fi

docker compose -f "$COMPOSE_FILE" --project-directory . up
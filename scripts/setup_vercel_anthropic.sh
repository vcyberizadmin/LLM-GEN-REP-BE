#!/usr/bin/env bash
# Configure Anthropic API key secret and environment variable on Vercel
# Requires: Vercel CLI installed and user logged in
# Usage: export ANTHROPIC_API_KEY=your_api_key && ./scripts/setup_vercel_anthropic.sh [all|production|preview|development]

set -euo pipefail

SECRET_NAME="anthropic_api_key"
ENV_NAME="ANTHROPIC_API_KEY"
TARGET="${1:-all}"
TARGETS=("development" "preview" "production")

if ! command -v vercel >/dev/null; then
  echo "Vercel CLI not found. Install with 'npm install -g vercel'" >&2
  exit 1
fi

# Ensure API key is provided via environment
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ANTHROPIC_API_KEY environment variable not set." >&2
  exit 1
fi

# Check if the secret exists
if ! vercel secrets ls | grep -q "\b$SECRET_NAME\b"; then
  echo "Adding Vercel secret '$SECRET_NAME'"
  vercel secrets add "$SECRET_NAME" "$ANTHROPIC_API_KEY"
else
  echo "Secret '$SECRET_NAME' already exists"
fi

# Set environment variable for requested targets
if [ "$TARGET" = "all" ]; then
  TARGETS_TO_SET=("${TARGETS[@]}")
else
  TARGETS_TO_SET=("$TARGET")
fi

for env in "${TARGETS_TO_SET[@]}"; do
  if ! vercel env ls "$env" | awk '{print $2}' | grep -q "^$ENV_NAME$"; then
    echo "Linking env var '$ENV_NAME' to secret '$SECRET_NAME' for $env"
    printf '@%s\n' "$SECRET_NAME" | vercel env add "$ENV_NAME" "$env" --yes > /dev/null
  else
    echo "Env var '$ENV_NAME' already set for $env"
  fi
done

echo "Environment variable configured. Trigger a redeploy with 'vercel deploy'"

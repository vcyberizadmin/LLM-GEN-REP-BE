#!/usr/bin/env bash
# Configure Anthropic API key secret and environment variable on Vercel
# Requires: Vercel CLI installed and user logged in
# Usage: export ANTHROPIC_API_KEY=your_api_key && ./scripts/setup_vercel_anthropic.sh [production|preview|development]

set -euo pipefail

SECRET_NAME="anthropic_api_key"
ENV_NAME="ANTHROPIC_API_KEY"
ENV_TARGET="${1:-preview}"

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

# Check if the environment variable exists for the target environment
if ! vercel env ls | grep -q "\b$ENV_NAME\b"; then
  echo "Linking env var '$ENV_NAME' to secret '$SECRET_NAME' for $ENV_TARGET"
  printf '@%s\n' "$SECRET_NAME" | vercel env add "$ENV_NAME" "$ENV_TARGET" --yes > /dev/null
fi

echo "Environment variable configured. Trigger a redeploy with 'vercel deploy'"

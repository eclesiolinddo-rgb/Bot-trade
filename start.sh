#!/usr/bin/env bash
set -euo pipefail

echo "Installing dependencies..."
if [ -f package.json ]; then
  # Use npm ci for reproducible installs if package-lock.json is present, otherwise fallback to npm install
  if [ -f package-lock.json ]; then
    npm ci --no-audit --no-fund
  else
    npm install --no-audit --no-fund
  fi

  echo "Starting app..."
  npm run start
  exit 0
fi

echo "No package.json found. Nothing to run." >&2
exit 1

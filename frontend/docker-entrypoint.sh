#!/bin/sh
set -eu

LOCKFILE_HASH_FILE="node_modules/.package-lock.hash"
CURRENT_HASH="$(sha256sum package.json package-lock.json | sha256sum | awk '{print $1}')"
API_BASE_URL_VALUE="${API_BASE_URL:-http://localhost:8000/api}"

if [ ! -d node_modules ] || [ ! -f "$LOCKFILE_HASH_FILE" ] || [ "$(cat "$LOCKFILE_HASH_FILE")" != "$CURRENT_HASH" ]; then
    echo "Refreshing frontend dependencies with npm ci..."
    npm ci
    printf '%s' "$CURRENT_HASH" > "$LOCKFILE_HASH_FILE"
fi

cat > public/app-config.js <<EOF
window.__APP_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL_VALUE}"
};
EOF

exec "$@"

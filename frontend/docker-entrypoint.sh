#!/bin/sh
set -eu

LOCKFILE_HASH_FILE="node_modules/.package-lock.hash"
CURRENT_HASH="$(sha256sum package.json package-lock.json | sha256sum | awk '{print $1}')"
API_BASE_URL_VALUE="${API_BASE_URL:-http://localhost:8000/api}"
REPORTS_API_BASE_URL_VALUE="${REPORTS_API_BASE_URL:-http://localhost:8010/api}"
AUTH_ENTRA_ENABLED_VALUE="${ENTRA_AUTH_ENABLED:-false}"
AUTH_LOCAL_ENABLED_VALUE="${LOCAL_ADMIN_ENABLED:-false}"
ENTRA_AUTHORITY_VALUE="${ENTRA_AUTHORITY:-}"
ENTRA_CLIENT_ID_VALUE="${ENTRA_CLIENT_ID:-}"
ENTRA_REDIRECT_URI_VALUE="${ENTRA_REDIRECT_URI:-}"
ENTRA_POST_LOGOUT_REDIRECT_URI_VALUE="${ENTRA_POST_LOGOUT_REDIRECT_URI:-}"
ENTRA_SCOPES_VALUE="${ENTRA_SCOPES:-openid profile email}"

if [ ! -d node_modules ] || [ ! -f "$LOCKFILE_HASH_FILE" ] || [ "$(cat "$LOCKFILE_HASH_FILE")" != "$CURRENT_HASH" ]; then
    echo "Refreshing frontend dependencies with npm ci..."
    npm ci
    printf '%s' "$CURRENT_HASH" > "$LOCKFILE_HASH_FILE"
fi

cat > public/app-config.js <<EOF
window.__APP_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL_VALUE}",
  reportsApiBaseUrl: "${REPORTS_API_BASE_URL_VALUE}",
  authEntraEnabled: ${AUTH_ENTRA_ENABLED_VALUE},
  authLocalEnabled: ${AUTH_LOCAL_ENABLED_VALUE},
  entraAuthority: "${ENTRA_AUTHORITY_VALUE}",
  entraClientId: "${ENTRA_CLIENT_ID_VALUE}",
  entraRedirectUri: "${ENTRA_REDIRECT_URI_VALUE}",
  entraPostLogoutRedirectUri: "${ENTRA_POST_LOGOUT_REDIRECT_URI_VALUE}",
  entraScopes: "${ENTRA_SCOPES_VALUE}"
};
EOF

exec "$@"

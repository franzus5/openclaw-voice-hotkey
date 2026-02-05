#!/usr/bin/env bash
set -euo pipefail

# Pair voice assistant with OpenClaw by reusing the existing CLI device
# Steps:
# 1. Find an existing operator CLI device (clientId=="cli")
# 2. Rotate a new token for it with read/write scopes
# 3. Write token + deviceId into config.json (gatewayToken + deviceId)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CONFIG_FILE="config.json"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "❌ 'openclaw' CLI not found in PATH."
  echo "   Make sure OpenClaw CLI is installed and available."
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "❌ 'jq' is required but not installed."
  echo "   Install it with: brew install jq"
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ $CONFIG_FILE not found in $ROOT_DIR"
  exit 1
fi

echo "🔍 Looking for existing operator CLI device…"
DEVICES_JSON="$(openclaw devices list --json)"

DEVICE_ID="$(printf '%s' "$DEVICES_JSON" | jq -r '.paired[] | select(.clientId=="cli" and .role=="operator") | .deviceId' | head -n1)"

if [ -z "$DEVICE_ID" ] || [ "$DEVICE_ID" = "null" ]; then
  echo "❌ No paired operator CLI device found."
  echo "   Run 'openclaw devices list --json' to inspect devices manually."
  exit 1
fi

echo "✅ Found CLI device: $DEVICE_ID"

echo "🔑 Rotating token for this device (scopes: operator.read, operator.write)…"
ROTATE_JSON="$(openclaw devices rotate \
  --device "$DEVICE_ID" \
  --role operator \
  --scope operator.read \
  --scope operator.write \
  --json)"

TOKEN="$(printf '%s' "$ROTATE_JSON" | jq -r '.token')"

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Failed to obtain device token from rotate response."
  echo "   Raw response: $ROTATE_JSON"
  exit 1
fi

echo "✅ Got device token: $TOKEN"

echo "📝 Updating $CONFIG_FILE (gatewayToken + deviceId)…"
TMP_CONFIG="$(mktemp)"

jq \
  --arg token "$TOKEN" \
  --arg device "$DEVICE_ID" \
  '.gatewayToken = $token | .deviceId = $device' \
  "$CONFIG_FILE" > "$TMP_CONFIG"

mv "$TMP_CONFIG" "$CONFIG_FILE"

echo "✅ Updated $CONFIG_FILE"

echo "🎉 Pairing complete! Voice assistant can now connect via WebSocket using:"
echo "   deviceId   = $DEVICE_ID"
echo "   gatewayToken = $TOKEN"
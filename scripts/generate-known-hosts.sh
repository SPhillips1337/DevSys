#!/usr/bin/env bash
set -euo pipefail

# generate-known-hosts.sh
# Usage: ./generate-known-hosts.sh <host> [port] [out-file]
# Example: ./generate-known-hosts.sh 192.168.5.69 22 ./secrets/remote_known_hosts

HOST=${1:-}
PORT=${2:-22}
OUT=${3:-./secrets/remote_known_hosts}

if [ -z "$HOST" ]; then
  echo "Usage: $0 <host> [port] [out-file]"
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

echo "Generating known_hosts for $HOST:$PORT -> $OUT"
ssh-keyscan -p "$PORT" "$HOST" > "$OUT" 2>/dev/null || {
  echo "ssh-keyscan failed; ensure the host is reachable and port is correct"
  exit 1
}

chmod 644 "$OUT"

echo "known_hosts saved to $OUT"
exit 0

#!/usr/bin/env bash
# End-to-end demo for the Verifiable Indexer Lyquid.
#
# Brings up the native Lyquor localnet (single or four-node mesh), deploys the
# Lyquid, configures the oracle committee, seeds each node with the same
# replay batch, triggers a committee-certified index update, and prints the
# verified records, committee and history over HTTP.
#
# Usage: scripts/run_demo.sh [single|multi]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LDK_DIR="$HOME/.shakenup/ldk"
DEMO_LIB="$LDK_DIR/lyquid-examples/scripts/lib/demo.sh"
TOPOLOGY="${1:-multi}"

# On localnet the HTTP exports live on the Lyquid virtual host. `shaker serve`
# proxies that host through a plain localhost port; we bind 127.0.0.1:8080.
SERVE_LISTEN="127.0.0.1:8080"
SERVE_API="http://127.0.0.1:8080"
SERVE_PID=""

cleanup_all() {
    if [[ -n "$SERVE_PID" ]] && kill -0 "$SERVE_PID" >/dev/null 2>&1; then
        kill -TERM "$SERVE_PID" 2>/dev/null || true
    fi
    demo_cleanup
}

export PATH="$HOME/.shakenup/bin:$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

# Deterministic demo batch: a small set of transfers for one address.
DEMO_ADDRESS="0x1111111111111111111111111111111111111111"
DEMO_HEAD_BLOCK=42000

SEED_PAYLOAD="$(python3 - "$DEMO_ADDRESS" "$DEMO_HEAD_BLOCK" <<'PY'
import json, sys
address, head = sys.argv[1], int(sys.argv[2])
events = [
    {"block": 41990, "tx_index": 0, "counterparty": "0xAlice", "amount": 500},
    {"block": 41991, "tx_index": 2, "counterparty": "0xBob", "amount": -180},
    {"block": 41995, "tx_index": 1, "counterparty": "0xAlice", "amount": 220},
    {"block": 42000, "tx_index": 0, "counterparty": "0xCarol", "amount": 90},
]
print(json.dumps({"address": address, "head_block": head, "events": events}))
PY
)"

# Source the shared localnet / deployment helpers from the installed LDK.
# shellcheck source=/dev/null
source "$DEMO_LIB"

echo "=== Starting localnet ($TOPOLOGY) ==="
demo_start_localnet "$TOPOLOGY"
trap cleanup_all EXIT

echo "=== Building and deploying the indexer Lyquid ==="
demo_deploy "verifiable-indexer" "$PROJECT_DIR/Cargo.toml"
demo_wait_for_lyquid "get_node_ids() returns (string[])"

echo "=== Starting the local HTTP proxy for $LYQUID_ID ==="
shaker serve --endpoint "$DEMO_PRIMARY_WS" --listen "$SERVE_LISTEN" "$LYQUID_ID" &
SERVE_PID=$!
sleep 2

echo "=== Configuring the committee ==="
demo_send "configure_committee(bytes32[])" "$(demo_node_ids_array)"
demo_activate_oracle "indexer"
demo_wait_for_committee "${#DEMO_NODE_WS[@]}"

echo "=== Seeding each node with the replay batch ==="
for index in "${!DEMO_NODE_WS[@]}"; do
    demo_expect_true \
        "$(demo_call_at "${DEMO_NODE_WS[$index]}" "set_local_seed(string) returns (bool)" "$SEED_PAYLOAD")" \
        "set_local_seed on node $((index + 1))"
done

echo "=== Triggering committee-certified replay ==="
demo_expect_true "$(demo_call "certify_replay() returns (bool)")" "certify_replay"

# Give the oracle committee a moment to finalize the certified call.
sleep 3

echo "=== Committee configuration (HTTP) ==="
curl -sf "$SERVE_API/api/committee" | jq .

echo "=== Verified records (HTTP) ==="
curl -sf "$SERVE_API/api/records" | jq .

echo "=== History snapshots (HTTP) ==="
curl -sf "$SERVE_API/api/history" | jq .

if [[ "${DEMO_HEADLESS:-0}" == "1" ]]; then
    echo "=== Headless run: tearing down localnet. ==="
    demo_cleanup
    exit 0
fi

echo "=== Demo complete. Localnet stays up until Ctrl-C. ==="
wait "$DEMO_LOCALNET_PID"

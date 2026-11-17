# Verifiable Indexer — Committee-Certified On-Chain Index (CS5298 Final Project)

A Lyquid application built on the Lyquor Network LDK (Rust, LDK 0.8.4). A committee
of hosting nodes replays a local batch of ledger events for a queried address,
runs the two-phase oracle flow to reconcile their observations, and — once the
configured threshold agrees — stores a certified index record and a rolling
history snapshot on the replicated network state. Other applications on the
network can read the verified result and its history in the same call, instead of
trusting a single off-chain data provider.

This project addresses **Direction 3: Verifiable Indexer** of the CS5298 final
project.

## What it demonstrates

- Each node computes a balance, event count and distinct-counterparty count by
  replaying a deterministic, canonically ordered event batch.
- The committee oracle (`indexer` topic) proposes each node's own observation,
  then a pure aggregation function tallies identical states grouped by head
  block, waits below the threshold, or flags a split as disputed.
- A reaching threshold produces a certified call that writes the agreed record,
  the signing committee nodes, and the number of candidate observations to the
  network state.
- A rolling history cache keeps the most recent finalized snapshots with their
  sequence id, timestamp and chain position.
- A small hosted single-page UI and three HTTP JSON endpoints expose the
  committee, records and history.

## Repository layout

```
verifiable-indexer/
├── Cargo.toml              # Lyquid crate manifest and pinned dependencies
├── build.rs                # WASM stack-pointer export required by the LDK
├── rust-toolchain.toml     # Pinned Rust toolchain for the WASM target
├── .cargo/config.toml      # Build target and git-fetch settings
├── assets/
│   └── index.html          # Hosted static SPA served by the Lyquid
├── src/
│   ├── lib.rs              # State model, oracle methods, ETH/HTTP exports
│   └── indexer/
│       └── mod.rs          # Deterministic replay, aggregation, consensus, tests
├── tests/
│   ├── simulated_user_session.py  # Read-only automated user-session harness
│   └── session-results.json       # Recorded 10/10 passing session log
├── demo/
│   └── README.md           # 3-minute recording script and ZIP packaging notes
├── report/
│   ├── build_report.py     # Report PDF generator (reportlab)
│   ├── make_figure.py       # Architecture diagram generator (Pillow)
│   └── figures/             # Generated architecture diagram
└── scripts/
    └── run_demo.sh         # Bring up localnet, deploy, certify, read results
```

## Prerequisites

- Rust (the pinned toolchain in `rust-toolchain.toml`; WASM target
  `wasm32-unknown-unknown`).
- Lyquor LDK 0.8.4 toolchain on `PATH`: `shaker`, `lyquor`, `ladle`, and the
  Foundry tools (`cast`, `anvil`). The LDK native devnet does not require Docker.
- `curl`, `jq`, and `python3` for the demo script.

## Build

```bash
shaker build Cargo.toml
```

The pack is written to
`lyquid_tools_target/release/verifiable-indexer/lyquid.pack`.

## Unit tests

The deterministic replay and consensus rules live in `src/indexer/mod.rs` and
run as guest tests through the LDK test harness:

```bash
shaker test Cargo.toml
```

The suite covers balance/party aggregation, replay order independence,
threshold agreement, waiting below threshold, split-tally disputes, and stale
head-block exclusion.

## Simulated-user session

After the demo network is running (see below), the read-only session harness
replays the same endpoints a visitor would open and asserts committee
membership, threshold, record presence, balance, event count, counterparties,
head block, signer count, candidate count, and history presence:

```bash
python3 tests/simulated_user_session.py
```

Results are written to `tests/session-results.json`. The recorded run shows
10/10 checks passed.

## End-to-end demo

```bash
bash scripts/run_demo.sh multi    # four-node localnet (default)
bash scripts/run_demo.sh single   # one-node localnet
```

The script:

1. Starts the native Lyquor localnet (`multi` = shared Anvil + four-node mesh).
2. Builds and deploys the Lyquid through `shaker deploy`.
3. Registers the four nodes as the oracle committee and activates the oracle
   epoch.
4. Loads the same deterministic seed batch on every node.
5. Calls `certify_replay()` to request a committee-certified update.
6. Starts a local `shaker serve` proxy and reads `/api/committee`,
   `/api/records`, and `/api/history`.

Expected demo batch (address `0x1111…1111`, head block 42000, four events):

| Replay result | Value |
|---|---|
| Balance | 630 |
| Event count | 4 |
| Distinct counterparties | 3 |
| Committee threshold | 3 of 4 |
| Signing committee nodes | 3 |

## Exports

Ethereum ABI methods (instance unless noted):

- `constructor()` — network, records the initializer.
- `configure_committee(bytes32[]) returns (bool)` — network, initializer only.
- `set_local_seed(string) returns (bool)` — loads a JSON seed batch.
- `get_record(string) returns (string)` — one record as JSON.
- `list_records() returns (string)` — all records as JSON.
- `get_node_ids() returns (string[])` — configured committee node ids.
- `certify_replay() returns (bool)` — request a certified committee replay.

HTTP endpoints (served on the Lyquid virtual host; proxied by `shaker serve` on
localnet):

- `/` — static SPA.
- `/api/committee` — committee node ids and threshold.
- `/api/records` — certified index records.
- `/api/history` — rolling finalized snapshots.

## Notes and limitations

- The devnet seed batch is injected through `set_local_seed`; a production
  deployment would pull events from a hosted archive node through the host API.
- This is a single-person group. External validation in the report is performed
  by a repeatable automated simulated-user session rather than human interviews.

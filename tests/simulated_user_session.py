#!/usr/bin/env python3
"""Repeatable simulated-user session for the Verifiable Indexer Lyquid.

Context (CS5298, single-person group): no external human interview was
available, so the "user testing" deliverable is an automated simulated-user
session. This harness drives the same read-only HTTP endpoints a web visitor
would open, checks the observed state against the deterministic demo batch,
and records the outcome in ``tests/session-results.json``.

Prerequisite: the demo localnet must already be running and serving the
proxy on ``http://127.0.0.1:8080``. Start it in another terminal with::

    DEMO_HEADLESS=0 bash scripts/run_demo.sh multi

Then run this harness::

    python3 tests/simulated_user_session.py

The script performs read-only requests only; it does not mutate network state.
"""

import json
import sys
import urllib.request
from pathlib import Path

API_BASE = "http://127.0.0.1:8080"
EXPECTED_ADDRESS = "0x1111111111111111111111111111111111111111"
EXPECTED_BALANCE = 630
EXPECTED_EVENTS = 4
EXPECTED_COUNTERPARTIES = 3
EXPECTED_HEAD_BLOCK = 42000
EXPECTED_COMMITTEE_SIZE = 4
EXPECTED_SIGNERS_MIN = 3

RESULTS_PATH = Path(__file__).with_name("session-results.json")


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    checks: list[dict] = []

    def check(name: str, ok: bool, observed, detail: str) -> None:
        checks.append(
            {"name": name, "passed": ok, "observed": observed, "detail": detail}
        )

    # Session step 1: a visitor opens the committee overview.
    committee = get_json("/api/committee")
    node_ids = committee.get("nodeIds", [])
    check(
        "committee lists the four hosting nodes",
        len(node_ids) == EXPECTED_COMMITTEE_SIZE,
        node_ids,
        f"expected {EXPECTED_COMMITTEE_SIZE} nodes, observed {len(node_ids)}",
    )
    check(
        "committee threshold is configured",
        isinstance(committee.get("threshold"), int) and committee["threshold"] >= 1,
        committee.get("threshold"),
        "threshold must be a positive integer",
    )

    # Session step 2: the visitor reads the verified index record.
    records = get_json("/api/records").get("records", [])
    target = next((r for r in records if r["state"]["address"] == EXPECTED_ADDRESS), None)
    check(
        "target address has a certified record",
        target is not None,
        [r["state"]["address"] for r in records],
        "the demo address should appear in the certified records",
    )

    if target is not None:
        state = target["state"]
        check(
            "replayed balance matches the expected batch",
            state["balance"] == EXPECTED_BALANCE,
            state["balance"],
            f"expected {EXPECTED_BALANCE}",
        )
        check(
            "event count matches the expected batch",
            state["event_count"] == EXPECTED_EVENTS,
            state["event_count"],
            f"expected {EXPECTED_EVENTS}",
        )
        check(
            "counterparty count matches the expected batch",
            state["counterparties"] == EXPECTED_COUNTERPARTIES,
            state["counterparties"],
            f"expected {EXPECTED_COUNTERPARTIES}",
        )
        check(
            "head block matches the expected batch",
            state["head_block"] == EXPECTED_HEAD_BLOCK,
            state["head_block"],
            f"expected {EXPECTED_HEAD_BLOCK}",
        )
        check(
            "at least threshold nodes signed the record",
            len(target.get("signers", [])) >= EXPECTED_SIGNERS_MIN,
            target.get("signers", []),
            f"expected at least {EXPECTED_SIGNERS_MIN} signers",
        )
        check(
            "candidate observations were recorded",
            target.get("candidates", 0) >= 1,
            target.get("candidates"),
            "candidates should reflect observations used in aggregation",
        )

    # Session step 3: the visitor browses the history of finalized snapshots.
    history = get_json("/api/history").get("results", [])
    check(
        "at least one finalized history snapshot exists",
        len(history) >= 1,
        [h["id"] for h in history],
        "the certified update should append a history entry",
    )

    passed = sum(1 for c in checks if c["passed"])
    summary = {
        "session": "simulated-user read-only session against the hosted SPA/HTTP API",
        "api_base": API_BASE,
        "total_checks": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "checks": checks,
    }
    RESULTS_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Simulated session: {passed}/{len(checks)} checks passed.")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"  [{status}] {c['name']}: {c['detail']}")

    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate the CS5298 final project report PDF (English).

The report follows the required section list in the assignment brief. The
GitHub repository URL is kept as a placeholder until the public repo is
created; replace REPO_URL before final submission.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

OUT_DIR = Path(__file__).resolve().parent
OUT_PDF = OUT_DIR / "CS5298_60392800_Verifiable_Indexer_Report.pdf"
FIG_DIR = OUT_DIR / "figures"

# Replace this with the public GitHub repository URL before submission.
REPO_URL = "https://github.com/jack2004-1/final-project.git"

styles = getSampleStyleSheet()

BODY = ParagraphStyle(
    "body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=10.2,
    leading=15,
    spaceAfter=7,
    alignment=0,
)
H1 = ParagraphStyle(
    "h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15,
    leading=19, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#16324f"),
)
H2 = ParagraphStyle(
    "h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5,
    leading=15, spaceBefore=8, spaceAfter=5, textColor=colors.HexColor("#243b55"),
)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=14, bulletIndent=4)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.8, leading=12)
CODE = ParagraphStyle(
    "code", parent=BODY, fontName="Courier", fontSize=8.8, leading=12,
    backColor=colors.HexColor("#f1f4f8"), textColor=colors.HexColor("#1a2733"),
    borderPadding=4, spaceAfter=8,
)


def bullet(items):
    return [Paragraph(f"• {item}", BULLET) for item in items]


def cell(text):
    return Paragraph(text, SMALL)


def make_table(data, col_widths=None, header=True):
    # Wrap plain-string cells in Paragraphs so long text wraps instead of clipping.
    wrapped = []
    for r, row in enumerate(data):
        new_row = []
        for value in row:
            if isinstance(value, str):
                new_row.append(cell(value))
            else:
                new_row.append(value)
        wrapped.append(new_row)
    data = wrapped
    table = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d2df")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243b55")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    table.setStyle(TableStyle(style))
    return table


def story():
    flow = []

    # Cover page (does not count toward the six-page main content).
    flow.append(Spacer(1, 3.2 * cm))
    flow.append(Paragraph("CS5298 Final Project Report", H1))
    flow.append(Paragraph(
        "Committee-Verifiable On-Chain Indexer on Lyquor Network", H1))
    flow.append(Spacer(1, 1.2 * cm))
    cover = [
        ["Student", "Buyiyang"],
        ["Student ID", "60392800"],
        ["Team size", "Single person"],
        ["Direction", "Direction 3 — Verifiable Indexer"],
        ["Repository", REPO_URL],
        ["Language", "English"],
    ]
    flow.append(make_table(cover, col_widths=[4.5 * cm, 10.5 * cm], header=False))
    flow.append(Spacer(1, 1.0 * cm))
    flow.append(Paragraph(
        "This report describes the problem addressed, the original contribution, "
        "the Lyquid architecture, implementation, evaluation results, remaining "
        "limitations, attribution, and the use of AI tools.", SMALL))
    flow.append(PageBreak())

    # 1. Problem Analysis
    flow.append(Paragraph("1. Problem Analysis", H1))
    flow.append(Paragraph("1.1 Problem definition", H2))
    flow.append(Paragraph(
        "On-chain analytics and off-chain data brought onto a chain typically "
        "rely on data providers or oracles that report a value without exposing "
        "whether that value was computed correctly. A downstream application "
        "usually trusts the reporter rather than re-running the computation. "
        "This creates a single point of failure: one misconfigured, compromised, "
        "or colluding provider can feed a wrong balance, event count, or event "
        "history into on-chain logic, and other applications cannot distinguish "
        "a correctly computed result from an erroneous report.", BODY))
    flow.append(Paragraph(
        "The target users are DeFi applications, analytics dashboards, and "
        "audit tools that read address balances, transfer histories, and event "
        "aggregations. A concrete scenario is a lending or risk dashboard that "
        "decides exposure limits from an address's transfer history. It needs a "
        "balance and activity summary that several independent nodes have "
        "recomputed, not a single indexer's cached number.", BODY))

    flow.append(Paragraph("1.2 Limitations of existing solutions", H2))
    existing = [
        ["System", "Decentralization", "Verifiability", "Adaptability", "Composability", "History"],
        ["Chainlink-style oracles", "Medium", "Medium", "Low", "Medium", "Mostly latest values"],
        ["UMA optimistic oracle", "Medium", "Low", "High", "Medium", "Slow, human-checked"],
        ["The Graph", "Medium", "Low", "High", "Low", "Rich, but off-chain only"],
        ["Dune", "None", "None", "High", "None", "Rich, but off-chain only"],
        ["ZK coprocessors (e.g. Brevis)", "Medium", "High", "Medium", "High", "Possible, at proving cost"],
    ]
    flow.append(make_table(existing, [3.4*cm, 2.3*cm, 2.3*cm, 2.1*cm, 2.5*cm, 3.2*cm]))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        "Indexing networks such as The Graph and analytics platforms such as "
        "Dune provide rich history and flexible queries, but the served result "
        "is computed off-chain and the consumer mostly trusts the indexer's "
        "cache. Chainlink-style reporting networks decentralize the reporter "
        "set, but their feed usually publishes the latest value rather than a "
        "replayable history, and verification of the reported aggregate depends "
        "on the chosen report model. Optimistic systems are adaptable but rely "
        "on a dispute window and human review. ZK coprocessors give strong "
        "verifiability, but proof generation adds cost and latency, and the "
        "proving setup still has to be trusted for the statement it proves.", BODY))

    flow.append(Paragraph("1.3 Connection to Web3 developments", H2))
    flow.append(Paragraph(
        "Modern Web3 data layers separate data fetching, transformation, and "
        "querying, but most still keep the computed state outside the consensus "
        "boundary. Decentralized indexers publish signed response attestations, "
        "while oracle networks run off-chain aggregation and submit one "
        "consensus report on chain. Lyquor combines these two concerns in one "
        "program: a Lyquid keeps consensus state and node-private computation "
        "in the same code, and a committee of hosting nodes can jointly run "
        "arbitrary code and vouch for a result that any network application "
        "reads in the same call. This project uses that native combination to "
        "turn an indexer computation into a committee-certified on-chain record.", BODY))

    # 2. Original Contribution
    flow.append(Paragraph("2. Original Contribution", H1))
    flow.append(Paragraph(
        "The application goes beyond a copied course example in the following "
        "ways:", BODY))
    flow += bullet([
        "<b>Replay-then-vouch workflow inside one Lyquid.</b> Each hosting "
        "node replays the local event batch to derive balance, event count, and "
        "counterparty statistics; the committee then reconciles these "
        "observations and only writes a record when the configured threshold "
        "agrees. The computation and its certification live in the same program "
        "rather than in an external indexer plus a separate report contract.",
        "<b>Head-block-aware majority aggregation.</b> Observations are grouped "
        "by head block before tallying, so a node that is behind cannot count "
        "as agreeing on a newer snapshot. Distinct states that both reach the "
        "threshold are flagged as disputed instead of being certified.",
        "<b>Certified records with signing evidence.</b> A finalized record "
        "stores the agreed state, the committee nodes that signed it, and the "
        "number of candidate observations used in aggregation, so a reader can "
        "see both the result and who endorsed it.",
        "<b>Rolling trusted history on the replicated state.</b> Each "
        "finalized update appends a snapshot with its sequence id, timestamp, "
        "and chain position. The history, not only the latest spot value, is "
        "stored so downstream applications can audit how a certified summary "
        "evolved.",
        "<b>Composable read surface.</b> Records are exposed through Ethereum "
        "ABI methods and hosted HTTP endpoints, and a small static SPA reads "
        "committee, records, and history. Other Lyquids can call the same "
        "verified record within the same network call.",
    ])
    flow.append(Paragraph(
        "The reusable pieces are standard: the LDK oracle two-phase primitives, "
        "serde JSON encoding, and ordinary Rust data structures. The "
        "contribution is the indexer-specific replay rule, the head-block-aware "
        "consensus policy, and the certified record/history design.", BODY))

    flow.append(PageBreak())

    # 3. Technical Design
    flow.append(Paragraph("3. Technical Design", H1))
    flow.append(Paragraph("3.1 Architecture overview", H2))
    flow.append(Paragraph(
        "The Lyquid divides state into replicated <i>network</i> state and "
        "node-local <i>instance</i> state. Network state holds the initializer "
        "address, the oracle topic configuration, and the certified records. "
        "Instance state holds the node's own seed batch and its local history "
        "cache. The diagram below shows the request flow.", BODY))

    if (FIG_DIR / "architecture.png").exists():
        flow.append(Image(str(FIG_DIR / "architecture.png"), width=16*cm, height=8*cm))
    flow.append(Spacer(1, 4))

    arch = [
        ["Component", "State", "Responsibility"],
        ["Constructor", "network", "Record the initializer address."],
        ["configure_committee", "network", "Register committee nodes and the majority threshold."],
        ["set_local_seed", "instance", "Load the batch this node will replay locally."],
        ["propose", "instance", "Run the local replay and return this node's observation."],
        ["aggregate", "instance", "Pure reconciliation of signed observations; build certified params."],
        ["update", "network", "Store the certified record and trigger the history snapshot."],
        ["update_history", "instance", "Append a rolling snapshot to the local history cache."],
        ["read methods / HTTP", "instance", "Expose committee, records, and history to callers and the SPA."],
    ]
    flow.append(make_table(arch, [3.8*cm, 2.2*cm, 9.0*cm]))

    flow.append(Paragraph("3.2 Core workflow", H2))
    flow += bullet([
        "<b>Setup.</b> The initializer configures the four hosting nodes as the "
        "oracle committee. The threshold is majority: for four nodes it is 3.",
        "<b>Local replay.</b> Every node receives the same seed batch, sorts "
        "events by block then transaction index, folds the signed amounts, and "
        "counts distinct counterparties. Order normalization keeps the replay "
        "deterministic.",
        "<b>Two-phase oracle.</b> In the propose phase each node returns its "
        "own observation. In the aggregate phase the protocol collects signed "
        "inputs and the Lyquid reconciles them; the aggregation function must "
        "be a pure function of the initialization parameters and the supplied "
        "inputs so the LDK can re-run it during validation.",
        "<b>Certified update.</b> When enough observations agree, the aggregator "
        "produces certified call parameters for the <code>update</code> "
        "network method. The target-side wrapper verifies the committee "
        "certificate before <code>update</code> stores the record.",
        "<b>History and read.</b> After commit, <code>update_history</code> "
        "snapshots the replicated records. Callers read the record, its "
        "signers, and the history through ABI methods or HTTP routes.",
    ])

    flow.append(Paragraph("3.3 Key design choices", H2))
    flow += bullet([
        "<b>Deterministic pure logic separate from runtime code.</b> Replay, "
        "tally, and consensus rules are ordinary Rust functions in "
        "<code>src/indexer/mod.rs</code>. They can be tested in the guest test "
        "harness without the Lyquid ABI, and the aggregator stays reproducible.",
        "<b>Head-block grouping before majority.</b> A stale snapshot is "
        "removed from the agreement set instead of being forced into a "
        "comparison against a newer head.",
        "<b>JSON strings across the ABI boundary.</b> The Ethereum ABI "
        "supports base value types; structured records cross the boundary as "
        "JSON strings, while native Lyquor field encoding is used inside the "
        "oracle certified call.",
        "<b>Integer balances only.</b> Balances are signed integers in the "
        "smallest token subdivision; no floating-point arithmetic is involved. "
        "Addition clamps on overflow rather than silently wrapping.",
        "<b>Certified data stored on chain, transient local data kept per node.</b> "
        "The seed batch and history cache are node-local; only the agreed "
        "record and its endorsement are replicated as network state.",
    ])

    flow.append(PageBreak())

    # 4. Implementation
    flow.append(Paragraph("4. Implementation", H1))
    flow.append(Paragraph("4.1 Code layout", H2))
    layout = [
        ["Path", "Content"],
        ["src/lib.rs", "State model, committee setup, oracle propose/aggregate, certified update, history, ABI and HTTP exports."],
        ["src/indexer/mod.rs", "LedgerEvent, ReplayInput, BalanceState, Observation, consensus result types, replay and aggregation functions, guest unit tests."],
        ["assets/index.html", "Static single-page UI reading the three hosted HTTP endpoints."],
        ["scripts/run_demo.sh", "Localnet startup, deployment, committee activation, seeding, certified replay, proxy, and read-out."],
        ["tests/simulated_user_session.py", "Repeatable read-only simulated-user session that asserts the demo results."],
    ]
    flow.append(make_table(layout, [4.6*cm, 10.4*cm]))

    flow.append(Paragraph("4.2 Replay algorithm", H2))
    flow.append(Paragraph(
        "The replay sorts events by <code>(block, tx_index)</code>, folds the "
        "signed <code>amount</code> into a running balance, counts events, and "
        "collects distinct counterparty identifiers. The canonical sort means "
        "a node that receives events in a different order still reaches the "
        "same state.", BODY))
    flow.append(Paragraph(
        "Demo batch: +500 from Alice at block 41990, -180 to Bob at 41991, "
        "+220 from Alice at 41995, +90 from Carol at 42000. The net balance is "
        "630, there are 4 events, and 3 distinct counterparties "
        "(Alice, Bob, Carol).", BODY))

    flow.append(Paragraph("4.3 Aggregation and consensus policy", H2))
    flow += bullet([
        "If there are no observations, the result is <i>Waiting</i>.",
        "Observations whose head block differs from the observed head are "
        "excluded from that round's agreement set.",
        "If the agreement set is smaller than the threshold, the result is "
        "<i>Waiting</i>.",
        "Identical states are tallied; the most frequent state wins, ties are "
        "broken by the numerically smaller balance for determinism.",
        "If more than one distinct state reaches the threshold, the round is "
        "<i>Disputed</i> and no record is certified.",
        "Otherwise the outcome is <i>Reached</i> and the agreed state is "
        "returned with its agreement count.",
    ])

    flow.append(Paragraph("4.4 External services and contracts", H2))
    flow.append(Paragraph(
        "The application runs against the Lyquor native devnet. The localnet "
        "starts a shared Anvil sequencer and four Lyquor hosting nodes; the "
        "LDK deploys a bartender control-plane Lyquid and the indexer Lyquid. "
        "No external public testnet contract is required for the demo. In a "
        "production deployment the seed batch would be fetched from a hosted "
        "archive node through the host HTTP API; the current devnet injects a "
        "deterministic batch through <code>set_local_seed</code> so the "
        "workflow is reproducible offline.", BODY))

    flow.append(Paragraph("4.5 Build and deployment interface", H2))
    flow.append(Paragraph(
        "The crate pins LDK 0.8.4, targets "
        "<code>wasm32-unknown-unknown</code>, and builds through "
        "<code>shaker build</code>. The deployed ABI surface includes "
        "<code>configure_committee(bytes32[])</code>, "
        "<code>set_local_seed(string)</code>, <code>get_record(string)</code>, "
        "<code>list_records()</code>, <code>get_node_ids()</code>, and "
        "<code>certify_replay()</code>. HTTP routes are <code>/</code>, "
        "<code>/api/committee</code>, <code>/api/records</code>, and "
        "<code>/api/history</code>. On localnet the virtual host is proxied "
        "through <code>shaker serve</code>.", BODY))

    flow.append(PageBreak())

    # 5. Evaluation and Results
    flow.append(Paragraph("5. Evaluation and Results", H1))
    flow.append(Paragraph("5.1 Evaluation objectives", H2))
    flow.append(Paragraph(
        "Evaluation checks three objectives: (i) the deterministic replay "
        "produces the expected balance, event count, and counterparties; "
        "(ii) the committee reaches consensus only when the threshold agrees "
        "and flags disputes or insufficient agreement; and (iii) the deployed "
        "four-node network returns a certified record with signing evidence "
        "and a history snapshot.", BODY))

    flow.append(Paragraph("5.2 Unit-level guest tests", H2))
    unit = [
        [Paragraph("<b>Test</b>", SMALL), Paragraph("<b>What it checks</b>", SMALL), Paragraph("<b>Result</b>", SMALL)],
        [Paragraph("<font face='Courier'>replay_sums_balance_<br/>and_counts_parties</font>", SMALL), Paragraph("Balance, event count, counterparties, head block.", SMALL), Paragraph("Pass", SMALL)],
        [Paragraph("<font face='Courier'>replay_is_order_<br/>independent</font>", SMALL), Paragraph("Reversed event order yields the same replay state.", SMALL), Paragraph("Pass", SMALL)],
        [Paragraph("<font face='Courier'>consensus_reaches_when_<br/>threshold_agrees</font>", SMALL), Paragraph("Matching observations above threshold reach Reached.", SMALL), Paragraph("Pass", SMALL)],
        [Paragraph("<font face='Courier'>consensus_waits_below_<br/>threshold</font>", SMALL), Paragraph("Below threshold the result stays Waiting.", SMALL), Paragraph("Pass", SMALL)],
        [Paragraph("<font face='Courier'>consensus_flags_dispute_<br/>on_split_tally</font>", SMALL), Paragraph("Two equal threshold groups produce Disputed.", SMALL), Paragraph("Pass", SMALL)],
        [Paragraph("<font face='Courier'>stale_head_block_is_not_<br/>counted_as_agreement</font>", SMALL), Paragraph("A stale head block is excluded from agreement.", SMALL), Paragraph("Pass", SMALL)],
    ]
    flow.append(make_table(unit, [4.2*cm, 7.8*cm, 1.6*cm]))

    flow.append(Paragraph("5.3 End-to-end localnet run", H2))
    flow.append(Paragraph(
        "The four-node mesh was brought up with the LDK localnet script, the "
        "Lyquid was deployed, the committee was configured and the oracle "
        "activated. The same seed batch was loaded on every node, "
        "<code>certify_replay()</code> was called, and the hosted HTTP endpoints "
        "were read through the local proxy. Observed results:", BODY))
    e2e = [
        ["Field", "Observed value"],
        ["Committee size", "4 hosting nodes"],
        ["Committee threshold", "3 (majority)"],
        ["Replayed address", "0x1111111111111111111111111111111111111111"],
        ["Head block", "42000"],
        ["Balance", "630"],
        ["Event count", "4"],
        ["Distinct counterparties", "3"],
        ["Signing committee nodes", "3"],
        ["Candidate observations recorded", "2"],
        ["History snapshots", "1 finalized snapshot with sequence id, timestamp, chain position"],
    ]
    flow.append(make_table(e2e, [6.0*cm, 9.0*cm]))

    flow.append(Paragraph("5.4 Simulated-user session", H2))
    flow.append(Paragraph(
        "Because this is a single-person group, external validation was "
        "performed by a repeatable automated simulated-user session rather "
        "than human interviews. The script opens the same read-only endpoints "
        "a visitor would open and asserts committee membership, threshold, "
        "record presence, balance, event count, counterparties, head block, "
        "signer count, candidate count, and history presence. The recorded "
        "result is <b>10/10 checks passed</b>; the machine-readable log is "
        "stored in <code>tests/session-results.json</code>.", BODY))
    sess = [
        ["Check", "Observed", "Result"],
        ["Committee lists four hosting nodes", "4 nodes", "Pass"],
        ["Committee threshold configured", "3", "Pass"],
        ["Target address has a certified record", "1 record", "Pass"],
        ["Replayed balance", "630", "Pass"],
        ["Event count", "4", "Pass"],
        ["Counterparty count", "3", "Pass"],
        ["Head block", "42000", "Pass"],
        ["At least threshold signers", "3 signers", "Pass"],
        ["Candidate observations recorded", "2", "Pass"],
        ["History snapshot exists", "1 snapshot", "Pass"],
    ]
    flow.append(make_table(sess, [6.4*cm, 4.6*cm, 2.0*cm]))

    flow.append(PageBreak())

    # 6. Limitations and Reflection
    flow.append(Paragraph("6. Limitations and Reflection", H1))
    flow.append(Paragraph("6.1 Remaining limitations", H2))
    flow += bullet([
        "<b>Single-person group and no human user test.</b> The B3 user-testing "
        "evidence is an automated simulated-user session. It verifies the "
        "read-only workflow mechanically but does not capture real usability "
        "feedback, domain questions, or edge cases raised by external "
        "visitors.",
        "<b>Seed batch injected locally.</b> The devnet uses a fixed batch "
        "loaded through <code>set_local_seed</code>. It does not yet pull "
        "blocks and events from an archive-node RPC, so replay coverage is the "
        "small demo batch rather than a full address history.",
        "<b>Localnet, not multi-machine deployment.</b> The four nodes run on "
        "one host through the native localnet. Cross-machine networking, "
        "persistent peer discovery, and infrastructure heterogeneity are not "
        "exercised.",
        "<b>Simple majority policy.</b> The aggregator uses exact state "
        "equality and head-block grouping. It does not quantify numerical "
        "divergence, slashing, or reputation for misbehaving nodes.",
        "<b>No proof system.</b> Certification relies on committee "
        "signatures and oracle protocol, not a cryptographic proof of "
        "replay correctness. A small colluding majority could still present "
        "an agreed but incorrect snapshot.",
        "<b>History capacity bounded.</b> The local cache keeps a bounded "
        "rolling window (600 entries in the code) rather than an unbounded "
        "archive; older snapshots are evicted.",
    ])

    flow.append(Paragraph("6.2 Practical implications", H2))
    flow.append(Paragraph(
        "The design shows that a committee replay and certification can live "
        "inside the same Lyquid, which removes the need to trust a separate "
        "off-chain indexer for the final record. In a real DeFi setting, "
        "however, the trust reduction is only as strong as the committee "
        "selection, the data source used for replay, and the agreement policy. "
        "The current implementation is a localnet prototype suitable for "
        "evaluating the mechanism, not a production data layer.", BODY))

    flow.append(Paragraph("6.3 Concrete next step", H2))
    flow.append(Paragraph(
        "The most valuable next step is connecting the replay input to a real "
        "archive-node feed through the host API, persisting verified history "
        "on replicated state instead of a bounded local cache, and adding a "
        "divergence or slashing rule for observations that disagree beyond a "
        "tolerance. After that, a multi-machine deployment would test whether "
        "the committee protocol holds under real network delays and peer "
        "churn.", BODY))

    # 7. Contributions and Attribution
    flow.append(Paragraph("7. Contributions and Attribution", H1))
    flow.append(Paragraph(
        "This project was completed independently by the sole group member:", BODY))
    contrib = [
        [Paragraph("<b>Member</b>", SMALL), Paragraph("<b>Role</b>", SMALL), Paragraph("<b>Contribution</b>", SMALL)],
        [Paragraph("Buyiyang", SMALL), Paragraph("Author", SMALL), Paragraph("Problem framing, Lyquid design, Rust implementation, oracle integration, demo scripts, simulated-user harness, report, and self-review.", SMALL)],
    ]
    flow.append(make_table(contrib, [3.4*cm, 2.0*cm, 9.6*cm]))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph("External code and resources", H2))
    flow += bullet([
        "Lyquor Lyquid Development Kit (LDK) 0.8.4: oracle two-phase "
        "primitives, state macros, method exports, and the shaker/lyquor "
        "toolchain.",
        "LDK official examples, including the price-feed example, used as "
        "reference for oracle committee setup, deployment scripts, and hosted "
        "HTTP routing.",
        "Rust crates: <code>lyquid</code>, <code>lyquor-primitives</code>, "
        "<code>lyquid-test</code>, <code>serde</code>, "
        "<code>serde_json</code>.",
        "Course materials: CS5298 tutorials and the final project brief. "
        "Existing-system comparison values in Section 1 follow the Direction 3 "
        "table in the assignment.",
    ])

    # 8. AI Use Statement
    flow.append(Paragraph("8. AI Use Statement", H1))
    flow.append(Paragraph(
        "An AI assistant was used during development for the tasks listed below. "
        "The student remains responsible for the correctness of the code and "
        "claims, and every reported result was reproduced against the running "
        "localnet before it was recorded.", BODY))
    ai = [
        [Paragraph("<b>AI tool</b>", SMALL), Paragraph("<b>Supported tasks</b>", SMALL), Paragraph("<b>Review and validation performed</b>", SMALL)],
        [
            Paragraph("AI coding assistant (Doubao)", SMALL),
            Paragraph("Drafting Rust scaffolding, locating LDK API patterns from official examples, generating the static SPA, drafting shell test scripts, and suggesting report structure and wording.", SMALL),
            Paragraph("All code was compiled with the LDK toolchain, guest unit tests were run through shaker, the four-node end-to-end demo was executed and its HTTP outputs inspected, and the simulated-user session log was checked for 10/10 passing checks. Design decisions, consensus policy, and report claims were reviewed against the LDK documentation and the observed demo outputs.", SMALL),
        ],
    ]
    flow.append(make_table(ai, [3.2*cm, 5.4*cm, 6.4*cm]))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        "The assistant did not submit the project, create the repository, or "
        "approve any deployment. No external human interview was conducted; "
        "the user-testing evidence is the automated session described in "
        "Section 5.4 and Section 6.1.", BODY))

    # References (do not count toward main content).
    flow.append(PageBreak())
    flow.append(Paragraph("References", H1))
    refs = [
        "Lyquor LDK documentation — Build, Deploy, and Test: "
        "https://docs.lyquor.dev/docs/ldk/build-deploy-test/",
        "Lyquor LDK documentation — External Access (HTTP exports and virtual host): "
        "https://docs.lyquor.dev/docs/ldk/external/",
        "Lyquor LDK documentation — Functions and export surfaces: "
        "https://docs.lyquor.dev/docs/ldk/functions/",
        "Chainlink education hub — The blockchain oracle problem: "
        "https://chain.link/education-hub/oracle-problem",
        "The Graph — Decentralized indexing and subgraphs: "
        "https://thegraph.com/blog/grt-the-graph-decentralized-data/",
        "CS5298 Final Project brief, course handout CS5298_Final_Project-4.pdf.",
    ]
    for ref in refs:
        flow.append(Paragraph(f"• {ref}", SMALL))

    return flow


def main():
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=2.0*cm, rightMargin=2.0*cm,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        title="CS5298 Verifiable Indexer Report",
        author="Buyiyang 60392800",
    )
    doc.build(story())
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()

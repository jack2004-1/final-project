# Demo Recording Guide (CS5298 Verifiable Indexer)

The in-person presentation is eight minutes: five minutes slides/talk and three
minutes prerecorded demo. This guide records the three-minute demo against the
four-node localnet and packages the video for the submission ZIP.

## Before recording

1. Start the demo localnet in a terminal:

   ```bash
   bash scripts/run_demo.sh multi
   ```

   Wait until the proxy prints
   `proxying http://127.0.0.1:8080/ => <lyquid>.<node> @ http://127.0.0.1:10087`.

2. Open two browser tabs:
   - `http://127.0.0.1:8080/` — hosted SPA.
   - `http://127.0.0.1:8080/api/records` — certified records JSON.

3. Have the terminal visible; it shows committee configuration, seeding each
   node, and the certified replay call.

## Three-minute narration outline

| Time | Action | What to say |
|---|---|---|
| 0:00–0:30 | Show the SPA and the three cards. | This Lyquid keeps a committee-verified index: nodes replay the same event batch locally, then the committee reconciles observations before a record is written on chain. |
| 0:30–1:10 | Terminal: committee configuration and seeding each node. | Four hosting nodes form the oracle committee; the threshold is majority (3 of 4). Each node receives the same deterministic batch and replays it independently. |
| 1:10–1:50 | Trigger `certify_replay()`, then refresh `/api/records`. | The two-phase oracle proposes observations, aggregates them by head block and majority tally, and only writes the record when the threshold agrees. The record lists the signers and the number of candidate observations. |
| 1:50–2:20 | Open `/api/committee` and `/api/history`. | The committee endpoint shows the four nodes and threshold; history stores each finalized snapshot with its sequence id, timestamp and chain position. |
| 2:20–3:00 | Point to balance 630, 4 events, 3 counterparties. | Replay sums +500, -180, +220, +90 = 630 over 4 events and 3 distinct counterparties; the committee-certified result matches the independent calculation. |

## Package the ZIP

Record the screen to `demo-recording.mp4`, place it next to this guide, then
from the repository root:

```bash
zip -r demo-recording.zip demo-recording.mp4 scripts/ tests/
```

The submitted ZIP should contain the recording and any repeatable scripts the
demo relied on.

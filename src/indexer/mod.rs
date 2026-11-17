//! Core indexer computation that does not depend on the Lyquid runtime.
//!
//! Keeping this logic in ordinary Rust functions lets us unit-test the replay,
//! aggregation and consensus rules with the standard `cargo test` harness,
//! exactly as the LDK recommends for deterministic application logic.

use serde::{Deserialize, Serialize};

/// A single ledger event that an indexer replays.
///
/// `block` is the height at which the event was observed, `tx_index` the order
/// of the event inside that block, and `counterparty` the other side of a
/// transfer. Positive `amount` means the target address received tokens, a
/// negative value means it sent them.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LedgerEvent {
    pub block: u64,
    pub tx_index: u32,
    pub counterparty: String,
    pub amount: i64,
}

/// A batch of events one committee node replayed locally for one address.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReplayInput {
    pub address: String,
    /// Highest block number included in this replay.
    pub head_block: u64,
    /// Events included, in canonical order.
    pub events: Vec<LedgerEvent>,
}

/// The result of replaying one event batch for one address.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct BalanceState {
    pub address: String,
    pub head_block: u64,
    pub event_count: u64,
    /// Signed running balance. Stored as an integer; the demo uses units of
    /// the smallest token subdivision so no float arithmetic is involved.
    pub balance: i64,
    /// Number of distinct counterparties seen.
    pub counterparties: u64,
}

/// Canonical ordering used before replay: block first, then transaction index.
fn canonical_order(a: &LedgerEvent, b: &LedgerEvent) -> std::cmp::Ordering {
    a.block.cmp(&b.block).then(a.tx_index.cmp(&b.tx_index))
}

/// Replay a batch and compute the running balance and event statistics.
///
/// The function is deterministic: input order is normalized before folding, so
/// nodes that receive the same batch always arrive at the same state.
pub fn replay_batch(mut input: ReplayInput) -> BalanceState {
    input.events.sort_by(canonical_order);

    let mut balance: i64 = 0;
    let mut counterparties: Vec<String> = Vec::new();
    let mut event_count: u64 = 0;

    for event in &input.events {
        balance = balance
            .checked_add(event.amount)
            .unwrap_or_else(|| balance.clamp(i64::MIN, i64::MAX));
        event_count += 1;
        if !counterparties.contains(&event.counterparty) {
            counterparties.push(event.counterparty.clone());
        }
    }

    BalanceState {
        address: input.address,
        head_block: input.head_block,
        event_count,
        balance,
        counterparties: counterparties.len() as u64,
    }
}

/// One node's certified observation: the state it reached plus the node id.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Observation {
    pub node: String,
    pub state: BalanceState,
}

/// Majority/median agreement over committee observations.
///
/// The aggregator requires `min_consensus` agreeing observations before it
/// produces a certified state. Observations that disagree on `head_block` are
/// ignored for that round; among the matching head block, the most frequent
/// balance wins. Ties are broken by the numerically smaller balance so the
/// result stays deterministic.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConsensusOutcome {
    /// Enough matching observations agreed.
    Reached,
    /// Not enough observations arrived yet.
    Waiting,
    /// Observations disagree past the allowed divergence.
    Disputed,
}

/// Result of aggregating a round of committee observations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConsensusResult {
    pub outcome: ConsensusOutcome,
    pub agreed: Option<BalanceState>,
    pub agreeing: u64,
    pub observed: u64,
}

/// Aggregate observations for one replay round.
pub fn aggregate_observations(
    observations: &[Observation],
    min_consensus: usize,
) -> ConsensusResult {
    let observed = observations.len() as u64;
    if observations.is_empty() {
        return ConsensusResult {
            outcome: ConsensusOutcome::Waiting,
            agreed: None,
            agreeing: 0,
            observed,
        };
    }

    // Group by head block so a node that is behind cannot be counted as
    // agreeing on a newer snapshot.
    let head = observations[0].state.head_block;
    let same_head: Vec<&Observation> = observations
        .iter()
        .filter(|o| o.state.head_block == head)
        .collect();

    if same_head.len() < min_consensus {
        return ConsensusResult {
            outcome: ConsensusOutcome::Waiting,
            agreed: None,
            agreeing: same_head.len() as u64,
            observed,
        };
    }

    // Tally identical states.
    let mut tally: Vec<(&BalanceState, usize)> = Vec::new();
    for obs in &same_head {
        if let Some(slot) = tally.iter_mut().find(|(s, _)| **s == obs.state) {
            slot.1 += 1;
        } else {
            tally.push((&obs.state, 1));
        }
    }

    tally.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.balance.cmp(&b.0.balance)));
    let (best_state, best_count) = tally[0];

    // More than one distinct state reached the threshold: the round is
    // disputed rather than certified.
    let competing = tally.iter().filter(|(_, c)| *c >= min_consensus).count();
    if competing > 1 {
        return ConsensusResult {
            outcome: ConsensusOutcome::Disputed,
            agreed: None,
            agreeing: best_count as u64,
            observed,
        };
    }

    ConsensusResult {
        outcome: ConsensusOutcome::Reached,
        agreed: Some((*best_state).clone()),
        agreeing: best_count as u64,
        observed,
    }
}

/// A finalized, on-chain index record stored after committee certification.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct IndexRecord {
    pub state: BalanceState,
    /// Committee nodes that certified this record.
    pub signers: Vec<String>,
    /// Number of candidate observations used for the aggregation.
    pub candidates: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn event(block: u64, tx: u32, party: &str, amount: i64) -> LedgerEvent {
        LedgerEvent {
            block,
            tx_index: tx,
            counterparty: party.to_string(),
            amount,
        }
    }

    #[lyquid_test::test]
    fn replay_sums_balance_and_counts_parties() {
        let input = ReplayInput {
            address: "0xabc".to_string(),
            head_block: 12,
            events: vec![
                event(10, 1, "0xAlice", 300),
                event(9, 0, "0xBob", -120),
                event(10, 0, "0xAlice", 50),
            ],
        };
        let state = replay_batch(input);
        assert_eq!(state.balance, 230);
        assert_eq!(state.event_count, 3);
        assert_eq!(state.counterparties, 2);
        assert_eq!(state.head_block, 12);
    }

    #[lyquid_test::test]
    fn replay_is_order_independent() {
        let events = vec![
            event(2, 2, "0xA", 10),
            event(1, 0, "0xB", -4),
            event(2, 0, "0xC", 7),
        ];
        let a = replay_batch(ReplayInput {
            address: "0x1".into(),
            head_block: 2,
            events: events.clone(),
        });
        let mut reversed = events;
        reversed.reverse();
        let b = replay_batch(ReplayInput {
            address: "0x1".into(),
            head_block: 2,
            events: reversed,
        });
        assert_eq!(a, b);
        assert_eq!(a.balance, 13);
    }

    #[lyquid_test::test]
    fn consensus_reaches_when_threshold_agrees() {
        let state = BalanceState {
            address: "0xabc".into(),
            head_block: 12,
            event_count: 3,
            balance: 230,
            counterparties: 2,
        };
        let observations = vec![
            Observation { node: "n1".into(), state: state.clone() },
            Observation { node: "n2".into(), state: state.clone() },
            Observation { node: "n3".into(), state: state.clone() },
        ];
        let result = aggregate_observations(&observations, 2);
        assert_eq!(result.outcome, ConsensusOutcome::Reached);
        assert_eq!(result.agreed, Some(state));
        assert_eq!(result.agreeing, 3);
    }

    #[lyquid_test::test]
    fn consensus_waits_below_threshold() {
        let state = BalanceState {
            address: "0xabc".into(),
            head_block: 12,
            event_count: 1,
            balance: 10,
            counterparties: 1,
        };
        let observations = vec![
            Observation { node: "n1".into(), state: state.clone() },
            Observation { node: "n2".into(), state: state.clone() },
        ];
        let result = aggregate_observations(&observations, 3);
        assert_eq!(result.outcome, ConsensusOutcome::Waiting);
        assert!(result.agreed.is_none());
    }

    #[lyquid_test::test]
    fn consensus_flags_dispute_on_split_tally() {
        let good = BalanceState {
            address: "0xabc".into(), head_block: 12, event_count: 3, balance: 230, counterparties: 2,
        };
        let bad = BalanceState {
            address: "0xabc".into(), head_block: 12, event_count: 3, balance: 999, counterparties: 2,
        };
        let observations = vec![
            Observation { node: "n1".into(), state: good.clone() },
            Observation { node: "n2".into(), state: good.clone() },
            Observation { node: "n3".into(), state: bad.clone() },
            Observation { node: "n4".into(), state: bad.clone() },
        ];
        let result = aggregate_observations(&observations, 2);
        assert_eq!(result.outcome, ConsensusOutcome::Disputed);
        assert!(result.agreed.is_none());
    }

    #[lyquid_test::test]
    fn stale_head_block_is_not_counted_as_agreement() {
        let fresh = BalanceState {
            address: "0xabc".into(), head_block: 12, event_count: 3, balance: 230, counterparties: 2,
        };
        let stale = BalanceState {
            address: "0xabc".into(), head_block: 10, event_count: 1, balance: 50, counterparties: 1,
        };
        let observations = vec![
            Observation { node: "n1".into(), state: fresh.clone() },
            Observation { node: "n2".into(), state: fresh.clone() },
            Observation { node: "n3".into(), state: stale },
        ];
        let result = aggregate_observations(&observations, 2);
        assert_eq!(result.outcome, ConsensusOutcome::Reached);
        assert_eq!(result.agreed, Some(fresh));
        assert_eq!(result.agreeing, 2);
    }
}

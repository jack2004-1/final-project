//! Verifiable Indexer Lyquid (CS5298 Final Project, Direction 3).
//!
//! Design overview
//! ---------------
//! Each hosting node replays a local batch of ledger events for a queried
//! address (instance state, node-local cache). A committee of hosting nodes
//! runs the oracle two-phase flow: `propose` returns the node's own replay,
//! `aggregate` deterministically reconciles the signed inputs, and once the
//! configured threshold agrees the certified call lands on the network
//! `update` function, which stores the verified record and a rolling history
//! on the replicated network state. Other applications can read the verified
//! snapshot and its history in the same call, instead of trusting a single
//! off-chain data provider.

use lyquid::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

pub mod indexer;

use indexer::{
    aggregate_observations, BalanceState, ConsensusOutcome, IndexRecord, LedgerEvent, Observation,
    ReplayInput,
};

/// Static index page served by the hosting node.
const SPA_INDEX_HTML: &[u8] = include_bytes!("../assets/index.html");

/// Default committee size assumed for setup when the caller does not list
/// nodes explicitly. The actual committee is whatever `configure_committee`
/// registers; the demo deploys a four-node devnet.
const MIN_CONSENSUS: u16 = 2;
/// Rolling history kept in the node-local cache.
const HISTORY_MAX: usize = 600;

/// A batch of seed events stored so the local replay can run without an
/// external RPC dependency on the devnet. In a production deployment these
/// would be pulled from a hosted archive node through the host HTTP API.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SeedBatch {
    address: String,
    head_block: u64,
    events: Vec<LedgerEvent>,
}

state! {
    // Address that registered the Lyquid; only it may configure the committee.
    network initializer: Address = Address::ZERO;
    // Oracle topic for committee-certified index updates.
    network oracle indexer;
    // Verified records keyed by address, replicated across hosting nodes.
    network records: HashMap<String, IndexRecord> = new_hashmap();

    // Node-local seed batch used for the offline replay on the devnet.
    instance local_seed: Option<SeedBatch> = None;
    // Node-local rolling cache of finalized snapshots.
    instance history_cache: VecDeque<(u64, u64, ChainPos, HashMap<String, IndexRecord>)> = VecDeque::new();
    instance history_id: u64 = 0;
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

#[method::network(export = eth)]
fn constructor(ctx: &mut _) {
    *ctx.network.initializer = ctx.caller;
}

// Register the oracle committee. Only the initializer may call this.
#[method::network(export = eth)]
fn configure_committee(ctx: &mut _, node_ids: Vec<NodeID>) -> LyquidResult<bool> {
    if ctx.caller != *ctx.network.initializer {
        return Err(LyquidError::LyquorRuntime(
            "only initializer can configure the indexer committee".into(),
        ));
    }
    if node_ids.is_empty() || node_ids.len() > u16::MAX as usize {
        return Err(LyquidError::LyquorRuntime("invalid committee size".into()));
    }

    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let threshold = u16::try_from(node_ids.len() / 2 + 1).map_err(|_| {
        LyquidError::LyquorRuntime("committee threshold overflow".into())
    })?;

    if !ctx
        .network
        .indexer
        .clone()
        .initialize(&mut ctx, target, node_ids, threshold)
    {
        return Err(LyquidError::LyquorRuntime(
            "indexer oracle committee initialization failed".into(),
        ));
    }
    Ok(true)
}

// Load the local seed batch that this node replays. The JSON payload mirrors
// `SeedBatch`; structured payloads crossing an exported boundary are passed
// as JSON strings because the Ethereum ABI only supports base value types.
#[method::instance(export = eth)]
fn set_local_seed(ctx: &mut _, payload: String) -> LyquidResult<bool> {
    let batch: SeedBatch = serde_json::from_str(&payload)
        .map_err(|e| LyquidError::LyquorRuntime(format!("invalid seed payload: {e}")))?;
    *ctx.instance.local_seed.write() = Some(batch.clone());
    lyquid::println!(
        "indexer: local seed loaded for {} ({} events)",
        batch.address,
        batch.events.len()
    );
    Ok(true)
}

// ---------------------------------------------------------------------------
// Oracle two-phase certification
// ---------------------------------------------------------------------------

// `propose`: run this node's local replay and return its observation.
#[method::instance(group = oracle::two_phase::indexer)]
fn propose(ctx: &mut _, min_consensus: u16, target: OracleTarget) -> LyquidResult<Observation> {
    let expected_target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    if target != expected_target || min_consensus == 0 {
        return Err(LyquidError::OracleError("invalid proposal".into()));
    }

    let seed = ctx.instance.local_seed.read().clone();
    let state = match seed {
        Some(batch) => indexer::replay_batch(ReplayInput {
            address: batch.address,
            head_block: batch.head_block,
            events: batch.events,
        }),
        None => BalanceState {
            address: String::new(),
            head_block: 0,
            event_count: 0,
            balance: 0,
            counterparties: 0,
        },
    };

    Ok(Observation {
        node: ctx.from.to_string(),
        state,
    })
}

// `aggregate`: deterministically reconcile signed node inputs into one
// certified `CertifiedCallParams`. Re-run by the LDK during validation, so it
// must be a pure function of `ctx.init` and `ctx.inputs`.
#[method::instance(group = oracle::two_phase::indexer)]
fn aggregate(ctx: &_) -> LyquidResult<Option<CertifiedCallParams>> {
    let init = decode_by_fields!(ctx.init, min_consensus: u16, target: OracleTarget)
        .ok_or_else(|| LyquidError::LyquorRuntime("failed to decode init params".into()))?;
    if init.target.seq_id != lyquor_api::sequence_backend_id()? {
        return Ok(None);
    }

    let mut observations: Vec<Observation> = Vec::new();
    for input in ctx.inputs.iter() {
        if let Some(obs) = lyquor_primitives::decode_object::<Observation>(&input.input) {
            observations.push(obs);
        }
    }

    let min_consensus = init.min_consensus as usize;
    let result = aggregate_observations(&observations, min_consensus);
    let Some(agreed) = result.agreed else {
        // Still waiting, or the round is disputed: do not certify.
        return Ok(None);
    };

    if result.outcome != ConsensusOutcome::Reached {
        return Ok(None);
    }

    let input = encode_by_fields!(state: BalanceState = agreed, candidates: u64 = result.observed).into();
    Ok(Some(CertifiedCallParams {
        origin: Address::ZERO,
        method: "update".into(),
        input,
        target: init.target,
    }))
}

// Submit a certified index update. This instance call asks the committee to
// reproduce the local replay and certify the reconciled record.
#[method::instance(export = eth)]
fn certify_replay(ctx: &mut _) -> LyquidResult<bool> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let oracle = ctx.network.indexer.clone();
    let call = oracle.propose_and_certify(
        &mut ctx,
        target,
        lyquor_primitives::encode_by_fields!(min_consensus: u16 = MIN_CONSENSUS, target: OracleTarget = target)
            .into(),
        None,
        None,
    )?;

    if let Some(call) = call {
        let _ = submit_certified_call!(call)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

// Certified network callback: store the verified record once the committee
// certificate has been verified by the target-side wrapper.
#[method::network(group = oracle::certified::indexer::two_phase)]
fn update(ctx: &mut _, state: BalanceState, candidates: u64) -> LyquidResult<bool> {
    let signer_ids = ctx.cert.signers.clone();
    let signers: Vec<String> = signer_ids
        .into_iter()
        .filter_map(|id| ctx.signer_node_id(id as u64))
        .map(|node| node.to_string())
        .collect();

    let address = state.address.clone();
    let record = IndexRecord {
        state,
        signers,
        candidates,
    };
    ctx.network.records.insert(address, record);

    trigger!(update_history(), TriggerMode::Commit);
    Ok(true)
}

// Node-local history snapshot, maintained after each committed update.
#[method::instance]
fn update_history(ctx: &mut _) -> LyquidResult<()> {
    let mut history = ctx.instance.history_cache.write();
    let mut id = ctx.instance.history_id.write();
    *id += 1;

    let snapshot: HashMap<String, IndexRecord> = ctx
        .network
        .records
        .iter()
        .map(|(addr, record)| (addr.clone(), record.clone()))
        .collect();

    history.push_back((
        *id,
        lyquor_api::systime()?,
        lyquor_api::chain_pos()?,
        snapshot,
    ));
    if history.len() > HISTORY_MAX {
        history.pop_front();
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Read-only queries (return JSON strings over the Ethereum ABI boundary)
// ---------------------------------------------------------------------------

// Return the verified record for one address, if it has been certified.
#[method::instance(export = eth)]
fn get_record(ctx: &_, address: String) -> LyquidResult<String> {
    let record = ctx.network.records.get(&address).cloned();
    serde_json::to_string(&record)
        .map_err(|e| LyquidError::LyquorRuntime(format!("JSON serialization failed: {e}")))
}

// List all verified records currently held in network state.
#[method::instance(export = eth)]
fn list_records(ctx: &_) -> LyquidResult<String> {
    let records: Vec<&IndexRecord> = ctx.network.records.values().collect();
    serde_json::to_string(&records)
        .map_err(|e| LyquidError::LyquorRuntime(format!("JSON serialization failed: {e}")))
}

// Return the committee node ids currently configured for the oracle topic.
#[method::instance(export = eth)]
fn get_node_ids(ctx: &_) -> LyquidResult<Vec<String>> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    Ok(ctx
        .network
        .indexer
        .config_current(&ctx, target)
        .committee
        .keys()
        .map(std::string::ToString::to_string)
        .collect())
}

// ---------------------------------------------------------------------------
// HTTP exports (used by the hosted static UI and the demo script)
// ---------------------------------------------------------------------------

#[method::instance(export = http, method = "GET", path_prefix = "/")]
fn index_spa(_ctx: &_, _req: http::Request) -> LyquidResult<http::Response> {
    Ok(http::Response {
        status: 200,
        headers: vec![http::Header {
            name: "content-type".into(),
            value: b"text/html; charset=utf-8".to_vec(),
        }],
        body: SPA_INDEX_HTML.to_vec(),
    })
}

#[method::instance(export = http, method = "GET", path_prefix = "/api/records")]
fn http_records(ctx: &_, _req: http::Request) -> LyquidResult<http::Response> {
    let records: Vec<_> = ctx
        .network
        .records
        .values()
        .map(|record| serde_json::to_value(record))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| LyquidError::LyquorRuntime(format!("JSON serialization failed: {e}")))?;
    let body = serde_json::to_vec(&serde_json::json!({ "records": records }))
        .map_err(|e| LyquidError::LyquorRuntime(format!("JSON serialization failed: {e}")))?;
    Ok(json_response(200, body))
}

#[method::instance(export = http, method = "GET", path_prefix = "/api/committee")]
fn http_committee(ctx: &_, _req: http::Request) -> LyquidResult<http::Response> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let config = ctx.network.indexer.config_current(&ctx, target);
    let node_ids = config.committee.keys().map(ToString::to_string).collect::<Vec<_>>();
    let body = serde_json::to_vec(&serde_json::json!({
        "nodeIds": node_ids,
        "threshold": config.threshold,
    }))
    .map_err(|e| LyquidError::LyquorRuntime(format!("JSON serialization failed: {e}")))?;
    Ok(json_response(200, body))
}

#[method::instance(export = http, method = "GET", path_prefix = "/api/history")]
fn http_history(ctx: &_, _req: http::Request) -> LyquidResult<http::Response> {
    let history = ctx.instance.history_cache.read();
    let results: Vec<_> = history
        .iter()
        .map(|(id, timestamp, chain_pos, snapshot)| {
            serde_json::json!({
                "id": id,
                "timestamp": timestamp,
                "chainPos": chain_pos,
                "records": snapshot,
            })
        })
        .collect();
    let body = serde_json::to_vec(&serde_json::json!({ "results": results }))
        .map_err(|e| LyquidError::LyquorRuntime(format!("JSON serialization failed: {e}")))?;
    Ok(json_response(200, body))
}

fn json_response(status: u16, body: Vec<u8>) -> http::Response {
    http::Response {
        status,
        headers: vec![
            http::Header {
                name: "content-type".into(),
                value: b"application/json; charset=utf-8".to_vec(),
            },
            http::Header {
                name: "cache-control".into(),
                value: b"no-cache".to_vec(),
            },
        ],
        body,
    }
}

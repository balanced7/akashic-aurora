//! Phase 0b criterion 5: do concurrent removals in p2panda-auth 0.7.1 converge?
//!
//! Replicas receive the same set of group operations in different causal (topological) orders.
//! p2panda-auth requires causal delivery, so "different orders" means different linear
//! extensions of the operation DAG. All replicas must end with the same members and access.
use std::collections::{BTreeMap, BTreeSet};

use p2panda_auth::Access;
use p2panda_auth::group::GroupMember;
use p2panda_auth::test_utils::{
    TestGroup, TestGroupState, TestOperation, add_member, create_group, demote_member,
    promote_member, remove_member,
};
use p2panda_auth::traits::Operation;
use proptest::prelude::*;

const G: char = 'G';
type Members = Vec<(char, String)>;

fn ind(c: char) -> GroupMember<char> {
    GroupMember::Individual(c)
}

fn members(y: &TestGroupState) -> Members {
    let mut m: Members = y
        .members(G)
        .into_iter()
        .map(|(id, a)| (id, a.to_string()))
        .collect();
    m.sort();
    m
}

/// Apply ops in the given order to a fresh replica.
fn replay(ops: &BTreeMap<u32, TestOperation>, order: &[u32]) -> Result<TestGroupState, String> {
    let mut y = TestGroup::init();
    for id in order {
        y = TestGroup::process(y, &ops[id]).map_err(|e| format!("op {id}: {e:?}"))?;
    }
    Ok(y)
}

/// All linear extensions (causal delivery orders) of the DAG.
fn all_orders(ops: &BTreeMap<u32, TestOperation>) -> Vec<Vec<u32>> {
    fn go(
        ops: &BTreeMap<u32, TestOperation>,
        done: &mut Vec<u32>,
        out: &mut Vec<Vec<u32>>,
    ) {
        if done.len() == ops.len() {
            out.push(done.clone());
            return;
        }
        let ready: Vec<u32> = ops
            .iter()
            .filter(|(id, op)| {
                !done.contains(id) && op.dependencies().iter().all(|d| done.contains(d))
            })
            .map(|(id, _)| *id)
            .collect();
        for id in ready {
            done.push(id);
            go(ops, done, out);
            done.pop();
        }
    }
    let mut out = vec![];
    go(ops, &mut vec![], &mut out);
    out
}

/// Replay every causal order; assert all replicas agree; return the agreed members.
fn assert_converges(ops: Vec<TestOperation>) -> (usize, Members) {
    let ops: BTreeMap<u32, TestOperation> = ops.into_iter().map(|o| (o.id, o)).collect();
    let orders = all_orders(&ops);
    let results: BTreeSet<Members> = orders
        .iter()
        .map(|o| members(&replay(&ops, o).expect("replay")))
        .collect();
    assert_eq!(results.len(), 1, "replicas diverged: {results:#?}");
    (orders.len(), results.into_iter().next().unwrap())
}

fn genesis(managers: &[char], others: &[(char, Access<()>)]) -> TestOperation {
    let mut init: Vec<_> = managers.iter().map(|m| (ind(*m), Access::manage())).collect();
    init.extend(others.iter().map(|(m, a)| (ind(*m), a.clone())));
    create_group(managers[0], 0, G, init, vec![])
}

// ---------------------------------------------------------------------------------------------
// Deterministic multi-order scenarios
// ---------------------------------------------------------------------------------------------

#[test]
fn s1_mutual_removal_two_managers() {
    // A, B, C manage; D reads. A removes B || B removes A.
    let ops = vec![
        genesis(&['A', 'B', 'C'], &[('D', Access::read())]),
        remove_member('A', 1, G, ind('B'), vec![0]),
        remove_member('B', 2, G, ind('A'), vec![0]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s1 orders={n} members={m:?}");
    assert_eq!(m, vec![('C', "manage".into()), ('D', "read".into())]);
}

#[test]
fn s2_mutual_removal_only_two_managers() {
    // A, B the only managers; D reads. A removes B || B removes A -> group has no manager left.
    let ops = vec![
        genesis(&['A', 'B'], &[('D', Access::read())]),
        remove_member('A', 1, G, ind('B'), vec![0]),
        remove_member('B', 2, G, ind('A'), vec![0]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s2 orders={n} members={m:?}");
    assert_eq!(m, vec![('D', "read".into())]);
}

#[test]
fn s3_both_remove_third() {
    // A removes C || B removes C.
    let ops = vec![
        genesis(&['A', 'B', 'C'], &[]),
        remove_member('A', 1, G, ind('C'), vec![0]),
        remove_member('B', 2, G, ind('C'), vec![0]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s3 orders={n} members={m:?}");
    assert_eq!(m, vec![('A', "manage".into()), ('B', "manage".into())]);
}

#[test]
fn s4_remove_vs_concurrent_actions_of_removed() {
    // A removes B || B adds E (manage) then E removes C. B's branch is invalidated transitively.
    let ops = vec![
        genesis(&['A', 'B', 'C'], &[]),
        remove_member('A', 1, G, ind('B'), vec![0]),
        add_member('B', 2, G, ind('E'), Access::manage(), vec![0]),
        remove_member('E', 3, G, ind('C'), vec![2]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s4 orders={n} members={m:?}");
    assert_eq!(m, vec![('A', "manage".into()), ('C', "manage".into())]);
}

#[test]
fn s5_removal_cycle_three_managers() {
    // A removes B || B removes C || C removes A -> all three in the cycle are removed.
    let ops = vec![
        genesis(&['A', 'B', 'C'], &[('D', Access::read())]),
        remove_member('A', 1, G, ind('B'), vec![0]),
        remove_member('B', 2, G, ind('C'), vec![0]),
        remove_member('C', 3, G, ind('A'), vec![0]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s5 orders={n} members={m:?}");
    assert_eq!(m, vec![('D', "read".into())]);
}

#[test]
fn s6_mutual_removal_plus_third_removes_and_merge() {
    // A removes B || B removes A || C removes D; then C (merging all heads) adds E.
    let ops = vec![
        genesis(&['A', 'B', 'C'], &[('D', Access::read())]),
        remove_member('A', 1, G, ind('B'), vec![0]),
        remove_member('B', 2, G, ind('A'), vec![0]),
        remove_member('C', 3, G, ind('D'), vec![0]),
        add_member('C', 4, G, ind('E'), Access::read(), vec![1, 2, 3]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s6 orders={n} members={m:?}");
    assert_eq!(m, vec![('C', "manage".into()), ('E', "read".into())]);
}

#[test]
fn s7_demote_counts_as_removal() {
    // A demotes B to read || B removes A: mutual (demotion of a manager is a removal of authority).
    let ops = vec![
        genesis(&['A', 'B', 'C'], &[]),
        demote_member('A', 1, G, ind('B'), Access::read(), vec![0]),
        remove_member('B', 2, G, ind('A'), vec![0]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s7 orders={n} members={m:?}");
}

#[test]
fn s8_remove_and_concurrent_readd() {
    // A removes C || B removes C then re-adds C: strong remove wins, C stays out.
    let ops = vec![
        genesis(&['A', 'B'], &[('C', Access::read())]),
        remove_member('A', 1, G, ind('C'), vec![0]),
        remove_member('B', 2, G, ind('C'), vec![0]),
        add_member('B', 3, G, ind('C'), Access::read(), vec![2]),
    ];
    let (n, m) = assert_converges(ops);
    println!("s8 orders={n} members={m:?}");
}

// ---------------------------------------------------------------------------------------------
// Property test: random concurrent DAGs of add/remove/promote/demote, random delivery orders
// ---------------------------------------------------------------------------------------------

const ACTORS: [char; 6] = ['A', 'B', 'C', 'D', 'E', 'F'];

#[derive(Clone, Debug)]
struct Step {
    author: usize,
    kind: u8,
    target: usize,
    level: u8,
    deps_mask: u16,
}

fn step() -> impl Strategy<Value = Step> {
    // Authors are biased towards the initial managers (A, B, C) so most candidates are valid;
    // kinds are biased towards removals.
    let author = prop_oneof![8 => 0..3usize, 2 => 0..ACTORS.len()];
    let kind = prop_oneof![5 => Just(0u8), 2 => Just(1u8), 1 => Just(2u8), 2 => Just(3u8)];
    (author, kind, 0..ACTORS.len(), 0u8..4, any::<u16>()).prop_map(
        |(author, kind, target, level, deps_mask)| Step { author, kind, target, level, deps_mask },
    )
}

fn level(l: u8) -> Access<()> {
    match l {
        0 => Access::pull(),
        1 => Access::read(),
        2 => Access::write(),
        _ => Access::manage(),
    }
}

/// Maximal elements of a set of op ids (drop any id that is an ancestor of another).
fn frontier(ops: &BTreeMap<u32, TestOperation>, ids: BTreeSet<u32>) -> Vec<u32> {
    fn ancestors(ops: &BTreeMap<u32, TestOperation>, id: u32, acc: &mut BTreeSet<u32>) {
        for d in ops[&id].dependencies() {
            if acc.insert(d) {
                ancestors(ops, d, acc);
            }
        }
    }
    let mut anc = BTreeSet::new();
    for id in &ids {
        ancestors(ops, *id, &mut anc);
    }
    ids.into_iter().filter(|i| !anc.contains(i)).collect()
}

fn causal_past(ops: &BTreeMap<u32, TestOperation>, deps: &[u32]) -> Vec<u32> {
    let mut acc: BTreeSet<u32> = deps.iter().copied().collect();
    let mut stack: Vec<u32> = deps.to_vec();
    while let Some(id) = stack.pop() {
        for d in ops[&id].dependencies() {
            if acc.insert(d) {
                stack.push(d);
            }
        }
    }
    acc.into_iter().collect() // ascending id == a valid causal order (deps have smaller ids)
}

/// Build a DAG of only *valid* operations: each candidate is checked against a replica holding
/// exactly its causal past (what its author would have seen).
fn build_dag(steps: &[Step]) -> BTreeMap<u32, TestOperation> {
    let mut ops = BTreeMap::new();
    ops.insert(
        0,
        genesis(&['A', 'B', 'C'], &[('D', Access::read())]),
    );
    let mut next_id = 1u32;
    for s in steps {
        let existing: Vec<u32> = ops.keys().copied().collect();
        let picked: BTreeSet<u32> = existing
            .iter()
            .enumerate()
            .filter(|(i, _)| s.deps_mask & (1 << (i % 16)) != 0)
            .map(|(_, id)| *id)
            .collect();
        let picked = if picked.is_empty() { BTreeSet::from([*existing.last().unwrap()]) } else { picked };
        let deps = frontier(&ops, picked);
        let author = ACTORS[s.author];
        let target = ind(ACTORS[s.target]);
        let op = match s.kind {
            0 => remove_member(author, next_id, G, target, deps.clone()),
            1 => add_member(author, next_id, G, target, level(s.level), deps.clone()),
            2 => promote_member(author, next_id, G, target, level(s.level), deps.clone()),
            _ => demote_member(author, next_id, G, target, level(s.level), deps.clone()),
        };
        let past = causal_past(&ops, &deps);
        let Ok(y) = replay(&ops, &past) else { continue };
        if TestGroup::process(y, &op).is_ok() {
            ops.insert(next_id, op);
            next_id += 1;
        }
    }
    ops
}

/// A pseudo-random causal order driven by `seed`.
fn random_order(ops: &BTreeMap<u32, TestOperation>, mut seed: u64) -> Vec<u32> {
    let mut done: Vec<u32> = vec![];
    while done.len() < ops.len() {
        let ready: Vec<u32> = ops
            .iter()
            .filter(|(id, op)| {
                !done.contains(id) && op.dependencies().iter().all(|d| done.contains(d))
            })
            .map(|(id, _)| *id)
            .collect();
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        done.push(ready[(seed >> 33) as usize % ready.len()]);
    }
    done
}

proptest! {
    #![proptest_config(ProptestConfig { cases: std::env::var("CASES").ok().and_then(|v| v.parse().ok()).unwrap_or(2000), .. ProptestConfig::default() })]

    #[test]
    fn random_concurrent_ops_converge(
        steps in prop::collection::vec(step(), 1..14),
        seeds in prop::collection::vec(any::<u64>(), 6),
    ) {
        let ops = build_dag(&steps);
        let reference = members(&replay(&ops, &ops.keys().copied().collect::<Vec<_>>()).unwrap());
        for seed in seeds {
            let order = random_order(&ops, seed);
            let got = replay(&ops, &order);
            prop_assert!(got.is_ok(), "replay error {:?} order {:?}", got.err(), order);
            let got = members(&got.unwrap());
            prop_assert_eq!(&got, &reference, "order {:?} ops {:#?}", order, ops);
        }
    }
}

/// Sanity check that the generator produces real concurrency (not just linear chains).
#[test]
fn generator_stats() {
    use proptest::strategy::ValueTree;
    use proptest::test_runner::TestRunner;
    let mut runner = TestRunner::deterministic();
    let strat = prop::collection::vec(step(), 1..14);
    let (mut total_ops, mut concurrent_dags, mut removes, mut mutual, mut orders_gt1) = (0, 0, 0, 0, 0);
    let n = 2000;
    for _ in 0..n {
        let steps = strat.new_tree(&mut runner).unwrap().current();
        let ops = build_dag(&steps);
        total_ops += ops.len() - 1;
        let concurrent = ops.values().any(|o| {
            ops.values().any(|p| p.id != o.id && p.dependencies() == o.dependencies() && o.id != 0)
        });
        if concurrent { concurrent_dags += 1; }
        let rem: Vec<_> = ops.values().filter(|o| matches!(o.action, p2panda_auth::group::GroupAction::Remove{..})).collect();
        removes += rem.len();
        if rem.iter().any(|a| rem.iter().any(|b| a.author == b.action_target() && b.author == a.action_target())) { mutual += 1; }
        let distinct: BTreeSet<Vec<u32>> = (0..6u64).map(|s| random_order(&ops, s * 7919 + 1)).collect();
        if distinct.len() > 1 { orders_gt1 += 1; }
    }
    println!("dags={n} avg_ops={:.2} dags_with_sibling_concurrency={concurrent_dags} removes={removes} dags_with_mutual_remove={mutual} dags_with_multiple_delivery_orders={orders_gt1}", total_ops as f64 / n as f64);
}

trait Target { fn action_target(&self) -> char; }
impl Target for TestOperation {
    fn action_target(&self) -> char {
        use p2panda_auth::group::GroupAction::*;
        match &self.action { Remove{member} | Add{member,..} | Promote{member,..} | Demote{member,..} => member.id(), Create{..} => '-' }
    }
}

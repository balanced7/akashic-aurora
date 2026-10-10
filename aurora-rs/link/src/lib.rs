//! `aurora-link`: the pure core of Aurora's fleet links.
//!
//! One implementation of every security-relevant rule: identity, the ACL log, the record
//! envelope, the per-link store and the sync plan. `aurora-linkd` adds the network and the RPC
//! channel around it; Python never re-implements any of it (aurora-rs/README.md, "Required
//! crates"). See RFC balanced7/akashic-aurora#70 and its Rust addendum.

pub mod acl;
pub mod codec;
pub mod crypto;
pub mod engine;
pub mod error;
pub mod identity;
pub mod invite;
pub mod record;
pub mod store;
pub mod sync;

pub use ed25519_dalek;
pub use error::{LinkError, Result};

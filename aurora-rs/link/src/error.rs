//! One error type for everything that comes off the wire or out of the store.
//!
//! The message says which check failed, for the local log. It never travels back to a remote
//! peer: the transport answers every refusal with the same close code, because a door that
//! explains itself precisely is an oracle (the rule `bridge_seal.SealRefused` already followed).

use thiserror::Error;

#[derive(Debug, Error)]
pub enum LinkError {
    /// Input was refused: malformed, unsigned, out of policy, or from a non-member.
    #[error("refused: {0}")]
    Refused(String),
    /// A local precondition is missing (no identity yet, unknown link, no read key).
    #[error("unavailable: {0}")]
    Unavailable(String),
    /// The local store could not be read or written.
    #[error("store: {0}")]
    Store(#[from] rusqlite::Error),
    /// Local file I/O.
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
}

pub type Result<T, E = LinkError> = std::result::Result<T, E>;

/// Shorthand for a refusal with a formatted reason.
#[macro_export]
macro_rules! refuse {
    ($($arg:tt)*) => { return Err($crate::error::LinkError::Refused(format!($($arg)*))) };
}

pub(crate) fn refused(why: impl Into<String>) -> LinkError {
    LinkError::Refused(why.into())
}

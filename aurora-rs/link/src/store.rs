//! The per-link SQLite store: `state/link/<link_id>.db`.
//!
//! Plain SQLite (not SQLCipher), WAL, the same pragmas as `SqliteStore`, so Python's stdlib
//! `sqlite3` can open it read-only for `doctor` and the console. Records are already sealed, so
//! the file needs no encryption of its own. Bodies opened for this fleet are cached in
//! `records.body`; that cache is plaintext on purpose, exactly like the bus and the inbox it feeds.
//!
//! Records are never rewritten (ADR 0003): retention clears `ct` and `body` and keeps the signed
//! header, so the chain still verifies.

use std::collections::BTreeMap;
use std::path::Path;

use rusqlite::{Connection, OptionalExtension, params};

use crate::acl::Entry;
use crate::error::Result;
use crate::record::Record;

pub const SCHEMA_VERSION: i64 = 1;

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS acl_entries(
  hash TEXT PRIMARY KEY, seq INTEGER NOT NULL, json TEXT NOT NULL, received_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS records(
  id TEXT PRIMARY KEY, author TEXT NOT NULL, seq INTEGER NOT NULL, epoch INTEGER NOT NULL,
  header TEXT NOT NULL, ct TEXT, status TEXT NOT NULL, body TEXT, reason TEXT,
  received_at INTEGER NOT NULL, cursor INTEGER UNIQUE, UNIQUE(author, seq));
CREATE TABLE IF NOT EXISTS heads(author TEXT PRIMARY KEY, seq INTEGER NOT NULL, id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS blobs(
  id TEXT PRIMARY KEY, record_id TEXT NOT NULL, name TEXT NOT NULL, bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS keys(epoch INTEGER PRIMARY KEY, wrap TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS promotions(
  record_id TEXT PRIMARY KEY, seat TEXT NOT NULL, by TEXT NOT NULL, bus_id TEXT, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS exports(source TEXT PRIMARY KEY, record_id TEXT NOT NULL, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS receipts(
  record_id TEXT NOT NULL, fleet TEXT NOT NULL, state TEXT NOT NULL, at INTEGER NOT NULL,
  PRIMARY KEY(record_id, fleet, state));
CREATE TABLE IF NOT EXISTS alarms(
  id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL, kind TEXT NOT NULL, author TEXT NOT NULL,
  detail TEXT NOT NULL, UNIQUE(kind, author, detail));
CREATE TABLE IF NOT EXISTS frozen(author TEXT PRIMARY KEY, reason TEXT NOT NULL, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS verified(root TEXT PRIMARY KEY, safety_number TEXT NOT NULL, at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS contacts(device TEXT PRIMARY KEY, at INTEGER NOT NULL, via TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS refusals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL, device TEXT NOT NULL, reason TEXT NOT NULL);
";

/// Record states. `admitted` reached the quarantine; `own` is this fleet's; `opaque` could not be
/// opened here (a mailbox, or no key yet); `withheld` passed the chain but its body was refused.
pub const ADMITTED: &str = "admitted";
pub const OWN: &str = "own";
pub const OPAQUE: &str = "opaque";
pub const WITHHELD: &str = "withheld";
/// Another fleet's `ack`: receipts for our mail, never surfaced and never "own".
pub const RECEIPT: &str = "receipt";

/// A promotion: (seat, promoted by, bus message id, when).
pub type Promotion = (String, String, Option<String>, u64);

pub struct Store {
    pub conn: Connection,
}

#[derive(Clone, Debug)]
pub struct StoredRecord {
    pub record: Record,
    pub status: String,
    pub body: Option<String>,
    pub reason: Option<String>,
    pub received_at: u64,
    pub cursor: Option<i64>,
}

impl Store {
    pub fn open(path: &Path) -> Result<Self> {
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir)?;
        }
        let conn = Connection::open(path)?;
        conn.busy_timeout(std::time::Duration::from_secs(10))?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.pragma_update(None, "synchronous", "NORMAL")?;
        conn.execute_batch(SCHEMA)?;
        conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema', ?1)",
            params![SCHEMA_VERSION.to_string()],
        )?;
        Ok(Self { conn })
    }

    pub fn in_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        conn.execute_batch(SCHEMA)?;
        Ok(Self { conn })
    }

    pub fn meta(&self, key: &str) -> Result<Option<String>> {
        Ok(self
            .conn
            .query_row("SELECT value FROM meta WHERE key = ?1", params![key], |r| r.get(0))
            .optional()?)
    }

    pub fn set_meta(&self, key: &str, value: &str) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?1, ?2)",
            params![key, value],
        )?;
        Ok(())
    }

    // ---- ACL
    pub fn put_acl(&self, hash: &str, e: &Entry, now: u64) -> Result<()> {
        let json = serde_json::to_string(e).expect("entries serialise");
        self.conn.execute(
            "INSERT OR IGNORE INTO acl_entries(hash, seq, json, received_at) VALUES (?1, ?2, ?3, ?4)",
            params![hash, e.seq as i64, json, now as i64],
        )?;
        Ok(())
    }

    pub fn acl_entries(&self) -> Result<Vec<Entry>> {
        let mut st = self.conn.prepare("SELECT json FROM acl_entries ORDER BY seq, hash")?;
        let rows = st.query_map([], |r| r.get::<_, String>(0))?;
        let mut out = Vec::new();
        for row in rows {
            out.push(serde_json::from_str(&row?).map_err(|e| crate::error::refused(format!("stored ACL entry: {e}")))?);
        }
        Ok(out)
    }

    // ---- records
    pub fn record_at(&self, author: &str, seq: u64) -> Result<Option<String>> {
        Ok(self
            .conn
            .query_row(
                "SELECT id FROM records WHERE author = ?1 AND seq = ?2",
                params![author, seq as i64],
                |r| r.get(0),
            )
            .optional()?)
    }

    pub fn head(&self, author: &str) -> Result<Option<(u64, String)>> {
        Ok(self
            .conn
            .query_row("SELECT seq, id FROM heads WHERE author = ?1", params![author], |r| {
                Ok((r.get::<_, i64>(0)? as u64, r.get(1)?))
            })
            .optional()?)
    }

    pub fn heads(&self) -> Result<BTreeMap<String, (u64, String)>> {
        let mut st = self.conn.prepare("SELECT author, seq, id FROM heads")?;
        let rows = st.query_map([], |r| {
            Ok((r.get::<_, String>(0)?, (r.get::<_, i64>(1)? as u64, r.get(2)?)))
        })?;
        Ok(rows.collect::<std::result::Result<_, _>>()?)
    }

    /// Store a verified record and advance its author's head. The caller has checked the chain.
    pub fn put_record(
        &self,
        id: &str,
        r: &Record,
        status: &str,
        body: Option<&str>,
        reason: Option<&str>,
        now: u64,
    ) -> Result<Option<i64>> {
        let header = serde_json::to_string(&r.retired()).expect("records serialise");
        let cursor: Option<i64> = if status == ADMITTED {
            Some(
                self.conn
                    .query_row("SELECT COALESCE(MAX(cursor), 0) + 1 FROM records", [], |row| row.get(0))?,
            )
        } else {
            None
        };
        let tx = self.conn.unchecked_transaction()?;
        tx.execute(
            "INSERT INTO records(id, author, seq, epoch, header, ct, status, body, reason, received_at, cursor)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                id,
                r.author,
                r.seq as i64,
                r.epoch as i64,
                header,
                r.ct,
                status,
                body,
                reason,
                now as i64,
                cursor
            ],
        )?;
        tx.execute(
            "INSERT INTO heads(author, seq, id) VALUES (?1, ?2, ?3)
             ON CONFLICT(author) DO UPDATE SET seq = excluded.seq, id = excluded.id WHERE excluded.seq > heads.seq",
            params![r.author, r.seq as i64, id],
        )?;
        tx.commit()?;
        Ok(cursor)
    }

    fn row_to_stored(r: &rusqlite::Row<'_>) -> rusqlite::Result<StoredRecord> {
        let header: String = r.get(0)?;
        let mut record: Record = serde_json::from_str(&header)
            .map_err(|e| rusqlite::Error::FromSqlConversionFailure(0, rusqlite::types::Type::Text, Box::new(e)))?;
        record.ct = r.get(1)?;
        Ok(StoredRecord {
            record,
            status: r.get(2)?,
            body: r.get(3)?,
            reason: r.get(4)?,
            received_at: r.get::<_, i64>(5)? as u64,
            cursor: r.get(6)?,
        })
    }

    const COLS: &'static str = "header, ct, status, body, reason, received_at, cursor";

    pub fn get(&self, id: &str) -> Result<Option<StoredRecord>> {
        let sql = format!("SELECT {} FROM records WHERE id = ?1", Self::COLS);
        Ok(self.conn.query_row(&sql, params![id], Self::row_to_stored).optional()?)
    }

    /// One author's records with `from < seq <= to`, in order.
    pub fn range(&self, author: &str, from: u64, to: u64) -> Result<Vec<Record>> {
        let sql = format!(
            "SELECT {} FROM records WHERE author = ?1 AND seq > ?2 AND seq <= ?3 ORDER BY seq",
            Self::COLS
        );
        let mut st = self.conn.prepare(&sql)?;
        let rows = st.query_map(params![author, from as i64, to as i64], Self::row_to_stored)?;
        Ok(rows
            .map(|r| r.map(|s| s.record))
            .collect::<std::result::Result<_, _>>()?)
    }

    /// Admitted records after `cursor`, oldest first.
    pub fn events_after(&self, cursor: i64, limit: u32) -> Result<Vec<(String, StoredRecord)>> {
        let sql = format!(
            "SELECT id, {} FROM records WHERE cursor > ?1 ORDER BY cursor LIMIT ?2",
            Self::COLS
        );
        let mut st = self.conn.prepare(&sql)?;
        let rows = st.query_map(params![cursor, limit], |r| {
            let id: String = r.get(0)?;
            let header: String = r.get(1)?;
            let mut record: Record = serde_json::from_str(&header)
                .map_err(|e| rusqlite::Error::FromSqlConversionFailure(1, rusqlite::types::Type::Text, Box::new(e)))?;
            record.ct = r.get(2)?;
            Ok((
                id,
                StoredRecord {
                    record,
                    status: r.get(3)?,
                    body: r.get(4)?,
                    reason: r.get(5)?,
                    received_at: r.get::<_, i64>(6)? as u64,
                    cursor: r.get(7)?,
                },
            ))
        })?;
        Ok(rows.collect::<std::result::Result<_, _>>()?)
    }

    pub fn last_cursor(&self) -> Result<i64> {
        Ok(self
            .conn
            .query_row("SELECT COALESCE(MAX(cursor), 0) FROM records", [], |r| r.get(0))?)
    }

    pub fn count_recent(&self, author: &str, since: u64) -> Result<u64> {
        let n: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM records WHERE author = ?1 AND received_at >= ?2",
            params![author, since as i64],
            |r| r.get(0),
        )?;
        Ok(n as u64)
    }

    /// Retire bodies older than `before`: drop ciphertext and cached plaintext, keep headers.
    pub fn retire_before(&self, before: u64) -> Result<usize> {
        Ok(self.conn.execute(
            "UPDATE records SET ct = NULL, body = NULL WHERE received_at < ?1 AND (ct IS NOT NULL OR body IS NOT NULL)",
            params![before as i64],
        )?)
    }

    // ---- bookkeeping
    pub fn alarm(&self, kind: &str, author: &str, detail: &str, now: u64) -> Result<()> {
        self.conn.execute(
            "INSERT OR IGNORE INTO alarms(at, kind, author, detail) VALUES (?1, ?2, ?3, ?4)",
            params![now as i64, kind, author, detail],
        )?;
        Ok(())
    }

    pub fn alarms(&self) -> Result<Vec<(u64, String, String, String)>> {
        let mut st = self
            .conn
            .prepare("SELECT at, kind, author, detail FROM alarms ORDER BY id")?;
        let rows = st.query_map([], |r| {
            Ok((r.get::<_, i64>(0)? as u64, r.get(1)?, r.get(2)?, r.get(3)?))
        })?;
        Ok(rows.collect::<std::result::Result<_, _>>()?)
    }

    pub fn freeze(&self, author: &str, reason: &str, now: u64) -> Result<()> {
        self.conn.execute(
            "INSERT OR IGNORE INTO frozen(author, reason, at) VALUES (?1, ?2, ?3)",
            params![author, reason, now as i64],
        )?;
        Ok(())
    }

    pub fn frozen(&self, author: &str) -> Result<bool> {
        Ok(self
            .conn
            .query_row("SELECT 1 FROM frozen WHERE author = ?1", params![author], |_| Ok(()))
            .optional()?
            .is_some())
    }

    pub fn put_blob(&self, id: &str, record_id: &str, name: &str, bytes: u64) -> Result<()> {
        self.conn.execute(
            "INSERT OR IGNORE INTO blobs(id, record_id, name, bytes) VALUES (?1, ?2, ?3, ?4)",
            params![id, record_id, name, bytes as i64],
        )?;
        Ok(())
    }

    pub fn blob_ids(&self) -> Result<Vec<String>> {
        let mut st = self.conn.prepare("SELECT id FROM blobs")?;
        let rows = st.query_map([], |r| r.get(0))?;
        Ok(rows.collect::<std::result::Result<_, _>>()?)
    }

    pub fn contact(&self, device: &str, via: &str, now: u64) -> Result<()> {
        self.conn.execute(
            "INSERT INTO contacts(device, at, via) VALUES (?1, ?2, ?3)
             ON CONFLICT(device) DO UPDATE SET at = excluded.at, via = excluded.via",
            params![device, now as i64, via],
        )?;
        Ok(())
    }

    pub fn refusal(&self, device: &str, reason: &str, now: u64) -> Result<()> {
        self.conn.execute(
            "INSERT INTO refusals(at, device, reason) VALUES (?1, ?2, ?3)",
            params![now as i64, device, reason],
        )?;
        self.conn.execute(
            "DELETE FROM refusals WHERE id <= (SELECT MAX(id) FROM refusals) - 500",
            [],
        )?;
        Ok(())
    }

    /// Record a receipt; returns true when it is new.
    pub fn receipt(&self, record_id: &str, fleet: &str, state: &str, now: u64) -> Result<bool> {
        Ok(self.conn.execute(
            "INSERT OR IGNORE INTO receipts(record_id, fleet, state, at) VALUES (?1, ?2, ?3, ?4)",
            params![record_id, fleet, state, now as i64],
        )? > 0)
    }

    /// Promote once: returns false when the record was already promoted.
    pub fn promote(&self, record_id: &str, seat: &str, by: &str, bus_id: &str, now: u64) -> Result<bool> {
        Ok(self.conn.execute(
            "INSERT OR IGNORE INTO promotions(record_id, seat, by, bus_id, at) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![record_id, seat, by, bus_id, now as i64],
        )? > 0)
    }

    pub fn promoted(&self, record_id: &str) -> Result<Option<Promotion>> {
        Ok(self
            .conn
            .query_row(
                "SELECT seat, by, bus_id, at FROM promotions WHERE record_id = ?1",
                params![record_id],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get::<_, i64>(3)? as u64)),
            )
            .optional()?)
    }

    /// Remember an exported bus message; returns false when it was already exported.
    pub fn export(&self, source: &str, record_id: &str, now: u64) -> Result<bool> {
        Ok(self.conn.execute(
            "INSERT OR IGNORE INTO exports(source, record_id, at) VALUES (?1, ?2, ?3)",
            params![source, record_id, now as i64],
        )? > 0)
    }

    pub fn exported(&self, source: &str) -> Result<Option<String>> {
        Ok(self
            .conn
            .query_row(
                "SELECT record_id FROM exports WHERE source = ?1",
                params![source],
                |r| r.get(0),
            )
            .optional()?)
    }

    pub fn mark_verified(&self, root: &str, safety: &str, now: u64) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO verified(root, safety_number, at) VALUES (?1, ?2, ?3)",
            params![root, safety, now as i64],
        )?;
        Ok(())
    }

    pub fn verified(&self, root: &str) -> Result<Option<String>> {
        Ok(self
            .conn
            .query_row(
                "SELECT safety_number FROM verified WHERE root = ?1",
                params![root],
                |r| r.get(0),
            )
            .optional()?)
    }
}

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

use crate::acl::{Entry, Evidence, EvidenceKey, EvidenceKind, Proposal, ProposalRefusal};
use crate::error::Result;
use crate::record::Record;

/// 2: records carry their signed write time (`written_at`), and blobs are listed per record.
/// 3: ACL entries name a set of parents and an author sequence; records name a set of ACL heads.
/// 4: a join counts toward no author sequence, and pruned ACL entries leave a stub.
/// 5: no stubs (review finding R4-2); certificates carry a proof of possession; joins name the
///    entry that issued their invite.
/// 6: the ACL is a linear chain ordered by one sequencer (review round 5): entries by seq,
///    equivocation evidence, proposals, and the chain position each record names.
/// 7: proposals carry an expiry, and each relayed proposal names its origin (`grp`: the
///    proposer's root, or the invite a join uses), so no origin fills the relay queue (review
///    round 6).
/// 8: equivocation evidence is kept as pairs, one per position and signer, each with what it did
///    (`halt`, `alarm` or `past`), and at most `acl::MAX_EVIDENCE_PAIRS` of them (review round 7).
pub const SCHEMA_VERSION: i64 = 8;

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS acl_entries(
  seq INTEGER PRIMARY KEY, hash TEXT NOT NULL, term INTEGER NOT NULL, json TEXT NOT NULL,
  received_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS acl_evidence(
  signer TEXT NOT NULL, term INTEGER NOT NULL, seq INTEGER NOT NULL, ours TEXT NOT NULL, theirs TEXT NOT NULL,
  kind TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY(signer, term, seq));
CREATE TABLE IF NOT EXISTS proposals(
  id TEXT PRIMARY KEY, json TEXT NOT NULL, mine INTEGER NOT NULL, status TEXT NOT NULL, why TEXT,
  refusal TEXT, at INTEGER NOT NULL, grp TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS records(
  id TEXT PRIMARY KEY, author TEXT NOT NULL, seq INTEGER NOT NULL, epoch INTEGER NOT NULL,
  header TEXT NOT NULL, ct TEXT, status TEXT NOT NULL, body TEXT, reason TEXT,
  received_at INTEGER NOT NULL, written_at INTEGER NOT NULL, cursor INTEGER UNIQUE,
  acl_seq INTEGER NOT NULL, acl_hash TEXT NOT NULL, UNIQUE(author, seq));
CREATE TABLE IF NOT EXISTS heads(author TEXT PRIMARY KEY, seq INTEGER NOT NULL, id TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS records_by_author_received ON records(author, received_at);
CREATE TABLE IF NOT EXISTS blobs(
  id TEXT NOT NULL, record_id TEXT NOT NULL, author TEXT NOT NULL, name TEXT NOT NULL,
  ct_bytes INTEGER NOT NULL, PRIMARY KEY(id, record_id));
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

/// A proposal's status, the reason it was refused, and the sequencer's signed refusal.
pub type ProposalStatus = (String, Option<String>, Option<ProposalRefusal>);

/// A proposal this replica holds: its own, or one it relays toward the sequencer.
#[derive(Clone, Debug)]
pub struct StoredProposal {
    pub id: String,
    pub proposal: Proposal,
    pub mine: bool,
    pub status: String,
    pub why: Option<String>,
    pub refusal: Option<ProposalRefusal>,
    pub at: u64,
}

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
        let store = Self { conn };
        if store.meta("schema")?.as_deref() != Some(SCHEMA_VERSION.to_string().as_str()) {
            return Err(crate::error::LinkError::Unavailable(format!(
                "{} was written in an older link format; remove it and sync the link again",
                path.display()
            )));
        }
        Ok(store)
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
    /// Rewrite the stored chain from `from` on with `entries` (the chain's entries from `from`).
    pub fn put_acl_from(&self, from: u64, entries: &[Entry], now: u64) -> Result<()> {
        let tx = self.conn.unchecked_transaction()?;
        tx.execute("DELETE FROM acl_entries WHERE seq >= ?1", params![from as i64])?;
        for e in entries {
            let json = serde_json::to_string(e).expect("entries serialise");
            tx.execute(
                "INSERT INTO acl_entries(seq, hash, term, json, received_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![e.seq as i64, e.hash()?, e.term as i64, json, now as i64],
            )?;
        }
        tx.commit()?;
        Ok(())
    }

    /// The stored chain, genesis first.
    pub fn acl_entries(&self) -> Result<Vec<Entry>> {
        Self::entries_of(&self.conn, "SELECT json FROM acl_entries ORDER BY seq")
    }

    fn entries_of(conn: &Connection, sql: &str) -> Result<Vec<Entry>> {
        let mut st = conn.prepare(sql)?;
        let rows = st.query_map([], |r| r.get::<_, String>(0))?;
        let mut out = Vec::new();
        for row in rows {
            out.push(serde_json::from_str(&row?).map_err(|e| crate::error::refused(format!("stored ACL entry: {e}")))?);
        }
        Ok(out)
    }

    /// Keep an evidence pair, the first one for its position and signer (review finding R7-1),
    /// within `cap` pairs. At the cap an alarm-only pair is not kept, and a halt's pair replaces
    /// the oldest pair that is not a halt (the oldest of any other kind first). Returns whether it
    /// was kept.
    pub fn put_evidence(&self, ev: &Evidence, now: u64, cap: u32) -> Result<bool> {
        let (signer, term, seq) = ev.key();
        let n: i64 = self
            .conn
            .query_row("SELECT count(*) FROM acl_evidence", [], |r| r.get(0))?;
        if n >= i64::from(cap) {
            if ev.kind != EvidenceKind::Halt {
                return Ok(false);
            }
            self.conn.execute(
                "DELETE FROM acl_evidence WHERE rowid IN
                   (SELECT rowid FROM acl_evidence WHERE kind != 'halt'
                    ORDER BY kind = 'past' DESC, at, seq LIMIT ?1)",
                params![n - i64::from(cap) + 1],
            )?;
        }
        Ok(self.conn.execute(
            "INSERT OR IGNORE INTO acl_evidence(signer, term, seq, ours, theirs, kind, at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                signer,
                term as i64,
                seq as i64,
                serde_json::to_string(&ev.ours).expect("entries serialise"),
                serde_json::to_string(&ev.theirs).expect("entries serialise"),
                ev.kind.as_str(),
                now as i64
            ],
        )? > 0)
    }

    /// Only the pair of the current halt (`halt`, as its key) stays a `halt`: one that a lower halt
    /// or a takeover replaced is `past`, and is not checked again on a restart.
    pub fn settle_evidence(&self, halt: Option<&EvidenceKey>) -> Result<()> {
        let (signer, term, seq) = halt.cloned().unwrap_or_default();
        self.conn.execute(
            "UPDATE acl_evidence SET kind = 'past'
             WHERE kind = 'halt' AND NOT (signer = ?1 AND term = ?2 AND seq = ?3)",
            params![signer, term as i64, seq as i64],
        )?;
        Ok(())
    }

    /// Every evidence pair kept, oldest first. A row that no longer parses is skipped.
    pub fn evidence(&self) -> Result<Vec<Evidence>> {
        let mut st = self
            .conn
            .prepare("SELECT ours, theirs, kind FROM acl_evidence ORDER BY at, signer, term, seq")?;
        let rows = st.query_map([], |r| {
            Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?, r.get::<_, String>(2)?))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (ours, theirs, kind) = row?;
            if let (Ok(ours), Ok(theirs), Some(kind)) = (
                serde_json::from_str(&ours),
                serde_json::from_str(&theirs),
                EvidenceKind::parse(&kind),
            ) {
                out.push(Evidence { ours, theirs, kind });
            }
        }
        Ok(out)
    }

    // ---- proposals
    /// Keep a proposal: ours (`mine`), or one we relay toward the sequencer. A known one keeps
    /// its status.
    pub fn put_proposal(&self, id: &str, p: &Proposal, mine: bool, now: u64) -> Result<bool> {
        let grp = match p.parsed() {
            Ok(crate::acl::Op::Join(j)) => format!("invite:{}", j.invite),
            _ => p.proposer.root.clone(),
        };
        Ok(self.conn.execute(
            "INSERT OR IGNORE INTO proposals(id, json, mine, status, at, grp) VALUES (?1, ?2, ?3, 'queued', ?4, ?5)",
            params![
                id,
                serde_json::to_string(p).expect("proposals serialise"),
                mine as i64,
                now as i64,
                grp
            ],
        )? > 0)
    }

    /// Mark a proposal `included` or `refused` (with the sequencer's signed refusal).
    pub fn set_proposal(
        &self,
        id: &str,
        status: &str,
        why: Option<&str>,
        refusal: Option<&ProposalRefusal>,
    ) -> Result<()> {
        self.conn.execute(
            "UPDATE proposals SET status = ?2, why = ?3, refusal = ?4 WHERE id = ?1",
            params![
                id,
                status,
                why,
                refusal.map(|r| serde_json::to_string(r).expect("refusals serialise"))
            ],
        )?;
        Ok(())
    }

    /// A proposal row (`id, json, mine, status, why, refusal, at`); `None` when its JSON no longer
    /// parses (an older format).
    fn row_to_proposal(r: &rusqlite::Row<'_>) -> rusqlite::Result<Option<StoredProposal>> {
        let json: String = r.get(1)?;
        let refusal: Option<String> = r.get(5)?;
        Ok(serde_json::from_str(&json).ok().map(|proposal| StoredProposal {
            id: r.get(0).unwrap_or_default(),
            proposal,
            mine: r.get::<_, i64>(2).unwrap_or(0) != 0,
            status: r.get(3).unwrap_or_default(),
            why: r.get(4).unwrap_or_default(),
            refusal: refusal.and_then(|x| serde_json::from_str(&x).ok()),
            at: r.get::<_, i64>(6).unwrap_or(0) as u64,
        }))
    }

    /// Proposals with `status`, oldest first.
    pub fn proposals(&self, status: &str) -> Result<Vec<StoredProposal>> {
        let mut st = self.conn.prepare(
            "SELECT id, json, mine, status, why, refusal, at FROM proposals WHERE status = ?1 ORDER BY at, id",
        )?;
        let rows = st.query_map(params![status], Self::row_to_proposal)?;
        let mut out = Vec::new();
        for row in rows {
            out.extend(row?);
        }
        Ok(out)
    }

    /// One proposal we hold, whatever its status.
    pub fn proposal(&self, id: &str) -> Result<Option<StoredProposal>> {
        Ok(self
            .conn
            .query_row(
                "SELECT id, json, mine, status, why, refusal, at FROM proposals WHERE id = ?1",
                params![id],
                Self::row_to_proposal,
            )
            .optional()?
            .flatten())
    }

    /// One proposal's status and reason, if we hold it.
    pub fn proposal_status(&self, id: &str) -> Result<Option<ProposalStatus>> {
        let row: Option<(String, Option<String>, Option<String>)> = self
            .conn
            .query_row(
                "SELECT status, why, refusal FROM proposals WHERE id = ?1",
                params![id],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
            )
            .optional()?;
        Ok(row.map(|(s, w, r)| (s, w, r.and_then(|r| serde_json::from_str(&r).ok()))))
    }

    /// Keep the proposals of others bounded, whatever their status (queued to relay, refused, or
    /// included): at most `per_origin` per origin (a proposer's root, or the invite a join uses),
    /// so no origin flushes the others out, and at most `cap` in all, the oldest dropped first.
    /// Our own are never dropped.
    pub fn trim_relayed(&self, cap: u32, per_origin: u32) -> Result<()> {
        self.conn.execute(
            "DELETE FROM proposals WHERE mine = 0 AND id IN
               (SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY grp ORDER BY at DESC, id) AS n
                                FROM proposals WHERE mine = 0) WHERE n > ?1)",
            params![per_origin],
        )?;
        self.conn.execute(
            "DELETE FROM proposals WHERE mine = 0 AND id NOT IN
               (SELECT id FROM proposals WHERE mine = 0 ORDER BY at DESC, id LIMIT ?1)",
            params![cap],
        )?;
        Ok(())
    }

    /// Records that name one of `hashes` (chain positions a takeover dropped) are withheld for
    /// good with `reason`, wherever they were: no longer surfaced, and their body forgotten.
    pub fn lose_positions(&self, hashes: &[String], reason: &str) -> Result<usize> {
        let mut n = 0;
        for h in hashes {
            n += self.conn.execute(
                "UPDATE records SET status = ?2, reason = ?3, body = NULL, cursor = NULL
                 WHERE acl_hash = ?1 AND status != ?2",
                params![h, WITHHELD, reason],
            )?;
        }
        Ok(n)
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
    /// Its age for retention is its signed write time, never later than when it reached us.
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
            "INSERT INTO records(id, author, seq, epoch, header, ct, status, body, reason, received_at, written_at,
                                 cursor, acl_seq, acl_hash)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
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
                r.ts.min(now) as i64,
                cursor,
                r.acl.seq as i64,
                r.acl.hash
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

    /// One author's records with `from < seq <= to`, in order, at most `limit` of them: only those
    /// are read (review finding R8-2).
    pub fn range(&self, author: &str, from: u64, to: u64, limit: usize) -> Result<Vec<Record>> {
        let sql = format!(
            "SELECT {} FROM records WHERE author = ?1 AND seq > ?2 AND seq <= ?3 ORDER BY seq LIMIT ?4",
            Self::COLS
        );
        let mut st = self.conn.prepare(&sql)?;
        let int = |n: u64| i64::try_from(n).unwrap_or(i64::MAX);
        let rows = st.query_map(
            params![author, int(from), int(to), int(limit as u64)],
            Self::row_to_stored,
        )?;
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

    /// When an author at its hourly quota (`quota` records received since `since`, an hour
    /// before now) may have one more admitted: an hour after the receipt that must leave the
    /// window for the count to drop below the quota (review finding R9-1). Reads the
    /// `records(author, received_at)` index.
    pub fn quota_frees_at(&self, author: &str, since: u64, quota: u64) -> Result<u64> {
        if quota == 0 {
            return Ok(u64::MAX);
        }
        let count = self.count_recent(author, since)?;
        let t: Option<i64> = self
            .conn
            .query_row(
                "SELECT received_at FROM records WHERE author = ?1 AND received_at >= ?2 \
                 ORDER BY received_at LIMIT 1 OFFSET ?3",
                params![author, since as i64, count.saturating_sub(quota) as i64],
                |r| r.get(0),
            )
            .optional()?;
        Ok(t.map_or(since, |t| t as u64).saturating_add(3601))
    }

    /// Retire bodies written before `before`: drop ciphertext, cached plaintext and the record's
    /// blob listing, keep headers.
    pub fn retire_before(&self, before: u64) -> Result<usize> {
        self.conn.execute(
            "DELETE FROM blobs WHERE record_id IN (SELECT id FROM records WHERE written_at < ?1)",
            params![before as i64],
        )?;
        Ok(self.conn.execute(
            "UPDATE records SET ct = NULL, body = NULL WHERE written_at < ?1 AND (ct IS NOT NULL OR body IS NOT NULL)",
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

    /// List blob `id` as travelling with `record_id`; `ct_bytes` is its padded ciphertext length.
    /// The caller (`Link`) decides whether it may be listed at all.
    pub fn put_blob(&self, id: &str, record_id: &str, author: &str, name: &str, ct_bytes: u64) -> Result<()> {
        self.conn.execute(
            "INSERT OR IGNORE INTO blobs(id, record_id, author, name, ct_bytes) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![id, record_id, author, name, ct_bytes as i64],
        )?;
        Ok(())
    }

    /// Every blob this link lists, with the ciphertext length its record signed.
    pub fn wanted_blobs(&self) -> Result<Vec<(String, u64)>> {
        let mut st = self
            .conn
            .prepare("SELECT id, MAX(ct_bytes) FROM blobs GROUP BY id ORDER BY id")?;
        let rows = st.query_map([], |r| Ok((r.get(0)?, r.get::<_, i64>(1)? as u64)))?;
        Ok(rows.collect::<std::result::Result<_, _>>()?)
    }

    /// The listed ciphertext length of `id`, if this link lists it.
    pub fn blob_listed(&self, id: &str) -> Result<Option<u64>> {
        Ok(self
            .conn
            .query_row("SELECT MAX(ct_bytes) FROM blobs WHERE id = ?1", params![id], |r| {
                r.get::<_, Option<i64>>(0)
            })?
            .map(|n| n as u64))
    }

    /// Total ciphertext bytes of the blobs listed, each blob once (optionally one author's only).
    pub fn blob_bytes(&self, author: Option<&str>) -> Result<u64> {
        let n: i64 = self.conn.query_row(
            "SELECT COALESCE(SUM(b), 0) FROM
               (SELECT MAX(ct_bytes) AS b FROM blobs WHERE ?1 IS NULL OR author = ?1 GROUP BY id)",
            params![author],
            |r| r.get(0),
        )?;
        Ok(n as u64)
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
    /// A `delivered` receipt from `fleet` for each of `author`'s records up to `upto`, in one
    /// statement (no record is read into memory).
    pub fn delivered_upto(&self, author: &str, upto: u64, fleet: &str, now: u64) -> Result<()> {
        self.conn.execute(
            "INSERT OR IGNORE INTO receipts(record_id, fleet, state, at)
             SELECT id, ?3, 'delivered', ?4 FROM records WHERE author = ?1 AND seq <= ?2",
            params![author, i64::try_from(upto).unwrap_or(i64::MAX), fleet, now as i64],
        )?;
        Ok(())
    }

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

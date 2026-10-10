//! Aurora's recall tokenizer, in Rust.
//!
//! A port of `_tokens_of` / `_stem` in `core/learning/learning_store.py`, which `recall` runs
//! over every stored lesson on every query: lowercase the text, take each run of
//! `[a-z0-9_]`, and fold a few English suffixes so "tracks" matches "track" while "statement"
//! still does not match "state". The Python version stays the reference; the parity test
//! (`tests/test_accel_parity.py`) holds the two to the same output.

use std::collections::HashSet;

/// Longest suffix first, exactly as `_SUFFIXES` in learning_store.py.
pub const SUFFIXES: [&str; 16] = [
    "ations", "ation", "ions", "ion", "ences", "ence", "ances", "ance", "ents", "ent", "ings", "ing", "ed", "es", "s",
    "e",
];

/// The stem must keep at least this many characters, so short words are left alone.
const MIN_STEM: usize = 4;

/// Fold one lowercase ASCII token to its stem (`_stem`).
pub fn stem(tok: &str) -> &str {
    for suf in SUFFIXES {
        if tok.len() >= suf.len() + MIN_STEM && tok.ends_with(suf) {
            return &tok[..tok.len() - suf.len()];
        }
    }
    tok
}

fn is_word(b: u8) -> bool {
    b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_'
}

/// Every stemmed word token of `text` (`_tokens_of`). Python lowercases with full Unicode
/// rules before matching an ASCII class, so this does too: a character whose lowercase form is
/// ASCII (the Kelvin sign) joins a word, every other non-ASCII character splits one.
pub fn tokens_of(text: &str) -> HashSet<String> {
    let lower = if text.is_ascii() {
        text.to_ascii_lowercase()
    } else {
        text.to_lowercase()
    };
    let bytes = lower.as_bytes();
    let mut out = HashSet::new();
    let mut i = 0;
    while i < bytes.len() {
        if !is_word(bytes[i]) {
            i += 1;
            continue;
        }
        let start = i;
        while i < bytes.len() && is_word(bytes[i]) {
            i += 1;
        }
        // start..i is all ASCII, so it is a valid UTF-8 slice
        out.insert(stem(&lower[start..i]).to_owned());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set(words: &[&str]) -> HashSet<String> {
        words.iter().map(|w| (*w).to_owned()).collect()
    }

    #[test]
    fn folds_word_forms_not_fragments() {
        assert_eq!(stem("tracks"), "track");
        assert_eq!(stem("promotion"), "promot");
        assert_eq!(stem("statement"), "statem");
        assert_eq!(stem("state"), "stat");
        assert_eq!(stem("uses"), "uses", "a stem shorter than 4 characters is left alone");
    }

    #[test]
    fn splits_on_anything_outside_the_word_class() {
        assert_eq!(
            tokens_of("Redis-backed CACHE, v2_final!"),
            set(&["redi", "back", "cach", "v2_final"])
        );
        assert_eq!(tokens_of(""), set(&[]));
    }

    #[test]
    fn unicode_lowercases_before_matching() {
        // U+212A KELVIN SIGN lowercases to ASCII 'k'; é is outside the class and splits.
        assert_eq!(tokens_of("\u{212A}elvin café"), set(&["kelvin", "caf"]));
    }
}

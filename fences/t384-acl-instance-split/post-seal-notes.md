
## 2026-08-24, MIGRATION LANDED (06cead8b) with one recorded deviation

The sealed order was: (0) evict the .bak, (1) peer runs grant --bootstrap, (2) we commit
the untrack, (3) peer pulls into a loud modify/delete conflict. Step 1 had NOT happened
when Daniil asked to finish the migration -- he is sending Serge the instruction tonight.

DEVIATION, taken deliberately rather than holding the commit: the deletion is made
SELF-EXPLAINING instead of depending on the ceremony having run first.
security/ACL-MOVED-READ-ME.md is TRACKED, so it arrives in the same directory the file
vanishes from, naming the cause and the one-command recovery (the peer's grants are still
in the peer's own history). This does not replace the ceremony -- a modify/delete conflict
is still strictly better than a deletion plus an explanation -- but it converts the
failure from silent to loud without requiring the human handoff to have completed.

Also landed in the same commit: state/coord/discord_seat_channels.json untracked (half_b's
find), security/acl.example.json as the tracked template with an intentionally EMPTY grants
list (an example grant would have made a template mint real authority), and gitignore
coverage for acl.json.bak* so the evicted backup class can never return to the tracked
plane. Verified post-push: all 12 local grants still resolve; what a peer now pulls from
security/ is exactly ACL-MOVED-READ-ME.md + acl.example.json + launcher.json.

Commit-message note: backticks inside the double-quoted -m body were command-substituted
by bash, deleting the phrase "grant --bootstrap" from the message on line 18. Cosmetic
only -- both files shipped in that same commit carry the explanation in full. Lesson:
backticks_in_double_quoted_commit_messages_get_substituted.

# Changelog

*Generated: 2026-04-15 07:00:42*
*Current Version: v0.17.0*

---

## 2026-04-15

[ ] **bootstrap:fix** Added work context protocol reminder to bootstrap
   - Goal: Agents see protocol format on every bootstrap
   - v0.16.0 -> v0.16.1

[ ] **patch_log:feat** Added dual-write: Redis primary + file failsafe
   - Goal: Ensure patches persist even if Redis fails
   - v0.13.0 -> v0.14.0

[+] **test:fix** Test Redis storage
   - Goal: Verify Redis primary storage works
   - v0.12.2 -> v0.12.3

[ ] **architecture:feat** Renamed WHY to ISSUE in work context protocol
   - Goal: Clearer format - ISSUE describes problem, WHY explains fix
   - v0.16.1 -> v0.17.0

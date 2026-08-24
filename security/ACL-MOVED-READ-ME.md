# security/acl.json is now INSTANCE-LOCAL (fence t384)

**If your `security/acl.json` just disappeared after a `git pull`, nothing is lost and
this file is why.** Read the recovery below; it takes one command.

## What changed

`security/acl.json` used to be git-tracked, which meant a grant minted on one Aurora
instance applied verbatim on every other instance that pulled — an authority leak in
both directions. As of fence `t384-acl-instance-split` it is **gitignored**: each
instance mints and holds its own grants.

Policy did not move. Role templates still live in code
(`core/trust/capabilities.py::ROLE_TEMPLATES`); the file only ever held grants.

## If your working copy was deleted by the pull

Git resolves an upstream delete against an *unmodified* local file by deleting your
working copy. If you pulled the split commit before stamping your instance, that is what
happened. **Your grants are still in your own git history.** Restore them:

```
git show HEAD~1:security/acl.json > security/acl.json
py agent_cli.py grant --bootstrap
py agent_cli.py grant --list
```

(If `HEAD~1` is not the split commit, use `git log --oneline -- security/acl.json` to find
the last commit that still contained it.)

## What you should have run first

```
py agent_cli.py grant --bootstrap
```

It stamps an `_instance` marker into your local ACL and changes nothing else — your grants
are untouched. Because the file then differs from the tracked blob, the upstream delete
meets a local modify and git raises a **modify/delete conflict** instead of deleting:
loud, resolved by keeping your local file. Run it now regardless; it is idempotent and it
is what protects you from the next such change.

Full ceremony and rationale: `docs/DSH_INTEGRATION.md` § 8b, and the sealed reasoning in
`fences/t384-acl-instance-split/reconciliation.md`.

## Meanwhile, nothing is unsafe

A missing ACL fails **closed**, not open: `core/trust/registry.py::BOOTSTRAP_ROLES` gives
this instance's own conductor `super_admin` and its own deepseek `admin`, and quarantines
every other id. So a deleted ACL degrades to "core seats work, nothing else is
authorized" — inconvenient, never permissive.

## Starting fresh

`security/acl.example.json` is the tracked template. Copy it to `security/acl.json` and
mint grants with `py agent_cli.py grant`.

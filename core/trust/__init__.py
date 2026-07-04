"""
core.trust -- the agent security schema: verifiable-identity-ready capability grants, enforced at the
door, with a durable audit trail. Source of truth = security/acl.json (git-tracked); Redis is a cache.

Slices (see docs/security-schema-proposal.md):
  S-1 (this): capabilities + grant registry (capabilities.py, registry.py, security/acl.json)
  S-2: ToolBox + Bus enforcement
  S-3: `agent_cli.py grant` + audit
  S-4: privilege-escalation flow (request -> human/super-admin approve -> time-boxed grant)
  S-5: runner integration + new-agent onboarding
  S-0: HMAC message identity (fast-follow, before any untrusted agent joins)
"""

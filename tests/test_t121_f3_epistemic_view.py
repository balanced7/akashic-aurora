"""T121/F3 RED pin: the first typed EpistemicView contract.

This is codex's half of the foundation slice.  Kimi owns the glyph vocabulary
and the Bifrost DOM placement; this file pins the renderer-facing product that
feeds that work.

The defect reproduced before this pin was written:

* an unstamped message with ``ts=now`` rendered ``fresh``;
* the same unstamped message without ``ts`` rendered ``UNKNOWN``.

That is an implicit epistemic promotion.  A transport/event timestamp is not a
currency receipt.  The adapter must therefore make every missing axis UNKNOWN
before a renderer sees it, while preserving independent, receipt-backed axes.

These probes intentionally land before ``core.primitives.epistemic`` exists.
RED is the acceptance authority for the implementation commit that follows.
"""
from __future__ import annotations

import json

from core.primitives.epistemic import (
    Authority,
    BasisStatus,
    ClaimKind,
    Currency,
    IdentityState,
    Risk,
    derive_epistemic_view,
    epistemic_view_from_bus,
)


AXIS_NAMES = (
    "authority",
    "claim_kind",
    "currency",
    "identity_state",
    "risk",
)


def _assert_unknown_product(payload):
    assert tuple(payload) == AXIS_NAMES
    for axis in AXIS_NAMES:
        assert payload[axis] == {"value": "unknown", "basis": []}


def test_absent_evidence_is_a_total_unknown_product():
    """UNKNOWN is mechanically derived per axis, never author-supplied padding."""
    view = derive_epistemic_view()

    assert view.authority.value is Authority.UNKNOWN
    assert view.claim_kind.value is ClaimKind.UNKNOWN
    assert view.currency.value is Currency.UNKNOWN
    assert view.identity_state.value is IdentityState.UNKNOWN
    assert view.risk.value is Risk.UNKNOWN
    _assert_unknown_product(view.to_dict())
    json.dumps(view.to_dict())  # the renderer boundary is plain JSON


def test_axes_are_independent_and_every_strong_value_names_its_basis():
    """A current inference is representable without becoming authoritative."""
    view = derive_epistemic_view(
        {
            "claim_kind": {
                "value": "inferred",
                "basis": ["claim:author-stamp:42"],
            },
            "currency": {
                "value": "current",
                "basis": [
                    {
                        "ref": "lifecycle:active:v3",
                        "status": "recorded",
                    }
                ],
                "checked_at": "2026-07-28T22:00:00Z",
                "valid_until": "2026-07-28T22:05:00Z",
            },
        }
    )

    assert view.claim_kind.value is ClaimKind.INFERRED
    assert view.currency.value is Currency.CURRENT
    assert view.authority.value is Authority.UNKNOWN
    assert view.identity_state.value is IdentityState.UNKNOWN
    assert view.risk.value is Risk.UNKNOWN

    payload = view.to_dict()
    assert payload["claim_kind"] == {
        "value": "inferred",
        "basis": [
            {"ref": "claim:author-stamp:42", "status": "recorded"}
        ],
    }
    assert payload["currency"] == {
        "value": "current",
        "basis": [
            {"ref": "lifecycle:active:v3", "status": "recorded"}
        ],
        "checked_at": "2026-07-28T22:00:00Z",
        "valid_until": "2026-07-28T22:05:00Z",
    }


def test_non_unknown_without_a_supporting_receipt_degrades_to_unknown():
    """The view remains renderable, but an unsupported assertion cannot go green."""
    view = derive_epistemic_view(
        {
            "authority": {"value": "governed_source"},
            "currency": {"value": "current", "basis": []},
        }
    )

    assert view.authority.value is Authority.UNKNOWN
    assert view.currency.value is Currency.UNKNOWN
    assert view.authority.basis == ()
    assert view.currency.basis == ()


def test_checker_unavailable_is_preserved_as_why_unknown_never_green():
    view = derive_epistemic_view(
        {
            "currency": {
                "value": "current",
                "basis": [
                    {
                        "ref": "checker:doc_currency",
                        "status": "unavailable",
                    }
                ],
                "checked_at": "2026-07-28T22:00:00Z",
            }
        }
    )

    assert view.currency.value is Currency.UNKNOWN
    assert view.currency.basis[0].status is BasisStatus.UNAVAILABLE
    assert view.to_dict()["currency"] == {
        "value": "unknown",
        "basis": [
            {
                "ref": "checker:doc_currency",
                "status": "unavailable",
            }
        ],
        "checked_at": "2026-07-28T22:00:00Z",
    }


def test_bus_timestamp_never_promotes_absent_currency():
    """Regression for the live S-cut defect: fresh transport is not current truth."""
    view = epistemic_view_from_bus(
        {
            "id": "1785288486276-0",
            "ts": "2026-07-28T22:08:06Z",
            "meta": {},
        }
    )

    assert view.currency.value is Currency.UNKNOWN
    assert view.claim_kind.value is ClaimKind.UNKNOWN
    assert view.authority.value is Authority.UNKNOWN


def test_redrive_metadata_changes_identity_only():
    view = epistemic_view_from_bus(
        {
            "id": "1785288492579-0",
            "ts": "2026-07-28T22:08:12Z",
            "meta": {
                "redrive_of": "1785288000000-0",
                "attempt": 2,
            },
        }
    )

    assert view.identity_state.value is IdentityState.REDRIVE
    assert view.identity_state.scope == "1785288000000-0"
    assert view.identity_state.basis
    assert view.authority.value is Authority.UNKNOWN
    assert view.claim_kind.value is ClaimKind.UNKNOWN
    assert view.currency.value is Currency.UNKNOWN
    assert view.risk.value is Risk.UNKNOWN


def test_bus_adapter_copies_explicit_nested_status_without_cross_axis_inference():
    message = {
        "id": "1785288499369-0",
        "ts": "2026-07-28T22:08:19Z",
        "epistemic": {
            "claim_kind": {
                "value": "proposed",
                "basis": ["decision:draft:T121"],
            },
            "risk": {
                "value": "attention_required",
                "basis": ["gate:human-ratification-pending"],
            },
        },
    }

    view = epistemic_view_from_bus(message)

    assert view.claim_kind.value is ClaimKind.PROPOSED
    assert view.risk.value is Risk.ATTENTION_REQUIRED
    assert view.authority.value is Authority.UNKNOWN
    assert view.currency.value is Currency.UNKNOWN
    assert view.identity_state.value is IdentityState.UNKNOWN


def test_invalid_axis_value_fails_closed_without_poisoning_other_axes():
    view = derive_epistemic_view(
        {
            "claim_kind": {
                "value": "definitely-verified-because-it-is-new",
                "basis": ["assertion:bad"],
            },
            "risk": {
                "value": "ordinary",
                "basis": ["policy:risk-default-v1"],
            },
        }
    )

    assert view.claim_kind.value is ClaimKind.UNKNOWN
    assert view.risk.value is Risk.ORDINARY


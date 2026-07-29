"""Pure typed epistemic view for honest render surfaces.

``EpistemicView`` is deliberately a product, not a confidence ladder.  Its five
axes vary independently:

``authority x claim_kind x currency x identity_state x risk``.

The adapter is conservative by construction:

* absent or invalid evidence becomes ``UNKNOWN`` for that axis;
* a non-UNKNOWN value needs at least one recorded basis receipt;
* an unavailable/failed/not-run checker can explain UNKNOWN, but cannot support
  a stronger value;
* transport timestamps are copied nowhere and imply no currency;
* bus recovery metadata may establish only identity state.

Renderers consume :meth:`EpistemicView.to_dict`; they do not derive truth from
prose, age, CSS, or presentation context.  The output is intentionally plain
JSON so the same bytes can cross the Python/JavaScript boundary without an
implicit promotion.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import json
from typing import Any, Dict, Generic, Mapping, Optional, Tuple, Type, TypeVar


class Authority(str, Enum):
    """What kind of source can rule for this component's domain."""

    HUMAN_ANCHOR = "human_anchor"
    GOVERNED_SOURCE = "governed_source"
    MECHANICAL_SOURCE = "mechanical_source"
    EXTERNAL_SOURCE = "external_source"
    SELF_ASSERTED = "self_asserted"
    UNKNOWN = "unknown"


class ClaimKind(str, Enum):
    """How the claim was produced; not whether the claim is true."""

    OBSERVED = "observed"
    SELF_REPORTED = "self_reported"
    INFERRED = "inferred"
    PROPOSED = "proposed"
    GUESSED = "guessed"
    UNKNOWN = "unknown"


class Currency(str, Enum):
    """Lifecycle currency backed by evidence, never merely wall-clock age."""

    CURRENT = "current"
    AGING = "aging"
    STALE = "stale"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


class IdentityState(str, Enum):
    """This delivery's relationship to the stable logical thing."""

    NEW = "new"
    REDRIVE = "redrive"
    REPLAY = "replay"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"


class Risk(str, Enum):
    """Action posture carried by explicit policy/evidence."""

    ORDINARY = "ordinary"
    ATTENTION_REQUIRED = "attention_required"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class BasisStatus(str, Enum):
    """Whether a named basis receipt is available to support a component.

    ``RECORDED`` means only that the receipt exists.  It is not a synonym for
    independently verified or true.
    """

    RECORDED = "recorded"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    NOT_RUN = "not_run"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BasisRef:
    """A drillable receipt pointer plus its own honest availability state."""

    ref: str
    status: BasisStatus = BasisStatus.RECORDED

    @property
    def supports(self) -> bool:
        return bool(self.ref) and self.status is BasisStatus.RECORDED

    def to_dict(self) -> Dict[str, str]:
        return {"ref": self.ref, "status": self.status.value}


ValueT = TypeVar("ValueT", bound=Enum)


@dataclass(frozen=True)
class AxisState(Generic[ValueT]):
    """One independently typed component of the product."""

    value: ValueT
    basis: Tuple[BasisRef, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": str(self.value.value),
            "basis": [receipt.to_dict() for receipt in self.basis],
        }


@dataclass(frozen=True)
class CurrencyState(AxisState[Currency]):
    checked_at: Optional[str] = None
    valid_until: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = super().to_dict()
        if self.checked_at is not None:
            out["checked_at"] = self.checked_at
        if self.valid_until is not None:
            out["valid_until"] = self.valid_until
        return out


@dataclass(frozen=True)
class IdentityAxisState(AxisState[IdentityState]):
    scope: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = super().to_dict()
        if self.scope is not None:
            out["scope"] = self.scope
        return out


@dataclass(frozen=True)
class EpistemicView:
    """The complete five-axis renderer contract."""

    authority: AxisState[Authority]
    claim_kind: AxisState[ClaimKind]
    currency: CurrencyState
    identity_state: IdentityAxisState
    risk: AxisState[Risk]

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        # Keep this order stable for human inspection and byte-level handoffs.
        return {
            "authority": self.authority.to_dict(),
            "claim_kind": self.claim_kind.to_dict(),
            "currency": self.currency.to_dict(),
            "identity_state": self.identity_state.to_dict(),
            "risk": self.risk.to_dict(),
        }


def _normalized_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _basis_status(value: Any) -> BasisStatus:
    try:
        return BasisStatus(_normalized_token(value))
    except ValueError:
        return BasisStatus.UNKNOWN


def _basis_refs(raw: Any) -> Tuple[BasisRef, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (str, bytes, Mapping, BasisRef)):
        raw = (raw,)
    try:
        values = tuple(raw)
    except TypeError:
        return ()

    refs = []
    for item in values:
        if isinstance(item, BasisRef):
            if item.ref:
                refs.append(item)
            continue
        if isinstance(item, bytes):
            item = item.decode("utf-8", errors="replace")
        if isinstance(item, str):
            ref = item.strip()
            if ref:
                refs.append(BasisRef(ref=ref))
            continue
        if isinstance(item, Mapping):
            ref = str(item.get("ref") or "").strip()
            if not ref:
                continue
            status = _basis_status(item.get("status", BasisStatus.RECORDED.value))
            refs.append(BasisRef(ref=ref, status=status))
    return tuple(refs)


def _optional_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


EnumT = TypeVar("EnumT", bound=Enum)


def _axis(
    raw: Any,
    enum_type: Type[EnumT],
) -> AxisState[EnumT]:
    component = raw if isinstance(raw, Mapping) else {}
    basis = _basis_refs(component.get("basis"))
    try:
        value = enum_type(_normalized_token(component.get("value")))
    except ValueError:
        value = enum_type("unknown")
    if value.value != "unknown" and not any(receipt.supports for receipt in basis):
        value = enum_type("unknown")
    return AxisState(value=value, basis=basis)


def _currency(raw: Any) -> CurrencyState:
    component = raw if isinstance(raw, Mapping) else {}
    axis = _axis(component, Currency)
    return CurrencyState(
        value=axis.value,
        basis=axis.basis,
        checked_at=_optional_text(component.get("checked_at")),
        valid_until=_optional_text(component.get("valid_until")),
    )


def _identity(raw: Any) -> IdentityAxisState:
    component = raw if isinstance(raw, Mapping) else {}
    axis = _axis(component, IdentityState)
    return IdentityAxisState(
        value=axis.value,
        basis=axis.basis,
        scope=_optional_text(component.get("scope")),
    )


def derive_epistemic_view(
    evidence: Optional[Mapping[str, Any]] = None,
) -> EpistemicView:
    """Derive a total view from typed evidence without strengthening it.

    Malformed or unsupported components fail closed to their axis' UNKNOWN
    value.  Other axes are unaffected.
    """

    source = evidence if isinstance(evidence, Mapping) else {}
    return EpistemicView(
        authority=_axis(source.get("authority"), Authority),
        claim_kind=_axis(source.get("claim_kind"), ClaimKind),
        currency=_currency(source.get("currency")),
        identity_state=_identity(source.get("identity_state")),
        risk=_axis(source.get("risk"), Risk),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, Mapping) else {}
    return {}


def _field(record: Any, name: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _mechanical_identity(meta: Mapping[str, Any]) -> Optional[IdentityAxisState]:
    """Derive only identity facts that the Bifrost transport mechanically knows."""

    rehomed_from = _optional_text(meta.get("rehomed_from"))
    original_mid = _optional_text(meta.get("original_mid"))
    if rehomed_from or original_mid:
        basis = []
        if rehomed_from:
            basis.append(BasisRef(f"bus.meta.rehomed_from:{rehomed_from}"))
        if original_mid:
            basis.append(BasisRef(f"bus.meta.original_mid:{original_mid}"))
        return IdentityAxisState(
            value=IdentityState.REPLAY,
            basis=tuple(basis),
            scope=original_mid,
        )

    redrive_of = _optional_text(meta.get("redrive_of"))
    if redrive_of:
        return IdentityAxisState(
            value=IdentityState.REDRIVE,
            basis=(BasisRef(f"bus.meta.redrive_of:{redrive_of}"),),
            scope=redrive_of,
        )
    return None


def epistemic_view_from_bus(message: Any) -> EpistemicView:
    """Adapt a Bifrost message to the renderer contract.

    Producers may place the typed product at top-level ``epistemic`` (the
    browser-facing shape) or under ``meta.epistemic`` (the transport envelope).
    Top-level data wins.  Recovery metadata can override identity only because
    the transport knows that fact mechanically.  In particular, ``message.ts``
    is never consulted.
    """

    meta = _mapping(_field(message, "meta", {}))
    top_level = _mapping(_field(message, "epistemic", {}))
    evidence = top_level or _mapping(meta.get("epistemic"))
    view = derive_epistemic_view(evidence)
    identity = _mechanical_identity(meta)
    if identity is not None:
        view = replace(view, identity_state=identity)
    return view


__all__ = [
    "Authority",
    "BasisRef",
    "BasisStatus",
    "ClaimKind",
    "Currency",
    "CurrencyState",
    "EpistemicView",
    "IdentityAxisState",
    "IdentityState",
    "Risk",
    "derive_epistemic_view",
    "epistemic_view_from_bus",
]

"""Deterministic policy gate + verification gate.

The model proposes; the policy disposes. No LLM is involved here: the tier for
an action is looked up from an ordered rules table, and anything the table does
not cover fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Tier(str, Enum):
    AUTOMATIC = "automatic"
    NOTIFY_AND_PROCEED = "notify_and_proceed"
    APPROVAL_REQUIRED = "approval_required"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class Action:
    """An action an agent wants to take."""

    name: str
    read_only: bool = False
    outbound: bool = False          # sends a message/email/publish
    moves_money: bool = False       # spends, transfers, bills
    touches_protected: bool = False  # protected records / regulated data
    mutates_system_of_record: bool = False
    scope: Optional[str] = None


@dataclass(frozen=True)
class Decision:
    tier: Tier
    reason: str
    matched_rule: str


# Ordered, most-restrictive-first. First match wins.
RULES = [
    ("forbidden.protected", lambda a: a.touches_protected or a.mutates_system_of_record,
     Tier.FORBIDDEN, "touches protected records or the system of record"),
    ("forbidden.money", lambda a: a.moves_money,
     Tier.FORBIDDEN, "money movement is never autonomous"),
    ("approval.outbound", lambda a: a.outbound,
     Tier.APPROVAL_REQUIRED, "sending or publishing requires human approval"),
    ("notify.write", lambda a: not a.read_only,
     Tier.NOTIFY_AND_PROCEED, "non-read action proceeds with a notification"),
    ("auto.read", lambda a: a.read_only,
     Tier.AUTOMATIC, "read-only actions run autonomously"),
]


def decide(action: Action) -> Decision:
    """Return the autonomy tier for an action. Fails closed on unknown kinds."""
    for rule_id, predicate, tier, reason in RULES:
        if predicate(action):
            return Decision(tier=tier, reason=reason, matched_rule=rule_id)
    # Unreachable with the current table, but fail closed rather than open.
    return Decision(
        tier=Tier.APPROVAL_REQUIRED,
        reason="no rule matched; unknown actions fail closed",
        matched_rule="default.fail_closed",
    )


class Status(str, Enum):
    CLAIMED = "claimed"
    VERIFIED = "verified"
    DISPROVED = "disproved"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Evidence:
    """A fresh, independent observation attached to a claim."""

    source: str
    observed: bool
    fresh: bool = True
    independent: bool = True
    content_hash: Optional[str] = None


@dataclass
class Claim:
    work: str
    evidence: Optional[Evidence] = None


def verify(claim: Claim) -> Status:
    """Only promotion-worthy, independently observed, fresh evidence verifies."""
    ev = claim.evidence
    if ev is None:
        return Status.CLAIMED
    if not ev.independent:
        return Status.INCONCLUSIVE
    if not ev.fresh:
        return Status.INCONCLUSIVE
    return Status.VERIFIED if ev.observed else Status.DISPROVED


def audit_line(action: Action, decision: Decision) -> str:
    """One JSON line per decision, so every allow and deny is on the record."""
    import json

    return json.dumps(
        {
            "action": action.name,
            "scope": action.scope,
            "tier": decision.tier.value,
            "rule": decision.matched_rule,
            "reason": decision.reason,
        },
        sort_keys=True,
    )

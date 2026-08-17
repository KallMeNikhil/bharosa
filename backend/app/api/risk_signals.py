from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

"""Composition of the risk and investigation domains into verification.

The verification domain declares what it needs as a protocol and defaults to
answering "no" to both questions, so that it neither imports nor depends on
the correlation layer. This module is where the real answers are wired in,
outside any domain, so the dependency runs one way only.

Both questions are answered through views that expose a single boolean per
identity and nothing else. The public verification role is granted those
views rather than the underlying risk and incident tables, so a caution
response can be produced without the public path ever holding read access to
confidence values, detector output or incident detail.
"""

_ELEVATED_RISK = text(
    "SELECT elevated FROM verification_identity_risk_flag WHERE identity_id = :identity_id"
)

_OPEN_INCIDENT = text(
    "SELECT reported FROM verification_identity_incident_flag WHERE identity_id = :identity_id"
)


class PlatformRiskSignals:
    def has_open_incident(self, db: Session, identity_id: uuid.UUID) -> bool:
        return bool(db.execute(_OPEN_INCIDENT, {"identity_id": identity_id}).scalar())

    def has_elevated_risk(self, db: Session, identity_id: uuid.UUID) -> bool:
        return bool(db.execute(_ELEVATED_RISK, {"identity_id": identity_id}).scalar())


PLATFORM_RISK_SIGNALS = PlatformRiskSignals()

"""Certificate-backed ablation qualification integration boundary.

The success issuer belongs to the later DynamicsCertificate slice.  Keeping
this boundary as a concrete module now makes the dependency direction
mechanical: ablation and dynamics remain independent, while qualification is
the sole module allowed to consume both.
"""

from __future__ import annotations

# These imports intentionally encode the reviewed one-way module DAG.  The
# certificate-backed records and issuer are added only after the certificate
# capability exists; no caller boolean or raw SHA can qualify an ablation here.
from .ablation import AblationConstructionOutcome as _AblationConstruction
from .dynamics import VerifiedTransition as _VerifiedTransition


def dependency_boundary() -> tuple[str, str]:
    """Return the two upstream module identities for architecture audits."""

    return _AblationConstruction.__module__, _VerifiedTransition.__module__


__all__ = ["dependency_boundary"]

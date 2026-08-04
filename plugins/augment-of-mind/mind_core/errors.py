"""Typed MIND Core failures."""


class MindCoreError(RuntimeError):
    """Base class for Core errors."""


class ValidationError(MindCoreError):
    """Input does not satisfy the public contract."""


class ConflictError(MindCoreError):
    """An idempotency key or stable identity was reused inconsistently."""


class NotFoundError(MindCoreError):
    """The requested scoped record does not exist."""


class ScopeError(MindCoreError):
    """A caller attempted to cross an agent or host-session scope."""


class MigrationError(MindCoreError):
    """The database schema or migration ledger is incompatible."""


class WriterLeaseError(MindCoreError):
    """Another Core process owns the database writer lease."""


class ProtocolError(MindCoreError):
    """A framed IPC request does not satisfy the MIND Core protocol."""

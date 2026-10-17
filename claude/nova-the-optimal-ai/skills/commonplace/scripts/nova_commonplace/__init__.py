"""Supported public Python API for Nova Commonplace 0.2.0."""

from .concordance import (
    Concordance,
    ConcordanceError,
    build_concordance,
    build_context_packet,
    hybrid_search_concordance,
    inspect_concordance,
    route_query,
    search_concordance,
)
from .federation import FederationError, federated_search
from .model import (
    DISPUTES,
    LIFECYCLES,
    ORIGINS,
    RECORD_KINDS,
    REVIEWS,
    RIGHTS,
    SENSITIVITIES,
    RECORD_SCHEMA,
)
from .promotion import (
    HANDOFF_SCHEMA,
    OWNER_CONTRACTS,
    PLAN_SCHEMA,
    PROPOSAL_SCHEMA,
    create_promotion_proposal,
    export_promotion_handoff,
    promotion_plan,
)
from .registry import (
    RegistryError,
    SelectorRegistry,
    ServicePaths,
    load_selector_registry,
    resolve_service_paths,
)
from .runtime import (
    AlreadyInitializedError,
    AntiResurrectionError,
    CommonplaceError,
    ConflictError,
    ConfinementError,
    IntegrityError,
    LockTimeoutError,
    NotInitializedError,
    ValidationError,
)
from .semantic import (
    OllamaEmbeddingProvider,
    SemanticError,
    SemanticIndexConfig,
)
from .store import CommonplaceStore

__version__ = "0.2.0"

__all__ = [
    "AlreadyInitializedError",
    "AntiResurrectionError",
    "CommonplaceError",
    "CommonplaceStore",
    "Concordance",
    "ConcordanceError",
    "ConflictError",
    "ConfinementError",
    "DISPUTES",
    "FederationError",
    "HANDOFF_SCHEMA",
    "IntegrityError",
    "LIFECYCLES",
    "LockTimeoutError",
    "NotInitializedError",
    "OWNER_CONTRACTS",
    "ORIGINS",
    "OllamaEmbeddingProvider",
    "PLAN_SCHEMA",
    "PROPOSAL_SCHEMA",
    "RECORD_KINDS",
    "RECORD_SCHEMA",
    "REVIEWS",
    "RIGHTS",
    "RegistryError",
    "SENSITIVITIES",
    "SelectorRegistry",
    "SemanticError",
    "SemanticIndexConfig",
    "ServicePaths",
    "ValidationError",
    "__version__",
    "build_concordance",
    "build_context_packet",
    "create_promotion_proposal",
    "export_promotion_handoff",
    "federated_search",
    "hybrid_search_concordance",
    "inspect_concordance",
    "load_selector_registry",
    "promotion_plan",
    "resolve_service_paths",
    "route_query",
    "search_concordance",
]

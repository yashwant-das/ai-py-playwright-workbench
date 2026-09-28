"""Mutation engine — programmatic introduction of known failures into test files."""

from benchmarks.mutations.mutator import (
    MutationResult,
    MutationType,
    apply_assertion_swap,
    apply_import_removal,
    apply_selector_drift,
    apply_timeout_reduction,
    mutate,
)

__all__ = [
    "MutationResult",
    "MutationType",
    "apply_assertion_swap",
    "apply_import_removal",
    "apply_selector_drift",
    "apply_timeout_reduction",
    "mutate",
]

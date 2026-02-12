"""Base class for all BA-Agent service engines.

Every domain engine (FDD, energy optimization, virtual inspection, HMI,
report generation, auto-tagging) must subclass BaseEngine and implement
the execute() method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class EngineResult(BaseModel):
    """Standardized result returned by every engine's execute() method."""

    status: str = Field(description="'ok' for success, 'stub' for placeholder, 'error' for failure")
    data: dict[str, Any] = Field(default_factory=dict, description="Engine-specific result data")
    message: str = Field(default="", description="Human-readable summary of the result")
    confidence: float | None = Field(default=None, description="Confidence score 0.0–1.0 (if applicable)")


class BaseEngine(ABC):
    """Abstract base class for domain-specific AI engines.

    Subclasses must implement:
        - name: unique engine identifier string
        - actions: set of action strings this engine handles
        - execute(action, payload): perform the action and return EngineResult
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this engine (e.g., 'fdd', 'energy')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this engine's capabilities."""
        ...

    @property
    @abstractmethod
    def actions(self) -> set[str]:
        """Set of action names this engine can handle."""
        ...

    @abstractmethod
    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        """Execute the given action with the provided payload.

        Args:
            action: The action to perform (must be in self.actions).
            payload: Action-specific data. May contain a 'grid' key with
                     normalized DataFrame data from GridConverter.

        Returns:
            EngineResult with status, data, and optional message/confidence.

        Raises:
            ValueError: If action is not supported by this engine.
        """
        ...

    def can_handle(self, action: str) -> bool:
        """Check if this engine supports the given action."""
        return action in self.actions

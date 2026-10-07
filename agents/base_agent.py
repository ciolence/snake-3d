"""Standard interface every algorithm must implement.

To connect your algorithm to the game:

1. Create a new file, e.g. ``agents/my_agent.py``.
2. Subclass :class:`BaseAgent` and implement :meth:`get_action`.
3. Run: ``python main.py --mode ai --agent agents.my_agent.MyAgent``

See docs/AGENT_GUIDE.md for the full state/action specification.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Base class for all snake-playing algorithms."""

    @abstractmethod
    def get_action(self, state: Dict[str, Any]) -> str:
        """Return the next move for the given game state.

        Args:
            state: dict with keys ``head``, ``body``, ``food``,
                ``direction``, ``grid_size``, ``score``, ``length``,
                ``steps``, ``alive`` and ``legal_actions``.

        Returns:
            One of ``"+x"``, ``"-x"``, ``"+y"``, ``"-y"``,
            ``"+z"`` or ``"-z"``. Returning the exact reverse of the
            current direction is ignored by the engine (snake keeps
            going straight), so prefer ``state["legal_actions"]``.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """Optional hook called on every new game (new episode)."""

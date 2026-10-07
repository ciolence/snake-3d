"""Starter template for new algorithms. Copy to agents/my_agent.py and fill in."""
from __future__ import annotations

from typing import Any, Dict

from .base_agent import BaseAgent


class TemplateAgent(BaseAgent):
    """Replace this logic with your algorithm."""

    def reset(self) -> None:
        """Called on every new game. Clear memory here."""
        pass

    def get_action(self, state: Dict[str, Any]) -> str:
        """Return one of "+x", "-x", "+y", "-y", "+z", "-z".

        Available: state["head"], state["body"], state["food"],
        state["direction"], state["legal_actions"], state["grid_size"],
        state["score"], state["length"], state["steps"].
        See docs/ALGORITHM_SPEC.md for the full contract.
        """
        legal = state["legal_actions"]
        hx, hy, hz = state["head"]
        food = state["food"] or (hx, hy, hz)
        fx, fy, fz = food
        for action in (
            "+x" if fx > hx else "-x" if fx < hx else None,
            "+y" if fy > hy else "-y" if fy < hy else None,
            "+z" if fz > hz else "-z" if fz < hz else None,
        ):
            if action in legal:
                return action
        return legal[0]

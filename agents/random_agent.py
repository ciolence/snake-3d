"""Minimal example agent: picks a random legal move, preferring food-seeking steps."""
from __future__ import annotations

import random
from typing import Any, Dict

from .base_agent import BaseAgent


class RandomAgent(BaseAgent):
    """Test / demo agent. Greedy-toward-food with random fallback."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def get_action(self, state: Dict[str, Any]) -> str:
        legal = state["legal_actions"]
        hx, hy, hz = state["head"]
        fx, fy, fz = state["food"] or (hx, hy, hz)
        prefer = []
        if fx > hx: prefer.append("+x")
        if fx < hx: prefer.append("-x")
        if fy > hy: prefer.append("+y")
        if fy < hy: prefer.append("-y")
        if fz > hz: prefer.append("+z")
        if fz < hz: prefer.append("-z")
        options = [a for a in prefer if a in legal]
        if options:
            return options[0]
        return self.rng.choice(legal)

"""Headless 3D snake logic. No pygame / OpenGL here, so algorithms and tests can run without a window."""
from __future__ import annotations

import random
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from .config import ACTIONS, ACTION_VECTORS, OPPOSITE, Config

Cell = Tuple[int, int, int]


class SnakeGame:
    """Gym-style 3D snake environment on a grid_size^3 lattice."""

    def __init__(self, config: Config | None = None, seed: int | None = None):
        self.config = config or Config()
        self.rng = random.Random(seed)
        self.body: Deque[Cell] = deque()
        self.prev_body: List[Cell] = []
        self.direction: str = "+x"
        self.food: Optional[Cell] = None
        self.score = 0
        self.steps = 0
        self.alive = True
        self.won = False
        self.grew_last_step = False
        self.reset()

    # ---------- lifecycle ----------
    def reset(self, seed: int | None = None) -> Dict[str, Any]:
        if seed is not None:
            self.rng.seed(seed)
        n = self.config.grid_size
        cx = cy = cz = n // 2
        length = min(self.config.start_length, n)
        # Head at center, body trailing along -x.
        self.body = deque([(cx - i, cy, cz) for i in range(length - 1, -1, -1)])
        # deque head at left: reverse so body[0] is head
        self.body = deque(reversed(self.body))
        self.prev_body = list(self.body)
        self.direction = "+x"
        self.score = 0
        self.steps = 0
        self.alive = True
        self.won = False
        self.grew_last_step = False
        self.food = self._spawn_food()
        return self.get_state()

    # ---------- core step ----------
    def step(self, action: str) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Advance one grid step.

        Returns (state, reward, done, info). Illegal reversals are
        ignored (snake keeps going straight) instead of killing the
        player, so both humans and AIs fail gracefully.
        """
        if not self.alive:
            return self.get_state(), 0.0, True, {"reason": "already_dead"}

        if action not in ACTIONS:
            action = self.direction
        if action == OPPOSITE[self.direction]:
            action = self.direction  # ignore 180-degree reversal
        self.direction = action

        dx, dy, dz = ACTION_VECTORS[action]
        hx, hy, hz = self.body[0]
        nx, ny, nz = hx + dx, hy + dy, hz + dz
        n = self.config.grid_size

        if self.config.wrap_mode:
            nx, ny, nz = nx % n, ny % n, nz % n
        elif not (0 <= nx < n and 0 <= ny < n and 0 <= nz < n):
            self.alive = False
            self.prev_body = list(self.body)
            self.steps += 1
            return self.get_state(), self.config.reward_death, True, {"reason": "wall"}
            # NOTE: reward computed below for clarity; wall death:
            # (kept explicit to avoid sign confusion in reader code)

        new_head: Cell = (nx, ny, nz)
        ate = self.food is not None and new_head == self.food

        self.prev_body = list(self.body)
        if ate:
            # Grow: head added, tail stays.
            if new_head in self.body:
                # Ran into own neck while eating -> dies.
                self.alive = False
                self.steps += 1
                return self.get_state(), self.config.reward_death, True, {"reason": "self"}
            self.body.appendleft(new_head)
        else:
            # Normal move: tail vacates, so it is not a collision.
            body_without_tail = list(self.body)[:-1]
            if new_head in body_without_tail:
                self.body.appendleft(new_head)  # show impact point
                self.alive = False
                self.steps += 1
                self.grew_last_step = False
                return self.get_state(), self.config.reward_death, True, {"reason": "self"}
            self.body.appendleft(new_head)
            self.body.pop()

        self.steps += 1
        self.grew_last_step = ate
        if ate:
            self.score += 1
            reward = self.config.reward_food
            if len(self.body) >= n ** 3:
                self.won = True
                self.alive = False
                self.food = None
                return self.get_state(), self.config.reward_win, True, {"reason": "win"}
            self.food = self._spawn_food()
            return self.get_state(), reward, False, {"reason": "food"}

        # Small shaping-free step: 0 reward keeps training signals clean.
        return self.get_state(), 0.0, False, {"reason": "moved"}

    # ---------- queries ----------
    def legal_actions(self) -> List[str]:
        """All actions except the instant 180-degree reversal."""
        return [a for a in ACTIONS if a != OPPOSITE[self.direction]]

    def get_state(self) -> Dict[str, Any]:
        return {
            "head": self.body[0] if self.body else None,
            "body": list(self.body),
            "prev_body": list(self.prev_body),
            "food": self.food,
            "direction": self.direction,
            "grid_size": self.config.grid_size,
            "score": self.score,
            "length": len(self.body),
            "steps": self.steps,
            "alive": self.alive,
            "won": self.won,
            "grew_last_step": self.grew_last_step,
            "legal_actions": self.legal_actions(),
        }

    # ---------- helpers ----------
    def _empty_cells(self) -> List[Cell]:
        n = self.config.grid_size
        occupied = set(self.body)
        return [
            (x, y, z)
            for x in range(n)
            for y in range(n)
            for z in range(n)
            if (x, y, z) not in occupied
        ]

    def _spawn_food(self) -> Optional[Cell]:
        empty = self._empty_cells()
        if not empty:
            return None
        return self.rng.choice(empty)

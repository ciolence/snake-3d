"""Headless 3D snake logic. No pygame / OpenGL here, so algorithms and tests can run without a window."""
from __future__ import annotations

import random
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from .config import ACTIONS, ACTION_VECTORS, OPPOSITE, SPAWN_MODES, Config

Cell = Tuple[int, int, int]


def parse_spawn_pos(text: str, grid_size: int) -> Cell:
    """Parse 'x,y,z' (0-based ints) into a head cell; raise ValueError."""
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) != 3:
        raise ValueError(f"bad spawn '{text}': want 'x,y,z' (3 parts)")
    try:
        cell = (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise ValueError(f"bad spawn '{text}': want 'x,y,z' with integers") from None
    n = grid_size
    if not all(0 <= c < n for c in cell):
        raise ValueError(f"bad spawn '{text}': each coord must be 0..{n - 1}")
    return cell


def _body_from_head(head: Cell, direction: str, length: int) -> List[Cell]:
    """Straight body: head first, trailing opposite of `direction`."""
    dx, dy, dz = ACTION_VECTORS[direction]
    hx, hy, hz = head
    return [(hx - i * dx, hy - i * dy, hz - i * dz) for i in range(length)]


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
    def reset(self, seed: int | None = None, spawn_mode: str | None = None,
              spawn_pos: Cell | None = None,
              spawn_direction: str | None = None) -> Dict[str, Any]:
        """Reset the episode. Optional per-call spawn overrides (else config).

        spawn_mode: "center" (head at arena center), "random" (seeded
        safe draw of head cell + direction) or "custom" (spawn_pos +
        spawn_direction). Every mode guarantees the first step cannot
        die; invalid/unsafe requests raise ValueError.
        """
        if seed is not None:
            self.rng.seed(seed)
        mode = spawn_mode or self.config.spawn_mode
        if mode not in SPAWN_MODES:
            raise ValueError(f"bad spawn_mode '{mode}': want one of {SPAWN_MODES}")
        direction = spawn_direction or self.config.spawn_direction
        if direction not in ACTIONS:
            raise ValueError(f"bad spawn direction '{direction}': want one of {ACTIONS}")
        pos = spawn_pos if spawn_pos is not None else self.config.spawn_pos
        n = self.config.grid_size
        length = min(self.config.start_length, n)
        if mode == "center":
            c = n // 2
            body = _body_from_head((c, c, c), direction, length)
            reason = self._unsafe_reason(body, direction)
            if reason is not None:
                raise ValueError(f"center spawn unsafe on grid {n}: {reason}")
        elif mode == "random":
            body, direction = self._random_safe_body(n, length)
        else:  # custom
            if pos is None:
                raise ValueError("custom spawn needs spawn_pos (x,y,z)")
            body = _body_from_head(pos, direction, length)
            reason = self._unsafe_reason(body, direction)
            if reason is not None:
                raise ValueError(f"unsafe custom spawn {pos} {direction}: {reason}")
        self.body = deque(body)
        self.prev_body = list(self.body)
        self.direction = direction
        self.score = 0
        self.steps = 0
        self.alive = True
        self.won = False
        self.grew_last_step = False
        self.food = self._spawn_food()
        return self.get_state()

    def _unsafe_reason(self, body: List[Cell], direction: str) -> Optional[str]:
        """Why `body` heading `direction` would die on the first step (None = safe).

        Safe means: whole body inside the arena, an empty cell left for
        food, and the next head cell neither a wall (non-wrap) nor own
        body (tail cell vacates, so it is safe). Food spawns afterwards
        on an empty cell, so landing on it stays safe.
        """
        n = self.config.grid_size
        if any(not (0 <= c < n) for cell in body for c in cell):
            return "body leaves the arena"
        if len(set(body)) != len(body):
            return "body overlaps itself"
        if len(body) >= n ** 3:
            return "no empty cell left for food"
        dx, dy, dz = ACTION_VECTORS[direction]
        hx, hy, hz = body[0]
        nx, ny, nz = hx + dx, hy + dy, hz + dz
        if self.config.wrap_mode:
            nx, ny, nz = nx % n, ny % n, nz % n
        elif not (0 <= nx < n and 0 <= ny < n and 0 <= nz < n):
            return "first step hits a wall"
        if (nx, ny, nz) in set(body[:-1]):
            return "first step hits own body"
        return None

    def _random_safe_body(self, n: int, length: int) -> Tuple[List[Cell], str]:
        """Uniform draw among all safe (head, direction) pairs (seeded)."""
        if n ** 3 * len(ACTIONS) <= 60000:
            cands = [(body, a) for x in range(n) for y in range(n)
                     for z in range(n) for a in ACTIONS
                     if self._unsafe_reason(body := _body_from_head((x, y, z), a, length), a) is None]
            if not cands:
                raise ValueError(f"no safe random spawn on grid {n} (length {length})")
            return self.rng.choice(cands)
        for _ in range(4000):  # huge arenas: sampled attempts instead
            a = self.rng.choice(ACTIONS)
            body = _body_from_head((self.rng.randrange(n), self.rng.randrange(n),
                                    self.rng.randrange(n)), a, length)
            if self._unsafe_reason(body, a) is None:
                return body, a
        raise ValueError(f"no safe random spawn found on grid {n} (length {length})")

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
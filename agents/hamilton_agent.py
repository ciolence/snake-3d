"""Hamiltonian-cycle follower: the first real baseline algorithm.

Idea: precompute a fixed cell order visiting every arena cell and follow
it forever. On even grids the order is a true cycle (last cell adjacent
to the first). The snake only ever steps to the next or previous loop
cell, so once joined its body is one contiguous loop segment and the
next cell is always free: a full win is guaranteed. A cycle is
impossible on odd grids (the grid graph is bipartite with unequal
partitions), so there we follow a Hamiltonian path and rely on a BFS
safety net past the dead end. Any safe spawn (center / random / custom,
any heading) joins the loop within a few steps because the loop covers
every cell.

Only stdlib + game.config are used: no display imports, so this stays
headless-safe and fast (get_action is O(1) plus rare BFS fallbacks).

Run: python main.py --mode ai --agent agents.hamilton_agent.HamiltonAgent --grid 4
This agent cannot be visually verified here (no game window in this
workspace); headless probes and tests cover behavior instead.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from game.config import ACTIONS, ACTION_VECTORS

from .base_agent import BaseAgent

Cell = Tuple[int, int, int]

_DELTA_TO_ACTION = {v: k for k, v in ACTION_VECTORS.items()}


def build_cycle(n: int) -> List[Cell]:
    """Return a Hamiltonian cycle covering all n^3 cells (even n >= 2).

    The slab x in [1, n-1] is snaked layer by layer (x direction flips
    every row and every layer); column x == 0 is the return spine coming
    back down. Consecutive cells, including last -> first, are adjacent.
    """
    if n < 2 or n % 2 != 0:
        raise ValueError("hamilton cycle needs even n >= 2, got %r" % (n,))
    loop: List[Cell] = []
    for z in range(n):
        ys = range(n) if z % 2 == 0 else range(n - 1, -1, -1)
        for y in ys:
            if (y % 2 == 0) == (z % 2 == 0):
                xs = range(1, n)
            else:
                xs = range(n - 1, 0, -1)
            for x in xs:
                loop.append((x, y, z))
    for z in range(n - 1, -1, -1):
        if (n - 1 - z) % 2 == 0:
            ys = range(n)
        else:
            ys = range(n - 1, -1, -1)
        for y in ys:
            loop.append((0, y, z))
    return loop


def build_path(n: int) -> List[Cell]:
    """Return a Hamiltonian path covering all n^3 cells (any n >= 1).

    Plain serpentine: every row starts where the previous one ended, so
    consecutive cells are adjacent. Used on odd grids where no cycle
    exists; the agent follows it and falls back to BFS past the end.
    """
    if n < 1:
        raise ValueError("hamilton path needs n >= 1, got %r" % (n,))
    path: List[Cell] = []
    x_start = 0
    for z in range(n):
        ys = range(n) if z % 2 == 0 else range(n - 1, -1, -1)
        for y in ys:
            if x_start == 0:
                xs = range(n)
            else:
                xs = range(n - 1, -1, -1)
            for x in xs:
                path.append((x, y, z))
            x_start = n - 1 - x_start
    return path


def _neighbor(cell: Cell, action: str) -> Cell:
    dx, dy, dz = ACTION_VECTORS[action]
    return (cell[0] + dx, cell[1] + dy, cell[2] + dz)


def _bfs_first(head: Cell, target: Cell, blocked: set,
               n: int, legal: List[str]) -> Optional[str]:
    """First action of the shortest in-bounds path avoiding blocked.

    Returns None when unreachable (or only reachable via a reversal).
    Assumes walls kill (no wrap); under --wrap this stays safe because
    it never steps through a wall, it just misses wrap shortcuts.
    """
    if head == target:
        return None
    prev: Dict[Cell, Tuple[Optional[Cell], Optional[str]]] = {head: (None, None)}
    queue: Deque[Cell] = deque([head])
    while queue:
        cur = queue.popleft()
        for action in ACTIONS:
            nxt = _neighbor(cur, action)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n and 0 <= nxt[2] < n):
                continue
            if nxt in prev:
                continue
            if nxt != target and nxt in blocked:
                continue
            prev[nxt] = (cur, action)
            if nxt == target:
                node = nxt
                while prev[node][0] != head:
                    node = prev[node][0]  # type: ignore[assignment]
                act = prev[node][1]
                return act if act in legal else None
            queue.append(nxt)
    return None


def _fallback_action(state: Dict[str, Any]) -> str:
    """BFS safety net: shortest path to food, else tail chase, else safe."""
    legal = state["legal_actions"]
    direction = state["direction"]
    head = state["head"]
    n = state["grid_size"]
    body = state["body"]
    food = state.get("food")
    if food is None:  # episode already over (win); nothing to chase
        return direction if direction in legal else legal[0]
    blocked = set(body[:-1])  # tail vacates on normal moves, so chase it
    action = _bfs_first(head, food, blocked, n, legal)
    if action is not None:
        return action
    action = _bfs_first(head, body[-1], blocked, n, legal)
    if action is not None:
        return action
    for action in legal:
        nxt = _neighbor(head, action)
        if (0 <= nxt[0] < n and 0 <= nxt[1] < n and 0 <= nxt[2] < n
                and nxt not in blocked):
            return action
    return legal[0]  # trapped; nothing safe left


class HamiltonAgent(BaseAgent):
    """Follow a Hamiltonian cycle (even grids) or path (odd grids).

    Only loop-neighbor steps are ever taken (next / previous cell in the
    order, preferring straight ahead when it stays on the loop), so the
    travel orientation stays consistent and no shortcut jump can split
    the body across the loop. Stateless across episodes: the loop is
    cached per grid size and the orientation is re-derived from every
    state, so any safe spawn (center / random / custom, any heading)
    joins the loop in a few steps and then never leaves it until the win.
    """

    def __init__(self) -> None:
        self._loops: Dict[int, Tuple[List[Cell], Dict[Cell, int], bool]] = {}

    def reset(self) -> None:
        pass  # nothing episode-specific; the loop cache is keyed by grid size

    def _loop_for(self, n: int) -> Tuple[List[Cell], Dict[Cell, int], bool]:
        hit = self._loops.get(n)
        if hit is None:
            if n % 2 == 0:
                loop = build_cycle(n)
                cyclic = True
            else:
                loop = build_path(n)
                cyclic = False
            hit = (loop, {cell: i for i, cell in enumerate(loop)}, cyclic)
            self._loops[n] = hit
        return hit

    def get_action(self, state: Dict[str, Any]) -> str:
        legal = state["legal_actions"]
        head = state["head"]
        direction = state["direction"]
        if not state.get("alive", True) or head is None:
            return direction if direction in legal else legal[0]
        loop, index, cyclic = self._loop_for(state["grid_size"])
        i = index.get(head)
        if i is not None and state.get("food") is not None:
            if cyclic:
                fwd = loop[(i + 1) % len(loop)]
                bwd = loop[(i - 1) % len(loop)]
            elif i + 1 < len(loop):
                fwd = loop[i + 1]
                bwd = loop[i - 1] if i > 0 else None
            else:  # path end: the only way is back
                fwd = None
                bwd = loop[i - 1] if i > 0 else None
            ordered: List[Cell] = []
            straight = _neighbor(head, direction)
            if straight == fwd or (bwd is not None and straight == bwd):
                # Keep going straight only while it stays on the loop.
                ordered.append(straight)
            if fwd is not None:
                ordered.append(fwd)
            if bwd is not None:
                ordered.append(bwd)
            seen = set()
            blocked = set(state["body"][:-1])  # tail vacates on normal moves
            for cell in ordered:
                if cell in seen:
                    continue
                seen.add(cell)
                if cell not in index:  # off-arena (e.g. facing a wall)
                    continue
                delta = (cell[0] - head[0], cell[1] - head[1], cell[2] - head[2])
                action = _DELTA_TO_ACTION.get(delta)
                if action is None or action not in legal:
                    continue
                if cell in blocked:
                    continue
                return action
        return _fallback_action(state)

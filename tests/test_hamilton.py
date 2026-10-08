"""Headless tests for the Hamilton-cycle baseline agent (no window required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.hamilton_agent import (
    HamiltonAgent,
    _fallback_action,
    build_cycle,
    build_path,
)
from game.config import ACTIONS, Config
from game.engine import SnakeGame


def adjacent(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) == 1


def play(game, agent, cap):
    state = game.get_state()
    done = False
    info = {}
    while not done and state["steps"] < cap:
        action = agent.get_action(state)
        assert action in state["legal_actions"], (action, state)
        state, _, done, info = game.step(action)
    return state, info


def test_cycles_cover_even_grids():
    for n in (2, 4, 6):
        loop = build_cycle(n)
        assert len(loop) == n ** 3, (n, len(loop))
        assert len(set(loop)) == n ** 3, n
        for i in range(len(loop)):
            assert adjacent(loop[i], loop[(i + 1) % len(loop)]), (n, i)


def test_cycle_rejected_on_odd_grid():
    for bad in (1, 3, 5):
        try:
            build_cycle(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("build_cycle(%r) accepted" % (bad,))


def test_paths_cover_any_grid():
    for n in (1, 2, 3, 4, 5):
        path = build_path(n)
        assert len(path) == n ** 3 and len(set(path)) == n ** 3, n
        for i in range(len(path) - 1):
            assert adjacent(path[i], path[i + 1]), (n, i)


def test_even_four_wins_every_seed():
    # Full 4^3 win: 64 cells - 3 start = 61 foods.
    for seed in range(3):
        game = SnakeGame(Config(grid_size=4, start_length=3), seed=seed)
        agent = HamiltonAgent()
        agent.reset()
        state, info = play(game, agent, 20000)
        assert state["won"] and info["reason"] == "win", (seed, state, info)
        assert state["score"] == 61, (seed, state)


def test_wins_from_random_spawn_and_wrap():
    game = SnakeGame(Config(grid_size=4, start_length=3), seed=0)
    game.reset(spawn_mode="random")
    state, _ = play(game, HamiltonAgent(), 20000)
    assert state["won"], state
    game = SnakeGame(Config(grid_size=4, start_length=3, wrap_mode=True), seed=3)
    state, _ = play(game, HamiltonAgent(), 20000)
    assert state["won"], state


def test_odd_grid_survives_and_eats():
    # Odd grids are best-effort (no cycle exists): require survival +
    # food, not a win. Uses a safe random spawn (center spawn of a
    # length-3 snake overflows small odd grids and is rejected).
    game = SnakeGame(Config(grid_size=3, start_length=1, spawn_mode="random"),
                     seed=1)
    agent = HamiltonAgent()
    state, info = play(game, agent, 3000)
    assert state["score"] > 0, (state, info)
    assert info["reason"] != "wall" or state["steps"] >= 3000, (state, info)


def test_actions_always_legal_and_headless():
    import subprocess
    probe = (
        "import sys; sys.path.insert(0, %r); "
        "import agents.hamilton_agent as h; "
        "assert 'pygame' not in sys.modules and 'OpenGL' not in sys.modules; "
        "a = h.HamiltonAgent(); "
        "s = {'head': (1, 1, 1), 'body': [(1, 1, 1)], 'food': (2, 2, 2), "
        "'direction': '+x', 'grid_size': 3, 'score': 0, 'length': 1, "
        "'steps': 0, 'alive': True, 'won': False, 'legal_actions': %r}; "
        "assert a.get_action(s) in s['legal_actions']; "
        "s['food'] = None; a.get_action(s); "
        "s['alive'] = False; a.get_action(s); print('headless-ok')"
    )
    root = str(Path(__file__).resolve().parents[1])
    out = subprocess.run(
        [sys.executable, "-c", probe % (root, sorted(ACTIONS))],
        capture_output=True, text=True, check=True)
    assert "headless-ok" in out.stdout, out


def test_fallback_reaches_food_and_chases_tail():
    game = SnakeGame(Config(grid_size=5, start_length=2), seed=0)
    state = game.reset(spawn_mode="custom", spawn_pos=(2, 2, 2),
                       spawn_direction="+x")
    game.food = (4, 2, 2)
    state = game.get_state()
    action = _fallback_action(state)
    assert action == "+x", (action, state)
    # Food boxed inside the body: fallback must still return a legal move.
    game.food = state["body"][-1]
    action = _fallback_action(game.get_state())
    assert action in game.get_state()["legal_actions"], action


if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_")}.items()):
        fn()
        print("PASS %s" % name)

"""Headless engine tests (no window required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.random_agent import RandomAgent
from game.config import Config
from game.engine import SnakeGame


def test_reset_shape():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=0)
    s = g.get_state()
    assert s["length"] == 3 and s["alive"]
    assert s["head"] == (3, 3, 3)
    assert len(s["legal_actions"]) == 5


def test_move_and_no_reverse_kill():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=0)
    before = g.get_state()["head"]
    s, r, done, info = g.step("+x")
    assert not done and s["head"][0] == before[0] + 1
    # reversal is ignored, not fatal
    s, r, done, info = g.step("-x")
    assert not done and s["direction"] == "+x"


def test_food_grows_and_scores():
    g = SnakeGame(Config(grid_size=5, start_length=2), seed=0)
    hx, hy, hz = g.get_state()["head"]
    g.food = (hx + 1, hy, hz)
    length = g.get_state()["length"]
    s, r, done, info = g.step("+x")
    assert s["length"] == length + 1 and s["score"] == 1 and r == 10.0


def test_wall_death_and_reward():
    g = SnakeGame(Config(grid_size=3, start_length=1), seed=0)
    g.step("+x")
    s, r, done, info = g.step("+x")
    assert done and info["reason"] == "wall" and r == -10.0 and not s["alive"]


def test_random_agent_episode():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=1)
    agent = RandomAgent(seed=1)
    state = g.get_state()
    for _ in range(60):
        state, _, done, _ = g.step(agent.get_action(state))
        if done:
            break
    assert state["steps"] > 0


if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items() if k.startswith("test_")}.items()):
        fn()
        print(f"PASS {name}")

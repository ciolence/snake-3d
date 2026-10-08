# Algorithm Control Spec - 3D Snake (living document, v1.2)

> **Normative contract** for any algorithm that plays this game. The friendly
> tutorial is `docs/AGENT_GUIDE.md`; when the two disagree, **this file wins**.
> Flexible: it evolves with development. Any change requires a version bump
> (see section 8) + a note in `MEMORY.md`.

## 1. Connection method

1. Write a module under `agents/`, e.g. `agents/my_agent.py`.
2. Expose a class subclassing `agents.base_agent.BaseAgent` implementing:
   `get_action(self, state: dict) -> str`, plus optional `reset(self)`.
3. Run: `python main.py --mode ai --agent agents.my_agent.MyAgent [--grid N] [--speed S] [--wrap] [--seed K]`.
4. Headless use (training, no window): import `game.engine.SnakeGame` + `game.config.Config` directly.

## 2. Action space (output)

- Exactly six discrete actions: `"+x"`, `"-x"`, `"+y"`, `"-y"`, `"+z"`, `"-z"` (`+y` = up).
- Returned action outside this set -> treated as "keep current direction".
- Returning the exact reverse of `state["direction"]` is **ignored** (keeps straight). It is never fatal. Prefer `state["legal_actions"]`.

## 3. Observation (input `state` dict)

| Key | Type | Semantics (guaranteed) |
|-----|------|------------------------|
| `head` | `(x,y,z)` ints | head cell; `0 <= c < grid_size` |
| `body` | `list[(x,y,z)]` head-first | full occupancy; `len == length` |
| `prev_body` | `list[(x,y,z)]` | body before the last step |
| `food` | `(x,y,z)` or `None` | target cell; `None` only after win |
| `direction` | one of the 6 actions | direction of the last executed step |
| `grid_size` | int | arena spans `[0, grid_size)` per axis |
| `score` | int | food eaten this episode (>= 0) |
| `length` | int | `len(body)` |
| `steps` | int | executed steps this episode |
| `alive` | bool | `False` after death or win |
| `won` | bool | `True` iff arena fully filled |
| `grew_last_step` | bool | last step ate food |
| `legal_actions` | `list[str]` | all actions except the reversal of `direction` |

- Coordinates are absolute arena cells. Do not mutate the dict contents.
- `Config` defaults: `grid_size=15`, `start_length=3`, `wrap_mode=False`.

## 4. Environment dynamics

1. **Step:** `state, reward, done, info = game.step(action)`; `done == (not state["alive"])`.
2. **Movement:** head advances one cell in the (possibly reversal-corrected) direction.
3. **Eating:** head lands on `food` -> length +1 (tail stays), `score` +1, new food on uniform-random empty cell.
4. **Normal move:** head added, tail removed (tail cell vacates - moving there is safe).
5. **Death:** outside arena (unless `--wrap` wraps coordinates mod `grid_size`) or head enters body (neck included while eating) -> `alive=False`, `done=True`.
6. **Win:** body fills all `grid_size^3` cells -> `won=True`, `done=True`, `food=None`.
7. **Food spawn:** uniform over empty cells via `random.Random(seed)`; `reset(seed)` re-seeds.
8. **Determinism:** same `seed` + same action sequence -> identical episode.
9. **Spawn:** `reset()` keeps the default center spawn (head at arena center, `+x`).
    `reset(spawn_mode="random")` draws a seeded safe (head, direction) pair;
    `reset(spawn_mode="custom", spawn_pos=(x,y,z), spawn_direction=D)` uses the given head cell + direction.
    Every mode guarantees the first step cannot die; invalid or unsafe requests raise `ValueError`.
    CLI: `--spawn center|random`, `--pos x,y,z` (implies custom), `--dir D`, `--length L`.

## 5. Rewards and termination

- `reward_food = +10.0`, `reward_death = -10.0`, `reward_win = +50.0`, plain move `0.0` (see `game/config.py`).
- `info["reason"]` in `{"food", "moved", "wall", "self", "win", "already_dead"}`.
- Stepping after `done` returns `(state, 0.0, True, {"reason": "already_dead"})`.

## 6. Timing / performance contract

- `get_action` is called once per logic step (default 8 steps/s, `--speed` up to `--max` 20).
- Keep it fast (soft budget: well under one step interval). Slow calls stall the render loop; there is no timeout kill yet.
- `reset()` is called once per episode (new game via UI `N` key too). Use it to clear memory.

## 7. Minimal examples

Starter template: `agents/template_agent.py`. Greedy demo: `agents/random_agent.py`.

```python
from agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def get_action(self, state):
        hx, hy, hz = state["head"]
        fx, fy, fz = state["food"] or (hx, hy, hz)
        prefer = []
        if fx > hx: prefer.append("+x")
        if fx < hx: prefer.append("-x")
        if fy > hy: prefer.append("+y")
        if fy < hy: prefer.append("-y")
        if fz > hz: prefer.append("+z")
        if fz < hz: prefer.append("-z")
        for a in prefer:
            if a in state["legal_actions"]:
                return a
        return state["legal_actions"][0]
```

Headless training loop:

```python
from game.config import Config
from game.engine import SnakeGame
from agents.random_agent import RandomAgent

game = SnakeGame(Config(grid_size=15), seed=1)
agent = RandomAgent(seed=0)
state = game.reset()
done = False
while not done:
    state, reward, done, info = game.step(agent.get_action(state))
print(state["score"], state["steps"], info)
```

## 8. Versioning

- `v1.2` (2026-10-08): additive spawn contract (section 4.9, Config.spawn_*); defaults unchanged.
- `v1.1` (2026-10-07): no contract change - the section 1.3 run command is portable now (`python main.py ...` instead of a machine-specific interpreter path).
- `v1.0` (2026-10-07): initial contract. Changes bump minor (additive/clarify) or major (dynamics, rewards, keys) versions and are logged here + in `MEMORY.md`.
- Planned (not promised): vector/batch observations, per-step time limits, replay/score files - pending user Q4 scope decision.

## 9. Changelog

- `v1.2 2026-10-08` Safe spawn modes (center/random/custom) + CLI flags; no default change.
- `v1.1 2026-10-07` Portable run command (section 1.3); no normative change.
- `v1.0 2026-10-07` Created from engine behavior + AGENT_GUIDE.

- `v1.1 2026-10-07` Portable run command (section 1.3); no normative change.
- `v1.0 2026-10-07` Created from engine behavior + AGENT_GUIDE.

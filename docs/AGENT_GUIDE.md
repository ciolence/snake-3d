# Agent Guide - How your algorithm connects to the 3D Snake game

This is the **standard interface** for algorithm control. You do NOT need to touch
the game engine or renderer - just write an agent file.

## 1. Quick start (3 steps)

1. Create `agents/my_agent.py`:

```python
from agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def get_action(self, state):
        # state is a dict (see section 2). Return one of:
        # "+x", "-x", "+y", "-y", "+z", "-z"
        return state["legal_actions"][0]
```

2. Run it:

```powershell
python main.py --mode ai --agent agents.my_agent.MyAgent
```

3. Optional speed / arena flags:

```powershell
python main.py --mode ai --agent agents.my_agent.MyAgent --speed 12 --grid 15 --seed 7 --spawn random
```

## 2. State dict (input to your algorithm)

| Key | Type | Meaning |
|-----|------|---------|
| `head` | `(x, y, z)` | head cell, origin `(0,0,0)` at corner |
| `body` | `list[(x,y,z)]` | head-first body cells |
| `prev_body` | `list[(x,y,z)]` | body before the last step (for motion cues) |
| `food` | `(x, y, z)` or `None` | apple cell |
| `direction` | `str` | current travel direction |
| `grid_size` | `int` | arena is `grid_size^3` |
| `score` | `int` | food eaten |
| `length` | `int` | current body length |
| `steps` | `int` | steps taken |
| `alive` | `bool` | `False` after death / win |
| `won` | `bool` | `True` if the whole arena was filled |
| `grew_last_step` | `bool` | whether the last step ate food |
| `legal_actions` | `list[str]` | all actions except the 180-degree reversal |

## 3. Actions (output of your algorithm)

Return exactly one of:

```text
+x  -x  +y  -y  +z  -z
```

`+y` is up, `-y` is down. Returning the exact reverse of `direction`
is **ignored** (snake keeps going straight) - it never kills you on the
spot. Unknown strings also fall back to going straight.

## 4. Rules

- Grid default `15 x 15 x 15`. Walls kill unless `--wrap` is used.
- Eating grows by 1 and respawns food on a random empty cell.
- Hitting a wall or your own body ends the episode (`alive=False`).
- Your `get_action` is called once per logic step (default 8 steps/sec,
  `--speed`, live +/- keys, or the setup menu (M)). Slow agents stutter the game.

## 5. Headless training (no window)

```python
from game.config import Config
from game.engine import SnakeGame
from agents.random_agent import RandomAgent

game = SnakeGame(Config(grid_size=15), seed=1)
agent = RandomAgent(seed=0)
state = game.reset()
done = False
while not done:
    action = agent.get_action(state)
    state, reward, done, info = game.step(action)
print("score:", state["score"], "steps:", state["steps"], info)
```

## 6. Tips

- Prefer `state["legal_actions"]` over the raw 6 moves.
- For pathfinding, BFS on the 3D grid from `head` to `food` avoiding `body`
  cells works well as a first baseline.
- Implement `reset()` if your algorithm keeps memory between episodes.

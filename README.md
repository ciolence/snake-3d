# 3D Snake (full 3D movement, PyOpenGL)

Software: `E:/anaconda3/python.exe` + `pygame` + `PyOpenGL` + `numpy` (all pre-installed, nothing else needed).

## Run

```powershell
E:/anaconda3/python.exe main.py --mode human
E:/anaconda3/python.exe main.py --mode ai --agent agents.random_agent.RandomAgent
E:/anaconda3/python.exe tests/test_engine.py
```

Flags: `--grid 15` `--speed 8` `--wrap` `--rotate` `--seed 7`

## Controls (human)

- `W/S` forward/back, `A/D` left/right (camera-relative), arrows work too
- `R/F` (or `Space/Shift`) up/down
- Mouse drag = orbit, wheel = zoom, `P` pause, `N` new game, `+/-` speed, `ESC` quit

## Algorithm interface

Write a class extending `agents/base_agent.py::BaseAgent` with `get_action(state) -> one of +x,-x,+y,-y,+z,-z`,
then pass `--agent your.module.YourClass`. Full spec: `docs/AGENT_GUIDE.md`.

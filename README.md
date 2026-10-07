# 3D Snake (full 3D movement, PyOpenGL)

Software: `E:/anaconda3/python.exe` + `pygame` + `PyOpenGL` + `numpy` (all pre-installed, nothing else needed).

## Run

```powershell
E:/anaconda3/python.exe main.py --mode human
E:/anaconda3/python.exe main.py --mode ai --agent agents.random_agent.RandomAgent
E:/anaconda3/python.exe tests/test_engine.py
E:/anaconda3/python.exe tests/test_control.py
```

Flags: `--grid 15` `--speed 8` `--wrap` `--rotate` `--seed 7`

## Controls (human)

Screen-relative, adapts to camera: `W/S` up/down on screen, `A/D` left/right on screen
(arrows work too), `Space/R` out of screen toward you, `Shift/F` into screen.
Hold to steer; quick taps are latched. Mouse drag = orbit, wheel = zoom,
`P` pause, `N` new game, `+/-` speed, `ESC` quit. HUD shows the live mapping.

## Docs

- `docs/AGENT_GUIDE.md` - tutorial: how to connect your algorithm.
- `docs/ALGORITHM_SPEC.md` - normative control contract, v1.0 (authoritative).
- `agents/template_agent.py` - starter template; `agents/random_agent.py` - demo.

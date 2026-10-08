# 3D Snake (full 3D movement, PyOpenGL)

Requirements: Python 3 + `pygame` + `PyOpenGL` + `numpy`.

## Run

```powershell
python main.py --mode human
python main.py --mode ai --agent agents.random_agent.RandomAgent
python tests/test_engine.py
python tests/test_control.py
python tests/test_spawn.py
```

Flags: `--grid 15` `--speed 8` `--wrap` `--rotate` `--seed 7 --length 3 --spawn center|random --pos 7,7,7 --dir +x`

## Controls (human)

Screen-relative, adapts to camera: `W/S` up/down on screen, `A/D` left/right on screen
(arrows work too), `Space/R` out of screen toward you, `Shift/F` into screen.
Hold to steer; quick taps are latched. Mouse drag = orbit, wheel = zoom,
`P` pause, `N` new game, `+/-` speed, `ESC` quit. `Tab` switches human/AI, `M` opens setup (mode, agent, speed, grid, wrap, spawn, seed, length). HUD shows the live mapping.

## Docs

- `docs/AGENT_GUIDE.md` - tutorial: how to connect your algorithm.
- `docs/ALGORITHM_SPEC.md` - normative control contract, v1.2 (authoritative).
- `agents/template_agent.py` - starter template; `agents/random_agent.py` - demo.

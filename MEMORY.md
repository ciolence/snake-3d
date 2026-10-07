# 3D Snake - Project Memory (living document)

> This file is the project journal. **Append, never rewrite history.**
> Update it on every behavior change: new entry under `## Log` + adjust
> `## Current state`. All three docs (`MEMORY.md`, `AGENTS.md`,
> `docs/ALGORITHM_SPEC.md`) are flexible and evolve with development.

## Current state (2026-10-07, commit a9bd438)

- **Goal:** full-3D snake (`grid^3`, 6-direction movement) playable by human
  or by external algorithm. Human play is accepted by the user; vision
  polish deferred.
- **Stack:** `E:/anaconda3/python.exe` (Python 3.13.5) + `pygame` 2.6.1 +
  `PyOpenGL` + `numpy`. No installs allowed.
- **Run:**
  - human: `E:/anaconda3/python.exe main.py --mode human`
  - ai: `E:/anaconda3/python.exe main.py --mode ai --agent agents.random_agent.RandomAgent`
  - tests: `E:/anaconda3/python.exe tests/test_engine.py` and `tests/test_control.py` (10 tests total)
- **Files:** `main.py` (loop) | `game/engine.py` (headless rules) |
  `game/renderer.py` (PyOpenGL + HUD texture) | `game/controller.py`
  (adaptive screen-relative input) | `game/config.py` (tuning) |
  `agents/base_agent.py` (interface) | `agents/random_agent.py` (demo) |
  `agents/template_agent.py` (starter) | `docs/AGENT_GUIDE.md` (tutorial) |
  `docs/ALGORITHM_SPEC.md` (normative contract)
- **Control model (accepted):** WASD = screen plane, Space/R = out of screen
  toward viewer, Shift/F = into screen; hold-to-steer + tap-latch queue
  (max 8, one consumed per step); reversals impossible by engine rule;
  HUD shows the live mapping.
- **Rewards:** food `+10`, death `-10`, win `+50`, plain move `0`.
- **Deferred:** vision polish (lighting/transparency/food glow); env
  extensions (vector obs, replay logging, scoring files).

## Decisions (D1...)

- **D1** Full 3D movement (6 dirs), not 2D-rendered-in-3D. Reason: user interest.
- **D2** PyOpenGL renderer (user installed it mid-project); software renderer dropped.
- **D3** Reversal of direction is *ignored* (keep straight), never fatal. Reason: forgiving for humans and AIs.
- **D4** Tail cell vacates on normal moves (no tail-chase false collision); moving into own neck while eating = death.
- **D5** Fixed rewards food +10 / death -10 / win +50; step reward 0 (clean training signal).
- **D6** Screen-relative adaptive control (yaw+pitch projection, diagonal blending, straight bonus 0.15) + hold-to-steer + tap latch. Reason: playtest "keys feel dead".
- **D7** One `flip()` per frame; HUD as OpenGL texture; 24-bit depth buffer.
- **D8** Robust font loader (Windows SysFont registry crash workaround).

## Bug history (B1...)

- **B1** `SyntaxWarning \p` in `main.py` docstring -> raw string.
- **B2** `pygame.font.SysFont` win32 crash (corrupt registry entry) -> `_make_font()` fallback chain.
- **B3** Black screen with one flash -> double `flip()` + 2D `blit()` on an OPENGL surface; fixed by HUD-texture + single flip.
- **B4** Keypresses dropped (60fps frames vs 8 steps/s sampling) -> hold-to-steer.
- **B5** Slow-speed taps lost (press+release between steps) -> tap-latch queue.
- **B6** Spawn bug: body trailed `+x` into its own path (instant self-collision) -> trail `-x`.
- **B7** Wall-death reward sign bug -> corrected to `reward_death`.

## Log (newest first)

- `2026-10-07` Control accepted by user at slow speed after tap-latch fix. Added MEMORY/AGENTS/SPEC docs.
- `2026-10-07` Adaptive screen-relative control + HUD mapping (e37d02f).
- `2026-10-07` Black-screen render fix (c5ba1c3); font + docstring fix (1f99c78).
- `2026-10-07` Initial env: engine, renderer, human+AI modes, guide, tests (05e2579). Repo `git init`.

## Open questions / next steps

1. Vision polish (user: "maybe later") - lighting, transparency, food glow, snake eyes.
2. Env extensions (user Q4 deferred) - vector/batch obs, replay logging, score files.
3. Real baseline agent (BFS 3D pathfinder) - not yet written.
4. Playtest open item: is HUD mapping line useful or noise?

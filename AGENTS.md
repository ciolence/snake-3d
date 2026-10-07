# Working Rules for AI Tools in `E:\Python\snake-3d` (living document)

> Scope: any AI coding agent working in this workspace. Flexible rules that
> evolve with the project; change them by editing this file + noting it in
> `MEMORY.md`. On conflict with a direct user instruction, the user wins.

## 1. Environment (hard constraints)

1. Python is **only** `E:/anaconda3/python.exe`. Never switch interpreters, never create venvs.
2. **Do NOT install** any package (`pip install` forbidden). If something is missing, work around it with the stdlib + preinstalled `pygame` / `PyOpenGL` / `numpy` / `tkinter` / `matplotlib`, or ask the user to install it themselves.
3. Windows + PowerShell. No heredocs (`<<`), no `rm -rf` style commands. One shell end-to-end for file ops.
4. The agent **cannot open a game window** - everything graphical must be verified headless (imports, probes, tests). Say so explicitly when a change needs human eyes.

## 2. Version control (local git only)

1. The repo is local-only: `git init` state, no remotes. **Never add a remote, push, or publish** without explicit user approval.
2. Commit small and conventional: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`.
3. Do not commit `__pycache__/`, `*.pyc`, `*.log`. Keep `.gitignore` covering them.
4. Escalated (unsandboxed) commands are allowed **only** for git writes under `.git/` (the sandbox mounts it read-only) - never for anything destructive.

## 3. How to work

1. **Plan before building** on new features: state goal, design, file list, test plan. For fixes, diagnose first (read code, reproduce headless), then patch.
2. Keep the headless core sacred: `game/engine.py` must stay importable with **no display** (no pygame/OpenGL imports). Renderer/input changes must never leak into it.
3. After every behavior change: run `tests/test_engine.py` + `tests/test_control.py`, plus a syntax/import check. Report results.
4. On every behavior change, append to `MEMORY.md` (Log + Current state + Decisions/Bugs as needed) and commit docs with the code.
5. Keep the three docs consistent: `MEMORY.md` (journal) / `AGENTS.md` (this file, tool rules) / `docs/ALGORITHM_SPEC.md` (algorithm contract). If a code change alters the algorithm-facing contract, update the SPEC in the same commit.
6. Prefer ASCII + minimal diffs. Do not reformat untouched code or rename files unprompted.

## 4. Safety / approval

1. Ask the user before: installing anything, deleting files, changing controls or rewards, touching git remotes, or expanding scope (e.g. Q4 env extensions).
2. Escalation requests must state exactly why unsandboxed execution is needed.
3. If a fix needs visual confirmation (rendering, feel), say what to run and what to look for - do not claim it is visually verified.

## 5. Changelog of these rules

- `2026-10-07` Created (v1). Covers env, git, workflow, safety.

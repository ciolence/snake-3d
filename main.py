r"""Entry point: human play or algorithm play.

Human:  PYTHON main.py --mode human
AI:     PYTHON main.py --mode ai --agent agents.random_agent.RandomAgent
"""
from __future__ import annotations
import inspect
import pkgutil

import argparse
import importlib
import time

import pygame

from agents.base_agent import BaseAgent
from game.config import ACTIONS, Config
from game.controller import (
    KEY_INTENTS,
    MOVE_KEYS,
    action_mapping_hint,
    choose_action,
    intent_from_keys,
    merge_intents,
)
from game.engine import SnakeGame, parse_spawn_pos
from game.renderer import Renderer

SETTING_MODES = ("human", "ai")
SETTING_SPAWNS = ("center", "random", "custom")
SETTING_DIRS = ("+x", "-x", "+y", "-y", "+z", "-z")

SPEED_STEP = 1.0
SPEED_MIN = 1.0
GRID_MIN = 3
GRID_MAX = 30
LENGTH_MIN = 1


def discover_agents(package="agents"):
    """Dotted paths of BaseAgent subclasses found under agents/ (import-safe)."""
    try:
        pkg = importlib.import_module(package)
        mods = sorted(m.name for m in pkgutil.iter_modules(getattr(pkg, "__path__", [])))
    except Exception:
        return []
    found = []
    for name in mods:
        if name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(package + "." + name)
        except Exception:
            continue
        for cls_name in sorted(vars(mod)):
            if cls_name.startswith("_"):
                continue
            try:
                cls = getattr(mod, cls_name)
                ok = inspect.isclass(cls) and issubclass(cls, BaseAgent) and cls is not BaseAgent
            except Exception:
                continue
            if ok:
                path = package + "." + name + "." + cls_name
                if path not in found:
                    found.append(path)
    return found


def cycle_agent(current, options, delta):
    """Left/Right agent step; unknown current snaps to nearest known entry."""
    if not options:
        return current
    i = options.index(current) if current in options else 0
    return options[(i + delta) % len(options)]

def clamp_speed(value, maximum) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = SPEED_MIN
    return max(SPEED_MIN, min(maximum, value))


def clamp_int(value, low, high) -> int:
    try:
        value = int(float(value))
    except (TypeError, ValueError):
        value = low
    return max(low, min(high, value))


def new_settings(mode: str, agent_path: str, config: Config,
                 seed: int | None) -> dict:
    """Editable copy of the live run state shown in the setup menu."""
    return {
        "mode": mode,
        "agent": agent_path,
        "speed": float(config.steps_per_second),
        "grid": int(config.grid_size),
        "wrap": bool(config.wrap_mode),
        "rotate": bool(config.auto_rotate),
        "spawn": str(config.spawn_mode),
        "pos": ",".join(str(c) for c in config.spawn_pos)
            if config.spawn_pos is not None else "",
        "dir": str(config.spawn_direction),
        "seed": "" if seed is None else str(seed),
        "length": int(config.start_length),
        "error": "",
    }


def menu_hint(draft, agents=None):
    agent = str(draft.get("agent", ""))
    if agents:
        pos = agents.index(agent) + 1 if agent in agents else 0
        agent_line = "Agent [%d/%d]: %s" % (pos, len(agents), agent)
    else:
        agent_line = "Agent: " + agent + " (no agents detected)"
    AGENT_LINE = agent_line
    return [
        f"Control: {draft['mode'].upper()} ({'AI agent' if draft['mode'] == 'ai' else 'human keys'})",
        AGENT_LINE,
        "Speed: %s steps/s" % str(draft["speed"]),
        "Grid: %s (arena %sx%sx%s)" % (str(draft["grid"]), str(draft["grid"]), str(draft["grid"]), str(draft["grid"])),
        f"Wrap: {'ON' if draft['wrap'] else 'OFF'} (walls {'wrap' if draft['wrap'] else 'kill'})",
        f"Rotate: {'ON' if draft['rotate'] else 'OFF'}",
        f"Spawn: {draft['spawn']}",
        f"Spawn pos: {draft['pos'] or '(none)'}  [custom only]",
        f"Spawn dir: {draft['dir']}",
        f"Seed: {draft['seed'] or '(none)'}",
        f"Length: {draft['length']}",
    ]


def cycle(value: str, options: tuple, delta: int) -> str:
    i = options.index(value) if value in options else 0
    return options[(i + delta) % len(options)]


def adjust_draft(draft: dict, row: int, delta: int, maximum: float, agents: list | None = None) -> None:
    """Left/Right tweak of the selected menu row (headless-testable)."""
    if row == 0:
        draft["mode"] = cycle(draft["mode"], SETTING_MODES, delta)
    elif row == 1:
        draft["agent"] = cycle_agent(str(draft["agent"]), list(agents or []), delta)
    elif row == 2:
        draft["speed"] = round(clamp_speed(clamp_speed(draft["speed"], 1e9) + delta * SPEED_STEP, maximum), 1)
    elif row == 3:
        draft["grid"] = clamp_int(clamp_int(draft["grid"], GRID_MIN, GRID_MAX) + delta, GRID_MIN, GRID_MAX)
    elif row == 4:
        draft["wrap"] = not draft["wrap"]
    elif row == 5:
        draft["rotate"] = not draft["rotate"]
    elif row == 6:
        draft["spawn"] = cycle(draft["spawn"], SETTING_SPAWNS, delta)
    elif row == 8:
        draft["dir"] = cycle(draft["dir"], SETTING_DIRS, delta)
    elif row == 10:
        n = clamp_int(draft["grid"], GRID_MIN, GRID_MAX)
        draft["length"] = clamp_int(clamp_int(draft["length"], LENGTH_MIN, GRID_MAX) + delta, LENGTH_MIN, n)


def apply_draft(draft: dict, args: argparse.Namespace, config: Config,
                load_agent_fn) -> tuple[str, BaseAgent | None, int | None, str]:
    """Validate the menu draft; on success mutate config/args, else (msg)."""
    mode = draft["mode"]
    speed = clamp_speed(draft["speed"], config.max_steps_per_second)
    grid = clamp_int(draft["grid"], GRID_MIN, GRID_MAX)
    length = clamp_int(draft["length"], LENGTH_MIN, grid)
    spawn = draft["spawn"]
    direction = draft["dir"]
    if spawn not in SETTING_SPAWNS:
        return mode, None, None, f"bad spawn '{spawn}'"
    if direction not in ACTIONS:
        return mode, None, None, f"bad direction '{direction}'"
    seed = None
    if str(draft["seed"]).strip():
        try:
            seed = int(str(draft["seed"]).strip())
        except ValueError:
            return mode, None, None, f"bad seed '{draft['seed']}': want an integer"
    pos = None
    if spawn == "custom":
        raw = str(draft["pos"]).strip()
        if not raw:
            return mode, None, None, "custom spawn needs a pos like 7,7,7"
        try:
            pos = parse_spawn_pos(raw, grid)
        except ValueError as exc:
            return mode, None, None, str(exc)
    agent = None
    if mode == "ai":
        try:
            agent = load_agent_fn(draft["agent"])
        except Exception as exc:
            return mode, None, None, f"cannot load agent: {exc}"
        try:
            agent.reset()
        except Exception:
            pass
    from dataclasses import replace as _replace
    probe_cfg = _replace(config, grid_size=grid, start_length=length,
                         steps_per_second=speed, wrap_mode=bool(draft["wrap"]),
                         auto_rotate=bool(draft["rotate"]), spawn_mode=spawn,
                         spawn_pos=pos, spawn_direction=direction)
    try:
        SnakeGame(config=probe_cfg, seed=seed)
    except ValueError as exc:
        return mode, None, None, str(exc)
    config.grid_size = grid
    config.start_length = length
    config.steps_per_second = speed
    config.wrap_mode = bool(draft["wrap"])
    config.auto_rotate = bool(draft["rotate"])
    config.spawn_mode = spawn
    config.spawn_pos = pos
    config.spawn_direction = direction
    args.mode = mode
    args.agent = draft["agent"]
    args.grid = grid
    args.speed = speed
    args.wrap = bool(draft["wrap"])
    args.rotate = bool(draft["rotate"])
    return mode, agent, seed, ""


def load_agent(path: str) -> BaseAgent:
    module_name, _, class_name = path.rpartition(".")
    if not module_name or not class_name:
        raise ValueError(f"Bad --agent '{path}'. Use e.g. agents.random_agent.RandomAgent")
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    agent = cls()
    if not isinstance(agent, BaseAgent):
        raise TypeError(f"{path} must subclass agents.base_agent.BaseAgent")
    return agent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="3D Snake (full 3D movement, PyOpenGL)")
    p.add_argument("--mode", choices=["human", "ai"], default="human")
    p.add_argument("--agent", default="agents.random_agent.RandomAgent",
                   help="Dotted path to agent class, used in --mode ai")
    p.add_argument("--grid", type=int, default=15)
    p.add_argument("--speed", type=float, default=8.0, help="steps per second")
    p.add_argument("--wrap", action="store_true", help="wrap around walls instead of dying")
    p.add_argument("--rotate", action="store_true", help="auto-rotate camera")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--length", type=int, default=3, help="initial snake length")
    p.add_argument("--spawn", choices=["center", "random"], default="center",
                   help="center = head at arena center; random = seeded safe draw")
    p.add_argument("--pos", default=None,
                   help="custom spawn head cell 'x,y,z' (implies --spawn custom)")
    p.add_argument("--dir", choices=["+x", "-x", "+y", "-y", "+z", "-z"], default="+x",
                   help="initial direction (center/custom spawn)")
    return p.parse_args()


def make_config(args: argparse.Namespace) -> tuple[Config, int | None, str]:
    """Build Config from CLI flags. Returns (config, seed, menu_error).

    Invalid/unsafe CLI spawns fall back to a safe center spawn and the
    setup menu (M) opens on launch showing the reason.
    """
    grid = clamp_int(args.grid, GRID_MIN, GRID_MAX)
    length = clamp_int(args.length, LENGTH_MIN, grid)
    speed = clamp_speed(args.speed, Config.max_steps_per_second)
    spawn = args.spawn
    pos = None
    menu_error = ""
    if args.pos is not None:
        spawn = "custom"
        try:
            pos = parse_spawn_pos(args.pos, grid)
        except ValueError as exc:
            spawn, pos = "center", None
            menu_error = str(exc)
    config = Config(grid_size=grid, start_length=length,
                    steps_per_second=speed,
                    wrap_mode=args.wrap, auto_rotate=args.rotate,
                    spawn_mode=spawn, spawn_pos=pos,
                    spawn_direction=args.dir)
    try:
        SnakeGame(config=config, seed=args.seed).reset()
    except ValueError as exc:
        menu_error = str(exc)
        config.spawn_mode, config.spawn_pos = "center", None
        config.spawn_direction = "+x"
    return config, args.seed, menu_error


def main() -> None:
    args = parse_args()
    config, seed, menu_error = make_config(args)

    mode = args.mode
    agent = load_agent(args.agent) if mode == "ai" else None
    if agent is not None:
        agent.reset()
    try:
        game = SnakeGame(config=config, seed=seed)
    except ValueError as exc:
        config.spawn_mode, config.spawn_pos = "center", None
        menu_error = menu_error or str(exc)
        game = SnakeGame(config=config, seed=seed)

    renderer = Renderer(config.grid_size, config.window_width, config.window_height)
    renderer.set_grid(config.grid_size)
    clock = pygame.time.Clock()
    paused = False
    speed = config.steps_per_second
    acc = 0.0
    last = time.perf_counter()
    msg = ""
    menu_open = menu_error != ""
    agent_options = discover_agents()
    draft = new_settings(mode, args.agent, config, seed)
    if menu_error:
        draft["error"] = menu_error
    row = 0
    edit: str | None = None
    edit_buf = ""

    # Hold-to-steer: remember which move keys are physically down. This is
    # polled every logic step, so inputs can no longer be dropped between
    # frames (the old bug: a keypress cleared each 60fps frame only landed
    # if a slower game step happened to run that same frame).
    held = {key: False for key in MOVE_KEYS}
    # Latched tap intent: every KEYDOWN adds its screen vector here, so a
    # quick tap that is released before the next (slow) logic step is still
    # honored. Consumed one step at a time (oldest first).
    tap_queue: list = []

    running = True
    while running:
        dt = time.perf_counter() - last
        last = time.perf_counter()
        fps = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION and event.buttons[0] and not menu_open:
                renderer.camera.drag(event.rel[0], event.rel[1])
            elif event.type == pygame.MOUSEWHEEL and not menu_open:
                renderer.camera.zoom(-event.y * 1.5)
            elif event.type == pygame.KEYDOWN:
                if menu_open:
                    if edit is not None:
                        if event.key == pygame.K_ESCAPE:
                            edit, edit_buf = None, ""
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            draft[edit] = edit_buf.strip()
                            edit, edit_buf = None, ""
                        elif event.key == pygame.K_BACKSPACE:
                            edit_buf = edit_buf[:-1]
                        elif event.unicode and event.unicode.isprintable() and len(edit_buf) < 80:
                            edit_buf += event.unicode
                        continue
                    if event.key == pygame.K_ESCAPE:
                        menu_open = False
                        draft["error"] = ""
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        row = (row - 1) % len(menu_hint(draft, agent_options))
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        row = (row + 1) % len(menu_hint(draft, agent_options))
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        draft["error"] = ""
                        adjust_draft(draft, row, -1, config.max_steps_per_second, agent_options)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        draft["error"] = ""
                        adjust_draft(draft, row, 1, config.max_steps_per_second, agent_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if row == 1 and not agent_options:
                            edit, edit_buf = "agent", draft["agent"]
                        elif row in (2, 3, 7, 9, 10):
                            key = {"2": "speed", "3": "grid", "7": "pos", "9": "seed", "10": "length"}[str(row)]
                            edit, edit_buf = key, str(draft[key])
                        else:
                            mode, agent, seed, err = apply_draft(
                                draft, args, config, load_agent)
                            draft["error"] = err
                            if not err:
                                renderer.set_grid(config.grid_size)
                                speed = config.steps_per_second
                                tap_queue.clear()
                                game = SnakeGame(config=config, seed=seed)
                                if agent is not None:
                                    try:
                                        agent.reset()
                                    except Exception:
                                        pass
                                msg, paused, acc = "", False, 0.0
                                menu_open = False
                    elif event.key == pygame.K_TAB:
                        draft["mode"] = cycle(draft["mode"], SETTING_MODES, 1)
                        draft["error"] = ""
                    continue
                if event.key in held:
                    held[event.key] = True
                    intent = KEY_INTENTS.get(event.key)
                    if intent is not None and len(tap_queue) < 8:
                        tap_queue.append(intent)
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    mode = "ai" if mode == "human" else "human"
                    if mode == "ai":
                        try:
                            agent = load_agent(args.agent)
                            agent.reset()
                        except Exception as exc:
                            msg = f"agent load failed: {exc}"
                            mode = "human"
                            agent = None
                    else:
                        agent = None
                    draft = new_settings(mode, args.agent, config, seed)
                elif event.key == pygame.K_m:
                    draft = new_settings(mode, args.agent, config, seed)
                    row, edit, edit_buf = 0, None, ""
                    menu_open = True
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_n:
                    tap_queue.clear()
                    game.reset()
                    if agent:
                        agent.reset()
                    msg = ""
                    paused = False
                    acc = 0.0
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed = min(config.max_steps_per_second, speed + 1.0)
                    config.steps_per_second = speed
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed = max(1.0, speed - 1.0)
                    config.steps_per_second = speed
            elif event.type == pygame.KEYUP:
                if event.key in held:
                    held[event.key] = False

        if not paused and not menu_open and game.alive:
            acc += dt
            interval = 1.0 / max(0.5, speed)
            while acc >= interval and game.alive:
                acc -= interval
                if mode == "ai" and agent is not None:
                    action = agent.get_action(game.get_state())
                else:
                    keys = pygame.key.get_pressed()
                    # Merge event-tracked state with live polling so a key
                    # held before window focus still steers.
                    merged = {k: (held.get(k, False) or bool(keys[k])) for k in held}
                    intent = merge_intents(
                        intent_from_keys(merged),
                        tap_queue.pop(0) if tap_queue else (0.0, 0.0, 0.0),
                    )
                    if intent == (0.0, 0.0, 0.0):
                        action = game.direction
                    else:
                        action = choose_action(intent, renderer.camera.yaw,
                                             renderer.camera.pitch,
                                             game.direction, game.legal_actions())
                game.step(action)

        state = game.get_state()
        msg = "" if state["alive"] else ("YOU WIN!" if state["won"] else "GAME OVER - press N")
        renderer.draw(state, mode, paused, config.auto_rotate or args.rotate)
        hint = (action_mapping_hint(renderer.camera.yaw, renderer.camera.pitch,
                                    game.direction, game.legal_actions())
                if mode == "human" else None)
        footer = "Spd %.1f  %s %s  Seed %s  Len %d  [Tab] mode  [M] setup  [N] new" % (speed, config.spawn_mode, config.spawn_direction, seed if seed is not None else "-", config.start_length)
        if config.spawn_pos:
            footer = "Spd %.1f  %s %s %s  Seed %s  Len %d  [Tab] mode  [M] setup  [N] new" % (speed, config.spawn_mode, ",".join(str(c) for c in config.spawn_pos), config.spawn_direction, seed if seed is not None else "-", config.start_length)
        if mode == "ai":
            footer += "  AI:" + str(args.agent).split(".")[-1]
        renderer.draw_overlay(state, mode, paused, fps, msg, hint, footer=footer,
                              menu_lines=menu_hint(draft, agent_options) if menu_open else None,
                              menu_row=row if menu_open else 0,
                              menu_edit=(edit, edit_buf) if menu_open else None,
                              menu_error=draft.get("error", "") if menu_open else "")
        clock.tick(60)

    renderer.close()


if __name__ == "__main__":
    main()

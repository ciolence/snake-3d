r"""Entry point: human play or algorithm play.

Human:  E:\anaconda3\python.exe main.py --mode human
AI:     E:\anaconda3\python.exe main.py --mode ai --agent agents.random_agent.RandomAgent
"""
from __future__ import annotations

import argparse
import importlib
import time

import pygame

from agents.base_agent import BaseAgent
from game.config import Config
from game.controller import key_to_action
from game.engine import SnakeGame
from game.renderer import Renderer


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
    return p.parse_args()


def main() -> None:
    args = parse_args()
    config = Config(grid_size=args.grid, steps_per_second=args.speed,
                    wrap_mode=args.wrap, auto_rotate=args.rotate)
    game = SnakeGame(config=config, seed=args.seed)

    agent = load_agent(args.agent) if args.mode == "ai" else None
    if agent is not None:
        agent.reset()

    renderer = Renderer(config.grid_size, config.window_width, config.window_height)
    clock = pygame.time.Clock()
    pending_action: str | None = None
    paused = False
    speed = config.steps_per_second
    acc = 0.0
    last = time.perf_counter()
    msg = ""

    running = True
    while running:
        dt = time.perf_counter() - last
        last = time.perf_counter()
        fps = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                renderer.camera.drag(event.rel[0], event.rel[1])
            elif event.type == pygame.MOUSEWHEEL:
                renderer.camera.zoom(-event.y * 1.5)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_n:
                    game.reset()
                    if agent: agent.reset()
                    msg = ""; paused = False; acc = 0.0
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed = min(config.max_steps_per_second, speed + 1.0)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed = max(1.0, speed - 1.0)
                elif args.mode == "human" and game.alive:
                    nxt = key_to_action(event.key, renderer.camera.yaw,
                                        game.direction, game.legal_actions())
                    if nxt:
                        pending_action = nxt

        if not paused and game.alive:
            acc += dt
            interval = 1.0 / max(0.5, speed)
            while acc >= interval and game.alive:
                acc -= interval
                if args.mode == "ai" and agent is not None:
                    action = agent.get_action(game.get_state())
                else:
                    action = pending_action or game.direction
                game.step(action)
            pending_action = None

        state = game.get_state()
        msg = "" if state["alive"] else ("YOU WIN!" if state["won"] else "GAME OVER - press N")
        renderer.draw(state, args.mode, paused, config.auto_rotate or args.rotate)
        renderer.draw_overlay(state, args.mode, paused, fps, msg)
        clock.tick(60)

    renderer.close()


if __name__ == "__main__":
    main()

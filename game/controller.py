"""Adaptive camera-relative human control for full 3D movement.

Screen intent model:
  W = up on screen, S = down on screen
  A = left on screen, D = right on screen
  Space/R/PageUp = out of the screen toward the viewer
  Shift/F/PageDown = into the screen away from the viewer

Every frame the six world moves (+x/-x/+y/-y/+z/-z) are projected onto the
current camera (yaw AND pitch). The held keys form one blended screen-space
intent vector, and the legal world move with the best alignment wins. This
means the meaning of WASD+Space/Shift continuously adapts as you orbit.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

import pygame

from .config import ACTION_VECTORS

# (screen_x, screen_y, screen_depth). Depth +1 = into the screen (away).
KEY_INTENTS = {
    pygame.K_w: (0.0, 1.0, 0.0),
    pygame.K_UP: (0.0, 1.0, 0.0),
    pygame.K_s: (0.0, -1.0, 0.0),
    pygame.K_DOWN: (0.0, -1.0, 0.0),
    pygame.K_a: (-1.0, 0.0, 0.0),
    pygame.K_LEFT: (-1.0, 0.0, 0.0),
    pygame.K_d: (1.0, 0.0, 0.0),
    pygame.K_RIGHT: (1.0, 0.0, 0.0),
    pygame.K_SPACE: (0.0, 0.0, -1.0),
    pygame.K_r: (0.0, 0.0, -1.0),
    pygame.K_PAGEUP: (0.0, 0.0, -1.0),
    pygame.K_LSHIFT: (0.0, 0.0, 1.0),
    pygame.K_RSHIFT: (0.0, 0.0, 1.0),
    pygame.K_f: (0.0, 0.0, 1.0),
    pygame.K_PAGEDOWN: (0.0, 0.0, 1.0),
}

MOVE_KEYS = tuple(KEY_INTENTS.keys())


def screen_basis(yaw_deg: float, pitch_deg: float):
    """Camera basis vectors expressed in world coordinates.

    Returns (right, cam_up, forward) where forward points from the camera
    toward the arena (i.e. into the screen).
    """
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    right = (math.sin(yaw), 0.0, -math.cos(yaw))
    cam_up = (-math.sin(pitch) * math.cos(yaw), math.cos(pitch),
              -math.sin(pitch) * math.sin(yaw))
    forward = (-math.cos(pitch) * math.cos(yaw), -math.sin(pitch),
               -math.cos(pitch) * math.sin(yaw))
    return right, cam_up, forward


def project_action(action: str, yaw_deg: float, pitch_deg: float) -> Tuple[float, float, float]:
    """Project a world move onto screen axes -> (sx, sy, depth)."""
    vx, vy, vz = ACTION_VECTORS[action]
    right, cam_up, forward = screen_basis(yaw_deg, pitch_deg)
    sx = vx * right[0] + vy * right[1] + vz * right[2]
    sy = vx * cam_up[0] + vy * cam_up[1] + vz * cam_up[2]
    depth = vx * forward[0] + vy * forward[1] + vz * forward[2]
    return (sx, sy, depth)


def intent_from_keys(keys) -> Tuple[float, float, float]:
    """Blend all held movement keys into one screen-space intent vector.

    `keys` is whatever ``pygame.key.get_pressed()`` returns (indexable by
    key constant). Returns (ix, iy, idepth).
    """
    ix = iy = idepth = 0.0
    for key, (kx, ky, kd) in KEY_INTENTS.items():
        try:
            held = keys[key]
        except Exception:
            held = False
        if held:
            ix += kx
            iy += ky
            idepth += kd
    return (ix, iy, idepth)


def intent_from_names(names: Iterable[str]) -> Tuple[float, float, float]:
    """Test/headless helper: names like {'w','a','out','in'}."""
    mapping = {
        "w": (0.0, 1.0, 0.0), "s": (0.0, -1.0, 0.0),
        "a": (-1.0, 0.0, 0.0), "d": (1.0, 0.0, 0.0),
        "out": (0.0, 0.0, -1.0), "in": (0.0, 0.0, 1.0),
    }
    ix = iy = idepth = 0.0
    for n in names:
        kx, ky, kd = mapping[n]
        ix += kx
        iy += ky
        idepth += kd
    return (ix, iy, idepth)


def choose_action(intent: Tuple[float, float, float], yaw_deg: float,
                  pitch_deg: float, current: str, legal: list[str],
                  straight_bonus: float = 0.15) -> str:
    """Pick the legal world move best aligned with a screen intent.

    A small bonus for continuing straight kills flicker when two moves
    score nearly equally (common near diagonal camera angles).
    """
    ix, iy, idepth = intent
    if ix == 0.0 and iy == 0.0 and idepth == 0.0:
        return current
    best = current if current in legal else (legal[0] if legal else current)
    best_score = float("-inf")
    for action in legal:
        sx, sy, depth = project_action(action, yaw_deg, pitch_deg)
        score = ix * sx + iy * sy + idepth * depth
        if action == current:
            score += straight_bonus
        if score > best_score:
            best_score = score
            best = action
    return best


def choose_from_held(keys, yaw_deg: float, pitch_deg: float,
                     current: str, legal: list[str]) -> str | None:
    """Return a new action if any movement key is held, else None."""
    intent = intent_from_keys(keys)
    if intent == (0.0, 0.0, 0.0):
        return None
    return choose_action(intent, yaw_deg, pitch_deg, current, legal)


def key_to_action(key: int, yaw_deg: float, pitch_deg: float,
                  current: str, legal: list[str]) -> str | None:
    """Single KEYDOWN compatibility: treat one key as its intent vector."""
    intent = KEY_INTENTS.get(key)
    if intent is None:
        return None
    return choose_action(intent, yaw_deg, pitch_deg, current, legal)


def action_mapping_hint(yaw_deg: float, pitch_deg: float,
                        current: str, legal: list[str]) -> Dict[str, str]:
    """Current adaptive mapping for the HUD, e.g. {'W': '+y', ...}."""
    hints = {}
    for label, names in (("W", ("w",)), ("S", ("s",)), ("A", ("a",)),
                         ("D", ("d",)), ("Spc", ("out",)), ("Shf", ("in",))):
        intent = intent_from_names(names)
        hints[label] = choose_action(intent, yaw_deg, pitch_deg, current, legal)
    return hints

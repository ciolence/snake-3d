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



def merge_intents(*intents: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Vector-sum of screen-space intents (held + latched taps)."""
    ix = iy = idepth = 0.0
    for (x, y, d) in intents:
        ix += x
        iy += y
        idepth += d
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

    W/S are depth-blind: only the on-screen vertical component counts, so
    W always means "most upward on screen". Near top-down view, where
    world-vertical moves are nearly edge-on (screen-vertical magnitude
    below 0.15), W/S switch to the horizontal-plane moves that look most
    up/down on screen instead. A/D use the screen-horizontal component; only
    Space/Shift (depth keys) consider depth. A small bonus for
    continuing straight kills flicker when two moves score nearly equally
    (common near diagonal camera angles).
    """
    ix, iy, idepth = intent
    if ix == 0.0 and iy == 0.0 and idepth == 0.0:
        return current
    use_x = ix != 0.0
    use_y = iy != 0.0
    use_depth = idepth != 0.0
    # Near top-down, world-vertical moves are nearly edge-on (they would
    # read as pure depth, like Space/Shift), so pure W/S skips them in
    # favour of the ground-plane moves that look most up/down on screen.
    # Threshold on the actual projection, not on the pitch angle.
    _up_y = project_action("+y", yaw_deg, pitch_deg)[1]
    top_down_ws = use_y and not use_x and not use_depth and abs(_up_y) < 0.15
    best = current if current in legal else (legal[0] if legal else current)
    best_score = float("-inf")
    for action in legal:
        if top_down_ws and action in ("+y", "-y"):
            continue
        sx, sy, depth = project_action(action, yaw_deg, pitch_deg)
        score = 0.0
        if use_x:
            score += ix * sx
        if use_y:
            score += iy * sy
        if use_depth:
            score += idepth * depth
        if action == current:
            score += straight_bonus
        # Tie-break: prefer genuinely moving on screen in the intended
        # sense (kills zero-component "sideways" picks when two moves tie).
        if use_y and not use_x and not use_depth:
            score += 1e-6 * (sy if iy > 0 else -sy)
        elif use_x and not use_y and not use_depth:
            score += 1e-6 * (sx if ix > 0 else -sx)
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

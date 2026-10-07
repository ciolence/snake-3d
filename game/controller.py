"""Human keyboard control: camera-relative WASD + absolute R/F + arrows."""
from __future__ import annotations

import math
import pygame


def camera_basis(yaw_deg: float):
    """Return (forward, right) unit vectors on the XZ plane for a camera yaw."""
    yaw = math.radians(yaw_deg)
    # Camera looks toward the origin from (cos yaw, sin yaw); forward on the
    # ground plane is the opposite of the camera offset direction.
    fx, fz = -math.cos(yaw), -math.sin(yaw)
    # Right vector = forward rotated -90 degrees on XZ.
    rx, rz = -fz, fx
    return (fx, fz), (rx, rz)


def pick_move(action_wanted: str, current: str, legal: list[str]) -> str:
    """Camera-relative moves resolve to the closest legal axis action."""
    from .config import ACTION_VECTORS, OPPOSITE
    if action_wanted in legal:
        return action_wanted
    if action_wanted == OPPOSITE.get(current):
        return current  # never allow the player to suicide by reversal
    return current


def key_to_action(key: int, yaw_deg: float, current: str, legal: list[str]) -> str | None:
    """Map a keypress to one of the 6 actions, camera-relative where sensible."""
    (fx, fz), (rx, rz) = camera_basis(yaw_deg)

    def axis_for(vec):
        x, z = vec
        if abs(x) >= abs(z):
            return "+x" if x > 0 else "-x"
        return "+z" if z > 0 else "-z"

    if key in (pygame.K_w, pygame.K_UP):
        return pick_move(axis_for((fx, fz)), current, legal)
    if key in (pygame.K_s, pygame.K_DOWN):
        return pick_move(axis_for((-fx, -fz)), current, legal)
    if key in (pygame.K_a, pygame.K_LEFT):
        return pick_move(axis_for((-rx, -rz)), current, legal)
    if key in (pygame.K_d, pygame.K_RIGHT):
        return pick_move(axis_for((rx, rz)), current, legal)
    if key in (pygame.K_r, pygame.K_SPACE, pygame.K_PAGEUP):
        return pick_move("+y", current, legal)
    if key in (pygame.K_f, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_PAGEDOWN):
        return pick_move("-y", current, legal)
    return None

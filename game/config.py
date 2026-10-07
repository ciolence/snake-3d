"""Central configuration for the 3D Snake game."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

# The six axis-aligned moves. "+y" is up, "-y" is down.
ACTIONS = ("+x", "-x", "+y", "-y", "+z", "-z")

ACTION_VECTORS: Dict[str, Tuple[int, int, int]] = {
    "+x": (1, 0, 0),
    "-x": (-1, 0, 0),
    "+y": (0, 1, 0),
    "-y": (0, -1, 0),
    "+z": (0, 0, 1),
    "-z": (0, 0, -1),
}

OPPOSITE: Dict[str, str] = {
    "+x": "-x", "-x": "+x",
    "+y": "-y", "-y": "+y",
    "+z": "-z", "-z": "+z",
}


@dataclass
class Config:
    """Tunable game settings."""

    grid_size: int = 15          # arena is grid_size^3 cells
    start_length: int = 3        # initial snake length
    steps_per_second: float = 8.0  # default logic speed
    max_steps_per_second: float = 20.0
    wrap_mode: bool = False      # False = walls kill, True = wrap around
    window_width: int = 1100
    window_height: int = 750
    auto_rotate: bool = False    # slowly orbit the camera

    # Rewards for algorithm training / scoring.
    reward_food: float = 10.0
    reward_death: float = -10.0
    reward_win: float = 50.0

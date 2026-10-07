"""Headless tests for the adaptive camera-relative controller."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: F401  (needed for key constants)

from game.controller import (
    action_mapping_hint,
    choose_action,
    intent_from_names,
)


def test_w_means_screen_up_down_default_cam():
    legal = ["+x", "-x", "+y", "-y", "+z", "-z"]
    hint = action_mapping_hint(45.0, 28.0, "+x", legal)
    assert hint["W"] == "+y", hint
    assert hint["S"] == "-y", hint


def test_mapping_adapts_to_camera():
    legal = ["+x", "-x", "+y", "-y", "+z", "-z"]
    h1 = action_mapping_hint(45.0, 28.0, "+x", legal)
    h2 = action_mapping_hint(200.0, 28.0, "+x", legal)
    assert h1 != h2, (h1, h2)


def test_diagonal_blend_picks_best_alignment():
    legal = ["+x", "-x", "+y", "-y", "+z", "-z"]
    # W+A intent (-1, +1, 0): -x scores highest at yaw45/pitch28.
    got = choose_action(intent_from_names(("w", "a")), 45.0, 28.0, "+x", legal)
    assert got == "-x", got


def test_no_keys_keeps_straight():
    got = choose_action((0.0, 0.0, 0.0), 45.0, 28.0, "+z", ["+x", "+z", "-z"])
    assert got == "+z", got


def test_reversal_never_offered_as_legal_target():
    # Engine excludes reversals from legal; controller must only pick legal.
    got = choose_action(intent_from_names(("s",)), 45.0, 28.0, "+y",
                        ["+x", "-x", "+y", "-y", "+z", "-z"])
    assert got == "-y", got


if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items() if k.startswith("test_")}.items()):
        fn()
        print(f"PASS {name}")

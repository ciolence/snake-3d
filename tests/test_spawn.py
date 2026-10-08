"""Spawn tests: center/random/custom safety (no window required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.config import ACTIONS, Config
from game.engine import SnakeGame, _body_from_head, parse_spawn_pos


def first_step_survives(game):
    s, reward, done, info = game.step(game.direction)
    assert not done, (game.get_state()["head"], game.direction, info)
    assert reward != game.config.reward_death
    return s


def test_center_default_is_safe():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=0)
    s = g.get_state()
    assert s["head"] == (3, 3, 3) and s["direction"] == "+x"
    first_step_survives(g)


def test_random_spawns_always_safe():
    for seed in range(30):
        g = SnakeGame(Config(grid_size=5, start_length=2), seed=seed)
        g.reset(spawn_mode="random")
        first_step_survives(g)


def test_random_respects_wrap_and_seed():
    g = SnakeGame(Config(wrap_mode=True), seed=9)
    s = g.reset(spawn_mode="random")
    assert s["alive"]
    g2 = SnakeGame(Config(wrap_mode=True), seed=9)
    assert g2.reset(spawn_mode="random")["head"] == s["head"]


def test_custom_valid_is_safe():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=0)
    s = g.reset(spawn_mode="custom", spawn_pos=(3, 3, 3), spawn_direction="-z")
    assert s["head"] == (3, 3, 3) and s["direction"] == "-z"
    first_step_survives(g)


def test_custom_wall_death_rejected():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=0)
    try:
        g.reset(spawn_mode="custom", spawn_pos=(6, 3, 3), spawn_direction="+x")
    except ValueError as exc:
        assert "wall" in str(exc), exc
    else:
        raise AssertionError("wall-facing custom spawn accepted")


def test_custom_out_of_arena_rejected():
    g = SnakeGame(Config(grid_size=7, start_length=3), seed=0)
    for bad in ("7,3,3", "-1,0,0", "1,2", "a,b,c"):
        try:
            parse_spawn_pos(bad, 7)
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad pos accepted: {bad}")
    try:
        g.reset(spawn_mode="custom", spawn_pos=(0, 0, 0), spawn_direction="+x")
    except ValueError as exc:
        assert "arena" in str(exc), exc
    else:
        raise AssertionError("out-of-arena body accepted")


def test_unsafe_reason_covers_all_pairs():
    g = SnakeGame(Config(grid_size=4, start_length=2))
    checked = 0
    for x in range(4):
        for y in range(4):
            for z in range(4):
                for a in ACTIONS:
                    body = _body_from_head((x, y, z), a, 2)
                    reason = g._unsafe_reason(body, a)
                    if reason is None:
                        g.body.clear()
                        g.body.extend(body)
                        g.direction = a
                        g.alive = True
                        first_step_survives(g)
                        checked += 1
    assert checked > 0, "expected some safe pairs on 4^3"


def test_bad_mode_and_direction_rejected():
    g = SnakeGame(Config(grid_size=5, start_length=2), seed=0)
    for kwargs in ({"spawn_mode": "middle"}, {"spawn_direction": "+q"},
                   {"spawn_mode": "custom"}):
        try:
            g.reset(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted {kwargs}")




def test_discover_agents_lists_bundled():
    import main
    opts = main.discover_agents()
    assert "agents.random_agent.RandomAgent" in opts, opts
    assert "agents.template_agent.TemplateAgent" in opts, opts
    assert opts == sorted(opts), opts


def test_cycle_agent_wraps_and_snaps():
    import main
    opts = ["a.A", "b.B"]
    assert main.cycle_agent("a.A", opts, 1) == "b.B"
    assert main.cycle_agent("b.B", opts, 1) == "a.A"
    assert main.cycle_agent("zzz", opts, 1) == "b.B"
    assert main.cycle_agent("a.A", [], 1) == "a.A"


def test_agent_row_tweak_never_crashes():
    import main
    from game.config import Config
    opts = main.discover_agents()
    d = main.new_settings("ai", opts[0], Config(), None)
    main.adjust_draft(d, 1, 1, 20.0, opts)
    assert d["agent"] in opts, d
    main.adjust_draft(d, 1, 1, 20.0, [])
    assert d["agent"] in opts, d
    rows = main.menu_hint(d, opts)
    assert rows[1].startswith("Agent [") and ("/%d" % len(opts)) in rows[1], rows[1]


def test_typed_strings_never_crash_apply():
    import argparse
    import main
    from game.config import Config
    ns = argparse.Namespace(mode="human", agent="x", grid=15, speed=8.0,
                            wrap=False, rotate=False, seed=None, length=3,
                            spawn="center", pos=None, dir="+x")
    cfg = Config()
    d = main.new_settings("ai", "agents.random_agent.RandomAgent", Config(), None)
    d.update({"grid": "15", "speed": "6", "length": "3", "seed": "4"})
    mode, agent, seed, err = main.apply_draft(d, ns, cfg, main.load_agent)
    assert err == "", err
    assert (cfg.grid_size, cfg.start_length) == (15, 3), (cfg.grid_size, cfg.start_length)
    assert seed == 4, seed
    d["length"] = "not-a-number"
    mode, agent, seed, err = main.apply_draft(d, ns, cfg, main.load_agent)
    assert err == "", err
    assert cfg.start_length >= 1, cfg.start_length
if __name__ == "__main__":
    for name, fn in sorted({k: v for k, v in globals().items() if k.startswith("test_")}.items()):
        fn()
        print(f"PASS {name}")

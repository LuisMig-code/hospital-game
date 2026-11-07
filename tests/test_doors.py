"""Testes das portas: posicionamento, bloqueio e abrir/fechar."""
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from doors import SIDES, try_toggle  # noqa: E402
from dungeon import FLOOR, generate  # noqa: E402
from fov import compute_fov  # noqa: E402

SEEDS = range(200)


class FakePlayer:
    def __init__(self, tile, facing, target=None):
        self.tile, self.facing, self.target = tile, facing, target


def player_facing(door):
    """Jogador parado do lado de dentro da sala, olhando para a porta."""
    (ax, ay), (ox, oy) = SIDES[door.side]
    x, y = door.tiles[0]
    facing = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}[(ox, oy)]
    return FakePlayer((x - ox, y - oy), facing)


class DoorPlacementTests(unittest.TestCase):
    def test_every_seed_has_doors_on_all_sides_overall(self):
        sides = Counter()
        for seed in SEEDS:
            d = generate(seed)
            self.assertTrue(d.doors, f"seed {seed} sem portas")
            sides.update(door.side for door in d.doors)
        self.assertEqual(set(sides), {"top", "bottom", "left", "right"})

    def test_door_shape(self):
        for seed in SEEDS:
            d = generate(seed)
            for door in d.doors:
                (ax, ay), (ox, oy) = SIDES[door.side]
                self.assertEqual(len(door.tiles), 2)
                (x0, y0), (x1, y1) = door.tiles
                self.assertEqual((x1 - x0, y1 - y0), (ax, ay))   # contíguos, na linha da parede
                for x, y in door.tiles:
                    self.assertEqual(d.grid[y][x], FLOOR)
                    self.assertTrue(d.is_floor(x + ox, y + oy))  # corredor do lado de fora
                    self.assertTrue(d.is_floor(x - ox, y - oy))  # sala do lado de dentro
                    self.assertIs(d.door_at[(x, y)], door)
                self.assertFalse(d.is_floor(x0 - ax, y0 - ay))   # pontas são parede
                self.assertFalse(d.is_floor(x1 + ax, y1 + ay))

    def test_doors_start_closed_and_deterministic(self):
        a, b = generate(42), generate(42)
        self.assertTrue(all(not door.open for door in a.doors))
        self.assertEqual([(x.side, x.tiles) for x in a.doors], [(x.side, x.tiles) for x in b.doors])


class DoorBehaviourTests(unittest.TestCase):
    def setUp(self):
        self.d = generate(42)
        self.door = self.d.doors[0]

    def test_closed_blocks_walk_and_sight(self):
        p = player_facing(self.door)
        tile = self.door.tiles[0]
        (_, _), (ox, oy) = SIDES[self.door.side]
        beyond = (tile[0] + 2 * ox, tile[1] + 2 * oy)          # corredor atrás da porta
        self.assertFalse(self.d.is_walkable(*tile))
        self.assertNotIn(beyond, compute_fov(self.d, p.tile, 8))
        self.door.open = True
        self.assertTrue(self.d.is_walkable(*tile))
        self.assertIn(beyond, compute_fov(self.d, p.tile, 8))

    def test_toggle(self):
        p = player_facing(self.door)
        self.assertEqual(try_toggle(self.d, p), ("abriu", self.door))
        self.assertTrue(self.door.open)
        self.assertEqual(try_toggle(self.d, p), ("fechou", self.door))
        self.assertFalse(self.door.open)

    def test_cannot_close_while_inside(self):
        p = player_facing(self.door)
        try_toggle(self.d, p)                         # abre
        p.tile = self.door.tiles[0]                   # entra na porta
        self.assertEqual(try_toggle(self.d, p)[0], "bloqueada")
        self.assertTrue(self.door.open)
        p.tile, p.target = player_facing(self.door).tile, self.door.tiles[1]  # indo para a porta
        self.assertEqual(try_toggle(self.d, p)[0], "bloqueada")

    def test_no_door_nearby(self):
        sx, sy = self.d.spawn
        far = FakePlayer((sx, sy), "up")
        if (sx, sy - 1) not in self.d.door_at:
            self.assertEqual(try_toggle(self.d, far), (None, None))


if __name__ == "__main__":
    unittest.main()

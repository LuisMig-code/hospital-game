"""Testes do campo de visão."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dungeon import FLOOR, WALL, Dungeon, generate  # noqa: E402
from fov import Vision, compute_fov, in_radius  # noqa: E402

R = 5


def make(rows):
    """Dungeon a partir de strings: '.' chão, '#' parede."""
    grid = [[FLOOR if c == "." else WALL for c in row] for row in rows]
    return Dungeon(0, len(rows[0]), len(rows), grid)


OPEN = make(["." * 21] * 21)


class FovTests(unittest.TestCase):
    def test_origin_and_radius(self):
        vis = compute_fov(OPEN, (10, 10), R)
        self.assertIn((10, 10), vis)
        for x, y in vis:
            self.assertTrue(in_radius(x - 10, y - 10, R))
        self.assertNotIn((10, 10 + R + 1), vis)
        self.assertNotIn((10 + R, 10 + R), vis)   # canto fora do círculo

    def test_open_room_sees_whole_circle(self):
        vis = compute_fov(OPEN, (10, 10), R)
        expected = {(10 + dx, 10 + dy) for dx in range(-R, R + 1) for dy in range(-R, R + 1)
                    if in_radius(dx, dy, R)}
        self.assertEqual(vis, expected)

    def test_wall_blocks_sight(self):
        d = make([
            "...........",
            "...........",
            ".....#.....",
            "...........",
            "...........",
        ])
        vis = compute_fov(d, (5, 4), R)
        self.assertIn((5, 2), vis)        # vê a parede
        self.assertNotIn((5, 1), vis)     # mas não o que está atrás
        self.assertNotIn((5, 0), vis)
        self.assertIn((4, 3), vis)

    def test_rooms_are_hidden_behind_walls(self):
        d = make([
            ".....#.....",
            ".....#.....",
            ".....#.....",
        ])
        vis = compute_fov(d, (3, 1), R)
        self.assertIn((5, 1), vis)
        self.assertFalse(any(x > 5 for x, _ in vis))

    def test_tall_wall_top_is_revealed(self):
        d = make([
            "#####",
            "#####",
            ".....",
            ".....",
        ])
        vis = compute_fov(d, (2, 3), R)
        self.assertIn((2, 1), vis)        # face da parede (chão abaixo)
        self.assertIn((2, 0), vis)        # parte de cima da parede alta

    def test_whole_wall_along_room_is_visible(self):
        d = make([
            "###########",
            "...........",
            "...........",
        ])
        vis = compute_fov(d, (5, 1), R)
        # olhando rente à parede de cima: a fileira inteira no alcance aparece
        for x in range(1, 10):
            self.assertIn((x, 0), vis)

    def test_top_door_reveals_tile_above(self):
        from doors import Door
        d = make([
            "##..##",
            "##..##",
            "......",
            "......",
        ])
        door = Door(tiles=[(2, 1), (3, 1)], side="top")
        d.doors.append(door)
        d.door_at.update({(2, 1): door, (3, 1): door})
        vis = compute_fov(d, (2, 3), R)
        self.assertIn((2, 1), vis)        # porta fechada é visível
        self.assertIn((2, 0), vis)        # e a parte de cima do desenho também

    def test_explored_grows_and_visible_in_radius(self):
        d = generate(42)
        v = Vision(d, R)
        x, y = d.spawn
        v.update((x, y))
        seen = set(v.explored)
        for tile in [(x + i, y) for i in range(1, 4) if d.is_walkable(x + i, y)]:
            new = v.update(tile)
            self.assertTrue(seen <= v.explored)
            self.assertEqual(new & seen, set())
            seen = set(v.explored)
            for tx, ty in v.visible:
                # paredes vizinhas de chão visível podem passar 1 tile do raio,
                # e o topo das paredes altas fica mais 1 tile acima
                self.assertTrue(any(in_radius(tx + ox - tile[0], ty + oy - tile[1], R)
                                    for ox in (-1, 0, 1) for oy in (-1, 0, 1, 2)))
        self.assertEqual(v.update(v.origin), set())   # mesmo tile: nada novo


if __name__ == "__main__":
    unittest.main()

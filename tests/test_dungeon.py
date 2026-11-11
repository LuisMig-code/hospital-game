"""Testes da geração da dungeon. Rodar: venv\\Scripts\\python.exe -m unittest discover tests"""
import sys
import unittest
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dungeon import FLOOR, generate, normalize_seed  # noqa: E402


def open_all_doors(d):
    for door in d.doors:
        door.open = True
    return d


def flood(d):
    sx, sy = d.spawn
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in seen and d.is_walkable(nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


class DungeonTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(generate(42).grid, generate(42).grid)
        self.assertEqual(generate("abc").grid, generate("abc").grid)

    def test_different_seeds(self):
        self.assertNotEqual(generate(1).grid, generate(2).grid)

    def test_string_seed(self):
        self.assertEqual(normalize_seed("123"), 123)
        self.assertEqual(normalize_seed("dungeon"), normalize_seed("dungeon"))

    def test_connected_and_bordered(self):
        for seed in range(200):
            d = open_all_doors(generate(seed))
            floor = {(x, y) for y in range(d.height) for x in range(d.width) if d.grid[y][x] == FLOOR}
            self.assertGreater(len(d.rooms), 3, seed)
            # todo chão sem móvel é alcançável (os móveis nunca fecham passagem)
            self.assertEqual(flood(d), floor - d.blocked, f"seed {seed} tem chão inalcançável")
            for x in range(d.width):
                self.assertNotEqual(d.grid[0][x], FLOOR)
                self.assertNotEqual(d.grid[d.height - 1][x], FLOOR)
            for y in range(d.height):
                self.assertNotEqual(d.grid[y][0], FLOOR)
                self.assertNotEqual(d.grid[y][d.width - 1], FLOOR)

    def test_spawn_is_in_front_of_arrival_elevator(self):
        """O spawn é a frente do elevador de chegada, na sala mais perto do
        canto de cima à esquerda (pelo caminho)."""
        from elevators import corner_floor, path_distances
        for seed in range(50):
            d = generate(seed)
            sx, sy = d.spawn
            self.assertTrue(d.is_walkable(sx, sy))
            self.assertNotIn((sx, sy), d.door_at)
            self.assertEqual((sx, sy), d.elevator_in.front[0])
            dist = path_distances(d, corner_floor(d))
            room_d = {id(r): min(dist.get((x, y), 10 ** 9) for y in range(r.y, r.y + r.h)
                                 for x in range(r.x, r.x + r.w)) for r in d.rooms}
            nearer = [r for r in d.rooms if room_d[id(r)] < room_d[id(d.elevator_in.room)]]
            from elevators import positions
            self.assertTrue(all(not positions(d, r) for r in nearer), seed)

    def test_no_one_tile_wide_passages(self):
        """Todo tile de chão faz parte de algum bloco 2x2 de chão
        (corredores e salas têm pelo menos 2 de largura; sem contar os móveis)."""
        for seed in range(200):
            d = open_all_doors(generate(seed))
            w = d.is_transparent
            for y in range(d.height):
                for x in range(d.width):
                    if not w(x, y):
                        continue
                    ok = any(w(x + ox, y + oy) and w(x + ox + 1, y + oy)
                             and w(x + ox, y + oy + 1) and w(x + ox + 1, y + oy + 1)
                             for ox in (-1, 0) for oy in (-1, 0))
                    self.assertTrue(ok, f"seed {seed}: passagem de 1 tile em ({x}, {y})")


if __name__ == "__main__":
    unittest.main()

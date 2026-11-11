"""Testes do kit médico: spawn nas salas e sprites."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from items import spawn_medkits  # noqa: E402
from sprites import load_kit_animations, load_medkit_item  # noqa: E402
from zombies import in_room, spawn_zombies  # noqa: E402


class SpawnTests(unittest.TestCase):
    def test_rules_over_many_seeds(self):
        rooms = with_kit = 0
        for seed in range(150):
            d = generate(seed)
            zombies = {z.tile for z in spawn_zombies(d, avoid=[d.spawn])}
            kits = spawn_medkits(d, avoid=[d.spawn], taken=zombies)
            for room in d.rooms:
                n = sum(1 for k in kits if in_room(room, k.tile))
                self.assertLessEqual(n, 1)                          # no máximo 1 por sala
                rooms += 1
                with_kit += n
            sx, sy = d.spawn
            for k in kits:
                x, y = k.tile
                self.assertTrue(d.is_walkable(x, y))
                self.assertNotIn(k.tile, zombies)
                self.assertGreater(max(abs(x - sx), abs(y - sy)), 2)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        self.assertNotIn((x + dx, y + dy), d.door_at)
        self.assertAlmostEqual(with_kit / rooms, S.MEDKIT_ROOM_CHANCE, delta=0.06)

    def test_deterministic(self):
        def tiles():
            d = generate(42)
            return [k.tile for k in spawn_medkits(d, avoid=[d.spawn])]
        self.assertEqual(tiles(), tiles())


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_kit_animations(self):
        anims = load_kit_animations()
        for d in ("down", "right", "left", "up"):
            self.assertEqual(len(anims[f"pickup_{d}"]), 6)
            self.assertEqual(len(anims[f"heal_{d}"]), 8)
        self.assertEqual(anims["heal_down"][-1].get_height(), S.PLAYER_SPRITE_HEIGHT)
        self.assertEqual(anims["pickup_down"][-1].get_height(), S.PLAYER_SPRITE_HEIGHT)

    def test_item_frames(self):
        frames, icon = load_medkit_item()
        self.assertEqual(len(frames), 8)
        self.assertEqual(max(f.get_width() for f in frames), S.MEDKIT_SIZE)
        self.assertLess(max(f.get_height() for f in frames), S.TILE)
        self.assertEqual(icon.get_height(), 20)


if __name__ == "__main__":
    unittest.main()

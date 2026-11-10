"""Testes do Espaço: abre/fecha porta à frente; sem porta, ataca."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from doors import SIDES  # noqa: E402
from player import Player  # noqa: E402

FACING = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}


class SpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = main.Game(42)

    def place_facing_door(self):
        """Personagem dentro da sala, olhando para a primeira porta."""
        g = self.game
        door = g.dungeon.doors[0]
        door.open = False
        (_, _), (ox, oy) = SIDES[door.side]
        x, y = door.tiles[0]
        g.player = Player(g.anims, (x - ox, y - oy))
        g.player.facing = FACING[(ox, oy)]
        return door

    def test_space_in_front_of_door_toggles_it(self):
        g = self.game
        door = self.place_facing_door()
        g.action()
        self.assertTrue(door.open)
        self.assertFalse(g.player.attack_queued)            # não ataca
        g.action()
        self.assertFalse(door.open)
        self.assertFalse(g.player.attack_queued)

    def test_space_without_door_attacks(self):
        g = self.game
        sx, sy = g.dungeon.spawn
        g.player = Player(g.anims, (sx, sy))
        g.player.facing = "down"
        front = (sx, sy + 1)
        self.assertNotIn(front, g.dungeon.door_at)
        self.assertNotIn((sx, sy), g.dungeon.door_at)
        g.action()
        self.assertTrue(g.player.attack_queued)

    def test_space_inside_open_door_does_not_attack(self):
        g = self.game
        door = self.place_facing_door()
        g.action()                                          # abre
        g.player = Player(g.anims, door.tiles[0])           # entra na porta
        g.action()                                          # não fecha (bloqueada) e não ataca
        self.assertTrue(door.open)
        self.assertFalse(g.player.attack_queued)


if __name__ == "__main__":
    unittest.main()

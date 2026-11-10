"""Testes do Espaço (porta à frente / ataque) e do game over."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
import settings as S  # noqa: E402
from doors import SIDES  # noqa: E402
from player import Player  # noqa: E402
from zombies import IDLE, Zombie  # noqa: E402

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

    def test_door_with_zombie_does_not_close(self):
        g = self.game
        door = self.place_facing_door()
        g.action()                                          # abre
        z = Zombie(door.tiles[0], None)
        z.state = IDLE
        g.horde.zombies.append(z)
        try:
            g.action()
            self.assertTrue(door.open)                      # zumbi na porta: não fecha
            self.assertFalse(g.player.attack_queued)
        finally:
            g.horde.zombies.remove(z)


class GameOverTests(unittest.TestCase):
    def test_zombie_hit_then_game_over_restarts_same_seed(self):
        g = main.Game(7)
        g.horde.zombies = []
        p = g.player
        x, y = p.tile
        z = Zombie((x + 1, y), None)
        g.zombie_hits([z])
        self.assertEqual(p.hp, S.PLAYER_HP - S.ZOMBIE_DAMAGE)
        self.assertTrue(p.hurt)
        self.assertGreater(g.hit_flash, 0)
        p.hp = S.ZOMBIE_DAMAGE                              # próximo golpe mata
        p.hurt, p.invulnerable, p.target = False, 0.0, None
        g.zombie_hits([z])
        self.assertTrue(p.dead)
        no_keys = _NoKeys()
        for _ in range(round((S.GAME_OVER_TIME - 0.2) * 60)):
            g.step(1 / 60, no_keys)
        self.assertIs(g.player, p)                          # ainda no game over
        g.draw_world(); g.draw_hit_flash(); g.draw_hud(); g.draw_game_over()
        for _ in range(round(0.4 * 60)):
            g.step(1 / 60, no_keys)
        self.assertIsNot(g.player, p)                       # recomeçou
        self.assertEqual(g.seed, 7)
        self.assertEqual(g.player.hp, S.PLAYER_HP)
        self.assertEqual(g.player.tile, g.dungeon.spawn)
        self.assertFalse(g.player.dead)


class _NoKeys:
    def __getitem__(self, k):
        return False


if __name__ == "__main__":
    unittest.main()

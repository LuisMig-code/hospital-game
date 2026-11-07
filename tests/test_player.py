"""Testes do movimento por grid e da estamina."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from player import Player, tile_center  # noqa: E402

DT = 1 / 60
ANIMS = {n: [pygame.Surface((10, 10))] * 8
         for n in ("idle", "walk_left", "walk_right", "walk_up", "walk_down")}


class Keys(dict):
    def __getitem__(self, k):
        return dict.get(self, k, False)


class OpenField:
    """Mapa sem paredes (para medir distâncias)."""
    def is_walkable(self, tx, ty):
        return True


def run(p, keys, seconds, dungeon):
    for _ in range(round(seconds / DT)):
        p.update(DT, keys, dungeon)


class PlayerTests(unittest.TestCase):
    def test_stops_aligned_and_never_enters_wall(self):
        d = generate(42)
        p = Player(ANIMS, d.spawn)
        for key in (pygame.K_d, pygame.K_s, pygame.K_a, pygame.K_w, pygame.K_d):
            for _ in range(37):  # tempo "quebrado" para soltar no meio de um passo
                p.update(DT, Keys({key: True, pygame.K_LSHIFT: key == pygame.K_s}), d)
                self.assertTrue(d.is_walkable(*p.tile))
                if p.target:
                    self.assertTrue(d.is_walkable(*p.target))
            run(p, Keys(), 0.5, d)  # solta a tecla
            self.assertIsNone(p.target)
            self.assertEqual((p.x, p.y), tile_center(p.tile))

    def test_speed_is_30_percent_faster(self):
        p = Player(ANIMS, (0, 0))
        run(p, Keys({pygame.K_d: True}), 1.0, OpenField())
        self.assertAlmostEqual(p.x - tile_center((0, 0))[0], 150 * 1.3, delta=1)

    def test_running_is_twice_as_fast(self):
        walk, sprint = Player(ANIMS, (0, 0)), Player(ANIMS, (0, 0))
        run(walk, Keys({pygame.K_d: True}), 2.0, OpenField())
        run(sprint, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 2.0, OpenField())
        start = tile_center((0, 0))[0]
        self.assertAlmostEqual((sprint.x - start) / (walk.x - start), 2.0, delta=0.02)

    def test_stamina_drain_and_regen(self):
        f = OpenField()
        p = Player(ANIMS, (0, 0))
        self.assertEqual(p.stamina, 100)
        run(p, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 1.0, f)
        self.assertAlmostEqual(p.stamina, 100 - S.STAMINA_DRAIN, delta=0.5)
        run(p, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 3.5, f)
        self.assertTrue(p.exhausted)                       # esgotou
        self.assertFalse(p.running)                        # não corre mais
        # cansado: mesmo segurando Shift não corre até recuperar o mínimo
        run(p, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 3.0, f)
        self.assertFalse(p.running)
        self.assertLess(p.stamina, S.STAMINA_RECOVER_TO_RUN)

        run(p, Keys({pygame.K_d: True}), 0.5, f)           # termina o passo
        s0 = p.stamina
        run(p, Keys({pygame.K_d: True}), 2.0, f)           # andando: +1/s
        self.assertAlmostEqual(p.stamina - s0, 2 * S.STAMINA_REGEN_WALK, delta=0.05)

        run(p, Keys(), 0.5, f)                             # para
        s0 = p.stamina
        run(p, Keys(), 2.0, f)                             # parado: +3/s
        self.assertAlmostEqual(p.stamina - s0, 2 * S.STAMINA_REGEN_IDLE, delta=0.05)

        run(p, Keys(), 100, f)
        self.assertEqual(p.stamina, S.STAMINA_MAX)         # não passa do máximo


if __name__ == "__main__":
    unittest.main()

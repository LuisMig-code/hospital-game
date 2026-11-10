"""Testes do combate: área de dano, vida e morte dos zumbis, sprite de ataque."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from combat import FloatingText, apply_attack, damage_map, texts_for  # noqa: E402
from dungeon import generate  # noqa: E402
from player import DIRS, tile_center  # noqa: E402
from sprites import is_attack_outline, load_animations, load_attack_animations  # noqa: E402
from zombies import DEAD, DYING, IDLE, UNDERGROUND, Horde, Zombie  # noqa: E402

DT = 1 / 60


class FakePlayer:
    def __init__(self, tile):
        self.tile, self.target = tile, None


class DamageMapTests(unittest.TestCase):
    def test_shape_in_all_directions(self):
        player = (10, 10)
        for d, (dx, dy) in DIRS.items():
            impact = (10 + dx, 10 + dy)
            dmg = damage_map(impact, player)
            self.assertEqual(dmg[impact], 11, d)
            self.assertNotIn(player, dmg, d)                        # não se acerta
            ring1 = [t for t, v in dmg.items() if v == 6]
            ring2 = [t for t, v in dmg.items() if v == 4]
            self.assertEqual(len(ring1), 8 - 1, d)                  # 8 vizinhos menos o personagem
            self.assertEqual(len(ring2), 16 - 5, d)                 # sem a fileira a 3 tiles à frente
            for t in ring1:
                self.assertEqual(max(abs(t[0] - impact[0]), abs(t[1] - impact[1])), 1)
            for t in ring2:
                self.assertEqual(max(abs(t[0] - impact[0]), abs(t[1] - impact[1])), 2)
            self.assertEqual(len(dmg), 1 + 7 + 11)                  # nada além de 2 tiles do impacto
            for t in dmg:                                           # nem além de 2 tiles à frente
                self.assertLessEqual((t[0] - 10) * dx + (t[1] - 10) * dy, S.ATTACK_REACH)

    def test_example_from_spec(self):
        dmg = damage_map((10, 9), (10, 10))   # olhando para cima
        self.assertEqual(dmg[(10, 9)], 11)
        self.assertEqual(dmg[(9, 9)], 6)
        self.assertEqual(dmg[(11, 10)], 6)    # ao lado do personagem, colado no impacto
        self.assertEqual(dmg[(10, 8)], 6)     # 2 tiles à frente: ainda alcança
        self.assertEqual(dmg[(8, 8)], 4)
        self.assertEqual(dmg[(8, 11)], 4)     # atrás, na diagonal
        self.assertNotIn((10, 7), dmg)        # 3 tiles à frente: fora do alcance
        self.assertNotIn((8, 7), dmg)


class ApplyAttackTests(unittest.TestCase):
    def setUp(self):
        self.d = generate(42)
        self.horde = Horde(self.d, avoid=[self.d.spawn])
        room = max(self.d.rooms, key=lambda r: r.w * r.h)
        self.room = room
        cx, cy = room.x + room.w // 2, room.y + room.h // 2
        self.player = FakePlayer((cx, cy + 1))
        self.impact = (cx, cy)
        self.horde.zombies = []
        self.visible = {(x, y) for x in range(cx - 4, cx + 5) for y in range(cy - 4, cy + 5)}

    def add(self, tile, state=IDLE):
        z = Zombie(tile, self.room)
        z.state = state
        self.horde.zombies.append(z)
        return z

    def test_damage_by_distance(self):
        ix, iy = self.impact
        a = self.add((ix, iy))            # impacto: 11 -> morre
        b = self.add((ix + 1, iy - 1))    # colado: 6 -> fica com 4
        c = self.add((ix - 2, iy - 1))    # a 2: 4 -> fica com 6
        out = self.add((ix, iy - 2))      # 3 à frente do personagem: fora do alcance
        far = self.add((ix + 3, iy))      # fora da área
        hits = apply_attack(self.horde, self.impact, self.player.tile, self.visible)
        self.assertEqual({(id(z), dmg, died) for z, dmg, died in hits},
                         {(id(a), 11, True), (id(b), 6, False), (id(c), 4, False)})
        self.assertEqual((a.state, a.hp), (DYING, 0))
        self.assertEqual((b.state, b.hp), (IDLE, 4))
        self.assertEqual((c.state, c.hp), (IDLE, 6))
        self.assertEqual(far.hp, S.ZOMBIE_HP)
        self.assertEqual(out.hp, S.ZOMBIE_HP)

    def test_six_plus_four_kills(self):
        ix, iy = self.impact
        z = self.add((ix + 1, iy))
        apply_attack(self.horde, self.impact, self.player.tile, self.visible)            # -6
        self.assertEqual(z.hp, 4)
        apply_attack(self.horde, (ix - 1, iy), (ix - 1, iy + 1), self.visible)           # a 2: -4
        self.assertEqual(z.state, DYING)

    def test_who_is_not_hit(self):
        ix, iy = self.impact
        buried = self.add((ix, iy), state=UNDERGROUND)
        hidden = self.add((ix + 1, iy))
        dying = self.add((ix - 1, iy), state=DYING)
        visible = self.visible - {hidden.tile}           # atrás de parede, por exemplo
        hits = apply_attack(self.horde, self.impact, self.player.tile, visible)
        self.assertEqual(hits, [])
        self.assertEqual((buried.hp, hidden.hp, dying.hp), (S.ZOMBIE_HP,) * 3)

    def test_dying_sinks_stops_blocking_and_is_counted(self):
        ix, iy = self.impact
        z = self.add((ix, iy))
        apply_attack(self.horde, self.impact, self.player.tile, self.visible)
        self.assertNotIn(z.tile, self.horde.blocked_tiles())     # morrendo não bloqueia
        self.assertIn(z, self.horde.active())                    # mas ainda aparece (afundando)
        frames = []
        for _ in range(round(1.0 / DT)):
            self.horde.update(DT, self.player, self.visible)
            if z.state == DYING:
                frames.append(z.frame)
        self.assertEqual(frames, sorted(frames, reverse=True))   # surgir ao contrário
        self.assertEqual(frames[0], 7)
        self.assertEqual(z.state, DEAD)
        self.assertNotIn(z, self.horde.zombies)
        self.assertEqual(self.horde.killed, 1)

    def test_hit_feedback_timers(self):
        ix, iy = self.impact
        z = self.add((ix + 1, iy))
        apply_attack(self.horde, self.impact, self.player.tile, self.visible)
        self.assertGreater(z.flash, 0)
        self.assertGreater(z.hp_bar, 0)
        for _ in range(round((S.HP_BAR_TIME + 0.1) / DT)):
            z.update(DT, self.d, set(), self.horde.rng)
        self.assertEqual((z.flash, z.hp_bar), (0, 0))

    def test_damage_texts(self):
        ix, iy = self.impact
        self.add((ix, iy))
        self.add((ix + 2, iy))
        texts = texts_for(apply_attack(self.horde, self.impact, self.player.tile, self.visible))
        self.assertEqual(sorted(t.text for t in texts), ["-11", "-4"])
        t = texts[0]
        y0 = t.y
        t.update(S.DAMAGE_TEXT_TIME / 2)
        self.assertLess(t.y, y0)                                 # sobe
        t.update(S.DAMAGE_TEXT_TIME)
        self.assertTrue(t.done)
        self.assertEqual(FloatingText(0, 0, "x", (0, 0, 0)).alpha, 255)


class AttackSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.idle_h = load_animations()["idle"][0].get_height()
        cls.anims = load_attack_animations(target_height=cls.idle_h)

    def test_frames(self):
        for d in DIRS:
            frames = self.anims[f"attack_{d}"]
            self.assertEqual(len(frames), 9)
            self.assertLessEqual(abs(frames[0].get_height() - self.idle_h), 2)

    def test_left_is_mirror_of_right(self):
        for r, l in zip(self.anims["attack_right"], self.anims["attack_left"]):
            flipped = pygame.transform.flip(r, True, False)
            self.assertEqual(pygame.image.tobytes(flipped, "RGBA"), pygame.image.tobytes(l, "RGBA"))

    def test_no_magenta_outline_left(self):
        raw = load_attack_animations(raw=True)
        for frames in raw.values():
            for img in frames:
                w, h = img.get_size()
                bad = sum(1 for y in range(0, h, 2) for x in range(0, w, 2)
                          if img.get_at((x, y)).a > 40 and is_attack_outline(img.get_at((x, y)))
                          and max(img.get_at((x, y)).r, img.get_at((x, y)).b) > 90)
                self.assertEqual(bad, 0)


if __name__ == "__main__":
    unittest.main()

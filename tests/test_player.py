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
        p.facing = "right"                                   # já virado: anda na hora
        run(p, Keys({pygame.K_d: True}), 1.0, OpenField())
        self.assertAlmostEqual(p.x - tile_center((0, 0))[0], 150 * 1.3, delta=1)

    def test_running_is_twice_as_fast(self):
        walk, sprint = Player(ANIMS, (0, 0)), Player(ANIMS, (0, 0))
        walk.facing = sprint.facing = "right"
        run(walk, Keys({pygame.K_d: True}), 2.0, OpenField())
        run(sprint, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 2.0, OpenField())
        start = tile_center((0, 0))[0]
        self.assertAlmostEqual((sprint.x - start) / (walk.x - start), 2.0, delta=0.02)

    def test_stamina_drain_and_regen(self):
        f = OpenField()
        p = Player(ANIMS, (0, 0))
        p.facing = "right"
        self.assertEqual(p.stamina, 100)
        run(p, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 1.0, f)
        self.assertAlmostEqual(p.stamina, 100 - S.STAMINA_DRAIN, delta=0.5)
        run(p, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), 3.5, f)
        self.assertTrue(p.exhausted)                       # esgotou
        self.assertFalse(p.running)                        # não corre mais
        # cansado: mesmo segurando Shift não corre até recuperar o mínimo
        # tempo para recuperar só 80% do que falta até poder correr de novo
        tired = 0.8 * (S.STAMINA_RECOVER_TO_RUN - p.stamina) / S.STAMINA_REGEN_WALK
        run(p, Keys({pygame.K_d: True, pygame.K_LSHIFT: True}), tired, f)
        self.assertFalse(p.running)
        self.assertLess(p.stamina, S.STAMINA_RECOVER_TO_RUN)

        run(p, Keys({pygame.K_d: True}), 0.5, f)           # termina o passo
        s0 = p.stamina
        run(p, Keys({pygame.K_d: True}), 2.0, f)           # andando: +STAMINA_REGEN_WALK/s
        self.assertAlmostEqual(p.stamina - s0, 2 * S.STAMINA_REGEN_WALK, delta=0.05)

        run(p, Keys(), 0.5, f)                             # para
        s0 = p.stamina
        run(p, Keys(), 2.0, f)                             # parado: +STAMINA_REGEN_IDLE/s
        self.assertAlmostEqual(p.stamina - s0, 2 * S.STAMINA_REGEN_IDLE, delta=0.05)

        run(p, Keys(), 100, f)
        self.assertEqual(p.stamina, S.STAMINA_MAX)         # não passa do máximo


class Grid:
    """Mapa pequeno a partir de strings: '.' chão, '#' parede."""
    def __init__(self, rows):
        self.rows = rows

    def is_walkable(self, tx, ty):
        return 0 <= ty < len(self.rows) and 0 <= tx < len(self.rows[0]) and self.rows[ty][tx] == "."


UP_LEFT = Keys({pygame.K_w: True, pygame.K_a: True})


class DiagonalTests(unittest.TestCase):
    def walk_one(self, p, keys, dungeon, blocked=frozenset()):
        """Anda até chegar no próximo tile e solta."""
        p.update(DT, keys, dungeon, blocked)
        for _ in range(200):
            if p.target is None:
                break
            p.update(DT, Keys(), dungeon, blocked)
        return p.tile

    def test_up_left_moves_diagonally_and_aligns(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "left"
        p.update(DT, UP_LEFT, OpenField())
        self.assertEqual(p.target, (4, 4))
        self.assertEqual(p.facing, "left")                          # sprite horizontal
        p.update(DT, UP_LEFT, OpenField())
        self.assertEqual(p.anim, "walk_left")
        run(p, Keys(), 1.0, OpenField())
        self.assertEqual(p.tile, (4, 4))
        self.assertEqual((p.x, p.y), tile_center((4, 4)))

    def test_all_four_diagonals(self):
        for keys, step in (({pygame.K_w: 1, pygame.K_d: 1}, (1, -1)), ({pygame.K_s: 1, pygame.K_d: 1}, (1, 1)),
                           ({pygame.K_s: 1, pygame.K_a: 1}, (-1, 1)), ({pygame.K_w: 1, pygame.K_a: 1}, (-1, -1))):
            p = Player(ANIMS, (5, 5))
            p.facing = "right" if step[0] > 0 else "left"
            self.assertEqual(self.walk_one(p, Keys(keys), OpenField()), (5 + step[0], 5 + step[1]))

    def test_same_speed_in_pixels(self):
        p = Player(ANIMS, (0, 0))
        p.facing = "left"
        start = (p.x, p.y)
        for _ in range(round(1.0 / DT)):
            p.update(DT, UP_LEFT, OpenField())
        dist = ((p.x - start[0]) ** 2 + (p.y - start[1]) ** 2) ** 0.5
        self.assertAlmostEqual(dist, S.PLAYER_SPEED, delta=3)       # não 195·√2

    def test_slides_along_wall(self):
        g = Grid(["....",
                  "#...",
                  "#...",
                  "#..."])
        p = Player(ANIMS, (1, 2))
        p.facing = "left"
        self.assertEqual(self.walk_one(p, UP_LEFT, g), (1, 1))      # parede à esquerda: sobe
        self.assertEqual(p.facing, "up")

    def test_does_not_cut_corners(self):
        # parede só no tile reto de cima: não corta a quina; vai para a esquerda
        g = Grid(["....",
                  "..#.",
                  "....",
                  "...."])
        p = Player(ANIMS, (2, 2))
        p.facing = "left"
        self.assertEqual(self.walk_one(p, UP_LEFT, g), (1, 2))
        # parede só no tile diagonal: também não vai na diagonal
        g = Grid(["....",
                  ".#..",
                  "....",
                  "...."])
        p = Player(ANIMS, (2, 2))
        p.facing = "left"
        self.assertEqual(self.walk_one(p, UP_LEFT, g), (1, 2))      # desliza: horizontal primeiro

    def test_zombies(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "left"
        self.assertEqual(self.walk_one(p, UP_LEFT, OpenField(), blocked={(4, 4)}), (4, 5))   # diagonal ocupada
        p = Player(ANIMS, (5, 5))
        p.facing = "left"
        self.assertEqual(self.walk_one(p, UP_LEFT, OpenField(), blocked={(4, 5), (5, 4)}), (4, 4))

    def test_opposite_keys_cancel(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "up"
        p.update(DT, Keys({pygame.K_a: True, pygame.K_d: True, pygame.K_w: True}), OpenField())
        self.assertEqual(p.target, (5, 4))
        p = Player(ANIMS, (5, 5))
        p.update(DT, Keys({pygame.K_a: True, pygame.K_d: True}), OpenField())
        self.assertIsNone(p.target)

    def test_turn_rule(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "up"                                             # já olha para um dos lados
        p.update(DT, UP_LEFT, OpenField())
        self.assertEqual(p.target, (4, 4))
        p = Player(ANIMS, (5, 5))                                   # olhando para baixo
        p.update(DT, UP_LEFT, OpenField())
        self.assertEqual((p.target, p.facing), (None, "left"))     # primeiro só vira

    def test_never_enters_wall_with_diagonals(self):
        d = generate(7)
        p = Player(ANIMS, d.spawn)
        combos = [{pygame.K_d: 1, pygame.K_s: 1}, {pygame.K_d: 1, pygame.K_w: 1},
                  {pygame.K_a: 1, pygame.K_s: 1}, {pygame.K_a: 1, pygame.K_w: 1}, {pygame.K_s: 1}]
        for keys in combos * 3:
            for _ in range(53):
                p.update(DT, Keys(keys), d)
                self.assertTrue(d.is_walkable(*p.tile))
                if p.target:
                    self.assertTrue(d.is_walkable(*p.target))
                    tx, ty = p.target
                    if tx != p.tile[0] and ty != p.tile[1]:          # diagonal: sem cortar quina
                        self.assertTrue(d.is_walkable(tx, p.tile[1]) and d.is_walkable(p.tile[0], ty))
            run(p, Keys(), 0.6, d)
            self.assertEqual((p.x, p.y), tile_center(p.tile))


class TurnTests(unittest.TestCase):
    def test_tap_only_turns(self):
        p = Player(ANIMS, (5, 5))                                   # começa olhando para baixo
        run(p, Keys({pygame.K_d: True}), 2 * DT, OpenField())       # toque rápido
        run(p, Keys(), 0.5, OpenField())
        self.assertEqual((p.facing, p.tile, p.target), ("right", (5, 5), None))

    def test_hold_turns_then_walks(self):
        p = Player(ANIMS, (5, 5))
        keys = Keys({pygame.K_d: True})
        p.update(DT, keys, OpenField())
        self.assertEqual((p.facing, p.target), ("right", None))     # primeiro só vira
        t = DT
        while p.target is None and t < 1:
            p.update(DT, keys, OpenField())
            t += DT
        self.assertEqual(p.target, (6, 5))                          # segurando, anda
        self.assertAlmostEqual(t, S.TURN_DELAY, delta=2 * DT)

    def test_same_direction_walks_immediately(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "right"
        p.update(DT, Keys({pygame.K_d: True}), OpenField())
        self.assertIsNotNone(p.target)

    def test_changing_direction_while_walking_has_no_pause(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "right"
        run(p, Keys({pygame.K_d: True}), 0.1, OpenField())          # andando para a direita
        self.assertEqual(p.target, (6, 5))
        while p.target == (6, 5):                                   # troca para baixo no meio
            p.update(DT, Keys({pygame.K_s: True}), OpenField())
        self.assertEqual(p.target, (6, 6))                          # ao chegar já segue para baixo


class IdleFacingTests(unittest.TestCase):
    def test_keeps_facing_when_stopping(self):
        anims = dict(ANIMS, **{f"idle_{d}": [pygame.Surface((10, 10))] for d in ("right", "left", "up")})
        for key, d in ((pygame.K_d, "right"), (pygame.K_a, "left"), (pygame.K_w, "up"), (pygame.K_s, "down")):
            p = Player(anims, (5, 5))
            run(p, Keys({key: True}), 0.3, OpenField())    # anda um pouco
            run(p, Keys(), 0.5, OpenField())               # solta e para
            self.assertEqual(p.facing, d)
            self.assertEqual(p.anim, "idle" if d == "down" else f"idle_{d}")

    def test_real_sprites_have_side_idles(self):
        pygame.init()
        from sprites import load_animations
        a = load_animations()
        for d in ("right", "left", "up"):
            self.assertIs(a[f"idle_{d}"][0], a[f"walk_{d}"][0])


class AttackTests(unittest.TestCase):
    ATTACK_TIME = 9 / S.ATTACK_FPS

    def test_hit_once_at_hit_frame_with_front_tile(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "up"
        p.request_attack()
        hits = []
        t = 0.0
        for _ in range(round((self.ATTACK_TIME + 0.2) / DT)):
            hit = p.update(DT, Keys(), OpenField())
            t += DT
            if hit is not None:
                hits.append((round(t, 3), hit))
        self.assertEqual(len(hits), 1)                              # uma vez só
        self.assertEqual(hits[0][1], (5, 4))                        # tile à frente
        hit_time = hits[0][0]
        self.assertGreaterEqual(hit_time, S.ATTACK_HIT_FRAME / S.ATTACK_FPS)
        self.assertLess(hit_time, (S.ATTACK_HIT_FRAME + 1) / S.ATTACK_FPS + DT)
        self.assertFalse(p.attacking)

    def test_attack_locks_movement_and_facing(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "right"
        p.request_attack()
        keys = Keys({pygame.K_s: True})                             # tenta andar para baixo
        for _ in range(round(self.ATTACK_TIME * 0.8 / DT)):
            p.update(DT, keys, OpenField())
            self.assertEqual((p.tile, p.target, p.facing), ((5, 5), None, "right"))
            self.assertEqual(p.anim, "attack_right")
        run(p, keys, self.ATTACK_TIME, OpenField())                 # acabou: volta a andar
        self.assertNotEqual(p.tile, (5, 5))

    def test_attack_requested_mid_step_starts_on_arrival(self):
        p = Player(ANIMS, (5, 5))
        p.facing = "right"
        keys = Keys({pygame.K_d: True})
        p.update(DT, keys, OpenField())                             # começa a andar
        self.assertEqual(p.target, (6, 5))
        p.request_attack()
        hit = None
        for _ in range(round(1.0 / DT)):                            # segurando a tecla
            hit = p.update(DT, keys, OpenField()) or hit
            if p.attacking or hit:
                break
        self.assertEqual(p.tile, (6, 5))                            # parou no tile seguinte
        self.assertIsNone(p.target)
        self.assertTrue(p.attacking)

    def test_no_stacking(self):
        p = Player(ANIMS, (5, 5))
        p.request_attack()
        p.update(DT, Keys(), OpenField())
        for _ in range(5):
            p.request_attack()                                      # ignorados durante o ataque
        hits = [h for _ in range(round(3 * self.ATTACK_TIME / DT))
                if (h := p.update(DT, Keys(), OpenField())) is not None]
        self.assertEqual(len(hits), 1)


HURT_ANIMS = dict(ANIMS)
for _d in ("right", "left", "up", "down"):
    HURT_ANIMS[f"hurt_{_d}"] = [pygame.Surface((10, 10))] * 6
    HURT_ANIMS[f"hurt_light_{_d}"] = [pygame.Surface((10, 10))] * 4
HURT_TIME = 6 / S.HURT_FPS


class HitTests(unittest.TestCase):
    """Golpe de zumbi: vida, empurrão para o lado oposto, invulnerabilidade, morte."""

    def hit(self, p, source, dungeon=None, blocked=frozenset()):
        return p.take_hit(S.ZOMBIE_DAMAGE, source, dungeon or OpenField(), blocked)

    def settle(self, p, dungeon=None, keys=None):
        run(p, keys or Keys(), HURT_TIME + 0.05, dungeon or OpenField())

    def test_damage_and_straight_push(self):
        p = Player(HURT_ANIMS, (5, 5))
        self.assertEqual(p.hp, S.PLAYER_HP)
        self.assertTrue(self.hit(p, (6, 5)))                       # zumbi à direita
        self.assertEqual(p.hp, S.PLAYER_HP - S.ZOMBIE_DAMAGE)
        self.assertEqual(p.facing, "right")                        # olha para o zumbi
        self.assertEqual(p.anim, "hurt_right")
        self.assertEqual(p.target, (4, 5))                         # empurrado para a esquerda
        run(p, Keys(), S.KNOCKBACK_TIME + DT, OpenField())
        self.assertEqual((p.tile, p.target), ((4, 5), None))
        self.assertEqual((p.x, p.y), tile_center((4, 5)))

    def test_diagonal_push(self):
        p = Player(HURT_ANIMS, (5, 5))
        self.hit(p, (6, 6))                                        # zumbi embaixo à direita
        self.settle(p)
        self.assertEqual(p.tile, (4, 4))

    def test_wall_behind_no_push_uses_light_hurt(self):
        g = Grid(["#####",
                  "#...#",
                  "#####"])
        p = Player(HURT_ANIMS, (1, 1))
        self.hit(p, (2, 1), g)                                     # parede atrás (à esquerda)
        self.assertIsNone(p.target)
        self.assertEqual(p.anim, "hurt_light_right")
        self.settle(p, g)
        self.assertEqual(p.tile, (1, 1))

    def test_diagonal_push_slides_when_blocked(self):
        g = Grid(["#####",
                  "#...#",
                  "#...#",
                  "#####"])
        p = Player(HURT_ANIMS, (1, 2))
        self.hit(p, (2, 1), g)                       # recuar para (0,3), (0,2) ou (1,3): tudo parede
        self.assertIsNone(p.target)
        p = Player(HURT_ANIMS, (2, 1))
        self.hit(p, (3, 2), g)                       # diagonal (1,0) é parede; desliza no eixo x
        self.assertEqual(p.target, (1, 1))

    def test_zombie_behind_blocks_push(self):
        p = Player(HURT_ANIMS, (5, 5))
        self.hit(p, (6, 5), blocked={(4, 5)})
        self.assertIsNone(p.target)

    def test_mid_step_starts_from_drawn_tile(self):
        p = Player(HURT_ANIMS, (5, 5))
        p.facing = "right"
        run(p, Keys({pygame.K_d: True}), 0.12, OpenField())      # passou da metade do passo
        self.assertEqual((p.tile, p.target), ((5, 5), (6, 5)))
        self.hit(p, (7, 5))
        self.assertEqual(p.target, (5, 5))                         # de (6,5) volta para (5,5)
        self.settle(p)
        self.assertEqual(p.tile, (5, 5))

    def test_cancels_attack_and_locks_controls(self):
        p = Player(HURT_ANIMS, (5, 5))
        p.request_attack()
        p.update(DT, Keys(), OpenField())
        self.assertTrue(p.attacking)
        self.hit(p, (5, 6))
        self.assertFalse(p.attacking or p.attack_queued)
        keys = Keys({pygame.K_s: True, pygame.K_LSHIFT: True})
        for _ in range(round((HURT_TIME - 0.05) / DT)):
            self.assertIsNone(p.update(DT, keys, OpenField()))     # sem golpe
            self.assertTrue(p.hurt)
            self.assertIn(p.tile, {(5, 5), (5, 4)})                # só o empurrão
        run(p, keys, 0.6, OpenField())                             # acabou: volta a andar
        self.assertFalse(p.hurt)
        self.assertGreater(p.tile[1], 5)

    def test_invulnerable_then_vulnerable(self):
        p = Player(HURT_ANIMS, (5, 5))
        self.hit(p, (6, 5))
        self.assertFalse(self.hit(p, (6, 5)))                      # durante o dano
        self.settle(p)
        self.assertFalse(p.hurt)
        self.assertGreater(p.invulnerable, 0)
        self.assertFalse(self.hit(p, (5, 5)))                      # piscando
        run(p, Keys(), S.PLAYER_INVULN_TIME, OpenField())
        self.assertEqual(p.invulnerable, 0)
        self.assertTrue(self.hit(p, (5, 5)))
        self.assertEqual(p.hp, S.PLAYER_HP - 2 * S.ZOMBIE_DAMAGE)

    def test_death(self):
        p = Player(HURT_ANIMS, (5, 5))
        p.hp = S.ZOMBIE_DAMAGE
        self.hit(p, (6, 5))
        self.assertEqual(p.hp, 0)
        self.assertTrue(p.dead)
        self.assertEqual(p.anim, "hurt_right")                     # cai com o empurrão
        run(p, Keys({pygame.K_s: True}), 3.0, OpenField())
        self.assertTrue(p.dead and p.hurt)                         # fica caído, sem controle
        self.assertEqual(p.frame, 4)                               # quadro "caído"
        self.assertEqual(p.tile, (4, 5))
        self.assertFalse(self.hit(p, (3, 5)))                      # morto não leva golpe


class DamageSpriteTests(unittest.TestCase):
    def test_frames(self):
        from sprites import load_damage_animations
        pygame.init()
        anims = load_damage_animations()
        for d in ("right", "left", "up", "down"):
            self.assertEqual(len(anims[f"hurt_{d}"]), 6)
            self.assertEqual(len(anims[f"hurt_light_{d}"]), 4)
        self.assertEqual(anims["hurt_down"][-1].get_height(), S.PLAYER_SPRITE_HEIGHT)


if __name__ == "__main__":
    unittest.main()

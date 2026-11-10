"""Testes dos zumbis: spawn, surgimento, vagar e colisão."""
import os
import random
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from player import Player  # noqa: E402
from sprites import ZOMBIE_ROWS, is_magenta, load_zombie_animations  # noqa: E402
from dungeon import Room  # noqa: E402
from zombies import (CHASE, DYING, EMERGING, IDLE, UNDERGROUND, WALK, Horde, Zombie,  # noqa: E402
                     chebyshev, in_room, spawn_zombies)

DT = 1 / 60
ANIMS = {n: [pygame.Surface((10, 10))] * 8
         for n in ("idle", "walk_left", "walk_right", "walk_up", "walk_down")}


class Keys(dict):
    def __getitem__(self, k):
        return dict.get(self, k, False)


class SpawnTests(unittest.TestCase):
    def test_per_room_count_and_placement(self):
        lo, hi = S.ZOMBIES_PER_ROOM
        for seed in range(60):
            d = generate(seed)
            zs = spawn_zombies(d, avoid=[d.spawn])
            tiles = [z.tile for z in zs]
            self.assertEqual(len(tiles), len(set(tiles)), seed)          # tiles distintos
            for room in d.rooms:
                n = sum(1 for z in zs if z.room is room)
                self.assertLessEqual(n, hi)
                if room.w * room.h >= 49:                                 # sala com espaço
                    self.assertGreaterEqual(n, lo, (seed, room))
            for z in zs:
                self.assertTrue(in_room(z.room, z.tile))
                self.assertTrue(d.is_walkable(*z.tile))
                self.assertEqual(z.state, UNDERGROUND)
                sx, sy = d.spawn
                self.assertGreater(max(abs(z.tile[0] - sx), abs(z.tile[1] - sy)), 2)

    def test_deterministic(self):
        a = [z.tile for z in spawn_zombies(generate(42), [generate(42).spawn])]
        b = [z.tile for z in spawn_zombies(generate(42), [generate(42).spawn])]
        self.assertEqual(a, b)


class BehaviourTests(unittest.TestCase):
    def setUp(self):
        self.d = generate(42)
        self.horde = Horde(self.d, avoid=[self.d.spawn])
        room = max(self.d.rooms, key=lambda r: r.w * r.h)
        self.room = room
        self.zs = [z for z in self.horde.zombies if z.room is room]
        self.player = Player(ANIMS, (-50, -50))     # longe: os zumbis só vagam
        self.room_tiles = {(x, y) for y in range(room.y, room.y + room.h)
                           for x in range(room.x, room.x + room.w)}

    diagonal_steps = 0

    def run_for(self, seconds, visible):
        for _ in range(round(seconds / DT)):
            self.horde.update(DT, self.player, visible)
            self.check_invariants()

    def check_invariants(self):
        occ = {}
        p_occ = {self.player.tile} | ({self.player.target} if self.player.target else set())
        for z in self.horde.active():
            self.assertTrue(in_room(z.room, z.tile))
            if z.target:
                self.assertTrue(in_room(z.room, z.target))
                self.assertTrue(self.d.is_walkable(*z.target))
                (x, y), (tx, ty) = z.tile, z.target
                self.assertLessEqual(max(abs(tx - x), abs(ty - y)), 1)       # vizinho (reto ou diagonal)
                if tx != x and ty != y:                                     # diagonal: sem cortar quina
                    for t in ((tx, y), (x, ty)):
                        self.assertTrue(in_room(z.room, t) and self.d.is_walkable(*t))
                    self.diagonal_steps += 1
            for t in z.occupied():
                self.assertNotIn(t, occ, "dois zumbis no mesmo tile")
                self.assertNotIn(t, p_occ, "zumbi no tile do personagem")
                occ[t] = z

    def test_stay_buried_until_seen_then_emerge(self):
        self.run_for(2, visible=set())
        self.assertTrue(all(z.state == UNDERGROUND for z in self.horde.zombies))
        self.run_for(DT, visible=self.room_tiles)
        self.assertTrue(all(z.state == EMERGING for z in self.zs))
        emerge_time = len(load_frames("emerge")) / S.ZOMBIE_EMERGE_FPS
        self.run_for(emerge_time + 0.1, visible=self.room_tiles)
        self.assertTrue(all(z.state in (IDLE, WALK) for z in self.zs))
        # zumbis de outras salas (não vistas) continuam enterrados
        others = [z for z in self.horde.zombies if z.room is not self.room]
        self.assertTrue(all(z.state == UNDERGROUND for z in others))

    def test_wander_inside_room_without_waiting(self):
        """Com ZOMBIE_IDLE_TIME = 0 emendam uma caminhada na outra: só param
        um instante entre caminhadas (ou um pouco mais se estiverem cercados)."""
        start = {id(z): z.tile for z in self.zs}
        stints = {id(z): 0.0 for z in self.zs}
        longest = 0.0
        for _ in range(round(30 / DT)):
            self.horde.update(DT, self.player, self.room_tiles)
            self.check_invariants()
            for z in self.zs:
                if z.state == IDLE:
                    stints[id(z)] += DT
                    longest = max(longest, stints[id(z)])
                else:
                    stints[id(z)] = 0.0
        for z in self.zs:
            total = z.time_in[IDLE] + z.time_in[WALK]
            self.assertGreater(z.time_in[WALK] / total, 0.9)    # quase sempre andando
        self.assertLessEqual(longest, 0.3 + 2 * DT)             # pior caso: cercado
        moved = sum(1 for z in self.zs if z.tile != start[id(z)])
        self.assertGreaterEqual(moved, len(self.zs) // 2)

    def test_walk_diagonally_too(self):
        self.run_for(30, visible=self.room_tiles)
        self.assertGreater(self.diagonal_steps, 0)                  # também andam na diagonal
        for z in self.zs:
            if z.state == WALK and z.move[0] and z.move[1]:
                self.assertEqual(z.facing, "right" if z.move[0] > 0 else "left")   # sprite horizontal

    def test_diagonal_same_pixel_speed(self):
        z = self.zs[0]
        z.wake()
        z.state, z.move, z.steps_left = WALK, (1, 1), 1
        z.tile = (5, 5)
        z.x, z.y = 5 * S.TILE + 16, 5 * S.TILE + 16
        z.target = (6, 6)
        x0, y0 = z.x, z.y
        z.update(0.1, OpenRoomDungeon(), set(), self.horde.rng)
        moved = ((z.x - x0) ** 2 + (z.y - y0) ** 2) ** 0.5
        self.assertAlmostEqual(moved, S.ZOMBIE_SPEED * 0.1, delta=0.01)

    def test_player_blocked_by_active_zombie_not_buried(self):
        z = self.zs[0]
        x, y = z.tile
        # personagem logo à esquerda do zumbi, andando para a direita
        self.player = Player(ANIMS, (x - 1, y)) if self.d.is_walkable(x - 1, y) else Player(ANIMS, (x + 1, y))
        key = pygame.K_d if self.player.tile[0] < x else pygame.K_a
        self.player.facing = "right" if key == pygame.K_d else "left"   # já virado: anda na hora
        # enterrado: não bloqueia
        self.player.update(DT, Keys({key: True}), self.d, blocked=self.horde.blocked_tiles())
        self.assertEqual(self.player.target, z.tile)
        # fora do chão: bloqueia
        self.player = Player(ANIMS, self.player.tile)
        self.player.facing = "right" if key == pygame.K_d else "left"
        z.wake()
        self.player.update(DT, Keys({key: True}), self.d, blocked=self.horde.blocked_tiles())
        self.assertIsNone(self.player.target)

    def test_does_not_wake_under_player(self):
        z = self.zs[0]
        self.player = Player(ANIMS, z.tile)
        self.horde.update(DT, self.player, {z.tile})
        self.assertEqual(z.state, UNDERGROUND)

    def test_chase_and_attack_in_real_dungeon(self):
        """Personagem parado na sala: os zumbis perto vão até ele e batem,
        sem nunca entrar no tile dele nem um no outro."""
        taken = {z.tile for z in self.horde.zombies}
        zx, zy = self.zs[0].tile
        near = next(t for t in self.room_tiles
                    if chebyshev(t, (zx, zy)) == 2 and self.d.is_walkable(*t) and t not in taken)
        self.player = Player(ANIMS, near)                  # a 2 tiles de um zumbi
        hits = 0
        for _ in range(round(15 / DT)):
            hits += len(self.horde.update(DT, self.player, self.room_tiles))
            occ = set()
            for z in self.horde.active():
                if z.target:
                    (x, y), (tx, ty) = z.tile, z.target
                    self.assertLessEqual(chebyshev(z.tile, z.target), 1)
                    self.assertTrue(self.d.is_walkable(tx, ty))
                    if tx != x and ty != y:
                        self.assertTrue(self.d.is_walkable(tx, y) and self.d.is_walkable(x, ty))
                for t in z.occupied():
                    self.assertNotIn(t, occ, "dois zumbis no mesmo tile")
                    self.assertNotEqual(t, self.player.tile, "zumbi no tile do personagem")
                    occ.add(t)
        self.assertGreater(hits, 0)
        self.assertTrue(any(z.state == CHASE for z in self.zs))


class OpenRoomDungeon:
    def is_walkable(self, tx, ty):
        return True


class MapDungeon:
    """Mapa pequeno a partir de strings: '.' chão, '#' parede, 'D' porta
    aberta, 'd' porta fechada. `rooms`: retângulos (x, y, w, h) das salas."""
    def __init__(self, rows, rooms):
        self.rows = rows
        self.rooms = [Room(*r) for r in rooms]
        self.door_at = {(x, y): True for y, r in enumerate(rows) for x, c in enumerate(r) if c in "Dd"}

    def is_walkable(self, tx, ty):
        return (0 <= ty < len(self.rows) and 0 <= tx < len(self.rows[0])
                and self.rows[ty][tx] in ".D")


def open_room(w):
    return MapDungeon(["#" * (w + 2)] + ["#" + "." * w + "#"] * 3 + ["#" * (w + 2)], [(1, 1, w, 3)])


TWO_ROOMS = ["###########",
             "#....#....#",
             "#....D....#",
             "#....#....#",
             "###########"]
ROOMS = [(1, 1, 4, 3), (6, 1, 4, 3)]


class ChaseTests(unittest.TestCase):
    """Perseguição e golpe dos zumbis (personagem parado num tile)."""

    def setUp(self):
        self.rng = random.Random(1)

    def zombie(self, d, tile):
        z = Zombie(tile, next(r for r in d.rooms if in_room(r, tile)))
        z.state = IDLE
        return z

    def simulate(self, z, d, player_tile, seconds):
        """Roda o zumbi; devolve os instantes dos golpes. Confere cada passo."""
        hits, t = [], 0.0
        for _ in range(round(seconds / DT)):
            t += DT
            if z.update(DT, d, {player_tile}, self.rng, player_tile):
                hits.append(t)
            if z.target:
                self.assertTrue(d.is_walkable(*z.target))
                self.assertNotEqual(z.target, player_tile)
                (x, y), (tx, ty) = z.tile, z.target
                self.assertLessEqual(chebyshev(z.tile, z.target), 1)
                if tx != x and ty != y:                                   # sem cortar quina
                    self.assertTrue(d.is_walkable(tx, y) and d.is_walkable(x, ty))
        return hits

    def test_starts_chasing_within_radius_only(self):
        d = open_room(10)
        z = self.zombie(d, (1, 2))
        z.update(DT, d, {(5, 2)}, self.rng, (5, 2))                     # a 4 tiles
        self.assertNotEqual(z.state, CHASE)
        z = self.zombie(d, (1, 2))
        z.update(DT, d, {(4, 2)}, self.rng, (4, 2))                     # a 3 tiles
        self.assertEqual(z.state, CHASE)

    def test_reaches_and_hits_with_windup_and_cooldown(self):
        d = open_room(10)
        z = self.zombie(d, (2, 2))
        hits = self.simulate(z, d, (5, 2), 5.0)
        self.assertEqual(z.tile, (4, 2))                                 # colado nele
        self.assertGreaterEqual(len(hits), 3)
        arrive = 2 * S.TILE / S.ZOMBIE_CHASE_SPEED
        self.assertGreaterEqual(hits[0], arrive + S.ZOMBIE_ATTACK_WINDUP - DT)
        for a, b in zip(hits, hits[1:]):
            self.assertAlmostEqual(b - a, S.ZOMBIE_ATTACK_COOLDOWN + S.ZOMBIE_ATTACK_WINDUP, delta=3 * DT)

    def test_follows_through_open_door_not_closed(self):
        d = MapDungeon(TWO_ROOMS, ROOMS)
        z = self.zombie(d, (4, 2))
        self.assertTrue(self.simulate(z, d, (7, 2), 3.0))
        self.assertEqual(z.tile, (6, 2))                                 # passou pela porta (5,2)
        d = MapDungeon([r.replace("D", "d") for r in TWO_ROOMS], ROOMS)
        z = self.zombie(d, (4, 2))
        self.assertEqual(self.simulate(z, d, (7, 2), 3.0), [])
        self.assertLessEqual(z.tile[0], 4)                               # porta fechada segura

    def test_stops_when_player_is_far_and_wanders_where_it_is(self):
        d = MapDungeon(TWO_ROOMS, ROOMS)
        z = self.zombie(d, (4, 2))
        self.simulate(z, d, (7, 2), 3.0)                                 # foi para a outra sala
        self.assertEqual(z.state, CHASE)
        self.simulate(z, d, (60, 60), 0.5)                               # longe: volta a vagar
        self.assertIn(z.state, (IDLE, WALK))
        self.assertIs(z.room, d.rooms[1])
        for _ in range(round(5 / DT)):
            z.update(DT, d, set(), self.rng, (60, 60))
            self.assertTrue(in_room(d.rooms[1], z.tile))

    def test_goes_around_wall(self):
        d = MapDungeon(["#######",
                        "#.....#",
                        "#.###.#",
                        "#.....#",
                        "#######"], [(1, 1, 5, 3)])
        z = self.zombie(d, (3, 1))
        self.assertTrue(self.simulate(z, d, (3, 3), 6.0))                # parede no meio
        self.assertEqual(z.tile[1], 3)

    def test_does_not_hit_across_corner(self):
        d = MapDungeon(["#####",
                        "#.#.#",
                        "##..#",
                        "#####"], [(1, 1, 3, 2)])
        z = self.zombie(d, (1, 1))                                       # (1,1)->(2,2): quina de parede
        self.assertEqual(self.simulate(z, d, (2, 2), 2.0), [])

    def test_dead_player_buried_or_dying_zombie_do_not_chase(self):
        d = open_room(6)
        z = self.zombie(d, (1, 2))
        z.update(DT, d, {(3, 2)}, self.rng, None)                        # personagem morto
        self.assertNotEqual(z.state, CHASE)
        z = Zombie((1, 2), d.rooms[0])                                   # enterrado
        self.assertFalse(z.update(DT, d, {(2, 2)}, self.rng, (2, 2)))
        self.assertEqual(z.state, UNDERGROUND)
        z = self.zombie(d, (1, 2))
        z.hit(S.ZOMBIE_HP)                                               # morrendo
        self.assertEqual(z.state, DYING)
        self.assertFalse(z.update(DT, d, {(2, 2)}, self.rng, (2, 2)))


def load_frames(name):
    return next([None] * n for _, row_name, n in ZOMBIE_ROWS if row_name == name)


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_frames(self):
        anims = load_zombie_animations()
        for _, name, count in ZOMBIE_ROWS:
            self.assertEqual(len(anims[name]), count)
            for img in anims[name]:
                self.assertEqual(img.get_size(), (S.ZOMBIE_SIZE, S.ZOMBIE_SIZE))

    def test_no_magenta_left(self):
        for frames in load_zombie_animations(raw=True).values():
            for img in frames:
                for y in range(32):
                    for x in range(32):
                        c = img.get_at((x, y))
                        if c.a:
                            self.assertFalse(is_magenta(c))
                            self.assertFalse(c.r > 120 and c.b > 120 and c.g < 0.5 * min(c.r, c.b))


if __name__ == "__main__":
    unittest.main()

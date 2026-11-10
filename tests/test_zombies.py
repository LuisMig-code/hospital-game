"""Testes dos zumbis: spawn, surgimento, vagar e colisão."""
import os
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
from zombies import EMERGING, IDLE, UNDERGROUND, WALK, Horde, in_room, spawn_zombies  # noqa: E402

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
        taken = {z.tile for z in self.horde.zombies}
        free = next((x, y) for y in range(room.y, room.y + room.h)
                    for x in range(room.x, room.x + room.w)
                    if self.d.is_walkable(x, y) and (x, y) not in taken)
        self.player = Player(ANIMS, free)
        self.room_tiles = {(x, y) for y in range(room.y, room.y + room.h)
                           for x in range(room.x, room.x + room.w)}

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

    def test_wander_and_rest_inside_room(self):
        start = {id(z): z.tile for z in self.zs}
        self.run_for(60, visible=self.room_tiles)
        for z in self.zs:
            self.assertGreater(z.time_in[IDLE], 1.0)     # ficou parado um tempo
            self.assertGreater(z.time_in[WALK], 1.0)     # e também andou
        moved = sum(1 for z in self.zs if z.tile != start[id(z)])
        self.assertGreaterEqual(moved, len(self.zs) // 2)

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

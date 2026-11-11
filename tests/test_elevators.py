"""Testes dos elevadores: posição (chegada e saída) e sprites."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from elevators import FRAMES, ElevatorActor, path_distances  # noqa: E402
from sprites import ELEVATOR_ANIMS, load_elevator_animations  # noqa: E402


def room_distance(room, dist):
    return min(dist.get((x, y), 10 ** 9) for y in range(room.y, room.y + room.h)
               for x in range(room.x, room.x + room.w))


class PlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maps = [generate(s) for s in range(100)]

    def test_on_top_wall_with_free_front(self):
        for d in self.maps:
            for ev in (d.elevator_in, d.elevator_out):
                self.assertIsNotNone(ev, d.seed)
                (x0, y), (x1, y1) = ev.wall
                self.assertEqual((x1, y1), (x0 + 1, y))
                self.assertEqual(y, ev.room.y - 1)                    # parede de cima da sala
                for (wx, wy), (fx, fy) in zip(ev.wall, ev.front):
                    self.assertFalse(d.is_floor(wx, wy))              # parede...
                    self.assertFalse(d.is_floor(wx, wy - 1))          # ...alta
                    self.assertTrue(d.is_walkable(fx, fy))            # frente: chão sem móvel
                    self.assertEqual(d.room_at((fx, fy)), ev.room)
                    for dx, dy in d.door_at:
                        self.assertGreater(max(abs(fx - dx), abs(fy - dy)), 1)
                for (fx, fy) in ev.front:                             # nada colado na frente
                    self.assertNotIn((fx, fy + 1), d.blocked)

    def test_spawn_and_exit(self):
        for d in self.maps:
            self.assertEqual(d.spawn, d.elevator_in.front[0])
            self.assertIsNot(d.elevator_out.room, d.elevator_in.room)
            dist = path_distances(d, d.spawn)
            for t in d.elevator_out.front:
                self.assertIn(t, dist)                                # alcançável
            others = sorted((r for r in d.rooms if r is not d.elevator_in.room),
                            key=lambda r: room_distance(r, dist))
            far = others[len(others) // 2:]
            if any(r is d.elevator_out.room for r in far):
                continue
            # só fica perto se nenhuma sala longe tem lugar na parede de cima
            from elevators import positions
            self.assertTrue(all(not positions(d, r) for r in far), d.seed)

    def test_exit_usually_far(self):
        far = 0
        for d in self.maps:
            dist = path_distances(d, d.spawn)
            others = sorted((r for r in d.rooms if r is not d.elevator_in.room),
                            key=lambda r: room_distance(r, dist))
            far += d.elevator_out.room in others[len(others) // 2:]
        self.assertGreater(far, 90)

    def test_deterministic(self):
        a, b = generate(42), generate(42)
        self.assertEqual((a.elevator_in.wall, a.elevator_out.wall), (b.elevator_in.wall, b.elevator_out.wall))


class ActorTests(unittest.TestCase):
    def test_play_once_and_reverse(self):
        a = ElevatorActor(None, "open_exit")
        self.assertEqual(a.frame(10), 0)
        a.update(0.35, 10)
        self.assertEqual(a.frame(10), 3)
        self.assertFalse(a.done)
        a.update(0.5, 10)
        self.assertTrue(a.done)
        self.assertEqual(a.frame(10), 7)                              # para no último
        a.play("open_exit", reverse=True)
        self.assertEqual(a.frame(10), 7)

    def test_loop(self):
        a = ElevatorActor(None)
        a.play("idle", loop=True)
        a.update(0.65, 10)
        self.assertEqual(a.frame(10), 0)                              # 6 quadros: deu a volta
        self.assertFalse(a.done)


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.anims = load_elevator_animations()

    def test_frames(self):
        self.assertEqual(set(self.anims), set(FRAMES))
        for name, frames in self.anims.items():
            self.assertEqual(len(frames), FRAMES[name], name)
            self.assertEqual(len(frames), len(ELEVATOR_ANIMS[name][2]))
            for img in frames:
                self.assertEqual(img.get_width(), S.ELEVATOR_WIDTH)
                self.assertGreater(img.get_height(), 2 * S.TILE)
                self.assertLess(img.get_height(), 3 * S.TILE)
                self.assertEqual(img.get_at((0, 0)).a < 255 or img.get_at((1, 1)).a < 255, True)


if __name__ == "__main__":
    unittest.main()

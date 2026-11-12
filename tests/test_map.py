"""Testes do mapa (tecla M): portas já abertas, salas com inimigos, desenho
do que foi descoberto e a pausa do jogo."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import main  # noqa: E402
import settings as S  # noqa: E402
from doors import SIDES, try_toggle  # noqa: E402
from fov import compute_fov  # noqa: E402
from items import MedKit  # noqa: E402
from map_view import MapBoard, discovered_rooms, room_status  # noqa: E402
from player import Player  # noqa: E402
from zombies import CHASE, Zombie  # noqa: E402

FACING = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}
C = S.MAP_COLORS


def play(g):
    g.phase, g.player_visible = "play", True
    return g


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


class DoorOpenedTests(unittest.TestCase):
    def test_opened_stays_after_closing(self):
        g = play(main.Game(42))
        door = g.dungeon.doors[0]
        other = g.dungeon.doors[1]
        (_, _), (ox, oy) = SIDES[door.side]
        x, y = door.tiles[0]
        p = Player(g.anims, (x - ox, y - oy))
        p.facing = FACING[(ox, oy)]
        self.assertFalse(door.opened)
        self.assertEqual(try_toggle(g.dungeon, p)[0], "abriu")
        self.assertTrue(door.opened)
        self.assertEqual(try_toggle(g.dungeon, p)[0], "fechou")
        self.assertFalse(door.open)
        self.assertTrue(door.opened)                      # já foi aberta: continua verde no mapa
        self.assertFalse(other.opened)                    # nunca tocada


class RoomStatusTests(unittest.TestCase):
    def setUp(self):
        self.g = play(main.Game(42))
        self.d = self.g.dungeon

    def test_rooms_with_living_zombies_born_there(self):
        zs = self.g.horde.zombies
        status = room_status(self.d, zs)
        for r in self.d.rooms:
            born = [z for z in zs if z.home is r]
            self.assertEqual(status[id(r)], "enemies" if born else "clear")    # enterrados contam

    def test_cleared_after_killing_everyone_born_there(self):
        room = next(r for r in self.d.rooms if any(z.home is r for z in self.g.horde.zombies))
        self.g.horde.zombies = [z for z in self.g.horde.zombies if z.home is not room]   # mortos saem da Horde
        self.assertEqual(room_status(self.d, self.g.horde.zombies)[id(room)], "clear")

    def test_zombie_that_left_still_counts_for_its_room(self):
        room = self.d.rooms[1]
        z = Zombie((0, 0), room)
        z.state, z.room = CHASE, None                     # perseguindo no corredor
        status = room_status(self.d, [z])
        self.assertEqual(status[id(room)], "enemies")
        self.assertEqual(status[id(self.d.rooms[0])], "clear")
        z.state = "dead"
        self.assertEqual(room_status(self.d, [z])[id(room)], "clear")


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = play(main.Game(42))
        cls.board = MapBoard()

    def setUp(self):
        self.d = self.g.dungeon
        for door in self.d.doors:
            door.open = door.opened = False

    def color(self, surf, tile):
        r = self.board.tile_rect(tile, self.board.layout(self.d))
        return tuple(surf.get_at(r.center))[:3]

    def render(self, explored, zombies=(), medkits=()):
        return self.board.render(self.d, explored, list(zombies), list(medkits), 1)

    def test_unexplored_keeps_the_board(self):
        surf = self.render(set())
        for t in ((5, 5), (40, 30), (70, 50)):
            r = self.board.tile_rect(t, self.board.layout(self.d))
            self.assertEqual(surf.get_at(r.center), self.board.board.get_at(r.center))

    def test_room_colors(self):
        a, b = self.d.rooms[0], self.d.rooms[1]
        ta, tb = (a.x + 1, a.y + 1), (b.x + 1, b.y + 1)
        z = Zombie(tb, b)
        surf = self.render({ta, tb}, [z])
        self.assertEqual(self.color(surf, ta), C["floor"])
        self.assertEqual(self.color(surf, tb), C["enemies"])

    def test_corridor_and_wall(self):
        corridor = next((x, y) for y in range(self.d.height) for x in range(self.d.width)
                        if self.d.is_floor(x, y) and self.d.room_at((x, y)) is None
                        and (x, y) not in self.d.door_at)
        wall = next((x, y) for y in range(self.d.height) for x in range(self.d.width)
                    if not self.d.is_floor(x, y))
        surf = self.render({corridor, wall})
        self.assertEqual(self.color(surf, corridor), C["corridor"])
        self.assertEqual(self.color(surf, wall), C["wall"])

    def test_door_colors_and_only_when_explored(self):
        d0, d1, d2 = self.d.doors[:3]
        d0.opened = True                                   # aberta e fechada de novo: verde
        explored = set(d0.tiles) | set(d1.tiles)
        surf = self.render(explored)
        self.assertEqual(self.color(surf, d0.tiles[0]), C["door_opened"])
        self.assertEqual(self.color(surf, d1.tiles[0]), C["door_new"])
        r = self.board.tile_rect(d2.tiles[0], self.board.layout(self.d))
        self.assertEqual(surf.get_at(r.center), self.board.board.get_at(r.center))   # não descoberta

    def test_exit_elevator_only_after_seen(self):
        ex = self.d.elevator_out
        surf = self.render(set())
        self.assertNotEqual(self.color(surf, ex.wall[0]), C["elevator_out"])
        surf = self.render(set(ex.wall))
        self.assertEqual(self.color(surf, ex.wall[0]), C["elevator_out"])

    def test_medkit_only_if_seen(self):
        room = self.d.rooms[2]
        t = (room.x + 1, room.y + 1)
        kit = MedKit(t)
        surf = self.render(set(), medkits=[kit])
        self.assertNotEqual(self.color(surf, t), C["medkit"])
        surf = self.render({t}, medkits=[kit])
        self.assertEqual(self.color(surf, t), C["medkit"])

    def test_summary_counts_discovered_and_clear_rooms(self):
        a, b = self.d.rooms[0], self.d.rooms[1]
        explored = {(a.x, a.y), (b.x, b.y)}
        self.assertEqual(discovered_rooms(self.d, explored), [a, b])
        self.render(explored, [Zombie((b.x, b.y), b)])   # desenha legenda e resumo sem quebrar

    def test_map_fits_inside_the_grid(self):
        ts, ox, oy = self.board.layout(self.d)
        grid = self.board._r(pygame.Rect(61, 211, 1042, 768))
        self.assertGreaterEqual(ts, 7)                    # ~8 px por tile
        self.assertGreaterEqual(ox, grid.x - 1)
        self.assertGreaterEqual(oy, grid.y - 1)
        self.assertLessEqual(ox + ts * self.d.width, grid.right + 1)
        self.assertLessEqual(oy + ts * self.d.height, grid.bottom + 1)
        self.assertLessEqual(self.board.size[0], S.SCREEN_W)
        self.assertLessEqual(self.board.size[1], S.SCREEN_H)


class GameMapTests(unittest.TestCase):
    def test_m_opens_only_while_playing_and_alive(self):
        g = main.Game(42)
        self.assertEqual(g.phase, "arrive")
        g.handle_event(key(pygame.K_m))
        self.assertFalse(g.map_open)                      # chegada do elevador
        play(g)
        g.handle_event(key(pygame.K_m))
        self.assertTrue(g.map_open)
        g.handle_event(key(pygame.K_m))
        self.assertFalse(g.map_open)
        g.player.dead = True
        g.handle_event(key(pygame.K_m))
        self.assertFalse(g.map_open)

    def test_paused_while_open(self):
        g = play(main.Game(42))
        z = Zombie((g.player.tile[0] + 3, g.player.tile[1]), None)
        z.state = CHASE
        g.horde.zombies = [z]
        g.handle_event(key(pygame.K_m))
        before = (z.x, z.y, g.time, g.player.stamina)
        for _ in range(60):
            g.frame(1 / 60, main._NO_KEYS)
        self.assertEqual((z.x, z.y, g.time, g.player.stamina), before)
        g.handle_event(key(pygame.K_m))
        for _ in range(30):
            g.frame(1 / 60, main._NO_KEYS)
        self.assertNotEqual((z.x, z.y), before[:2])       # fechado: volta a andar

    def test_escape_closes_map_without_quitting(self):
        g = play(main.Game(42))
        g.handle_event(key(pygame.K_m))
        self.assertTrue(g.handle_event(key(pygame.K_ESCAPE)))
        self.assertFalse(g.map_open)
        self.assertFalse(g.handle_event(key(pygame.K_ESCAPE)))   # sem o mapa, ESC sai

    def test_keys_ignored_while_open_and_r_starts_new_run(self):
        g = play(main.Game(42))
        g.player.medkits, g.player.hp = 1, 4
        g.handle_event(key(pygame.K_m))
        g.handle_event(key(pygame.K_h))
        g.handle_event(key(pygame.K_SPACE))
        self.assertFalse(g.player.heal_queued or g.player.attack_queued)
        seed = g.run_seed
        g.handle_event(key(pygame.K_r))
        self.assertFalse(g.map_open)
        self.assertNotEqual(g.run_seed, seed)


if __name__ == "__main__":
    unittest.main()

"""Testes das salas temáticas: temas, posição dos móveis, colisão e passagens livres."""
import os
import sys
import unittest
from collections import deque
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from furnish import spawn_room  # noqa: E402
from props import PropArt, load_prop_images  # noqa: E402
from themes import PROPS, SPAWN_THEME, THEMES  # noqa: E402

SEEDS = range(100)


def in_room(room, t):
    return room.x <= t[0] < room.x + room.w and room.y <= t[1] < room.y + room.h


def flood(d, start):
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in seen and d.is_floor(*n) and n not in d.blocked:   # portas contam como abertas
                seen.add(n)
                q.append(n)
    return seen


class FurnishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maps = [generate(s) for s in SEEDS]

    def test_every_room_has_theme_and_spawn_room_is_reception(self):
        seen = set()
        for d in self.maps:
            for room in d.rooms:
                self.assertIn(room.theme, THEMES)
                self.assertIn(room.floor, THEMES[room.theme].floors)
                seen.add(room.theme)
            self.assertEqual(spawn_room(d).theme, SPAWN_THEME)
        self.assertEqual(seen, set(THEMES))                      # todos os temas aparecem

    def test_props_inside_room_away_from_doors_and_spawn(self):
        for d in self.maps:
            sx, sy = d.spawn
            doors = list(d.door_at)
            tiles = []
            for pp in d.props:
                room = d.room_at(pp.tile)
                self.assertIsNotNone(room)
                self.assertTrue(PROPS[pp.name].solid)
                self.assertIn(pp.name, _theme_props(room.theme), (d.seed, pp))
                for t in pp.tiles:
                    tiles.append(t)
                    self.assertTrue(in_room(room, t))
                    self.assertTrue(d.is_floor(*t))
                    self.assertGreater(max(abs(t[0] - sx), abs(t[1] - sy)), 2)
                    for dx, dy in doors:
                        self.assertGreater(max(abs(t[0] - dx), abs(t[1] - dy)), 2)
            self.assertEqual(len(tiles), len(set(tiles)))         # sem sobreposição
            self.assertEqual(set(tiles), d.blocked)

    def test_all_floor_still_connected(self):
        """Nenhum móvel fecha passagem: todo chão sem móvel é alcançável."""
        for d in self.maps:
            free = {(x, y) for y in range(d.height) for x in range(d.width) if d.is_floor(x, y)} - d.blocked
            self.assertEqual(flood(d, d.spawn), free, d.seed)

    def test_occupation_is_moderate(self):
        total = used = 0
        for d in self.maps:
            for room in d.rooms:
                n = sum(1 for t in d.blocked if in_room(room, t))
                self.assertLessEqual(n, int(room.w * room.h * S.FURNITURE_DENSITY))
                total += room.w * room.h
                used += n
        self.assertGreater(used / total, 0.05)                   # tem móvel de verdade

    def test_collision_blocks_walk_not_sight(self):
        d = self.maps[0]
        t = next(iter(d.blocked))
        self.assertFalse(d.is_walkable(*t))
        self.assertTrue(d.is_transparent(*t))

    def test_decals_have_no_collision(self):
        for d in self.maps[:30]:
            for dec in d.decals:
                self.assertFalse(PROPS[dec.name].solid)
                for t in dec.tiles:
                    self.assertTrue(d.is_floor(*t))

    def test_deterministic(self):
        a, b = generate(42), generate(42)
        self.assertEqual([(p.name, p.tile) for p in a.props], [(p.name, p.tile) for p in b.props])
        self.assertEqual([r.theme for r in a.rooms], [r.theme for r in b.rooms])


def _theme_props(key):
    th = THEMES[key]
    names = set(th.top) | set(th.side) | set(th.loose)
    for group in th.center:
        names |= {n for n, _, _ in group}
    return names


class PropArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.images = load_prop_images()

    def test_all_props_cut(self):
        self.assertEqual(set(self.images), set(PROPS))
        for name, img in self.images.items():
            p = PROPS[name]
            self.assertEqual(img.get_width(), p.width, name)
            self.assertGreater(img.get_height(), 8, name)
            self.assertLess(img.get_height(), 4 * S.TILE, name)
            # recortado no desenho: bordas com pixels opacos
            mask = pygame.mask.from_surface(img, 70)
            self.assertGreater(mask.count() / (img.get_width() * img.get_height()), 0.25, name)

    def test_themes_use_known_props(self):
        for key, th in THEMES.items():
            for name in _theme_props(key) | set(th.scatter):
                self.assertIn(name, PROPS, (key, name))
            for name in th.scatter:
                self.assertFalse(PROPS[name].solid)

    def test_anchor_on_footprint_base(self):
        art = PropArt(self.images)
        d = generate(42)
        pp = d.props[0]
        r = art.rect(pp)
        self.assertEqual(r.bottom, (pp.tile[1] + pp.fh) * S.TILE - 2)
        self.assertAlmostEqual(r.centerx, (pp.tile[0] + pp.fw / 2) * S.TILE, delta=1)


if __name__ == "__main__":
    unittest.main()

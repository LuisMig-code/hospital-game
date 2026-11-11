"""Testes do piso, paredes e portas novos e da montagem do mapa com a arte."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from props import PropArt  # noqa: E402
from themes import CORRIDOR, THEMES  # noqa: E402
from tileset import (DOOR_CLOSED, FLOOR_BLOCKS, WALL_PARTS, WALL_STYLES, Tileset, draw_door,  # noqa: E402
                     load_door_pieces, load_wall_pieces, render_map, theme_at)


def is_magenta(c):
    return c.a > 0 and c.r > 200 and c.b > 200 and c.g < 80


class TilesetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.tiles = Tileset()
        cls.props = PropArt()

    def test_floor_blocks(self):
        self.assertEqual(len(self.tiles.floor), 32)
        for name, img in self.tiles.floor.items():
            self.assertEqual(img.get_size(), (3 * S.TILE, 3 * S.TILE), name)
        for theme in list(THEMES.values()) + [CORRIDOR]:      # todo piso usado existe
            for name in theme.floors + theme.decals:
                self.assertIn(name, FLOOR_BLOCKS)

    def test_wall_pieces(self):
        pieces = load_wall_pieces()
        for s in range(WALL_STYLES):
            for i in range(len(WALL_PARTS)):
                img = pieces[(s, i)]
                self.assertGreater(img.get_width(), 100)
                self.assertGreater(img.get_height(), 60)
        for (r, c), img in pieces.items():                    # sem fundo magenta
            w, h = img.get_size()
            magenta = sum(is_magenta(img.get_at((x, y))) for y in range(0, h, 2) for x in range(0, w, 2))
            self.assertEqual(magenta, 0, (r, c))

    def test_walls_scaled_to_grid(self):
        t = S.TILE
        for s, style in self.tiles.walls.items():
            self.assertEqual(len(style["plain"]), 4)
            for img in style["plain"]:
                self.assertEqual(img.get_size(), (t, 2 * t))
            for img in [style["left"], style["right"]] + style["details"]:
                self.assertEqual(img.get_size(), (2 * t, 2 * t))
            self.assertEqual(style["low"].get_size(), (2 * t, t))
        self.assertEqual(set(self.tiles.walls), set(range(WALL_STYLES)))

    def test_doors(self):
        doors = load_door_pieces()
        self.assertEqual(len(doors), 8)
        for img in doors.values():                            # dentro do contorno: sem magenta
            w, h = img.get_size()
            self.assertAlmostEqual(w / h, 0.95, delta=0.1)
            magenta = sum(is_magenta(img.get_at((x, y))) for y in range(0, h, 2) for x in range(0, w, 2))
            self.assertEqual(magenta, 0)
        t = S.TILE
        sizes = {"top": (2 * t, 2 * t), "bottom": (2 * t, t), "left": (t, 2 * t), "right": (t, 2 * t)}
        for variant in DOOR_CLOSED:
            for side, size in sizes.items():
                for is_open in (False, True):
                    self.assertEqual(self.tiles.door[variant][side][is_open].get_size(), size)
        for theme in THEMES.values():
            self.assertIn(theme.door, DOOR_CLOSED)

    def test_render_is_deterministic(self):
        d = generate(42)
        a = render_map(d, self.tiles, self.props)
        b = render_map(generate(42), self.tiles, self.props)
        self.assertEqual(a.get_size(), (d.width * S.TILE, d.height * S.TILE))
        self.assertEqual(pygame.image.tobytes(a, "RGB"), pygame.image.tobytes(b, "RGB"))

    def test_theme_floor_in_rooms(self):
        """O piso de uma sala de centro cirúrgico é o azul; o do corredor, o liso."""
        for seed in range(30):
            d = generate(seed)
            room = next((r for r in d.rooms if r.theme == "cirurgia"), None)
            if room is None:
                continue
            self.assertEqual(theme_at(d, room.center), THEMES["cirurgia"])
            self.assertEqual(room.floor, "blue")
            corridor = next(((x, y) for y in range(d.height) for x in range(d.width)
                             if d.is_floor(x, y) and d.room_at((x, y)) is None), None)
            self.assertIs(theme_at(d, corridor), CORRIDOR)
            return
        self.fail("nenhuma sala de centro cirúrgico em 30 seeds")

    def test_wall_shadow_on_floor(self):
        d = generate(42)
        surf = render_map(d, self.tiles)
        x, y = next((x, y) for y in range(d.height) for x in range(d.width)
                    if d.is_floor(x, y) and not d.is_floor(x, y - 1)
                    and (x, y) not in d.door_at and (x, y - 1) not in d.door_at)
        t = S.TILE

        def lum(px, py):
            r, g, b, _ = surf.get_at((px, py))
            return r + g + b
        # topo do tile (encostado na parede) bem mais escuro que o meio
        top = sum(lum(x * t + i, y * t + 1) for i in range(8, 24))
        mid = sum(lum(x * t + i, y * t + t // 2 + 6) for i in range(8, 24))
        self.assertLess(top, mid * 0.8)

    def test_door_toggle_redraw(self):
        d = generate(42)
        surf = render_map(d, self.tiles)
        before = pygame.image.tobytes(surf, "RGB")
        for door in d.doors:
            door.open = True
            draw_door(surf, door, self.tiles)
        self.assertNotEqual(pygame.image.tobytes(surf, "RGB"), before)
        for door in d.doors:
            door.open = False
            draw_door(surf, door, self.tiles)
        self.assertEqual(pygame.image.tobytes(surf, "RGB"), before)

    def test_door_follows_room_theme(self):
        for seed in range(40):
            d = generate(seed)
            door = next((dr for dr in d.doors if dr.room is not None and dr.room.theme == "necroterio"), None)
            if door is not None:
                self.assertIs(self.tiles.door_image(door), self.tiles.door["vault"][door.side][False])
                return
        self.fail("nenhuma porta de necrotério em 40 seeds")


if __name__ == "__main__":
    unittest.main()

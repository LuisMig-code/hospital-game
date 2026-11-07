"""Testes do recorte do tileset e da montagem do mapa com a arte."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
from dungeon import generate  # noqa: E402
from tileset import PIECE_ROWS, Tileset, _is_outline, draw_door, find_pieces, load_pieces, render_map  # noqa: E402


class TilesetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.pieces = load_pieces()
        cls.tiles = Tileset(cls.pieces)

    def test_finds_all_pieces_in_order(self):
        rects = find_pieces(pygame.image.load(str(S.TILESET)))
        self.assertEqual(list(rects), [n for row in PIECE_ROWS for n in row])
        # pisos em cima, paredes no meio, portas embaixo
        self.assertLess(rects["floor"].bottom, rects["wall_vent"].top)
        self.assertLess(rects["wall_vent"].bottom, rects["door_double_closed"].top)
        # pisos são ~quadrados; parede baixa é larga
        f = rects["floor"]
        self.assertAlmostEqual(f.w / f.h, 1.0, delta=0.1)
        self.assertGreater(rects["wall_low"].w / rects["wall_low"].h, 1.5)

    def test_no_outline_left(self):
        for name, img in self.pieces.items():
            w, h = img.get_size()
            purple = sum(_is_outline(img.get_at((x, y))) for y in range(h) for x in range(w))
            self.assertEqual(purple, 0, name)

    def test_scaled_to_grid(self):
        t = S.TILE
        self.assertEqual(self.tiles.floor.get_size(), (3 * t, 3 * t))
        for img in self.tiles.wall_plain:
            self.assertEqual(img.get_size(), (t, 2 * t))
        for img in (self.tiles.wall_vent, self.tiles.wall_left, self.tiles.wall_right):
            self.assertEqual(img.get_height(), 2 * t)
            self.assertEqual(img.get_width() % t, 0)
        self.assertEqual(self.tiles.wall_low.get_height(), t)

    def test_render_is_deterministic(self):
        d = generate(42)
        a = render_map(d, self.tiles)
        b = render_map(generate(42), self.tiles)
        self.assertEqual(a.get_size(), (d.width * S.TILE, d.height * S.TILE))
        self.assertEqual(pygame.image.tobytes(a, "RGB"), pygame.image.tobytes(b, "RGB"))


    def test_door_sprites_and_toggle_redraw(self):
        t = S.TILE
        sizes = {"top": (2 * t, 2 * t), "bottom": (2 * t, t), "left": (t, 2 * t), "right": (t, 2 * t)}
        for side, size in sizes.items():
            for is_open in (False, True):
                self.assertEqual(self.tiles.door[side][is_open].get_size(), size)

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


if __name__ == "__main__":
    unittest.main()

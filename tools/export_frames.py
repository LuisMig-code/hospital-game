"""Exporta os frames recortados para conferência visual.

Uso: venv\\Scripts\\python.exe tools\\export_frames.py
Saída: assets/personagem/frames/<anim>_<i>.png e preview.png (todos os frames)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from settings import ASSETS  # noqa: E402
from sprites import load_animations, slice_sheet  # noqa: E402
from settings import CHARACTER_SHEET  # noqa: E402


def main():
    pygame.init()
    out = ASSETS / "personagem" / "frames"
    out.mkdir(parents=True, exist_ok=True)

    rects = slice_sheet(pygame.image.load(str(CHARACTER_SHEET)))
    for name, frames in rects.items():
        print(f"{name:11s} {len(frames)} frames, tamanho {frames[0].size}, linha y={frames[0].y}..{frames[0].bottom}")

    anims = load_animations(raw=True)
    for name, frames in anims.items():
        for i, img in enumerate(frames):
            pygame.image.save(img, str(out / f"{name}_{i}.png"))

    # Preview: grade com bordas vermelhas em cada frame
    fw = max(f.get_width() for fr in anims.values() for f in fr)
    fh = max(f.get_height() for fr in anims.values() for f in fr)
    pad = 4
    cols = max(len(fr) for fr in anims.values())
    preview = pygame.Surface((cols * (fw + pad), len(anims) * (fh + pad)))
    preview.fill((60, 170, 80))
    for r, frames in enumerate(anims.values()):
        for c, img in enumerate(frames):
            x, y = c * (fw + pad), r * (fh + pad)
            preview.blit(img, (x, y))
            pygame.draw.rect(preview, (255, 0, 0), (x, y, img.get_width(), img.get_height()), 1)
    pygame.image.save(preview, str(out / "preview.png"))
    print(f"Frames salvos em {out}")
    export_tileset()


def export_tileset():
    """Salva cada peça do tileset do hospital e um preview com todas."""
    from tileset import load_pieces

    out = ASSETS / "background" / "pieces"
    out.mkdir(parents=True, exist_ok=True)
    pieces = load_pieces()
    pad = 8
    width = sum(p.get_width() + pad for p in pieces.values())
    height = max(p.get_height() for p in pieces.values())
    preview = pygame.Surface((width, height))
    preview.fill((255, 0, 255))
    x = 0
    for name, img in pieces.items():
        pygame.image.save(img, str(out / f"{name}.png"))
        preview.blit(img, (x, 0))
        x += img.get_width() + pad
        print(f"{name:20s} {img.get_size()}")
    pygame.image.save(preview, str(out / "preview.png"))
    print(f"Peças do tileset salvas em {out}")


if __name__ == "__main__":
    main()

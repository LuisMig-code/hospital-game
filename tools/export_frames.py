"""Exporta os frames recortados para conferência visual.

Uso: venv\\Scripts\\python.exe tools\\export_frames.py
Saída: assets/personagem/frames/<anim>_<i>.png e preview.png (todos os frames)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

import settings as S  # noqa: E402
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
    export_zombie()
    export_attack()
    export_damage()
    export_medkit()


def export_tileset():
    """Salva os blocos de piso, as peças de parede e as portas (cenário novo),
    e os props das salas temáticas com um preview numerado."""
    from props import load_prop_images, slice_sheet
    from tileset import FLOOR_BLOCKS, load_door_pieces, load_floor_blocks, load_wall_pieces

    out = ASSETS / "background" / "pieces"
    out.mkdir(parents=True, exist_ok=True)
    for name, img in load_floor_blocks().items():
        pygame.image.save(img, str(out / f"floor_{name}.png"))
    for (r, c), img in load_wall_pieces().items():
        pygame.image.save(img, str(out / f"wall_{r}_{c}.png"))
    for c, img in load_door_pieces().items():
        pygame.image.save(img, str(out / f"door_{c}.png"))
    print(f"{len(FLOOR_BLOCKS)} blocos de piso, paredes e portas salvos em {out}")

    # props: cada sheet com as peças numeradas (linha,coluna) e cada prop do catálogo
    font = pygame.font.SysFont("consolas", 18, bold=True)
    pout = ASSETS / "cenario" / "pieces"
    pout.mkdir(parents=True, exist_ok=True)
    for key, path in S.PROP_SHEETS.items():
        sheet = pygame.image.load(str(path))
        preview = pygame.Surface(sheet.get_size())
        preview.fill((70, 110, 80))
        preview.blit(sheet, (0, 0))
        for (r, c), rect in slice_sheet(sheet).items():
            pygame.draw.rect(preview, (255, 255, 0), rect, 2)
            preview.blit(font.render(f"{r},{c}", True, (255, 255, 0), (0, 0, 0)), rect.topleft)
        pygame.image.save(preview, str(pout / f"preview_{key}.png"))
    for name, img in load_prop_images().items():
        pygame.image.save(img, str(pout / f"{name}.png"))
    print(f"Props salvos em {pout}")


def export_zombie():
    """Salva os quadros do zumbi (sem escala) e um preview ampliado sobre fundo escuro."""
    from sprites import load_zombie_animations

    out = ASSETS / "monster" / "frames"
    out.mkdir(parents=True, exist_ok=True)
    anims = load_zombie_animations(raw=True)
    scale = 4
    cols = max(len(f) for f in anims.values())
    preview = pygame.Surface((cols * 32 * scale, len(anims) * 32 * scale))
    preview.fill((40, 45, 45))
    for r, (name, frames) in enumerate(anims.items()):
        for c, img in enumerate(frames):
            pygame.image.save(img, str(out / f"{name}_{c}.png"))
            preview.blit(pygame.transform.scale(img, (32 * scale, 32 * scale)), (c * 32 * scale, r * 32 * scale))
        print(f"zumbi {name:11s} {len(frames)} quadros")
    pygame.image.save(preview, str(out / "preview.png"))
    print(f"Quadros do zumbi salvos em {out}")


def export_attack():
    """Quadros do ataque (escala do jogo e ampliados 3x num preview)."""
    from sprites import load_animations, load_attack_animations

    out = ASSETS / "personagem" / "attack_frames"
    out.mkdir(parents=True, exist_ok=True)
    idle_h = load_animations()["idle"][0].get_height()
    anims = load_attack_animations(target_height=idle_h)
    z, cw, ch = 3, 70, 52
    cols = max(len(f) for f in anims.values())
    preview = pygame.Surface((cols * cw * z, len(anims) * ch * z))
    preview.fill((40, 45, 45))
    for r, (name, frames) in enumerate(anims.items()):
        for c, img in enumerate(frames):
            pygame.image.save(img, str(out / f"{name}_{c}.png"))
            big = pygame.transform.scale_by(img, z)
            preview.blit(big, big.get_rect(midbottom=(c * cw * z + cw * z // 2, (r + 1) * ch * z - 4)))
        print(f"ataque {name:13s} {len(frames)} quadros")
    pygame.image.save(preview, str(out / "preview.png"))
    print(f"Quadros do ataque salvos em {out}")


def export_damage():
    """Quadros do dano (escala do jogo e ampliados 3x num preview)."""
    from sprites import load_animations, load_damage_animations

    out = ASSETS / "personagem" / "damage_frames"
    out.mkdir(parents=True, exist_ok=True)
    idle_h = load_animations()["idle"][0].get_height()
    anims = load_damage_animations(target_height=idle_h)
    z, cw, ch = 3, 70, 56
    cols = max(len(f) for f in anims.values())
    preview = pygame.Surface((cols * cw * z, len(anims) * ch * z))
    preview.fill((40, 45, 45))
    for r, (name, frames) in enumerate(sorted(anims.items())):
        for c, img in enumerate(frames):
            pygame.image.save(img, str(out / f"{name}_{c}.png"))
            big = pygame.transform.scale_by(img, z)
            preview.blit(big, big.get_rect(midbottom=(c * cw * z + cw * z // 2, (r + 1) * ch * z - 4)))
        print(f"dano {name:17s} {len(frames)} quadros")
    pygame.image.save(preview, str(out / "preview.png"))
    print(f"Quadros do dano salvos em {out}")


def export_medkit():
    """Quadros do kit médico (no chão) e do personagem pegando/usando o kit."""
    from sprites import load_animations, load_kit_animations, load_medkit_item

    out = ASSETS / "personagem" / "medkit_frames"
    out.mkdir(parents=True, exist_ok=True)
    idle_h = load_animations()["idle"][0].get_height()
    anims = load_kit_animations(target_height=idle_h)
    frames, icon = load_medkit_item()
    anims["medkit_item"] = frames
    anims["medkit_icon"] = [icon]
    z, cw, ch = 3, 50, 56
    cols = max(len(f) for f in anims.values())
    preview = pygame.Surface((cols * cw * z, len(anims) * ch * z))
    preview.fill((40, 45, 45))
    for r, (name, frs) in enumerate(anims.items()):
        for c, img in enumerate(frs):
            pygame.image.save(img, str(out / f"{name}_{c}.png"))
            big = pygame.transform.scale_by(img, z)
            preview.blit(big, big.get_rect(midbottom=(c * cw * z + cw * z // 2, (r + 1) * ch * z - 4)))
        print(f"kit {name:13s} {len(frs)} quadros")
    pygame.image.save(preview, str(out / "preview.png"))
    print(f"Quadros do kit médico salvos em {out}")


if __name__ == "__main__":
    main()

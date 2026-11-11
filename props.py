"""Arte dos props (móveis e detalhes de chão) das salas temáticas.

Os três sheets de cenário têm fundo transparente (com uma névoa de alpha
baixo). Cada um é recortado em linhas (projeção do alpha >= 250) e colunas
(projeção do alpha >= 220, vãos de 3 px); `themes.PROPS` diz qual (linha,
coluna) é cada prop e a largura na tela.

- Detalhes de chão (sem colisão) são desenhados uma vez no mapa
  (`draw_decals`, chamado por `tileset.render_map`).
- Móveis (com colisão) são desenhados a cada quadro junto com os
  personagens, ordenados pela base (`PropArt.draw`), para o personagem
  poder passar por trás de uma estante.
"""
import pygame

import settings as S
from themes import PROPS

ALPHA_CUT = 70      # pixels mais transparentes que isso são a névoa do fundo do sheet


def slice_sheet(sheet):
    """{(linha, coluna): Rect} de cada peça do sheet."""
    from sprites import _col_counts, _row_counts, _runs
    w, h = sheet.get_size()
    strong = pygame.mask.from_surface(sheet, 250)
    mask = pygame.mask.from_surface(sheet, 220)
    rows = [r for r in _runs(_row_counts(strong, 0, 0, w, h), min_gap=3) if r[1] - r[0] > 40]
    out = {}
    for ri, (y0, y1) in enumerate(rows):
        cols = [c for c in _runs(_col_counts(mask, 0, y0, w, y1 - y0), min_gap=3) if c[1] - c[0] > 25]
        for ci, (x0, x1) in enumerate(cols):
            out[(ri, ci)] = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
    return out


def _clean(img):
    """Tira a névoa do fundo e recorta para o desenho."""
    keep = pygame.mask.from_surface(img, ALPHA_CUT)
    src = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    src.blit(img, (0, 0))
    out = keep.to_surface(setsurface=src, unsetcolor=(0, 0, 0, 0))
    rects = keep.get_bounding_rects()
    if not rects:
        return out
    return out.subsurface(rects[0].unionall(rects[1:])).copy()


def load_prop_images(names=None):
    """{nome: Surface} já na escala do jogo (largura = PROPS[nome].width)."""
    names = list(names or PROPS)
    sheets, cells = {}, {}
    out = {}
    for name in names:
        p = PROPS[name]
        if p.sheet not in sheets:
            sheet = pygame.image.load(str(S.PROP_SHEETS[p.sheet]))
            if pygame.display.get_surface() is not None:
                sheet = sheet.convert_alpha()
            sheets[p.sheet] = sheet
            cells[p.sheet] = slice_sheet(sheet)
        img = _clean(sheets[p.sheet].subsurface(cells[p.sheet][(p.row, p.col)]))
        scale = p.width / img.get_width()
        out[name] = pygame.transform.smoothscale(img, (p.width, max(1, round(img.get_height() * scale))))
    return out


class PropArt:
    def __init__(self, images=None):
        self.images = images or load_prop_images()

    @staticmethod
    def anchor(pp):
        """Ponto (px do mundo) onde fica o meio da base do desenho."""
        t = S.TILE
        x, y = pp.tile
        return ((x + pp.fw / 2) * t, (y + pp.fh) * t - 2)

    def rect(self, pp):
        img = self.images[pp.name]
        ax, ay = self.anchor(pp)
        return img.get_rect(midbottom=(round(ax), round(ay)))

    def draw(self, surf, camera, pp):
        img = self.images[pp.name]
        r = self.rect(pp)
        surf.blit(img, (r.x - camera[0], r.y - camera[1]))

    def draw_decals(self, surf, dungeon):
        """Detalhes no chão (sem colisão), centralizados na pegada."""
        t = S.TILE
        for dec in dungeon.decals:
            img = self.images[dec.name]
            x, y = dec.tile
            center = ((x + dec.fw / 2) * t, (y + dec.fh / 2) * t)
            surf.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))

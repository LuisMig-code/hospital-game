"""Piso, paredes e portas do hospital, e a montagem do mapa com a arte.

Três sheets (veja docs/assets.md):
- piso: grade 8x4 de blocos, cada bloco = 3x3 placas = 3x3 tiles do jogo;
- paredes: fundo magenta, 8 linhas x 6 peças (6 estilos de parede + cantos
  + detalhes extras);
- portas: fundo preto e contorno magenta, grade 8x4 (usamos as portas
  duplas da linha 0).

O estilo da parede, a porta e o piso de cada lugar vêm do tema da sala
(`themes.py`); corredores usam o tema CORRIDOR.
"""
import random

import pygame

import settings as S
from dungeon import FLOOR
from themes import CORRIDOR, THEMES

# --------------------------------------------------------------------- piso
FLOOR_GRID = (8, 4)          # colunas, linhas de blocos
FLOOR_BLOCKS = {
    "plain": (0, 0), "cracked": (1, 0), "broken": (2, 0), "footprints": (3, 0),
    "puddle": (4, 0), "papers": (5, 0), "plain_streak": (6, 0), "blood_smear": (7, 0),
    "beige": (0, 1), "blue": (1, 1), "checker": (2, 1), "dark": (3, 1),
    "slime": (4, 1), "yellow_line": (5, 1), "grate": (6, 1), "concrete": (7, 1),
    "blood_drops": (0, 2), "blood_splat": (1, 2), "blood_hand": (2, 2), "blood_trail": (3, 2),
    "dirt": (4, 2), "blood_crack": (5, 2), "blood_dried": (6, 2), "mold": (7, 2),
    "metal_bar": (0, 3), "drain": (1, 3), "hatch": (2, 3), "hole": (3, 3),
    "carpet": (4, 3), "burnt": (5, 3), "glass_floor": (6, 3), "blood_bag": (7, 3),
}

# ------------------------------------------------------------------ paredes
WALL_STYLES = 6              # linhas 0-5: um estilo cada
WALL_PARTS = ("full", "low", "pillar_left", "pillar_right", "window", "detail")
WALL_EXTRAS = ("hole", "rubble", "red_lamp", "blinds", "extinguisher", "plaque")   # linha 7
EXTRA_STYLES = (0,)          # estilos em que os extras combinam (parede branca rachada)

# -------------------------------------------------------------------- portas
DOOR_GRID = (8, 4)
DOOR_CLOSED = {"closed": 0, "blood": 1, "shattered": 6, "vault": 7}   # colunas da linha 0
DOOR_OPEN = 3


def remove_magenta(img, tolerance=90):
    """Fundo magenta vira transparente; a franja arroxeada que sobra na borda
    das peças vira traço escuro (como o contorno do desenho)."""
    bg = pygame.mask.from_threshold(img, (255, 0, 255, 255), (tolerance, tolerance, tolerance, 255))
    fg = bg.copy()
    fg.invert()
    src = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    src.blit(img, (0, 0))
    out = fg.to_surface(setsurface=src, unsetcolor=(0, 0, 0, 0))
    fringe = pygame.mask.from_threshold(img, (175, 40, 175, 255), (80, 41, 80, 255))
    fringe = fringe.overlap_mask(fg, (0, 0))      # só onde é peça
    out.blit(fringe.to_surface(setcolor=(22, 18, 24, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
    return out, fg


def _runs(counts, min_gap):
    from sprites import _runs as runs
    return runs(counts, min_gap)


def load_floor_blocks(path=None):
    """{nome: Surface 96x96} de cada bloco 3x3 do piso."""
    sheet = pygame.image.load(str(path or S.FLOOR_SHEET))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert()
    w, h = sheet.get_size()
    cols, rows = FLOOR_GRID
    out = {}
    for name, (c, r) in FLOOR_BLOCKS.items():
        x0, x1 = round(c * w / cols), round((c + 1) * w / cols)
        y0, y1 = round(r * h / rows), round((r + 1) * h / rows)
        out[name] = pygame.transform.smoothscale(sheet.subsurface((x0, y0, x1 - x0, y1 - y0)),
                                                 (3 * S.TILE, 3 * S.TILE))
    return out


def load_wall_pieces(path=None):
    """{(linha, coluna): Surface} das peças de parede, sem o magenta,
    recortadas pela projeção do alpha."""
    from sprites import _col_counts, _row_counts
    raw = pygame.image.load(str(path or S.WALL_SHEET))
    img, fg = remove_magenta(raw)
    w, h = img.get_size()
    rows = [r for r in _runs(_row_counts(fg, 0, 0, w, h), 4) if r[1] - r[0] > 40]
    pieces = {}
    for ri, (y0, y1) in enumerate(rows):
        cols = [c for c in _runs(_col_counts(fg, 0, y0, w, y1 - y0), 4) if c[1] - c[0] > 40]
        for ci, (x0, x1) in enumerate(cols):
            cell = img.subsurface((x0, y0, x1 - x0, y1 - y0))
            pieces[(ri, ci)] = cell.subsurface(_opaque_rect(cell)).copy()
    return pieces


def load_door_pieces(path=None):
    """{coluna: Surface} das portas duplas (linha 0), recortadas por dentro
    do contorno magenta."""
    sheet = pygame.image.load(str(path or S.DOOR_SHEET))
    w, h = sheet.get_size()
    cols, rows = DOOR_GRID
    mag = pygame.mask.from_threshold(sheet, (240, 0, 240, 255), (110, 70, 110, 255))
    out = {}
    for c in range(cols):
        cell = pygame.Rect(round(c * w / cols), 0, round(w / cols), round(h / rows))
        sub = pygame.mask.Mask(cell.size)
        sub.draw(mag, (-cell.x, -cell.y))
        rects = sub.get_bounding_rects()
        bb = rects[0].unionall(rects[1:]).inflate(-10, -10).move(cell.x, cell.y)
        out[c] = sheet.subsurface(bb).copy()
    return out


class Tileset:
    """Peças já escaladas para o grid."""

    def __init__(self):
        t = S.TILE
        self.floor = load_floor_blocks()
        walls = load_wall_pieces()
        # Paredes por estilo: {estilo: {...}}
        self.walls = {}
        for s in range(WALL_STYLES):
            part = {name: walls[(s, i)] for i, name in enumerate(WALL_PARTS)}
            left = self._crop_to_wall(part["pillar_left"], 0.7)
            right = self._crop_to_wall(part["pillar_right"], 0.3)
            style = {
                # Parede lisa: faixas de 1 coluna tiradas do miolo das paredes
                # com pilar (sem o pilar), sorteadas por coluna
                "plain": [pygame.transform.smoothscale(self._strip(img, a, b), (t, 2 * t))
                          for img, a, b in ((left, 0.32, 0.66), (left, 0.66, 1.0),
                                            (right, 0.0, 0.34), (right, 0.34, 0.68))],
                "left": self._sized(left, 2, 2),
                "right": self._sized(right, 2, 2),
                "low": self._sized(part["low"], 2, 1),
                # detalhes de 2 colunas: parede cheia (rachadura/sangue...), janela e o detalhe
                "details": [self._sized(self._crop_to_wall(part[n], 0.5), 2, 2)
                            for n in ("full", "window", "detail")],
            }
            if s in EXTRA_STYLES:
                style["details"] += [self._sized(self._crop_to_wall(walls[(7, i)], 0.5), 2, 2)
                                     for i in range(len(WALL_EXTRAS))]
            self.walls[s] = style
        # Portas duplas: {variante: {lado: {aberta: Surface}}}
        doors = load_door_pieces()
        self.door = {}
        for variant, col in DOOR_CLOSED.items():
            self.door[variant] = {}
            for side in ("top", "bottom", "left", "right"):
                self.door[variant][side] = {False: self._door(doors[col], side),
                                            True: self._door(doors[DOOR_OPEN], side)}

    @staticmethod
    def _door(img, side):
        t = S.TILE
        img = pygame.transform.smoothscale(img, (2 * t, 2 * t))
        if side == "bottom":      # achatada: 1 tile de altura
            return pygame.transform.smoothscale(img, (2 * t, t))
        if side == "left":        # base virada para dentro da sala (leste)
            return pygame.transform.smoothscale(pygame.transform.rotate(img, 90), (t, 2 * t))
        if side == "right":       # base virada para dentro da sala (oeste)
            return pygame.transform.smoothscale(pygame.transform.rotate(img, -90), (t, 2 * t))
        return img

    def door_image(self, door):
        theme = THEMES.get(getattr(door.room, "theme", ""), CORRIDOR)
        return self.door[theme.door][door.side][door.open]

    @staticmethod
    def _sized(img, cols, rows, trim=0.025):
        """Escala para cols x rows tiles, cortando um pouco das laterais (o
        contorno escuro da peça, que viraria uma risca no meio da parede)."""
        w, h = img.get_size()
        dx = round(w * trim)
        img = img.subsurface((dx, 0, w - 2 * dx, h))
        return pygame.transform.smoothscale(img, (cols * S.TILE, rows * S.TILE))

    @staticmethod
    def _crop_to_wall(img, ref_x):
        """Recorta a altura da peça pelo topo/base da parede medidos na coluna
        ref_x (fração da largura), cortando a ponta do pilar que sobe acima."""
        w, h = img.get_size()
        x = min(w - 1, round(w * ref_x))
        # leitura direta dos pixels (mask.from_surface numa subsurface de
        # 1 px de largura derruba o pygame-ce 2.5.8 no Windows)
        ys = [y for y in range(h) if img.get_at((x, y)).a >= 128]
        if not ys:
            return img.copy()
        return img.subsurface((0, ys[0], w, ys[-1] - ys[0] + 1)).copy()

    @staticmethod
    def _strip(img, a, b):
        """Faixa vertical entre as frações a e b da largura."""
        w, h = img.get_size()
        x0, x1 = round(w * a), round(w * b)
        return img.subsurface((x0, 0, x1 - x0, h)).copy()

    @staticmethod
    def column(img, index, width=S.TILE):
        """Fatia vertical `index` (em tiles) de uma imagem, repetindo em ciclo."""
        n = max(1, img.get_width() // width)
        x = (index % n) * width
        return img.subsurface((x, 0, width, img.get_height()))


def theme_at(dungeon, tile):
    """Tema do lugar: o da sala que contém o tile, ou o do corredor."""
    room = dungeon.room_at(tile)
    return THEMES[room.theme] if room is not None and room.theme in THEMES else CORRIDOR


def render_map(dungeon, tileset, props=None):
    """Desenha a dungeon com a arte. Retorna uma Surface do mapa.
    `props` (props.PropArt): desenha os detalhes de chão sem colisão."""
    t = S.TILE
    w, h = dungeon.width, dungeon.height
    surf = pygame.Surface((w * t, h * t))
    surf.fill(S.COLOR_WALL_TOP)
    rng = random.Random(dungeon.seed ^ 0x5EED)

    # Piso: blocos 3x3 alinhados ao grid. Cada lugar usa o piso base da sala
    # (ou do corredor) e às vezes um bloco com detalhe do tema.
    chosen = {}
    for y in range(h):
        for x in range(w):
            if dungeon.grid[y][x] != FLOOR:
                continue
            room = dungeon.room_at((x, y))
            theme = theme_at(dungeon, (x, y))
            key = (x - x % 3, y - y % 3, id(room))
            if key not in chosen:
                base = room.floor if room is not None and room.floor else rng.choice(theme.floors)
                if theme.decals and rng.random() < S.FLOOR_DECAL_CHANCE:
                    base = rng.choice(theme.decals)
                chosen[key] = base
            surf.blit(tileset.floor[chosen[key]], (x * t, y * t), ((x % 3) * t, (y % 3) * t, t, t))

    if props is not None:
        props.draw_decals(surf, dungeon)

    # Paredes frontais: parede com chão logo abaixo, por trechos contínuos
    # do mesmo estilo (o da sala embaixo) para colocar pilares nas pontas.
    for y in range(h):
        x = 0
        while x < w:
            if not is_front_wall(dungeon, x, y):
                x += 1
                continue
            style = theme_at(dungeon, (x, y + 1)).wall
            start = x
            while x < w and is_front_wall(dungeon, x, y) and theme_at(dungeon, (x, y + 1)).wall == style:
                x += 1
            _draw_wall_run(surf, dungeon, tileset.walls[style], rng, start, x - 1, y)

    bake_wall_shadows(surf, dungeon)
    init_doors(surf, dungeon, tileset)
    return surf


def _gradient(size, horizontal, reverse=False):
    """Faixa preta com alpha em degradê: WALL_SHADOW_ALPHA na borda da
    parede até 0. horizontal=True degradê na largura; reverse inverte o lado."""
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    n = w if horizontal else h
    for i in range(n):
        k = 1 - i / n
        alpha = round(S.WALL_SHADOW_ALPHA * k * k)   # queda quadrática: mais suave
        pos = n - 1 - i if reverse else i
        rect = (pos, 0, 1, h) if horizontal else (0, pos, w, 1)
        surf.fill((0, 0, 0, alpha), rect)
    return surf


def bake_wall_shadows(surf, dungeon):
    """Sombra das paredes no piso (ambient occlusion), desenhada uma vez no
    mapa pré-renderizado. Usa o grid (is_floor), então não depende das portas."""
    t = S.TILE
    top = _gradient((t, S.WALL_SHADOW_TOP), horizontal=False)
    left = _gradient((S.WALL_SHADOW_SIDE, t), horizontal=True)
    right = _gradient((S.WALL_SHADOW_SIDE, t), horizontal=True, reverse=True)
    floor = dungeon.is_floor
    for y in range(dungeon.height):
        for x in range(dungeon.width):
            if not floor(x, y):
                continue
            px, py = x * t, y * t
            if not floor(x, y - 1):
                surf.blit(top, (px, py))
            if not floor(x - 1, y):
                surf.blit(left, (px, py))
            if not floor(x + 1, y):
                surf.blit(right, (px + t - S.WALL_SHADOW_SIDE, py))


def _solid(dungeon, x, y):
    """Parede ou porta (para decidir o desenho, independente do estado da porta)."""
    return not dungeon.is_floor(x, y) or (x, y) in dungeon.door_at


def is_front_wall(dungeon, x, y):
    """Parede de verdade (não porta) com chão livre logo abaixo."""
    return not dungeon.is_floor(x, y) and not _solid(dungeon, x, y + 1)


def door_rect(door):
    """Área do mapa (em pixels) ocupada pelo desenho da porta."""
    t = S.TILE
    x0 = min(x for x, _ in door.tiles)
    y0 = min(y for _, y in door.tiles)
    if door.side == "top":       # 2 tiles de altura, como a parede alta
        return pygame.Rect(x0 * t, (y0 - 1) * t, 2 * t, 2 * t)
    if door.side == "bottom":
        return pygame.Rect(x0 * t, y0 * t, 2 * t, t)
    return pygame.Rect(x0 * t, y0 * t, t, 2 * t)


def init_doors(surf, dungeon, tileset):
    """Guarda o mapa por baixo de cada porta e desenha as portas."""
    for door in dungeon.doors:
        door.base = surf.subsurface(door_rect(door)).copy()
        draw_door(surf, door, tileset)


def draw_door(surf, door, tileset):
    """(Re)desenha a porta no estado atual. Sem tileset, usa cores sólidas."""
    rect = door_rect(door)
    if door.base is not None:
        surf.blit(door.base, rect.topleft)
    if tileset is not None:
        surf.blit(tileset.door_image(door), rect.topleft)
    else:
        t = S.TILE
        for x, y in door.tiles:
            color = S.COLOR_DOOR_OPEN if door.open else S.COLOR_DOOR_CLOSED
            surf.fill(color, (x * t, y * t, t, t))


def _draw_wall_run(surf, dungeon, style, rng, x0, x1, y):
    t = S.TILE
    detail_left = 0   # colunas restantes do detalhe (2 colunas) em andamento
    detail, detail_index = None, 0
    for x in range(x0, x1 + 1):
        tall = 0 <= y - 1 and _solid(dungeon, x, y - 1)
        if not tall:
            img = Tileset.column(style["low"], x - x0)
            surf.blit(img, (x * t, y * t))
            detail_left = 0
            continue
        if x == x0 and x1 > x0:
            img = Tileset.column(style["left"], 0)
        elif x == x1 and x1 > x0:
            img = Tileset.column(style["right"], 1)
        elif detail_left > 0:
            img = Tileset.column(detail, detail_index)
            detail_index += 1
            detail_left -= 1
        elif x + 1 < x1 and rng.random() < S.WALL_DETAIL_CHANCE:
            # o detalhe ocupa 2 colunas seguidas (cabe antes do pilar da direita)
            detail = rng.choice(style["details"])
            img = Tileset.column(detail, 0)
            detail_index, detail_left = 1, 1
        else:
            img = rng.choice(style["plain"])
        surf.blit(img, (x * t, (y - 1) * t))


def _opaque_rect(img, threshold=128):
    """Retângulo que envolve todos os pixels com alpha >= threshold."""
    rects = pygame.mask.from_surface(img, threshold).get_bounding_rects()
    if not rects:
        return pygame.Rect(0, 0, *img.get_size())
    return rects[0].unionall(rects[1:])

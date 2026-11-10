"""Recorte do tileset do hospital e montagem do mapa com a arte.

O arquivo não é uma grade uniforme: são peças soltas (pisos, paredes, portas)
com fundo transparente. Elas são encontradas pelos componentes conectados
do canal alpha, agrupadas por linha e ordenadas da esquerda para a direita.
"""
import random

import pygame

import settings as S
from dungeon import FLOOR

# Nomes das peças por linha do arquivo, da esquerda para a direita
PIECE_ROWS = [
    ["floor", "floor_blood"],
    ["wall_vent", "wall_low", "wall_pillar_left", "wall_pillar_right"],
    ["door_double_closed", "door_double_open", "door_single_left", "door_single_right"],
]
TRIM = 2          # px removidos de cada borda (início do contorno roxo)
MIN_AREA = 400    # componentes menores que isso são ruído


def _is_outline(color):
    """O contorno das peças é roxo/magenta: vermelho e azul bem acima do verde."""
    r, g, b, a = color
    return a > 0 and r - g > 25 and b - g > 20


def clean_outline(img):
    """Torna transparentes os pixels do contorno roxo e recorta a imagem
    para a área que sobrou."""
    img = img.copy()
    w, h = img.get_size()
    img.lock()
    for y in range(h):
        for x in range(w):
            c = img.get_at((x, y))
            if _is_outline(c):
                img.set_at((x, y), (c.r, c.g, c.b, 0))
    img.unlock()
    rect = _opaque_rect(img)
    return img.subsurface(rect).copy() if rect.w and rect.h else img


def find_pieces(sheet):
    """Retorna {nome: Rect} com o retângulo de cada peça no arquivo."""
    mask = pygame.mask.from_surface(sheet, 20)
    rects = []
    for comp in mask.connected_components():
        if comp.count() >= MIN_AREA:
            rects.append(comp.get_bounding_rects()[0].unionall(comp.get_bounding_rects()))
    expected = sum(len(r) for r in PIECE_ROWS)
    if len(rects) != expected:
        raise ValueError(f"tileset: esperava {expected} peças, encontrou {len(rects)}")

    # Agrupa em linhas: peças cujo centro Y fica dentro da altura da linha atual
    rects.sort(key=lambda r: r.centery)
    rows = []
    for r in rects:
        if rows and r.centery < rows[-1][0].bottom:
            rows[-1].append(r)
        else:
            rows.append([r])
    if [len(r) for r in rows] != [len(r) for r in PIECE_ROWS]:
        raise ValueError(f"tileset: linhas com {[len(r) for r in rows]} peças, "
                         f"esperava {[len(r) for r in PIECE_ROWS]}")

    pieces = {}
    for names, row in zip(PIECE_ROWS, rows):
        for name, r in zip(names, sorted(row, key=lambda r: r.x)):
            pieces[name] = r.inflate(-2 * TRIM, -2 * TRIM)
    return pieces


def load_pieces(path=None):
    """Carrega o tileset e devolve {nome: Surface} com cada peça recortada."""
    sheet = pygame.image.load(str(path or S.TILESET))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    return {name: clean_outline(sheet.subsurface(r))
            for name, r in find_pieces(sheet).items()}


class Tileset:
    """Peças já escaladas para o tamanho do grid."""

    def __init__(self, pieces=None):
        p = pieces or load_pieces()
        t = S.TILE
        self.pieces = p
        # Piso: 3x3 placas -> 3x3 tiles
        self.floor = pygame.transform.smoothscale(p["floor"], (3 * t, 3 * t))
        self.floor_blood = pygame.transform.smoothscale(p["floor_blood"], (3 * t, 3 * t))
        # Paredes altas: 2 tiles de altura. Todas recortadas pelo topo da
        # parede (não pelo topo do pilar) para os topos ficarem alinhados.
        left = self._crop_to_wall(p["wall_pillar_left"], 0.6)
        right = self._crop_to_wall(p["wall_pillar_right"], 0.4)
        # Parede lisa: várias faixas de 1 coluna tiradas do miolo das paredes
        # com pilar; sorteadas por coluna para a rachadura não se repetir.
        self.wall_plain = [
            pygame.transform.smoothscale(self._strip(img, a, b), (t, 2 * t))
            for img, a, b in ((left, 0.28, 0.60), (left, 0.60, 0.92),
                              (right, 0.08, 0.40), (right, 0.40, 0.72))
        ]
        self.wall_vent = self._tall(self._crop_to_wall(p["wall_vent"], 0.5))
        self.wall_left = self._tall(left)
        self.wall_right = self._tall(right)
        # Parede baixa: 1 tile de altura
        self.wall_low = self._scale_to_tiles(p["wall_low"], S.TILE)
        # Portas duplas: {lado: {aberta: Surface}}
        self.door = {}
        for side in ("top", "bottom", "left", "right"):
            self.door[side] = {}
            for is_open, name in ((False, "door_double_closed"), (True, "door_double_open")):
                img = pygame.transform.smoothscale(p[name], (2 * t, 2 * t))
                if side == "bottom":      # achatada: 1 tile de altura
                    img = pygame.transform.smoothscale(img, (2 * t, t))
                elif side == "left":      # base virada para dentro da sala (leste)
                    img = pygame.transform.smoothscale(pygame.transform.rotate(img, 90), (t, 2 * t))
                elif side == "right":     # base virada para dentro da sala (oeste)
                    img = pygame.transform.smoothscale(pygame.transform.rotate(img, -90), (t, 2 * t))
                self.door[side][is_open] = img

    @staticmethod
    def _scale_to_tiles(img, height):
        """Escala para a altura dada mantendo a proporção, arredondando a
        largura para um múltiplo inteiro de tiles (as peças viram colunas)."""
        w = img.get_width() * height / img.get_height()
        cols = max(1, round(w / S.TILE))
        return pygame.transform.smoothscale(img, (cols * S.TILE, height))

    @classmethod
    def _tall(cls, img):
        return cls._scale_to_tiles(img, 2 * S.TILE)

    @staticmethod
    def _crop_to_wall(img, ref_x):
        """Recorta a altura da peça pelo topo/base da parede medidos na coluna
        ref_x (fração da largura), cortando a ponta do pilar que sobe acima."""
        w, h = img.get_size()
        x = round(w * ref_x)
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
        """Fatia vertical `index` (em tiles) de uma imagem, repetindo em ciclo,
        mas sempre usando colunas que cabem inteiras na imagem."""
        n = max(1, img.get_width() // width)
        x = (index % n) * width
        return img.subsurface((x, 0, width, img.get_height()))


def render_map(dungeon, tileset):
    """Desenha a dungeon com a arte do tileset. Retorna uma Surface do mapa."""
    t = S.TILE
    w, h = dungeon.width, dungeon.height
    surf = pygame.Surface((w * t, h * t))
    surf.fill(S.COLOR_WALL_TOP)
    rng = random.Random(dungeon.seed ^ 0x5EED)

    # Piso: blocos 3x3 alinhados ao grid; alguns blocos com sangue
    blood_blocks = {(bx, by) for by in range(0, h, 3) for bx in range(0, w, 3)
                    if rng.random() < S.FLOOR_BLOOD_CHANCE}
    for y in range(h):
        for x in range(w):
            if dungeon.grid[y][x] == FLOOR:
                src = tileset.floor_blood if (x - x % 3, y - y % 3) in blood_blocks else tileset.floor
                surf.blit(src, (x * t, y * t), ((x % 3) * t, (y % 3) * t, t, t))

    # Paredes frontais: parede com chão logo abaixo. Processa por trechos
    # horizontais contínuos para colocar pilares nas pontas.
    for y in range(h):
        x = 0
        while x < w:
            if not is_front_wall(dungeon, x, y):
                x += 1
                continue
            start = x
            while x < w and is_front_wall(dungeon, x, y):
                x += 1
            _draw_wall_run(surf, dungeon, tileset, rng, start, x - 1, y)

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
        surf.blit(tileset.door[door.side][door.open], rect.topleft)
    else:
        t = S.TILE
        for x, y in door.tiles:
            color = S.COLOR_DOOR_OPEN if door.open else S.COLOR_DOOR_CLOSED
            surf.fill(color, (x * t, y * t, t, t))


def _draw_wall_run(surf, dungeon, ts, rng, x0, x1, y):
    t = S.TILE
    vent_left = 0   # colunas restantes da peça com ventilação em andamento
    vent_index = 0
    for x in range(x0, x1 + 1):
        tall = 0 <= y - 1 and _solid(dungeon, x, y - 1)
        if not tall:
            img = Tileset.column(ts.wall_low, x - x0)
            surf.blit(img, (x * t, y * t))
            vent_left = 0
            continue
        if x == x0 and x1 > x0:
            img = Tileset.column(ts.wall_left, 0)
        elif x == x1 and x1 > x0:
            n = max(1, ts.wall_right.get_width() // t)
            img = Tileset.column(ts.wall_right, n - 1)
        elif vent_left > 0:
            img = Tileset.column(ts.wall_vent, vent_index)
            vent_index += 1
            vent_left -= 1
        elif x + 1 < x1 and rng.random() < S.WALL_VENT_CHANCE:
            # a ventilação ocupa 2 colunas seguidas (cabe antes do pilar da direita)
            vent_index, vent_left = 0, 1
            img = Tileset.column(ts.wall_vent, vent_index)
            vent_index += 1
        else:
            img = rng.choice(ts.wall_plain)
        surf.blit(img, (x * t, (y - 1) * t))


def _opaque_rect(img, threshold=128):
    """Retângulo que envolve todos os pixels com alpha >= threshold."""
    rects = pygame.mask.from_surface(img, threshold).get_bounding_rects()
    if not rects:
        return pygame.Rect(0, 0, *img.get_size())
    return rects[0].unionall(rects[1:])

"""Recorte do sprite sheet do personagem em animações.

O sheet tem 8 colunas x 5 linhas, mas a altura das células não é inteira
(1024 / 5 = 204.8), então as fronteiras são detectadas pela projeção do
canal alpha em vez de divisão fixa.
"""
import pygame

from settings import (ATTACK_SHEET, CHARACTER_SHEET, DAMAGE_SHEET, HEAL_SHEET, MEDKIT_SHEET, PICKUP_SHEET,
                      PLAYER_SPRITE_HEIGHT, ZOMBIE_SHEET,
                      ZOMBIE_SIZE)

# Ordem das linhas no sheet
ROW_NAMES = ["idle", "walk_right", "walk_left", "walk_up", "walk_down"]
COLS = 8
ALPHA_THRESHOLD = 40
MIN_GAP = 6  # vãos menores que isso são considerados parte do mesmo bloco


def _runs(counts, min_gap=MIN_GAP):
    """Retorna lista de (inicio, fim) de trechos com contagem > 0,
    juntando trechos separados por vãos pequenos."""
    runs = []
    start = None
    for i, c in enumerate(counts):
        if c > 0 and start is None:
            start = i
        elif c == 0 and start is not None:
            runs.append([start, i])
            start = None
    if start is not None:
        runs.append([start, len(counts)])
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [tuple(r) for r in merged]


def _keep_largest(runs, n):
    """Mantém os n trechos maiores (descarta ruído), em ordem."""
    if len(runs) <= n:
        return runs
    biggest = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:n]
    return sorted(biggest)


def _bands(runs, total):
    """Converte trechos ocupados em faixas que cobrem todo o espaço,
    dividindo os vãos ao meio."""
    bands = []
    for i, (s, e) in enumerate(runs):
        lo = 0 if i == 0 else (runs[i - 1][1] + s) // 2
        hi = total if i == len(runs) - 1 else (e + runs[i + 1][0]) // 2
        bands.append((lo, hi))
    return bands


def _row_counts(mask, x, y, w, h):
    """Quantidade de pixels opacos em cada linha do retângulo."""
    line = pygame.mask.Mask((w, 1), fill=True)
    return [mask.overlap_area(line, (x, y + j)) for j in range(h)]


def _col_counts(mask, x, y, w, h):
    """Quantidade de pixels opacos em cada coluna do retângulo."""
    line = pygame.mask.Mask((1, h), fill=True)
    return [mask.overlap_area(line, (x + i, y)) for i in range(w)]


def slice_sheet(sheet):
    """Retorna {nome: [pygame.Rect, ...]} com o retângulo de cada frame
    no sheet. Todos os frames de uma mesma animação têm o mesmo tamanho
    e mesma posição relativa (pés alinhados)."""
    w, h = sheet.get_size()
    mask = pygame.mask.from_surface(sheet, ALPHA_THRESHOLD)

    row_runs = _keep_largest(_runs(_row_counts(mask, 0, 0, w, h)), len(ROW_NAMES))
    if len(row_runs) == len(ROW_NAMES):
        row_bands = _bands(row_runs, h)
    else:  # fallback: divisão uniforme
        row_bands = [(round(i * h / len(ROW_NAMES)), round((i + 1) * h / len(ROW_NAMES)))
                     for i in range(len(ROW_NAMES))]

    result = {}
    for name, (y0, y1) in zip(ROW_NAMES, row_bands):
        bh = y1 - y0
        col_runs = _keep_largest(_runs(_col_counts(mask, 0, y0, w, bh)), COLS)
        if len(col_runs) == COLS:
            col_bands = _bands(col_runs, w)
        else:
            col_bands = [(round(i * w / COLS), round((i + 1) * w / COLS)) for i in range(COLS)]

        # bbox de cada frame relativo à sua célula; depois a união
        cells, rel = [], []
        for x0, x1 in col_bands:
            cell = pygame.Rect(x0, y0, x1 - x0, bh)
            bb = _cell_bbox(mask, cell)
            cells.append(cell)
            rel.append(bb.move(-cell.x, -cell.y))
        union = rel[0].unionall(rel[1:])
        frames = []
        for cell in cells:
            r = union.move(cell.x, cell.y).clip(pygame.Rect(0, 0, w, h))
            frames.append(r)
        result[name] = frames
    return result


def _cell_bbox(mask, cell):
    """Bounding box dos pixels opacos dentro de uma célula."""
    rows = _row_counts(mask, cell.x, cell.y, cell.w, cell.h)
    cols = _col_counts(mask, cell.x, cell.y, cell.w, cell.h)
    ys = [i for i, c in enumerate(rows) if c]
    xs = [i for i, c in enumerate(cols) if c]
    if not xs or not ys:
        return cell.copy()
    return pygame.Rect(cell.x + xs[0], cell.y + ys[0], xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1)


def load_animations(target_height=PLAYER_SPRITE_HEIGHT, raw=False):
    """Carrega as animações do personagem.

    Retorna {nome: [Surface, ...]}. Todas as animações usam o mesmo fator
    de escala (baseado no frame mais alto) para o personagem não mudar de
    tamanho entre animações. Com raw=True, devolve os frames sem escalar.
    """
    sheet = pygame.image.load(str(CHARACTER_SHEET))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    rects = slice_sheet(sheet)

    tallest = max(r.h for frames in rects.values() for r in frames)
    scale = 1.0 if raw else target_height / tallest

    anims = {}
    for name, frames in rects.items():
        surfs = []
        for r in frames:
            img = sheet.subsurface(r).copy()
            if scale != 1.0:
                size = (max(1, round(r.w * scale)), max(1, round(r.h * scale)))
                img = pygame.transform.smoothscale(img, size)
            surfs.append(img)
        anims[name] = surfs
    # Poses paradas viradas para os lados/costas: o 1º quadro de cada
    # caminhada é a pose com os pés juntos ("idle" só existe de frente).
    for d in ("right", "left", "up"):
        anims[f"idle_{d}"] = [anims[f"walk_{d}"][0]]
    return anims


# --------------------------------------------------------------------- zumbi
# Sheet do zumbi: grade uniforme de 32x32, fundo magenta. (linha, nome, quadros)
ZOMBIE_ROWS = [
    (0, "idle", 2),
    (1, "walk_right", 4),
    (2, "walk_left", 4),
    (3, "walk_up", 4),
    (4, "walk_down", 4),
    (5, "emerge", 8),
]
ZOMBIE_FRAME = 32


def is_magenta(color):
    """Fundo magenta (e a franja quase-magenta na borda dos quadros)."""
    return color.r > 200 and color.b > 200 and color.g < 80


def is_purple_fringe(color):
    """Pixels de transição entre o magenta e o desenho: vermelho e azul
    parecidos e bem acima do verde (o sangue, vermelho, não entra)."""
    lo = min(color.r, color.b)
    return lo >= 25 and color.g < 0.5 * lo


def _remove_magenta(img):
    """Fundo magenta vira transparente. A franja roxa clara também; a
    escura vira contorno quase preto (faz parte do traço do desenho)."""
    w, h = img.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)   # garante canal alpha
    out.blit(img, (0, 0))
    img = out
    img.lock()
    for y in range(h):
        for x in range(w):
            c = img.get_at((x, y))
            if is_magenta(c):
                img.set_at((x, y), (0, 0, 0, 0))
            elif is_purple_fringe(c):
                if max(c.r, c.b) > 90:
                    img.set_at((x, y), (0, 0, 0, 0))
                else:
                    img.set_at((x, y), (22, 16, 20, 255))
    img.unlock()
    return img


def load_zombie_animations(size=ZOMBIE_SIZE, raw=False):
    """{nome: [Surface, ...]} do zumbi. Escala por vizinho mais próximo
    (pixel art nítida). raw=True devolve os quadros de 32x32 sem escalar."""
    sheet = _remove_magenta(pygame.image.load(str(ZOMBIE_SHEET)))
    f = ZOMBIE_FRAME
    anims = {}
    for row, name, count in ZOMBIE_ROWS:
        frames = []
        for col in range(count):
            img = sheet.subsurface((col * f, row * f, f, f)).copy()
            if not raw and size != f:
                img = pygame.transform.scale(img, (size, size))
            frames.append(img)
        anims[name] = frames
    return anims


# -------------------------------------------------------------------- ataque
# Sheet de ataque: 5 linhas x 9 quadros, ~159 px de passo. Linha -> animação.
# A linha 0 repete a 4 (de frente). A linha 3 (esquerda) tem o rastro do golpe
# indo para a direita, então "attack_left" é a linha 1 (direita) espelhada.
ATTACK_ROWS = {1: "attack_right", 2: "attack_up", 4: "attack_down"}
ATTACK_SHEET_ROWS = 5
ATTACK_FRAMES = 9
ATTACK_NARROW = 115   # quadros sem rastro do golpe têm menos que isso de largura


def is_attack_outline(color):
    """Contorno magenta do sheet de ataque: roxo saturado (verde quase zero).
    O rastro rosa do golpe tem verde alto e não entra."""
    lo = min(color.r, color.b)
    return lo >= 25 and color.g < 0.3 * lo


def _clean_attack_outline(img):
    """Contorno claro vira transparente; o escuro vira traço quase preto."""
    img = img.copy()
    w, h = img.get_size()
    img.lock()
    for y in range(h):
        for x in range(w):
            c = img.get_at((x, y))
            if c.a and is_attack_outline(c):
                if max(c.r, c.b) > 90:
                    img.set_at((x, y), (0, 0, 0, 0))
                else:
                    img.set_at((x, y), (22, 16, 20, c.a))
    img.unlock()
    return img


def _attack_columns(counts):
    """Fronteiras (x0, x1) dos 9 quadros de uma linha do sheet de ataque.

    Os quadros sem rastro dão os centros (e o passo da grade); entre dois
    centros vizinhos a fronteira fica no "vale" da projeção alpha — os
    rastros dos quadros 5-6 encostam no quadro seguinte."""
    runs = _runs(counts, min_gap=3)
    narrow = [(a + b) / 2 for a, b in runs if b - a <= ATTACK_NARROW]
    pitch0 = 159.5
    c0 = narrow[0]
    pts = [(round((c - c0) / pitch0), c) for c in narrow]
    # regressão linear: centro = a + b * índice
    n = len(pts)
    mk = sum(k for k, _ in pts) / n
    mc = sum(c for _, c in pts) / n
    b = sum((k - mk) * (c - mc) for k, c in pts) / sum((k - mk) ** 2 for k, _ in pts)
    a = mc - b * mk
    centers = [a + b * k for k in range(ATTACK_FRAMES)]
    bounds = [0]
    for k in range(ATTACK_FRAMES - 1):
        lo = int(centers[k] + 0.25 * b)
        hi = int(centers[k + 1] - 0.25 * b)
        best = min(counts[lo:hi])
        xs = [x for x in range(lo, hi) if counts[x] == best]
        bounds.append(xs[len(xs) // 2])
    bounds.append(len(counts))
    return list(zip(bounds[:-1], bounds[1:]))


def _anchored(img, anchor_x):
    """Põe margem dos lados para a âncora (x) ficar no centro da imagem."""
    w, h = img.get_size()
    half = max(anchor_x, w - anchor_x)
    out = pygame.Surface((2 * half, h), pygame.SRCALPHA)
    out.blit(img, (half - anchor_x, 0))
    return out


def load_attack_animations(target_height=PLAYER_SPRITE_HEIGHT, raw=False):
    # target_height: altura de "attack_down" na tela. O jogo passa a altura
    # do "idle" (o desenho do sheet de ataque é menor que o do sheet de andar).
    """{attack_<direção>: [Surface, ...]} do ataque com faca.

    Cada quadro é recortado da base da linha até o topo do desenho e
    centralizado pelo cabelo (faixa de cima, sem faca nem rastro), para
    `Player.draw` poder desenhar pelo meio da base, como nas outras animações.
    """
    sheet = pygame.image.load(str(ATTACK_SHEET))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    w, h = sheet.get_size()
    mask = pygame.mask.from_surface(sheet, 40)
    rows = _keep_largest(_runs(_row_counts(mask, 0, 0, w, h)), ATTACK_SHEET_ROWS)

    scale = None if not raw else 1.0

    anims = {}
    for row, name in ATTACK_ROWS.items():
        y0, y1 = rows[row]
        counts = _col_counts(mask, 0, y0, w, y1 - y0)
        frames = []
        for x0, x1 in _attack_columns(counts):
            cell = _clean_attack_outline(sheet.subsurface((x0, y0, x1 - x0, y1 - y0)))
            bb = _opaque_bbox(cell)
            # recorte: largura do desenho, do topo do desenho até a base da linha
            crop = cell.subsurface((bb.x, bb.y, bb.w, cell.get_height() - bb.y))
            hair = _opaque_bbox(crop.subsurface((0, 0, bb.w, max(1, round(bb.h * 0.22)))))
            frames.append(_anchored(crop.copy(), round(hair.centerx)))
        anims[name] = frames
    if scale is None:   # mesma escala para todas as direções, pela altura de "attack_down"
        scale = target_height / anims["attack_down"][0].get_height()
    if scale != 1.0:
        for name, frames in anims.items():
            anims[name] = [pygame.transform.smoothscale(
                f, (max(1, round(f.get_width() * scale)), max(1, round(f.get_height() * scale))))
                for f in frames]
    anims["attack_left"] = [pygame.transform.flip(f, True, False) for f in anims["attack_right"]]
    return anims


# ---------------------------------------------------------------------- dano
# Sheet de dano: 8 linhas numa grade de 6 colunas (1024 / 6 px de passo).
# Linhas 0-3: dano curto (4 quadros); linhas 4-7: dano com empurrão (6 quadros:
# silhueta branca, recuando, no ar, caindo, caído, de pé). Linha -> animação;
# as direções que faltam (ou estão confusas no sheet) são espelhadas.
DAMAGE_COLS = 6
DAMAGE_SHEET_ROWS = 8
DAMAGE_ROWS = {
    0: ("hurt_light_down", 4),
    2: ("hurt_light_left", 4),
    3: ("hurt_light_up", 4),
    4: ("hurt_down", 6),
    5: ("hurt_right", 6),
    7: ("hurt_up", 6),
}
DAMAGE_MIRROR = {"hurt_light_right": "hurt_light_left", "hurt_left": "hurt_right"}
HURT_FALLEN_FRAME = 4    # quadro "caído" do empurrão (o personagem morto fica nele)


def load_damage_animations(target_height=PLAYER_SPRITE_HEIGHT, raw=False):
    """{hurt_<direção>: [...], hurt_light_<direção>: [...]} do personagem levando dano.

    Mesmo esquema do ataque: cada quadro vai do topo do desenho até a base
    da linha e é centralizado pelo cabelo, para desenhar pelo meio da base.
    target_height: altura do último quadro de "hurt_down" (de pé) na tela."""
    sheet = pygame.image.load(str(DAMAGE_SHEET))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    w, h = sheet.get_size()
    mask = pygame.mask.from_surface(sheet, 40)
    rows = _keep_largest(_runs(_row_counts(mask, 0, 0, w, h)), DAMAGE_SHEET_ROWS)

    anims = {}
    for row, (name, count) in DAMAGE_ROWS.items():
        y0, y1 = rows[row]
        frames = []
        for c in range(count):
            x0, x1 = round(c * w / DAMAGE_COLS), round((c + 1) * w / DAMAGE_COLS)
            cell = _clean_attack_outline(sheet.subsurface((x0, y0, x1 - x0, y1 - y0)))
            bb = _opaque_bbox(cell)
            crop = cell.subsurface((bb.x, bb.y, bb.w, cell.get_height() - bb.y))
            hair = _opaque_bbox(crop.subsurface((0, 0, bb.w, max(1, round(bb.h * 0.22)))))
            frames.append(_anchored(crop.copy(), round(hair.centerx)))
        anims[name] = frames
    if not raw:
        scale = target_height / anims["hurt_down"][-1].get_height()
        for name, frames in anims.items():
            anims[name] = [pygame.transform.smoothscale(
                f, (max(1, round(f.get_width() * scale)), max(1, round(f.get_height() * scale))))
                for f in frames]
    for name, src in DAMAGE_MIRROR.items():
        anims[name] = [pygame.transform.flip(f, True, False) for f in anims[src]]
    return anims


# ----------------------------------------------------------------- kit médico
# Sheets do personagem pegando e usando o kit: grade uniforme, uma linha por
# direção (de frente, direita, esquerda, costas — a mesma ordem do sheet de andar).
KIT_DIRS = ("down", "right", "left", "up")
PICKUP_GRID = (4, 6)     # linhas, colunas
HEAL_GRID = (4, 8)


def _load_grid_animation(path, grid, prefix, target_height, raw=False):
    """{<prefix>_<direção>: [Surface, ...]} de um sheet em grade uniforme.

    A grade é fixa (as linhas do sheet de cura se encostam por causa do
    brilho). Em cada linha, o "chão" é o pixel opaco mais baixo da linha; cada
    quadro vai do topo do desenho até esse chão e é centralizado pelo cabelo,
    como no ataque. A escala faz o último quadro de frente (de pé) ter
    `target_height`."""
    sheet = pygame.image.load(str(path))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    w, h = sheet.get_size()
    rows, cols = grid
    mask = pygame.mask.from_surface(sheet, 40)
    anims = {}
    for r, d in enumerate(KIT_DIRS):
        y0, y1 = round(r * h / rows), round((r + 1) * h / rows)
        counts = _row_counts(mask, 0, y0, w, y1 - y0)
        ground = y0 + max(i for i, c in enumerate(counts) if c) + 1
        frames = []
        for c in range(cols):
            x0, x1 = round(c * w / cols), round((c + 1) * w / cols)
            cell = sheet.subsurface((x0, y0, x1 - x0, ground - y0))
            bb = _opaque_bbox(cell)
            crop = cell.subsurface((bb.x, bb.y, bb.w, cell.get_height() - bb.y))
            hair = _opaque_bbox(crop.subsurface((0, 0, bb.w, max(1, round(bb.h * 0.22)))))
            frames.append(_anchored(crop.copy(), round(hair.centerx)))
        anims[f"{prefix}_{d}"] = frames
    if not raw:
        scale = target_height / anims[f"{prefix}_down"][-1].get_height()
        for name, frames in anims.items():
            anims[name] = [pygame.transform.smoothscale(
                f, (max(1, round(f.get_width() * scale)), max(1, round(f.get_height() * scale))))
                for f in frames]
    return anims


def load_kit_animations(target_height=PLAYER_SPRITE_HEIGHT, raw=False):
    """Animações do personagem com o kit: `pickup_<dir>` (pegar e guardar,
    6 quadros) e `heal_<dir>` (usar, 8 quadros)."""
    anims = _load_grid_animation(PICKUP_SHEET, PICKUP_GRID, "pickup", target_height, raw)
    anims.update(_load_grid_animation(HEAL_SHEET, HEAL_GRID, "heal", target_height, raw))
    return anims


MEDKIT_ROW = 1           # linha com brilho verde (mais fácil de ver no escuro)
MEDKIT_FRAMES = 8


def load_medkit_item(width=None, raw=False):
    """Kit no chão girando: (quadros, ícone). Colunas pela projeção do alpha.
    `width`: largura do quadro mais largo na tela (padrão MEDKIT_SIZE)."""
    from settings import MEDKIT_SIZE
    width = width or MEDKIT_SIZE
    sheet = pygame.image.load(str(MEDKIT_SHEET))
    if pygame.display.get_surface() is not None:
        sheet = sheet.convert_alpha()
    w, h = sheet.get_size()
    mask = pygame.mask.from_surface(sheet, 40)
    rows = _keep_largest(_runs(_row_counts(mask, 0, 0, w, h)), 2)

    def row_frames(row):
        y0, y1 = rows[row]
        cols = _keep_largest(_runs(_col_counts(mask, 0, y0, w, y1 - y0), min_gap=3), MEDKIT_FRAMES)
        return [sheet.subsurface((x0, y0, x1 - x0, y1 - y0)).copy() for x0, x1 in cols]

    frames = [_anchored(f, f.get_width() // 2) for f in row_frames(MEDKIT_ROW)]
    plain = row_frames(0)[0]
    if raw:
        return frames, plain
    scale = width / max(f.get_width() for f in frames)
    frames = [pygame.transform.smoothscale(
        f, (max(1, round(f.get_width() * scale)), max(1, round(f.get_height() * scale)))) for f in frames]
    icon_scale = 20 / plain.get_height()
    icon = pygame.transform.smoothscale(
        plain, (round(plain.get_width() * icon_scale), round(plain.get_height() * icon_scale)))
    return frames, icon


def _opaque_bbox(img, threshold=40):
    """Retângulo dos pixels com alpha >= threshold (lendo linhas/colunas)."""
    w, h = img.get_size()
    mask = pygame.mask.from_surface(img, threshold)
    rects = mask.get_bounding_rects()
    if not rects:
        return pygame.Rect(0, 0, w, h)
    return rects[0].unionall(rects[1:])

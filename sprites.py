"""Recorte do sprite sheet do personagem em animações.

O sheet tem 8 colunas x 5 linhas, mas a altura das células não é inteira
(1024 / 5 = 204.8), então as fronteiras são detectadas pela projeção do
canal alpha em vez de divisão fixa.
"""
import pygame

from settings import CHARACTER_SHEET, PLAYER_SPRITE_HEIGHT

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
    return anims

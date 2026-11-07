"""Geração procedural de dungeon (BSP: salas + corredores) a partir de uma seed."""
import random
import zlib
from dataclasses import dataclass, field

WALL = 0
FLOOR = 1

MIN_LEAF = 14     # tamanho mínimo de uma folha da BSP (tiles)
MIN_ROOM = 6      # tamanho mínimo de uma sala (tiles)
CORRIDOR_WIDTHS = (2, 3)  # larguras possíveis dos corredores (mínimo 2)


def normalize_seed(seed):
    """Aceita int ou string. Strings numéricas viram int; outras usam crc32
    (estável entre execuções, ao contrário de hash())."""
    if isinstance(seed, int):
        return seed
    s = str(seed).strip()
    try:
        return int(s)
    except ValueError:
        return zlib.crc32(s.encode("utf-8"))


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)


@dataclass
class Dungeon:
    seed: int
    width: int
    height: int
    grid: list = field(default_factory=list)   # grid[y][x]
    rooms: list = field(default_factory=list)

    def is_walkable(self, tx, ty):
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.grid[ty][tx] == FLOOR
        return False

    @property
    def spawn(self):
        return self.rooms[0].center


class _Leaf:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.left = self.right = None
        self.room = None

    def split(self, rng):
        if self.left or self.right:
            return False
        # Decide orientação: corta a dimensão maior; se parecidas, aleatório
        if self.w > self.h and self.w / self.h >= 1.25:
            horizontal = False
        elif self.h > self.w and self.h / self.w >= 1.25:
            horizontal = True
        else:
            horizontal = rng.random() < 0.5
        size = self.h if horizontal else self.w
        if size < MIN_LEAF * 2:
            return False
        cut = rng.randint(MIN_LEAF, size - MIN_LEAF)
        if horizontal:
            self.left = _Leaf(self.x, self.y, self.w, cut)
            self.right = _Leaf(self.x, self.y + cut, self.w, self.h - cut)
        else:
            self.left = _Leaf(self.x, self.y, cut, self.h)
            self.right = _Leaf(self.x + cut, self.y, self.w - cut, self.h)
        return True

    def leaves(self):
        if not self.left and not self.right:
            yield self
        else:
            for c in (self.left, self.right):
                if c:
                    yield from c.leaves()

    def any_room(self, rng):
        """Uma sala qualquer dentro deste ramo (usada para ligar ramos)."""
        if self.room:
            return self.room
        rooms = [l.room for l in self.leaves() if l.room]
        return rng.choice(rooms)


def generate(seed, width=80, height=60):
    seed = normalize_seed(seed)
    rng = random.Random(seed)
    grid = [[WALL] * width for _ in range(height)]
    d = Dungeon(seed, width, height, grid)

    # 1) Particiona o mapa (deixando 1 tile de borda de parede)
    root = _Leaf(1, 1, width - 2, height - 2)
    pending = [root]
    while pending:
        leaf = pending.pop()
        # folhas grandes sempre dividem; médias dividem com 75% de chance
        big = leaf.w > MIN_LEAF * 3 or leaf.h > MIN_LEAF * 3
        if (big or rng.random() < 0.75) and leaf.split(rng):
            pending.extend([leaf.left, leaf.right])

    # 2) Cria uma sala dentro de cada folha
    for leaf in root.leaves():
        rw = rng.randint(MIN_ROOM, leaf.w - 2)
        rh = rng.randint(MIN_ROOM, leaf.h - 2)
        rx = rng.randint(leaf.x + 1, leaf.x + leaf.w - rw - 1)
        ry = rng.randint(leaf.y + 1, leaf.y + leaf.h - rh - 1)
        leaf.room = Room(rx, ry, rw, rh)
        d.rooms.append(leaf.room)
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                grid[y][x] = FLOOR

    # 3) Liga ramos irmãos com corredores (garante conectividade total)
    def connect(node):
        if not node.left or not node.right:
            return
        connect(node.left)
        connect(node.right)
        _corridor(grid, rng, node.left.any_room(rng).center, node.right.any_room(rng).center)

    connect(root)
    return d


def _carve(grid, x, y, thick):
    for dy in range(thick):
        for dx in range(thick):
            yy, xx = y + dy, x + dx
            if 0 < yy < len(grid) - 1 and 0 < xx < len(grid[0]) - 1:
                grid[yy][xx] = FLOOR


def _corridor(grid, rng, a, b):
    """Corredor em L entre os pontos a e b, com largura de CORRIDOR_WIDTHS."""
    (x1, y1), (x2, y2) = a, b
    thick = rng.choice(CORRIDOR_WIDTHS)
    if rng.random() < 0.5:
        corner = (x2, y1)
    else:
        corner = (x1, y2)
    for (sx, sy), (ex, ey) in (((x1, y1), corner), (corner, (x2, y2))):
        if sx == ex:
            for y in range(min(sy, ey), max(sy, ey) + 1):
                _carve(grid, sx, y, thick)
        else:
            for x in range(min(sx, ex), max(sx, ex) + 1):
                _carve(grid, x, sy, thick)

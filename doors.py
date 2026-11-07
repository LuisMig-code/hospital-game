"""Portas: onde ficam (geração) e abrir/fechar (interação)."""
from dataclasses import dataclass, field

from dungeon import WALL

# Para cada lado da sala: (passo ao longo da parede, passo para fora da sala)
SIDES = {
    "top": ((1, 0), (0, -1)),
    "bottom": ((1, 0), (0, 1)),
    "left": ((0, 1), (-1, 0)),
    "right": ((0, 1), (1, 0)),
}

DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}


@dataclass(eq=False)
class Door:
    tiles: list                 # 2 tiles contíguos, na linha da parede
    side: str                   # lado da sala: top, bottom, left, right
    open: bool = False
    base: object = field(default=None, repr=False)  # pedaço do mapa por baixo (desenho)


def _wall_line(room, side):
    """Tiles da linha/coluna de parede logo fora da sala, no lado dado."""
    if side == "top":
        return [(x, room.y - 1) for x in range(room.x, room.x + room.w)]
    if side == "bottom":
        return [(x, room.y + room.h) for x in range(room.x, room.x + room.w)]
    if side == "left":
        return [(room.x - 1, y) for y in range(room.y, room.y + room.h)]
    return [(room.x + room.w, y) for y in range(room.y, room.y + room.h)]


def _runs(tiles, pred):
    """Trechos contínuos de tiles que satisfazem pred."""
    runs, cur = [], []
    for t in tiles:
        if pred(t):
            cur.append(t)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def place_doors(dungeon, rng):
    """Coloca portas duplas (fechadas) nas entradas das salas."""
    floor = dungeon.is_floor
    for room in dungeon.rooms:
        for side, ((ax, ay), (ox, oy)) in SIDES.items():
            line = _wall_line(room, side)
            # abertura: chão na linha da parede com corredor do lado de fora
            openings = _runs(line, lambda t: floor(*t) and floor(t[0] + ox, t[1] + oy))
            for run in openings:
                if len(run) not in (2, 3):
                    continue
                first, last = run[0], run[-1]
                before = (first[0] - ax, first[1] - ay)
                after = (last[0] + ax, last[1] + ay)
                # pontas da abertura são parede, e o corredor entra perpendicular
                if floor(*before) or floor(*after):
                    continue
                if floor(before[0] + ox, before[1] + oy) or floor(after[0] + ox, after[1] + oy):
                    continue
                # o lado de dentro da abertura é a sala
                if not all(floor(x - ox, y - oy) for x, y in run):
                    continue
                if any(t in dungeon.door_at for t in run):
                    continue
                if len(run) == 3:
                    # estreita para 2: uma das pontas vira parede
                    drop = run.pop(0) if rng.random() < 0.5 else run.pop()
                    dungeon.grid[drop[1]][drop[0]] = WALL
                door = Door(tiles=list(run), side=side)
                dungeon.doors.append(door)
                for t in run:
                    dungeon.door_at[t] = door
    _fill_nubs(dungeon)


def _fill_nubs(dungeon):
    """Estreitar aberturas de 3 para 2 pode deixar "tocos" de chão com 1 tile
    de largura (ex.: corredor curto entre duas portas). Todo chão que não faz
    parte de nenhum bloco 2x2 de chão vira parede."""
    floor = dungeon.is_floor
    changed = True
    while changed:
        changed = False
        for y in range(dungeon.height):
            for x in range(dungeon.width):
                if not floor(x, y) or (x, y) in dungeon.door_at:
                    continue
                in_block = any(floor(x + ox, y + oy) and floor(x + ox + 1, y + oy)
                               and floor(x + ox, y + oy + 1) and floor(x + ox + 1, y + oy + 1)
                               for ox in (-1, 0) for oy in (-1, 0))
                if not in_block:
                    dungeon.grid[y][x] = WALL
                    changed = True


def try_toggle(dungeon, player):
    """Abre/fecha a porta à frente do personagem (ou onde ele está).

    Retorna (resultado, porta): resultado é "abriu", "fechou", "bloqueada"
    (não dá para fechar com o personagem na porta) ou None (nenhuma porta).
    """
    dx, dy = DIRS[player.facing]
    front = (player.tile[0] + dx, player.tile[1] + dy)
    door = dungeon.door_at.get(front) or dungeon.door_at.get(player.tile)
    if door is None:
        return None, None
    if door.open:
        occupied = {player.tile, player.target}
        if occupied & set(door.tiles):
            return "bloqueada", door
        door.open = False
        return "fechou", door
    door.open = True
    return "abriu", door



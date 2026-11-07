"""Campo de visão (FOV) com linha de visão e memória do que já foi descoberto."""


def _line(a, b):
    """Tiles de uma linha de Bresenham de a até b (inclusive)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        yield (x0, y0)
        if (x0, y0) == (x1, y1):
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def in_radius(dx, dy, radius):
    # radius² + radius deixa o círculo mais "redondo" no grid
    return dx * dx + dy * dy <= radius * radius + radius


def compute_fov(dungeon, origin, radius):
    """Conjunto de tiles visíveis a partir de origin.

    Um tile é visível se está no raio e todos os tiles entre a origem e ele
    são chão. O próprio tile pode ser parede: as paredes que cercam a área
    aparecem, mas o que está atrás delas não.
    """
    ox, oy = origin
    visible = {origin}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if not in_radius(dx, dy, radius):
                continue
            target = (ox + dx, oy + dy)
            if not (0 <= target[0] < dungeon.width and 0 <= target[1] < dungeon.height):
                continue
            path = list(_line(origin, target))
            if all(dungeon.is_walkable(x, y) for x, y in path[1:-1]):
                visible.add(target)

    # Paredes altas ocupam 2 tiles: a face frontal (parede com chão abaixo)
    # e o tile de cima. Se a face é visível, a parte de cima também é.
    for x, y in list(visible):
        if (not dungeon.is_walkable(x, y) and dungeon.is_walkable(x, y + 1)
                and y > 0 and not dungeon.is_walkable(x, y - 1)):
            visible.add((x, y - 1))
    return visible


class Vision:
    """Guarda o que o personagem vê agora e o que já descobriu."""

    def __init__(self, dungeon, radius):
        self.dungeon = dungeon
        self.radius = radius
        self.visible = set()
        self.explored = set()
        self.origin = None

    def update(self, origin):
        """Recalcula se o personagem mudou de tile. Retorna os tiles
        descobertos pela primeira vez (vazio se nada mudou)."""
        if origin == self.origin:
            return set()
        self.origin = origin
        self.visible = compute_fov(self.dungeon, origin, self.radius)
        new = self.visible - self.explored
        self.explored |= new
        return new

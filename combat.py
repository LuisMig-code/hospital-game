"""Combate: área de dano do golpe, aplicação nos zumbis e números de dano.

O golpe acerta o tile à frente do personagem (o impacto) e espalha em volta:
distância de Chebyshev ao impacto 0 → ATTACK_DAMAGE[0] (11), 1 → [1] (6),
2 → [2] (4). Para a frente só alcança ATTACK_REACH (2) tiles a partir do
personagem. O personagem não se acerta. Só leva dano quem o personagem
está vendo (parede bloqueia o golpe, igual à visão).

Sem pygame aqui: a parte de desenho dos números fica em main.py.
"""
import settings as S


def damage_map(impact, player_tile):
    """{tile: dano} do golpe com impacto em `impact`.

    Para a frente (direção do personagem até o impacto) o golpe só alcança
    ATTACK_REACH tiles a partir do personagem; para os lados e para trás
    vale a área inteira em volta do impacto."""
    ix, iy = impact
    px, py = player_tile
    fx, fy = ix - px, iy - py                     # direção para onde ele olha
    spread = len(S.ATTACK_DAMAGE) - 1
    out = {}
    for dy in range(-spread, spread + 1):
        for dx in range(-spread, spread + 1):
            tile = (ix + dx, iy + dy)
            ahead = (tile[0] - px) * fx + (tile[1] - py) * fy
            if tile != (px, py) and ahead <= S.ATTACK_REACH:
                out[tile] = S.ATTACK_DAMAGE[max(abs(dx), abs(dy))]
    return out


def apply_attack(horde, impact, player_tile, visible):
    """Aplica o golpe nos zumbis. Devolve [(zumbi, dano, morreu)]."""
    dmg = damage_map(impact, player_tile)
    hits = []
    for z in horde.zombies:
        if not z.solid:                       # enterrado, morrendo: não leva dano
            continue
        tile = z.pixel_tile()                 # onde está desenhado agora
        if tile in dmg and tile in visible:
            died = z.hit(dmg[tile])
            hits.append((z, dmg[tile], died))
    return hits


class FloatingText:
    """Número de dano que sobe e some (posição em pixels do mundo)."""

    RISE = 28          # pixels que sobe durante a vida

    def __init__(self, x, y, text, color):
        self.x, self.y0 = x, y
        self.text, self.color = text, color
        self.age = 0.0

    @property
    def done(self):
        return self.age >= S.DAMAGE_TEXT_TIME

    @property
    def progress(self):
        return min(1.0, self.age / S.DAMAGE_TEXT_TIME)

    @property
    def y(self):
        p = self.progress
        return self.y0 - self.RISE * (1 - (1 - p) ** 2)   # sobe rápido e desacelera

    @property
    def alpha(self):
        p = self.progress
        return 255 if p < 0.5 else round(255 * (1 - (p - 0.5) / 0.5))

    def update(self, dt):
        self.age += dt


def damage_color(damage):
    """Cor do número pela força do golpe."""
    if damage >= S.ATTACK_DAMAGE[0]:
        return (255, 80, 60)
    if damage >= S.ATTACK_DAMAGE[1]:
        return (255, 170, 60)
    return (240, 230, 200)


def texts_for(hits):
    """Números de dano (um por zumbi atingido), em cima da cabeça."""
    out = []
    for z, dmg, _ in hits:
        out.append(FloatingText(z.x, z.feet_y() - S.ZOMBIE_SIZE + 2, f"-{dmg}", damage_color(dmg)))
    return out

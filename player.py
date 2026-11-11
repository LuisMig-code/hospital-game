"""Jogador: movimento tile a tile no grid, corrida com estamina, ataque, vida
(dano com empurrão, invulnerabilidade, morte), kit médico (pegar e usar) e
animação."""
import math

import pygame

import settings as S
from sprites import HURT_FALLEN_FRAME

DIRS = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),
    "down": (0, 1),
}


def _read_move(keys):
    """Vetor (dx, dy) das teclas apertadas, com diagonal (ex.: W+A = (-1, -1)).
    Teclas opostas se anulam. None se nenhuma direção."""
    dx = (bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])
          - bool(keys[pygame.K_a] or keys[pygame.K_LEFT]))
    dy = (bool(keys[pygame.K_s] or keys[pygame.K_DOWN])
          - bool(keys[pygame.K_w] or keys[pygame.K_UP]))
    return (dx, dy) if (dx or dy) else None


def _facing_for(dx, dy):
    """Sprite para um movimento: só há 4 direções; na diagonal vale a horizontal."""
    if dx:
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def tile_center(tile):
    return (tile[0] * S.TILE + S.TILE / 2, tile[1] * S.TILE + S.TILE / 2)


class Player:
    def __init__(self, anims, tile_pos):
        self.anims = anims
        self.tile = tuple(tile_pos)        # tile onde o jogador está (ou de onde saiu)
        self.target = None                 # tile para onde está indo
        self.x, self.y = tile_center(self.tile)
        self.facing = "down"
        self.moving = False
        self.running = False
        self.stamina = float(S.STAMINA_MAX)
        self.exhausted = False             # zerou a estamina: não corre até recuperar
        self.anim = "idle"
        self.frame_time = 0.0
        self.frame = 0
        # ataque
        self.attacking = False
        self.attack_time = 0.0
        self.attack_queued = False         # pedido no meio de um passo: começa ao chegar
        self.turn_timer = 0.0              # virou parado: espera isso para começar a andar
        self.hit_done = False              # o golpe deste ataque já acertou?
        # vida
        self.hp = S.PLAYER_HP
        self.hurt = False                  # tocando a animação de dano (sem controle)
        self.hurt_time = 0.0
        self.hurt_anim = "hurt_down"
        self.knock_from = None             # (x, y) de onde começou o empurrão
        self.invulnerable = 0.0            # segundos sem levar dano (piscando)
        self.dead = False
        # kit médico
        self.medkits = 0                   # kits guardados
        self.action = None                 # "pickup" (pegando) ou "heal" (usando): sem controle
        self.action_time = 0.0
        self.heal_queued = False           # H no meio de um passo: começa ao chegar
        self.healed = False                # o kit desta animação já curou?
        self.healed_now = False            # curou neste quadro (main mostra o +2)

    # -------------------------------------------------------------------- vida
    def pixel_tile(self):
        """Tile onde o personagem está desenhado agora (muda no meio do passo)."""
        return (int(self.x // S.TILE), int(self.y // S.TILE))

    def take_hit(self, damage, source, dungeon, blocked=frozenset()):
        """Golpe de um zumbi no tile `source`. Tira vida, cancela passo e
        ataque, vira o personagem para o zumbi e o empurra 1 tile para o lado
        oposto (se der; senão usa o dano curto, sem empurrão).
        Durante o dano e por PLAYER_INVULN_TIME s depois, não leva outro golpe.
        Devolve True se o golpe contou."""
        if self.dead or self.hurt or self.invulnerable > 0:
            return False
        self.hp = max(0, self.hp - damage)
        # parte do tile onde está desenhado (pode estar no meio de um passo)
        self.tile, self.target = self.pixel_tile(), None
        self.attacking = self.attack_queued = False
        self.action, self.heal_queued = None, False   # usando o kit: cancela (não gasta)
        self.running = False
        self.turn_timer = 0.0
        x, y = self.tile
        dx = (x > source[0]) - (x < source[0])
        dy = (y > source[1]) - (y < source[1])
        if not (dx or dy):                 # zumbi no mesmo tile (não deveria): para trás
            dx, dy = (-c for c in DIRS[self.facing])
        self.facing = _facing_for(-dx, -dy)    # olha para o zumbi e recua de costas
        push = self._choose_step(dx, dy, dungeon, blocked)
        if push is not None:
            self.target = (x + push[0], y + push[1])
            self.knock_from = (self.x, self.y)
        self.dead = self.hp <= 0
        light = push is None and not self.dead
        name = f"hurt_light_{self.facing}" if light else f"hurt_{self.facing}"
        self.hurt_anim = name if name in self.anims else "idle"
        self.hurt, self.hurt_time = True, 0.0
        self.anim, self.frame, self.frame_time = self.hurt_anim, 0, 0.0
        return True

    def hurt_frames(self):
        return len(self.anims[self.hurt_anim])

    def _update_hurt(self, dt):
        """Empurrão (desacelerando) e animação de dano. Morto, fica caído."""
        self.hurt_time += dt
        if self.target is not None:
            p = min(1.0, self.hurt_time / S.KNOCKBACK_TIME)
            ease = 1 - (1 - p) ** 2
            (x0, y0), (tx, ty) = self.knock_from, tile_center(self.target)
            self.x, self.y = x0 + (tx - x0) * ease, y0 + (ty - y0) * ease
            if p >= 1:
                self.x, self.y = tx, ty
                self.tile, self.target = self.target, None
        frame = int(self.hurt_time * S.HURT_FPS)
        n = self.hurt_frames()
        if self.dead:
            self.frame = min(frame, min(HURT_FALLEN_FRAME, n - 1))
        elif frame >= n and self.target is None:
            self.hurt = False
            self.invulnerable = S.PLAYER_INVULN_TIME
            self.anim, self.frame_time = self.idle_anim(), 0.0
            self.frame = 0
            return
        else:
            self.frame = min(frame, n - 1)
        self.anim = self.hurt_anim
        self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_IDLE * dt)

    @property
    def blinking(self):
        """Invulnerável depois do dano: alterna visível/transparente."""
        return self.invulnerable > 0 and not self.hurt and int(self.invulnerable * 12) % 2 == 0

    # ------------------------------------------------------------------ ataque
    def attack_frames(self):
        frames = self.anims.get(f"attack_{self.facing}")
        return len(frames) if frames else 9

    def request_attack(self):
        """Espaço (sem porta à frente): ataca na direção em que está virado. Durante um ataque o
        pedido é ignorado; no meio de um passo, o ataque começa ao chegar."""
        if not self.attacking:
            self.attack_queued = True

    def impact_tile(self):
        dx, dy = DIRS[self.facing]
        return (self.tile[0] + dx, self.tile[1] + dy)

    def _start_attack(self):
        self.attacking, self.attack_queued, self.hit_done = True, False, False
        self.attack_time = 0.0
        self.running = False

    def _update_attack(self, dt):
        """Avança o ataque. Devolve o tile de impacto no quadro do golpe (uma vez)."""
        self.attack_time += dt
        frame = int(self.attack_time * S.ATTACK_FPS)
        hit = None
        if not self.hit_done and frame >= S.ATTACK_HIT_FRAME:
            self.hit_done = True
            hit = self.impact_tile()
        if frame >= self.attack_frames():
            self.attacking = False
        self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_IDLE * dt)  # parado
        return hit

    # -------------------------------------------------------------- kit médico
    @property
    def busy(self):
        """Fazendo algo que trava os controles (dano, ataque, pegar/usar kit)."""
        return self.hurt or self.dead or self.attacking or self.action is not None

    def can_pickup(self):
        return not self.busy and self.target is None and not self.attack_queued

    def start_pickup(self):
        """Espaço em cima de um kit: animação de pegar e guardar (quem conta
        o kit é o `Game`). Só parado e sem fazer outra coisa."""
        if not self.can_pickup():
            return False
        self._start_action("pickup")
        return True

    def request_heal(self):
        """H: usa um kit (precisa ter kit e não estar com a vida cheia). No
        meio de um passo, começa ao chegar no tile. Devolve se aceitou."""
        if self.medkits <= 0 or self.hp >= S.PLAYER_HP or self.busy or self.heal_queued:
            return False
        self.heal_queued = True
        return True

    def _start_action(self, kind):
        self.action, self.action_time = kind, 0.0
        self.heal_queued = False
        self.healed = False
        self.running = False

    def action_anim(self):
        return f"{self.action}_{self.facing}"

    def action_frames(self):
        frames = self.anims.get(self.action_anim())
        if frames:
            return len(frames)
        return 6 if self.action == "pickup" else 8

    def _update_action(self, dt):
        """Pegando/usando o kit: no quadro HEAL_FRAME da cura recupera a vida e
        gasta o kit (golpe antes disso cancela sem gastar)."""
        self.action_time += dt
        fps = S.PICKUP_FPS if self.action == "pickup" else S.HEAL_FPS
        frame = int(self.action_time * fps)
        if self.action == "heal" and not self.healed and frame >= S.HEAL_FRAME:
            self.healed = self.healed_now = True
            self.medkits -= 1
            self.hp = min(S.PLAYER_HP, self.hp + S.MEDKIT_HEAL)
        n = self.action_frames()
        self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_IDLE * dt)   # parado
        name = self.action_anim()
        if frame >= n:
            self.action = None
            self.anim, self.frame, self.frame_time = self.idle_anim(), 0, 0.0
            return
        if name in self.anims:
            self.anim, self.frame = name, frame
        else:
            self.anim, self.frame = "idle", 0

    # ------------------------------------------------------------------ input
    def _try_start_step(self, keys, dungeon, blocked=frozenset(), chained=False):
        """Se uma direção está pressionada, vira para ela e, se o tile vizinho
        é chão, começa a andar até ele.

        Duas teclas (ex.: W+A) andam na diagonal; se a diagonal está
        bloqueada, desliza pelo eixo livre (veja `_choose_step`).

        Parado, apertar uma direção diferente da atual primeiro só **vira**
        (na diagonal: se já olha para um dos dois lados, não precisa virar);
        segurando a tecla, anda depois de TURN_DELAY s. Já andando
        (chained=True, ao chegar num tile com a tecla apertada) troca de
        direção e segue direto, sem pausa."""
        move = _read_move(keys)
        if move is None:
            self.turn_timer = 0.0
            return
        dx, dy = move
        want = _facing_for(dx, dy)
        parts = {_facing_for(dx, 0) if dx else None, _facing_for(0, dy) if dy else None} - {None}
        if self.facing not in parts and not chained:
            self.facing = want
            self.turn_timer = S.TURN_DELAY
            return
        if self.turn_timer > 0:            # acabou de virar: espera para andar
            return
        step = self._choose_step(dx, dy, dungeon, blocked)
        if step is None:                   # nada livre: só fica virado para lá
            self.facing = want
            return
        self.facing = _facing_for(*step)
        self.target = (self.tile[0] + step[0], self.tile[1] + step[1])

    def _choose_step(self, dx, dy, dungeon, blocked):
        """Primeiro passo possível entre: a diagonal, só o eixo horizontal e
        só o vertical (deslizar na parede). A diagonal não corta quina: os
        dois tiles retos que ela atravessa também têm que ser andáveis."""
        x, y = self.tile
        cands = ([(dx, dy)] if dx and dy else []) + ([(dx, 0)] if dx else []) + ([(0, dy)] if dy else [])
        for sx, sy in cands:
            nxt = (x + sx, y + sy)
            if not dungeon.is_walkable(*nxt) or nxt in blocked:
                continue
            if sx and sy and not (dungeon.is_walkable(x + sx, y) and dungeon.is_walkable(x, y + sy)):
                continue
            return (sx, sy)
        return None

    def _wants_run(self, keys):
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if self.exhausted and self.stamina >= S.STAMINA_RECOVER_TO_RUN:
            self.exhausted = False
        return shift and not self.exhausted and self.stamina > 0

    # ----------------------------------------------------------------- update
    def update(self, dt, keys, dungeon, blocked=frozenset()):
        """blocked: tiles ocupados por outros (zumbis) — não dá para entrar.

        Devolve o tile de impacto quando um golpe acerta neste quadro (senão None)."""
        budget = dt
        self.moving = False
        self.healed_now = False
        if self.hurt:                      # levando dano (ou morto): sem controle
            self.running = False
            self._update_hurt(dt)
            return None
        self.invulnerable = max(0.0, self.invulnerable - dt)

        if self.attack_queued and not self.attacking and self.target is None and self.action is None:
            self._start_attack()
        if self.heal_queued and not self.attacking and self.target is None and self.action is None:
            self._start_action("heal")
        if self.action is not None:        # pegando/usando o kit: não anda nem vira
            self._update_action(dt)
            return None
        if self.attacking:                 # atacando: não anda nem vira
            hit = self._update_attack(dt)
            self._animate(dt)
            return hit

        self.turn_timer = max(0.0, self.turn_timer - dt)
        if self.target is None:
            self._try_start_step(keys, dungeon, blocked)

        # Consome o tempo do frame andando; ao chegar num tile, encaixa
        # exatamente nele e (se a tecla continua pressionada) segue para o próximo.
        while self.target is not None and budget > 1e-9:
            self.moving = True
            self.running = self._wants_run(keys)
            speed = S.PLAYER_SPEED * (S.RUN_MULT if self.running else 1.0)
            tx, ty = tile_center(self.target)
            dist = math.hypot(tx - self.x, ty - self.y)  # reto ou diagonal: mesma velocidade
            t = min(budget, dist / speed)
            self._spend_stamina(t)
            budget -= t
            if t * speed >= dist - 1e-6:
                self.x, self.y = tx, ty
                self.tile, self.target = self.target, None
                if self.attack_queued or self.heal_queued:   # chegou: o ataque/cura pedido começa
                    break
                self._try_start_step(keys, dungeon, blocked, chained=True)
            else:
                k = speed * t / dist
                self.x += (tx - self.x) * k
                self.y += (ty - self.y) * k

        if self.target is None:
            self.running = False
            if budget > 0:  # tempo do frame em que ficou parado
                self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_IDLE * budget)

        self._animate(dt)
        return None

    def _spend_stamina(self, t):
        if self.running:
            self.stamina = max(0.0, self.stamina - S.STAMINA_DRAIN * t)
            if self.stamina <= 0:
                self.exhausted = True
        else:
            self.stamina = min(S.STAMINA_MAX, self.stamina + S.STAMINA_REGEN_WALK * t)

    def idle_anim(self):
        """Parado: continua olhando para onde estava indo. De frente usa a
        animação "idle"; nas outras direções, a pose parada "idle_<direção>"."""
        if self.facing != "down" and f"idle_{self.facing}" in self.anims:
            return f"idle_{self.facing}"
        return "idle"

    def _animate(self, dt):
        if self.attacking:
            self.anim = f"attack_{self.facing}"
            n = self.attack_frames()
            self.frame = min(n - 1, int(self.attack_time * S.ATTACK_FPS))
            self.frame_time = 0.0
            return
        anim = f"walk_{self.facing}" if self.moving else self.idle_anim()
        if anim != self.anim:
            self.anim, self.frame_time = anim, 0.0
        self.frame_time += dt * (S.RUN_MULT if self.running else 1.0)
        frames = self.anims[self.anim]
        self.frame = int(self.frame_time * S.ANIM_FPS) % len(frames)

    # ------------------------------------------------------------------- draw
    def feet(self):
        """Ponto dos pés em pixels do mundo (base do sprite)."""
        return (self.x, self.y + S.TILE / 2 - 4)

    def sprite_rect(self):
        """Retângulo do sprite atual em pixels do mundo."""
        img = self.anims[self.anim][self.frame]
        fx, fy = self.feet()
        return img.get_rect(midbottom=(round(fx), round(fy)))

    _shadow = None

    @classmethod
    def shadow(cls):
        """Elipse escura e suave sob os pés (criada uma vez)."""
        if cls._shadow is None:
            w, h = 28, 10
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            # elipses concêntricas: mais escuro no centro, borda suave
            for i in range(4):
                a = round(S.PLAYER_SHADOW_ALPHA * (i + 1) / 4)
                pygame.draw.ellipse(surf, (0, 0, 0, a), (i * 2, i, w - i * 4, h - i * 2))
            cls._shadow = surf
        return cls._shadow

    def draw(self, surf, camera):
        img = self.anims[self.anim][self.frame]
        fx, fy = self.feet()
        feet = (round(fx - camera[0]), round(fy - camera[1]))
        shadow = self.shadow()
        surf.blit(shadow, shadow.get_rect(center=(feet[0], feet[1] + 1)))
        if self.blinking:
            img = img.copy()
            img.set_alpha(70)
        surf.blit(img, img.get_rect(midbottom=feet))

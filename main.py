"""Dungeon procedural — ponto de entrada.

Uso:
    venv\\Scripts\\python.exe main.py            # seed aleatória
    venv\\Scripts\\python.exe main.py 12345      # seed específica (número ou texto)

Controles: WASD/setas movem, Shift corre, Espaço ataca (zumbi colado) / pega o kit embaixo ou do lado /
abre/fecha a porta à frente / ataca, H usa o kit médico, roda do mouse dá zoom, R gera nova dungeon,
G liga/desliga o grid, V liga/desliga a névoa, ESC sai.
"""
import math
import random
import sys

import pygame

import settings as S
from dungeon import FLOOR, generate
from fov import Vision
from lighting import FogLayer, Light
from player import DIRS, Player, _facing_for
from combat import FloatingText, apply_attack, texts_for
from elevators import ElevatorActor
from video import FloorVideo
from items import spawn_medkits
from sprites import (load_animations, load_attack_animations, load_damage_animations, load_elevator_animations,
                     load_kit_animations, load_medkit_item, load_zombie_animations)
from zombies import Horde, touching
from doors import try_toggle
from props import PropArt
from themes import THEMES
from tileset import Tileset, bake_wall_shadows, door_rect, draw_door, init_doors, render_map


def build_map_surface(dungeon, tiles=None, props=None):
    """Pré-renderiza o mapa inteiro (tiles não mudam). Usa a arte do tileset
    (piso, paredes, portas e detalhes de chão dos props); sem tileset,
    desenha com cores sólidas (verde/cinza)."""
    if tiles is not None:
        return render_map(dungeon, tiles, props)
    surf = pygame.Surface((dungeon.width * S.TILE, dungeon.height * S.TILE))
    for y, row in enumerate(dungeon.grid):
        for x, cell in enumerate(row):
            color = S.COLOR_FLOOR if cell == FLOOR else S.COLOR_WALL
            surf.fill(color, (x * S.TILE, y * S.TILE, S.TILE, S.TILE))
    bake_wall_shadows(surf, dungeon)
    init_doors(surf, dungeon, None)
    return surf


def build_grid_surface(dungeon):
    """Linhas do grid só sobre o piso (não cortam a arte das paredes)."""
    t = S.TILE
    surf = pygame.Surface((dungeon.width * t, dungeon.height * t), pygame.SRCALPHA)
    for y, row in enumerate(dungeon.grid):
        for x, cell in enumerate(row):
            if cell == FLOOR:
                pygame.draw.rect(surf, S.COLOR_GRID, (x * t, y * t, t + 1, t + 1), 1)
    return surf


class Game:
    def __init__(self, seed):
        pygame.init()
        pygame.display.set_caption("Dungeon")
        self.screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
        # O mundo ocupa a tela abaixo da tarja do HUD (a tarja não cobre o mapa)
        self.world_rect = pygame.Rect(0, S.HUD_BAR_H, S.SCREEN_W, S.SCREEN_H - S.HUD_BAR_H)
        self.world_screen = self.screen.subsurface(self.world_rect)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.anims = load_animations()
        # ataque: mesma altura do personagem parado (o desenho do sheet é menor)
        self.anims.update(load_attack_animations(target_height=self.anims["idle"][0].get_height()))
        self.anims.update(load_damage_animations(target_height=self.anims["idle"][0].get_height()))
        self.anims.update(load_kit_animations(target_height=self.anims["idle"][0].get_height()))
        self.medkit_frames, self.medkit_icon = load_medkit_item()
        self.elevator_anims = load_elevator_animations()
        self.time = 0.0                    # segundos de jogo (animação dos itens)
        self.zombie_anims = load_zombie_animations()
        self.small_font = pygame.font.SysFont("consolas", 15)
        self.big_font = pygame.font.SysFont("consolas", 72, bold=True)
        self._vignette = None
        self.dmg_font = pygame.font.SysFont("consolas", 15, bold=True)
        self._dmg_cache = {}
        r = S.VISION_RADIUS
        self.light = Light(round(math.sqrt(r * r + r) * S.TILE))   # mesmo raio de fov.in_radius
        try:
            self.tiles = Tileset()
            self.props = PropArt()
        except (pygame.error, FileNotFoundError, ValueError, KeyError) as err:
            print(f"Tileset não carregado ({err}); usando cores sólidas.")
            self.tiles = self.props = None
        self.show_grid = True
        self.show_fog = True
        self.message, self.message_until = "", 0
        self.zoom = S.ZOOM_MIN             # zoom atual (vai suavemente até o alvo)
        self.zoom_target = S.ZOOM_MIN      # zoom pedido pela roda do mouse
        self.new_run(seed)

    # ---------------------------------------------------------------- andares
    def new_run(self, seed):
        """Run nova: andar 1, vida cheia, sem kits."""
        self.run_seed = seed
        self.floor = 1
        self.new_level(seed)

    def next_floor(self):
        """Saiu pelo elevador: próximo andar (dungeon nova, seed derivada da
        run), mantendo a vida e os kits."""
        hp, kits = self.player.hp, self.player.medkits
        self.floor += 1
        self.new_level(f"{self.run_seed}-{self.floor}")
        self.player.hp, self.player.medkits = hp, kits

    def new_level(self, seed):
        if getattr(self, "video", None) is not None:      # R no meio do vídeo: para o som
            self.video.close()
        self.dungeon = generate(seed, S.MAP_W, S.MAP_H)
        self.map_surf = build_map_surface(self.dungeon, self.tiles, self.props)
        self.current_room = None           # sala onde o personagem está (mostra o nome ao entrar)
        self.grid_surf = build_grid_surface(self.dungeon)
        self.player = Player(self.anims, self.dungeon.spawn)
        # Zumbis enterrados nas salas (longe do spawn); saem do chão quando vistos
        exit_front = self.dungeon.elevator_out.front
        self.horde = Horde(self.dungeon, avoid=[self.dungeon.spawn, *exit_front])
        # Kits médicos no chão (40% das salas), fora dos tiles dos zumbis
        self.medkits = spawn_medkits(self.dungeon, avoid=[self.dungeon.spawn, *exit_front],
                                     taken={z.tile for z in self.horde.zombies})
        self.texts = []                    # números de dano flutuando
        self.seed = seed
        self.seed_label = str(seed)
        self.hit_flash = 0.0               # vermelho nas bordas ao levar golpe
        self.dead_time = 0.0               # segundos desde o game over
        # Névoa: começa toda preta; tiles descobertos viram "escurecidos"
        self.vision = Vision(self.dungeon, S.VISION_RADIUS)
        self.fog = FogLayer(self.dungeon.width, self.dungeon.height)
        # Elevadores: o andar começa com a chegada (personagem saindo do elevador)
        self.exit_avoid = list(self.dungeon.elevator_out.front)
        self.el_in = ElevatorActor(self.dungeon.elevator_in, "arrive")
        self.el_out = ElevatorActor(self.dungeon.elevator_out, "closed")
        self.phase = "arrive"              # arrive -> play -> exit -> video (ou fade) -> próximo andar
        self.video = None
        self.phase_time = 0.0
        self.player_visible = False
        self.update_vision()
        print(f"Seed: {seed} -> {len(self.dungeon.rooms)} salas (andar {getattr(self, 'floor', 1)})")

    def action(self):
        """Espaço, nesta ordem:
        1. zumbi colado no personagem → ataca (atacar tem preferência);
        2. parado na frente do elevador de saída → entra (próximo andar);
        3. parado em cima ou do lado de um kit médico → pega e guarda;
        4. porta à frente (ou embaixo) → abre/fecha;
        5. senão → ataca na direção em que ele está virado.
        Levando dano, atacando, pegando/usando kit ou fora do jogo normal
        (chegada/saída do elevador): nada."""
        p = self.player
        if p.busy or self.phase != "play":
            return
        if self.zombie_touching():
            p.request_attack()
            return
        if self.at_exit():
            self.enter_elevator()
            return
        kit = self.reachable_medkit() if p.target is None else None
        if kit is not None and p.can_pickup():
            if kit.tile != p.tile:             # kit do lado: vira para ele antes de pegar
                p.facing = _facing_for(kit.tile[0] - p.tile[0], kit.tile[1] - p.tile[1])
            p.start_pickup()
            self.medkits.remove(kit)
            p.medkits += 1
            self.show_message("Kit médico guardado  [H] usar")
            return
        if self.toggle_door() is None:
            p.request_attack()

    def at_exit(self):
        p = self.player
        return p.target is None and p.tile in self.dungeon.elevator_out.front

    def enter_elevator(self):
        """Começa a saída: as portas abrem, o personagem entra, as portas
        fecham e a tela escurece (veja update_elevators)."""
        p = self.player
        self.phase, self.phase_time = "exit", 0.0
        self.exit_stage = "open"
        self.el_out.play("open_exit")
        p.facing, p.running = "up", False
        self.exit_from = (p.x, p.y)

    def update_elevators(self, dt):
        """Animações dos elevadores e as fases de chegada/saída do andar."""
        fps = S.ELEVATOR_FPS
        self.phase_time += dt
        self.el_in.update(dt, fps)
        self.el_out.update(dt, fps)
        p = self.player
        if self.phase == "arrive":
            if self.el_in.done:                # portas abertas: ele sai e elas fecham
                self.player_visible = True
                p.facing = "down"
                self.el_in.play("close")
                self.phase, self.phase_time = "play", 0.0
                self.show_message(f"Andar {self.floor} — encontre o elevador", 2.5)
        elif self.phase == "play":
            ex = self.dungeon.elevator_out
            near = min(max(abs(p.tile[0] - x), abs(p.tile[1] - y)) for x, y in ex.front) <= S.ELEVATOR_NEAR
            want = "idle" if near else "closed"
            if self.el_out.anim != want:
                self.el_out.play(want, loop=near)
        elif self.phase == "exit":
            if self.exit_stage == "open" and self.el_out.done:
                self.exit_stage, self.phase_time = "walk", 0.0
            elif self.exit_stage == "walk":
                k = min(1.0, self.phase_time / S.ELEVATOR_WALK_TIME)
                ex = self.dungeon.elevator_out
                tx = (ex.wall[0][0] + 1) * S.TILE                      # meio do elevador
                ty = (ex.base_y - 0.7) * S.TILE                        # para dentro
                x0, y0 = self.exit_from
                p.x, p.y = x0 + (tx - x0) * k, y0 + (ty - y0) * k
                p.moving = True
                p._animate(dt)
                if k >= 1:
                    self.player_visible = False
                    self.exit_stage = "close"
                    self.el_out.play("open_exit", reverse=True)
            elif self.exit_stage == "close" and self.el_out.done:
                self.start_floor_video()
        elif self.phase == "video":
            self.video.update(dt)
            if self.video.done:
                self.end_floor_video()
        elif self.phase == "fade" and self.phase_time >= S.FLOOR_FADE_TIME:
            self.next_floor()

    def start_floor_video(self):
        """Portas fechadas: toca o vídeo do elevador (com som). Sem OpenCV
        ou sem o arquivo, só escurece a tela com "Andar N"."""
        self.video = FloorVideo.open()
        if self.video is None:
            self.phase, self.phase_time = "fade", 0.0
            return
        self.phase, self.phase_time = "video", 0.0
        self.video.play_sound()
        self.video.update(0.0)

    def end_floor_video(self):
        """Fim do vídeo (ou Espaço/Enter para pular): próximo andar."""
        if self.video is not None:
            self.video.close()
            self.video = None
        self.next_floor()

    def zombie_touching(self):
        """Algum zumbi fora do chão e vivo colado no personagem (8 direções,
        sem quina de parede no meio)?"""
        here = self.player.pixel_tile()
        return any(z.solid and touching(self.dungeon, z.pixel_tile(), here) for z in self.horde.zombies)

    def medkit_at(self, tile):
        return next((k for k in self.medkits if k.tile == tile), None)

    def reachable_medkit(self):
        """Kit que o personagem alcança: embaixo dele ou colado (8 direções,
        sem quina de parede no meio). Preferência: embaixo, à frente, o resto."""
        p = self.player
        here = self.medkit_at(p.tile)
        if here is not None:
            return here
        fx, fy = DIRS[p.facing]
        front = self.medkit_at((p.tile[0] + fx, p.tile[1] + fy))
        if front is not None:
            return front
        return next((k for k in self.medkits if touching(self.dungeon, p.tile, k.tile)), None)

    def use_medkit(self):
        """H: usa um kit médico (+2 de vida)."""
        p = self.player
        if p.busy:
            return
        if p.medkits <= 0:
            self.show_message("Sem kit médico")
        elif p.hp >= S.PLAYER_HP:
            self.show_message("Vida cheia")
        else:
            p.request_heal()

    def toggle_door(self):
        """Espaço: abre/fecha a porta à frente do personagem."""
        result, door = try_toggle(self.dungeon, self.player, self.horde.blocked_tiles())
        if result in ("abriu", "fechou"):
            draw_door(self.map_surf, door, self.tiles)
            self.update_vision(force=True)   # a porta muda o que dá para ver
        elif result == "bloqueada":
            self.show_message("Saia da porta para fechá-la")
        elif result == "zumbi":
            self.show_message("Tem um zumbi na porta!")
        return result

    def update_room(self):
        """Ao entrar numa sala, mostra o nome do tema dela."""
        room = self.dungeon.room_at(self.player.pixel_tile())
        if room is not self.current_room:
            self.current_room = room
            if room is not None and room.theme in THEMES:
                self.show_message(THEMES[room.theme].name, 2.0)

    def update_vision(self, force=False):
        # Tile onde o personagem está desenhado (avança no meio do passo)
        origin = (int(self.player.x // S.TILE), int(self.player.y // S.TILE))
        self.vision.update(origin, force)
        if self.vision.visible != self.fog.visible:
            self.fog.update(self.vision.visible)

    def change_zoom(self, notches):
        """Roda do mouse: cada "clique" muda o alvo em ZOOM_STEP (para cima
        aproxima). O zoom de verdade chega lá aos poucos em update_zoom."""
        target = self.zoom_target + notches * S.ZOOM_STEP
        # arredonda: somar 0.1 dez vezes dá 1.9999999, e 2.0 exato usa escala nítida
        self.zoom_target = round(max(S.ZOOM_MIN, min(S.ZOOM_MAX, target)), 3)

    def update_zoom(self, dt):
        """Aproxima o zoom do alvo com amortecimento exponencial (suave e
        independente do FPS); encaixa no alvo quando a diferença é mínima."""
        diff = self.zoom_target - self.zoom
        if abs(diff) < 0.002:
            self.zoom = self.zoom_target
        else:
            self.zoom += diff * (1 - math.exp(-S.ZOOM_SMOOTHING * dt))

    def view_size(self):
        """Tamanho (em pixels do mundo) da área visível com o zoom atual
        (a tela abaixo da tarja do HUD)."""
        w, h = self.world_rect.size
        return round(w / self.zoom), round(h / self.zoom)

    def camera(self):
        vw, vh = self.view_size()
        mw, mh = self.map_surf.get_size()
        cx = self.player.x - vw / 2
        cy = self.player.y - vh / 2
        cx = max(0, min(cx, mw - vw)) if mw > vw else (mw - vw) / 2
        cy = max(0, min(cy, mh - vh)) if mh > vh else (mh - vh) / 2
        return round(cx), round(cy)

    def draw_world(self):
        """Desenha o mundo numa superfície do tamanho da área visível e
        escala para a tela de acordo com o zoom."""
        cam = self.camera()
        view = pygame.Surface(self.view_size())
        view.fill(S.COLOR_BG)
        view.blit(self.map_surf, (-cam[0], -cam[1]))
        if self.show_grid:
            view.blit(self.grid_surf, (-cam[0], -cam[1]))
        self.draw_actors(view, cam)          # personagem e zumbis, com sombra
        self.draw_door_overlap(view, cam)
        if self.show_fog:
            center = (round(self.player.x - cam[0]), round(self.player.y - cam[1]))
            self.light.draw(view, center)
            fog, pos = self.fog.render(cam, view.get_size())
            view.blit(fog, pos)
        self.draw_damage_texts(view, cam)    # por cima da névoa, para ler bem
        dest = self.world_screen              # abaixo da tarja do HUD
        size = dest.get_size()
        if view.get_size() == size:
            dest.blit(view, (0, 0))
        elif float(self.zoom).is_integer():   # 2x exato: pixels nítidos
            pygame.transform.scale(view, size, dest)
        else:                                 # zoom fracionário: suavizado, sem serrilhar
            pygame.transform.smoothscale(view, size, dest)

    def draw_actors(self, view, cam):
        """Personagem, zumbis, kits e móveis ordenados pela altura dos pés (a
        base, nos móveis): quem está mais embaixo na tela é desenhado por
        último (fica na frente) — o personagem passa por trás de uma estante.
        Com a névoa ligada, só aparecem os zumbis que o personagem está vendo;
        kits e móveis ficam embaixo da névoa (escurecidos fora da visão)."""
        actors = []
        if self.player_visible:
            # entrando no elevador: por cima dele (anda para dentro da porta aberta)
            key = 10 ** 9 if self.phase == "exit" else self.player.feet()[1]
            actors.append((key, lambda: self.player.draw(view, cam)))
        for actor in (self.el_in, self.el_out):
            ev = actor.elevator
            actors.append((ev.base_y * S.TILE - 1, lambda a=actor: self.draw_elevator(view, cam, a)))
        if self.props is not None:   # móveis: só os que aparecem na tela
            view_rect = pygame.Rect(cam, view.get_size())
            for pp in self.dungeon.props:
                if self.props.rect(pp).colliderect(view_rect):
                    actors.append((self.props.anchor(pp)[1], lambda pp=pp: self.props.draw(view, cam, pp)))
        for k in self.medkits:   # kits: a névoa por cima esconde/escurece os fora da visão
            actors.append((k.feet_y(), lambda k=k: k.draw(view, cam, self.medkit_frames, self.time)))
        for z in self.horde.active():
            if self.show_fog and z.pixel_tile() not in self.vision.visible:
                continue
            actors.append((z.feet_y(), lambda z=z: z.draw(view, cam, self.zombie_anims)))
        for _, draw in sorted(actors, key=lambda a: a[0]):
            draw()

    def draw_elevator(self, view, cam, actor):
        ev = actor.elevator
        img = self.elevator_anims[actor.anim][actor.frame(S.ELEVATOR_FPS)]
        bottom = (ev.wall[0][0] + 1) * S.TILE - cam[0], ev.base_y * S.TILE - cam[1]
        view.blit(img, img.get_rect(midbottom=(round(bottom[0]), round(bottom[1]))))

    def draw_floor_video(self):
        """Vídeo do elevador em tela cheia: surge do preto e, no fim, mostra
        o próximo andar por cima."""
        v = self.video
        if self.phase != "video" or v is None or v.surface is None:
            return False
        self.screen.blit(v.surface, (0, 0))
        if v.time < 0.4:                                          # surge do preto
            shade = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, round(255 * (1 - v.time / 0.4))))
            self.screen.blit(shade, (0, 0))
        left = v.duration - v.time
        if left < S.FLOOR_VIDEO_TEXT_TIME:                       # "Andar N" aparecendo
            a = round(255 * min(1.0, 1 - left / S.FLOOR_VIDEO_TEXT_TIME) * 1.6) if left > 0 else 255
            a = max(0, min(255, a))
            text = f"Andar {self.floor + 1}"
            center = (S.SCREEN_W // 2, S.SCREEN_H // 2)
            for color, off in (((20, 15, 10), (3, 3)), ((40, 30, 20), (0, 0))):
                img = self.big_font.render(text, True, color)
                img.set_alpha(a)
                self.screen.blit(img, img.get_rect(center=(center[0] + off[0], center[1] + off[1])))
        hint = self.small_font.render("[Espaço] pular", True, (235, 235, 235))
        self.screen.blit(hint, hint.get_rect(bottomright=(S.SCREEN_W - 12, S.SCREEN_H - 10)))
        return True

    def draw_floor_fade(self):
        """Entre andares: tela escurece e mostra o próximo andar."""
        if self.phase != "fade":
            return
        k = min(1.0, self.phase_time / (S.FLOOR_FADE_TIME * 0.5))
        shade = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, round(255 * k)))
        self.screen.blit(shade, (0, 0))
        img = self.big_font.render(f"Andar {self.floor + 1}", True, (230, 230, 220))
        img.set_alpha(round(255 * k))
        self.screen.blit(img, img.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2)))

    def _damage_surface(self, text, color):
        """Número de dano com contorno escuro (cacheado)."""
        key = (text, color)
        if key not in self._dmg_cache:
            fg = self.dmg_font.render(text, True, color)
            bg = self.dmg_font.render(text, True, (20, 10, 10))
            w, h = fg.get_size()
            surf = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            for ox, oy in ((0, 1), (2, 1), (1, 0), (1, 2)):
                surf.blit(bg, (ox, oy))
            surf.blit(fg, (1, 1))
            self._dmg_cache[key] = surf
        return self._dmg_cache[key]

    def draw_damage_texts(self, view, cam):
        for t in self.texts:
            img = self._damage_surface(t.text, t.color)
            img.set_alpha(t.alpha)
            view.blit(img, img.get_rect(midbottom=(round(t.x - cam[0]), round(t.y - cam[1]))))

    def draw_door_overlap(self, view, cam):
        """Profundidade: portas da parede de cima ocupam 2 tiles de altura, e
        a metade de cima fica sobre o corredor. Se o personagem está nesse
        corredor (ao norte da porta), a porta é redesenhada por cima dele,
        semitransparente, para ele continuar visível "através" dela."""
        t = S.TILE
        sprite = self.player.sprite_rect()
        for door in self.dungeon.doors:
            if door.side != "top":
                continue
            rect = door_rect(door)
            upper = pygame.Rect(rect.x, rect.y, rect.w, t)   # metade de cima (tile do corredor)
            door_row_top = rect.y + t
            if self.player.y < door_row_top and upper.colliderect(sprite):
                part = self.map_surf.subsurface(upper).copy()
                part.set_alpha(S.OCCLUDER_ALPHA)
                view.blit(part, (upper.x - cam[0], upper.y - cam[1]))

    def _text(self, text, pos, color=S.COLOR_TEXT, font=None, anchor="topleft"):
        """Texto com sombra de 1 px (legível sobre qualquer fundo). `anchor`
        diz qual ponto do texto fica em `pos` (topleft, midleft, topright...)."""
        font = font or self.font
        img = font.render(text, True, color)
        rect = img.get_rect(**{anchor: pos})
        self.screen.blit(font.render(text, True, (0, 0, 0)), rect.move(1, 1))
        self.screen.blit(img, rect)
        return rect

    def _bar(self, x, y, w, h, ratio, color, marks=0):
        """Barra arredondada (vida/estamina) com `marks` divisões internas."""
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, w, h), border_radius=4)
        if ratio > 0:
            pygame.draw.rect(self.screen, color, (x, y, max(4, round(w * ratio)), h), border_radius=4)
        for i in range(1, marks):
            mx = x + round(w * i / marks)
            pygame.draw.line(self.screen, (20, 20, 20), (mx, y + 2), (mx, y + h - 3))
        pygame.draw.rect(self.screen, (230, 230, 230), (x, y, w, h), 1, border_radius=4)

    def draw_hud(self):
        """Tarja preta no topo (o mundo fica abaixo dela): vida, estamina e
        kits à esquerda; a mensagem temporária no meio; andar, abatidos,
        seed, tile e zoom à direita."""
        p = self.player
        bar_h = S.HUD_BAR_H
        self.screen.fill(S.COLOR_HUD_BAR, (0, 0, S.SCREEN_W, bar_h))
        pygame.draw.line(self.screen, (70, 70, 70), (0, bar_h - 1), (S.SCREEN_W, bar_h - 1))
        small = self.small_font
        mid = bar_h // 2

        # Esquerda: vida (marcas = cada golpe de zumbi) e estamina
        x, w, h = 12, 180, 12
        y1, y2 = mid - h - 2, mid + 2
        self._bar(x, y1, w, h, p.hp / S.PLAYER_HP, (200, 40, 45), marks=S.PLAYER_HP // S.ZOMBIE_DAMAGE)
        self._text(f"Vida {p.hp}/{S.PLAYER_HP}", (x + w + 10, y1 + h // 2), font=small, anchor="midleft")
        ratio = p.stamina / S.STAMINA_MAX
        self._bar(x, y2, w, h, ratio, (220, 60, 50) if ratio < 0.25 else (240, 200, 40))
        label = f"Estamina {int(p.stamina)}/{S.STAMINA_MAX}" + ("  CORRENDO" if p.running else "")
        self._text(label, (x + w + 10, y2 + h // 2), font=small, anchor="midleft")

        # Kits médicos guardados
        kx = x + w + 10 + small.size(f"Estamina {S.STAMINA_MAX}/{S.STAMINA_MAX}  CORRENDO")[0] + 24
        icon = self.medkit_icon.get_rect(midleft=(kx, mid))
        self.screen.blit(self.medkit_icon, icon)
        kits = self._text(f"Kits: {p.medkits}", (icon.right + 6, mid), (150, 230, 140) if p.medkits else S.COLOR_TEXT,
                          anchor="midleft")

        # Direita: andar e abatidos; embaixo, menor, seed/tile/zoom
        tx, ty = p.tile
        right = S.SCREEN_W - 12
        top = self._text(f"Andar {self.floor}   Abatidos: {self.horde.killed}", (right, mid - 1), anchor="bottomright")
        info = self._text(f"Seed: {self.run_seed}   Tile: ({tx}, {ty})   Zoom: {self.zoom:.1f}x",
                          (right, mid + 2), (170, 170, 170), font=small, anchor="topright")

        # Meio: mensagem temporária (nome da sala, kit guardado, porta bloqueada...)
        if self.message and pygame.time.get_ticks() < self.message_until:
            left, end = kits.right + 20, min(top.left, info.left) - 20
            font = self.font if self.font.size(self.message)[0] <= end - left else small
            self._text(self.message, ((left + end) // 2, mid), (255, 200, 120), font=font, anchor="center")

        self.draw_controls()

    CONTROLS = ("[WASD] andar  [Shift] correr  [Espaço] atacar/pegar/porta  [H] kit médico  "
                "[Roda] zoom  [R] nova  [G] grid  [V] névoa  [ESC] sair")

    def draw_controls(self):
        """Ajuda dos controles num painel pequeno no rodapé."""
        img = self.small_font.render(self.CONTROLS, True, (220, 220, 220))
        rect = img.get_rect(bottomleft=(10, S.SCREEN_H - 8))
        if getattr(self, "_controls_panel", None) is None:
            panel = pygame.Surface((rect.w + 12, rect.h + 8), pygame.SRCALPHA)
            pygame.draw.rect(panel, (10, 12, 14, S.HUD_PANEL_ALPHA), panel.get_rect(), border_radius=6)
            self._controls_panel = panel
        self.screen.blit(self._controls_panel, (rect.x - 6, rect.y - 4))
        self.screen.blit(img, rect)

    def vignette(self):
        """Moldura vermelha que some para o centro (criada uma vez)."""
        if self._vignette is None:
            small = pygame.Surface((64, 36), pygame.SRCALPHA)
            for y in range(36):
                for x in range(64):
                    d = min(x, 63 - x, (y * 64 / 36), (35 - y) * 64 / 36) / 32   # 0 na borda, 1 no meio
                    a = round(200 * max(0.0, 1 - d / 0.45) ** 2)
                    small.set_at((x, y), (200, 0, 0, a))
            self._vignette = pygame.transform.smoothscale(small, (S.SCREEN_W, S.SCREEN_H))
        return self._vignette

    def draw_hit_flash(self):
        if self.hit_flash > 0:
            v = self.vignette()
            v.set_alpha(round(255 * self.hit_flash / S.HIT_SCREEN_FLASH))
            self.screen.blit(v, (0, 0))

    def draw_game_over(self):
        """Vida zerada: escurece a tela aos poucos e mostra GAME OVER."""
        if not self.player.dead:
            return
        k = min(1.0, self.dead_time / 1.0)
        shade = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        shade.fill((25, 0, 0, round(190 * k)))
        self.screen.blit(shade, (0, 0))
        if self.dead_time < 0.4:
            return
        a = round(255 * min(1.0, (self.dead_time - 0.4) / 0.6))
        wr = self.world_rect                                     # acima do personagem caído
        center = (wr.centerx, wr.y + round(wr.h * 0.27))
        for img, dy in ((self.big_font.render("GAME OVER", True, (220, 40, 40)), -10),
                        (self.font.render("Recomeçando a dungeon...", True, (230, 230, 230)), 50)):
            img.set_alpha(a)
            self.screen.blit(img, img.get_rect(center=(center[0], center[1] + dy)))

    def show_message(self, text, seconds=1.5):
        self.message = text
        self.message_until = pygame.time.get_ticks() + int(seconds * 1000)

    def zombie_hits(self, attackers):
        """Golpes dos zumbis neste quadro: o primeiro que conta tira vida e
        empurra o personagem (os outros caem na invulnerabilidade)."""
        p = self.player
        for z in attackers:
            if p.take_hit(S.ZOMBIE_DAMAGE, z.tile, self.dungeon, self.horde.blocked_tiles()):
                self.hit_flash = S.HIT_SCREEN_FLASH
                fx, fy = p.feet()
                self.texts.append(FloatingText(p.x, fy - S.PLAYER_SPRITE_HEIGHT, f"-{S.ZOMBIE_DAMAGE}",
                                               (255, 60, 60)))

    def step(self, dt, keys):
        """Um quadro da lógica do jogo (sem desenhar)."""
        self.update_elevators(dt)
        if self.phase in ("exit", "video", "fade"):   # entrando no elevador: o andar "pausa"
            self.time += dt
            self.light.update(dt)
            self.update_zoom(dt)
            return
        self.zombie_hits(self.horde.update(dt, self.player, self.vision.visible))
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if self.player.dead:               # game over: run nova (andar 1, outra seed)
            self.dead_time += dt
            if self.dead_time >= S.GAME_OVER_TIME:
                self.new_run(random.randrange(1_000_000))
                return
        if self.phase == "arrive":         # saindo do elevador: sem controle
            keys = _NO_KEYS
        impact = self.player.update(dt, keys, self.dungeon, blocked=self.horde.blocked_tiles())
        if impact is not None:   # quadro do golpe: dano em área nos zumbis
            p = self.player
            hits = apply_attack(self.horde, impact, p.tile, self.vision.visible,
                                dungeon=self.dungeon, player_occ={p.tile, p.target} - {None})
            self.texts.extend(texts_for(hits))
        for t in self.texts:
            t.update(dt)
        self.texts = [t for t in self.texts if not t.done]
        if self.player.healed_now:
            p = self.player
            self.texts.append(FloatingText(p.x, p.feet()[1] - S.PLAYER_SPRITE_HEIGHT, f"+{S.MEDKIT_HEAL}",
                                           (110, 235, 110)))
        self.time += dt
        self.update_room()
        self.light.update(dt)
        self.update_zoom(dt)
        self.update_vision()

    def run(self):
        while True:
            dt = min(self.clock.tick(S.FPS) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    return
                if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                    self.new_run(random.randrange(1_000_000))
                if e.type == pygame.KEYDOWN and e.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                if e.type == pygame.KEYDOWN and e.key == pygame.K_v:
                    self.show_fog = not self.show_fog
                if e.type == pygame.KEYDOWN and e.key == pygame.K_h:
                    self.use_medkit()
                if e.type == pygame.KEYDOWN and self.phase == "video" and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.end_floor_video()             # pula o vídeo
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                    self.action()
                if e.type == pygame.MOUSEWHEEL:
                    # precise_y: frações de "clique" em touchpads (scroll contínuo)
                    self.change_zoom(getattr(e, "precise_y", e.y))

            self.step(dt, pygame.key.get_pressed())
            if not self.draw_floor_video():    # vídeo da troca de andar ocupa a tela toda
                self.draw_world()
                self.draw_hit_flash()
                self.draw_hud()
                self.draw_game_over()
                self.draw_floor_fade()
            pygame.display.flip()


class _NoKeys:
    def __getitem__(self, key):
        return False


_NO_KEYS = _NoKeys()


def main():
    seed = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else random.randrange(1_000_000)
    Game(seed).run()
    pygame.quit()


if __name__ == "__main__":
    main()

"""Configurações globais do jogo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CHARACTER_SHEET = ASSETS / "personagem" / "Chibi Character Animation Sprite Sheet.png"
TILESET = ASSETS / "background" / "hospital-tiles.png"
ZOMBIE_SHEET = ASSETS / "monster" / "zombie_spritesheet_32x32.png"
ATTACK_SHEET = ASSETS / "personagem" / "atack_spritsheet.png"
DAMAGE_SHEET = ASSETS / "personagem" / "damage.png"   # personagem levando dano (com e sem empurrão)

# Tela / grid
TILE = 32
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

# Zoom da câmera (roda do mouse, contínuo e suave)
ZOOM_MIN = 1.0                  # mais afastado (e zoom inicial)
ZOOM_MAX = 2.0                  # mais aproximado
ZOOM_STEP = 0.1                 # quanto cada "clique" da roda muda o zoom
ZOOM_SMOOTHING = 12             # velocidade da transição (maior = chega mais rápido)

# Mapa (em tiles)
MAP_W, MAP_H = 80, 60

# Cores
COLOR_FLOOR = (60, 170, 80)     # verde: dá para andar (fallback sem tileset)
COLOR_WALL = (90, 90, 90)       # cinza: não dá para andar (fallback sem tileset)
COLOR_WALL_TOP = (35, 40, 42)   # topo das paredes visto de cima
COLOR_DOOR_CLOSED = (120, 80, 40)  # porta fechada (fallback sem tileset)
COLOR_DOOR_OPEN = (50, 35, 20)     # porta aberta (fallback sem tileset)
COLOR_GRID = (0, 0, 0, 40)      # linhas do grid (com transparência)
COLOR_BG = (20, 20, 20)
COLOR_TEXT = (255, 255, 255)

# Variações do tileset (escolhidas pela seed)
FLOOR_BLOOD_CHANCE = 0.08       # chance de um bloco 3x3 de piso ter sangue
WALL_VENT_CHANCE = 0.15         # chance de uma parede ter ventilação

# Sombras e luz
WALL_SHADOW_TOP = 20            # px de sombra no piso logo abaixo de uma parede
WALL_SHADOW_SIDE = 8            # px de sombra no piso ao lado de uma parede
WALL_SHADOW_ALPHA = 150         # intensidade máxima da sombra das paredes (0-255)
PLAYER_SHADOW_ALPHA = 130       # sombra (elipse) sob os pés do personagem
OCCLUDER_ALPHA = 150            # opacidade da porta quando o personagem passa atrás dela
LIGHT_EDGE_ALPHA = 110          # escurecimento na borda do raio de visão (0 = sem queda de luz)
LIGHT_FLICKER = True            # tremulação sutil da luz (lâmpada de hospital)
HUD_PANEL_ALPHA = 150           # opacidade do painel atrás do HUD

# Visão (névoa de guerra)
VISION_RADIUS = 8               # raio de visão em tiles
FOG_EXPLORED_ALPHA = 160        # escurecimento do já descoberto fora da visão (0-255)
COLOR_UNEXPLORED = (0, 0, 0)

# Jogador
PLAYER_SPEED = 150 * 1.3        # pixels por segundo (andando) — 195 px/s
RUN_MULT = 2.0                  # correndo (Shift) anda 2x mais rápido
PLAYER_SPRITE_HEIGHT = 48       # altura do sprite na tela (1.5 tile)
ANIM_FPS = 13                   # frames de animação por segundo (2x correndo)
TURN_DELAY = 0.12               # parado: apertar outra direção só vira; segurando, anda depois disso

# Estamina
STAMINA_MAX = 100
STAMINA_DRAIN = 25              # gasto por segundo correndo (100 -> 0 em 4 s)
STAMINA_REGEN_IDLE = 20         # recuperação por segundo parado
STAMINA_REGEN_WALK = 10         # recuperação por segundo andando normal
STAMINA_RECOVER_TO_RUN = 20     # ao zerar, fica "cansado" até recuperar isso

# Zumbis
ZOMBIE_SIZE = 64                # quadro de 32 px escalado 2x (pixel art nítida; ~ altura do personagem)
ZOMBIES_PER_ROOM = (3, 5)       # mínimo e máximo de zumbis por sala
ZOMBIE_SPEED = 45               # pixels por segundo (bem mais lento que o jogador)
ZOMBIE_IDLE_TIME = (0.0, 0.0)   # segundos parado entre caminhadas (0 = emenda uma caminhada na outra)
ZOMBIE_WANDER_STEPS = (1, 4)    # tiles andados em cada caminhada
ZOMBIE_ANIM_FPS = 6             # animação parado/andando
ZOMBIE_EMERGE_FPS = 8           # animação saindo do chão (8 quadros = 1 s)

# Combate
ATTACK_FPS = 22                 # 9 quadros de ataque ≈ 0,4 s
ATTACK_HIT_FRAME = 5            # quadro em que o golpe acerta (começo do rastro)
ATTACK_DAMAGE = (11, 6, 4)      # dano no impacto, colado no impacto, a 2 tiles do impacto
ATTACK_REACH = 2                # alcance do golpe à frente do personagem (em tiles)
ZOMBIE_HP = 10                  # vida de cada zumbi
ZOMBIE_DEATH_FPS = 14           # zumbi afundando no chão ao morrer (surgir ao contrário)
HIT_FLASH_TIME = 0.12           # segundos piscando ao levar dano
HP_BAR_TIME = 2.0               # segundos mostrando a barra de vida depois de um golpe
DAMAGE_TEXT_TIME = 0.7          # segundos do número de dano flutuando

# Vida do personagem e ataque dos zumbis
PLAYER_HP = 10                  # vida do personagem
ZOMBIE_DAMAGE = 2               # dano de cada golpe de zumbi
ZOMBIE_CHASE_RADIUS = 3         # zumbis a até 3 tiles (Chebyshev) perseguem o personagem
ZOMBIE_CHASE_SPEED = 70         # pixels por segundo perseguindo (vagando: ZOMBIE_SPEED)
ZOMBIE_CHASE_SEARCH = 6         # o caminho é procurado até essa distância além do raio
ZOMBIE_ATTACK_WINDUP = 0.4      # segundos preparando o golpe, colado no personagem
ZOMBIE_ATTACK_COOLDOWN = 1.0    # segundos entre um golpe e o próximo preparo
ZOMBIE_LUNGE = 7                # pixels que o zumbi avança ao dar o golpe (só visual)
KNOCKBACK_TIME = 0.15           # segundos do empurrão de 1 tile ao levar um golpe
ZOMBIE_KNOCKBACK_TIME = 0.15    # segundos do zumbi sendo lançado 1 tile ao levar golpe do personagem
HURT_FPS = 12                   # animação de dano (6 quadros com empurrão = 0,5 s)
PLAYER_INVULN_TIME = 1.0        # segundos invulnerável (piscando) depois do dano
HIT_SCREEN_FLASH = 0.35         # segundos do vermelho nas bordas da tela ao levar golpe
GAME_OVER_TIME = 3.0            # segundos de "GAME OVER" antes de recomeçar a mesma dungeon
